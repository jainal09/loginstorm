#!/usr/bin/env bash
# Long soak: runs several identity providers side by side, each in its own
# isolated stack (own containers, ports and network) with its own day-to-day load:
# token introspection over open sessions plus a trickle of logins whose sessions
# are left to expire. Load runs in k6 chunks (hourly by default) until END_AT, so
# latency can be tracked over time; container stats are sampled every 0.5 to 1 s,
# and database sizes hourly. Profiles that set BENCH_CLEANUP_INTERVAL get Authelia's
# expired-token cleanup (scripts/authelia-cleanup.sh) on that schedule.
# Containers restart after a crash the way production ones would; scripts/soak-events.sh
# keeps a record of every crash and OOM kill in events.jsonl.
# Usage: END_AT=2026-11-01T14:00:00Z scripts/soak.sh profiles/keycloak.env profiles/authelia.env ...
#        HOURS=60 instead of END_AT runs that long from now.
#        STACK_CPUS / STACK_MEM / STACK_CPUSET / K6_CPUSET as for run-matrix.sh: one budget per stack.
# After an interruption (reboot, closed terminal), continue the same run with the same arguments plus
#        RESUME=1 OUT=results/<that run>
# Stacks are stopped, not removed, at the end; their volumes stay for inspection.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$PWD"

if [ -n "${END_AT:-}" ]; then END_EPOCH=$(date -d "$END_AT" +%s) || exit 2
else END_EPOCH=$(( $(date +%s) + ${HOURS:-60} * 3600 )); fi
CHUNK="${CHUNK:-1h}"            # length of each k6 chunk
API_RATE="${API_RATE:-10}"      # introspections per second, per stack
API_VUS="${API_VUS:-25}"        # open sessions, per stack
API_CALL="${API_CALL:-introspect}"
LOGIN_VUS="${LOGIN_VUS:-2}"     # users cycling through logins, per stack
DB_STATS_EVERY="${DB_STATS_EVERY:-3600}"
K6_IMAGE="${K6_IMAGE:-grafana/k6:2.3.0}"
RESUME="${RESUME:-}"
[ -z "$RESUME" ] || [ -n "${OUT:-}" ] || { echo "RESUME needs OUT=results/<the run to continue>" >&2; exit 2; }
OUT="${OUT:-results/soak-$(date -u +%Y%m%dT%H%M%SZ)}"
[ $# -gt 0 ] || { echo "usage: END_AT=2026-11-01T14:00:00Z $0 profiles/x.env ..." >&2; exit 2; }
k6_cpus=""; [ -z "${K6_CPUSET:-}" ] || k6_cpus="--cpuset-cpus=$K6_CPUSET"

scripts/gen-secrets.sh
docker image inspect authbench/sqlite:1 >/dev/null 2>&1 || docker build -q -t authbench/sqlite:1 tools/sqlite >/dev/null
mkdir -p "$OUT"
if [ -n "$RESUME" ]; then
  echo "resumed $(date -u +%FT%TZ) until $(date -u -d "@$END_EPOCH" +%FT%TZ)" >> "$OUT/soak.log"
else
  echo "started $(date -u +%FT%TZ) until $(date -u -d "@$END_EPOCH" +%FT%TZ) chunk=$CHUNK api_call=$API_CALL api_rate=$API_RATE api_vus=$API_VUS login_vus=$LOGIN_VUS stack_cpus=${STACK_CPUS:-} stack_mem=${STACK_MEM:-}" > "$OUT/soak.log"
fi

profile_value() { grep -E "^$2=" "$1" | head -1 | cut -d= -f2-; }
# Stops the process groups recorded in a pid file, so a resumed run never doubles them up.
stop_groups() { [ -f "$1" ] && while read -r pid; do kill -- -"$pid" 2>/dev/null; done < "$1"; rm -f "$1"; }
running() { [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = true ]; }

# One crash and OOM log for the whole run; a resumed run replays what Docker still holds since the start.
stop_groups "$OUT/events.pid"
SINCE="$(head -1 "$OUT/soak.log" | awk '{print $2}')" setsid scripts/soak-events.sh "$OUT/events.jsonl" \
  "$(date -u -d "@$((END_EPOCH + 7200))" +%FT%TZ)" 2>>"$OUT/events.err" &
echo $! > "$OUT/events.pid"

pids=()
i=0
for profile in "$@"; do
  i=$((i + 1))
  name="$(basename "$profile" .env)"
  dir="$OUT/$name"; mkdir -p "$dir"
  export PROFILE_FILE="$ROOT/$profile"
  # An isolated copy of the stack: its own project, container names, host ports and budget.
  export COMPOSE_PROJECT_NAME="soak-$name" BENCH_NAME="soak-$name" BENCH_RESTART=unless-stopped
  export BENCH_PORT=$((28500 + i * 10 + 1)) BENCH_PORT2=$((28500 + i * 10 + 2)) BENCH_PORT3=$((28500 + i * 10 + 3))
  idp="$BENCH_NAME-idp"
  # The profile's STACK and BENCH_* knobs feed compose interpolation; the whole file goes to the container.
  loaded=()
  while IFS='=' read -r key value; do
    case "$key" in STACK|BENCH_*) export "$key=$value"; loaded+=("$key");; esac
  done < <(grep -E '^[A-Z0-9_]+=' "$profile")
  stack_keys=($(grep -oE '^[A-Z0-9_]+' "stacks/$STACK/stack.env"))
  set -a; . "stacks/$STACK/stack.env"; set +a
  compose=(docker compose -f "stacks/$STACK/compose.yml" --env-file "$PROFILE_FILE")
  export BENCH_SLICE=""
  if [ -n "${STACK_CPUS:-}" ] && [ -n "${STACK_MEM:-}" ]; then
    # Changing a running stack's budget would skew its results, so a resumed run keeps the one it has.
    if [ -z "$RESUME" ]; then BENCH_SLICE="$(scripts/envelope.sh "soak-$name" "$STACK_CPUS" "$STACK_MEM" "${STACK_CPUSET:-}")"
    else BENCH_SLICE="authbench-soak_${name//-/_}.slice"; fi
  fi

  if [ -z "$RESUME" ]; then
    [ -n "${PRESTART:-}" ] && eval "$PRESTART"
    "${compose[@]}" up -d --quiet-pull > "$dir/compose.log" 2>&1 || echo "$name: compose up failed; see $dir/compose.log"
  else
    # Containers keep their data across a restart; one that the kernel OOM-killed stays down, since that is a result.
    for c in $CONTAINERS; do
      docker inspect "$c" >/dev/null 2>&1 || continue
      if ! running "$c"; then
        if [ "$(docker inspect -f '{{.State.OOMKilled}}' "$c")" = true ]; then
          echo "$name: $c was OOM-killed; not restarting it" | tee -a "$OUT/soak.log"
        else
          docker start "$c" >/dev/null
        fi
      fi
    done
  fi

  stop_groups "$dir/collectors.pid"
  for c in $CONTAINERS; do
    setsid scripts/collect-stats.sh "$c" "$dir/stats-${c#"$BENCH_NAME"-}.csv" &
    echo $! >> "$dir/collectors.pid"
  done
  if [ -n "$BENCH_SLICE" ]; then
    setsid scripts/collect-cgroup.sh "$BENCH_SLICE" "$dir/stats-stack.csv" &
    echo $! >> "$dir/collectors.pid"
  fi

  ready=false
  for _ in $(seq 1 900); do
    curl -skf "$READY_URL" >/dev/null 2>&1 && { ready=true; break; }
    running "$idp" || break
    sleep 1
  done
  if [ -z "$RESUME" ]; then
    : > "$dir/provided.env"
    if $ready && [ -n "${PROVISION:-}" ]; then
      $PROVISION 2>"$dir/provision.err" > "$dir/provided.env" || ready=false
    fi
  fi
  provided="$(tr '\n' ' ' < "$dir/provided.env" 2>/dev/null)"
  echo "$name stack=$STACK ready=$ready port=$BENCH_PORT $(date -u +%FT%TZ)" | tee -a "$OUT/soak.log"
  if $ready; then
    stop_groups "$dir/loops.pid"
    if [ -n "${DB_STATS:-}" ]; then
      echo "$DB_STATS" > "$dir/db-stats.args"
      setsid scripts/db-stats.sh "$dir/db.csv" "$DB_STATS_EVERY" $DB_STATS &
      echo $! >> "$dir/loops.pid"
    fi
    cleanup_every="$(profile_value "$profile" BENCH_CLEANUP_INTERVAL)"
    if [ -n "$cleanup_every" ] && [ -n "${CLEANUP_VOLUME:-}" ]; then
      setsid scripts/authelia-cleanup.sh "$CLEANUP_VOLUME" "$dir/cleanup.csv" "$cleanup_every" \
        "$(profile_value "$profile" BENCH_CLEANUP_RETENTION_MIN)" &
      echo $! >> "$dir/loops.pid"
    fi

    # Chunks are numbered across resumes; an interrupted chunk is not repeated.
    last=$(grep -oE 'chunk [0-9]+ start' "$dir/load.log" 2>/dev/null | awk '{print $2}' | sort -n | tail -1)
    next=$(( 10#${last:-0} + 1 ))

    # The load loop for this stack, in its own process group. k6 containers carry a label, so ones left
    # running by an interrupted run are removed instead of doubling the load.
    stop_groups "$dir/load.pid"
    docker ps -q --filter "label=authbench.k6=$idp" | xargs -r docker rm -f >/dev/null
    setsid bash -c '
      dir=$1; net=$2; idp=$3; next=$4; end=$5; chunk=$6; image=$7; root=$8; cpus=$9; shift 9; env_list=("$@")
      # k6 sees the repository at /bench, so its summary paths stay relative.
      abs="$root/$dir"
      k6_args=($cpus); for kv in "${env_list[@]}"; do k6_args+=(-e "$kv"); done
      while [ "$(date +%s)" -lt "$end" ]; do
        h=$(printf %03d "$next")
        # With a restart policy a crashed IdP comes back by itself; only a stack that stays down ends the loop.
        if [ "$(docker inspect -f "{{.State.Running}}" "$idp" 2>/dev/null)" != true ]; then
          sleep 60
          [ "$(docker inspect -f "{{.State.Running}}" "$idp" 2>/dev/null)" = true ] || { echo "$(date -u +%FT%TZ) $idp not running; stopping" >> "$abs/load.log"; break; }
        fi
        echo "$(date -u +%FT%TZ) chunk $h start" >> "$abs/load.log"
        docker run --rm --label "authbench.k6=$idp" --user "$(id -u):$(id -g)" --network "$net" -v "$root:/bench" -w /bench "${k6_args[@]}" \
          -e INSECURE_TLS=true -e SCENARIO=api -e API_CALL='"$API_CALL"' -e VUS='"$API_VUS"' -e RATE='"$API_RATE"' \
          -e DURATION="$chunk" -e SUMMARY_FILE="$dir/api-$h.json" "$image" run -q bench.js > "$abs/api-$h.txt" 2>&1 &
        api=$!
        docker run --rm --label "authbench.k6=$idp" --user "$(id -u):$(id -g)" --network "$net" -v "$root:/bench" -w /bench "${k6_args[@]}" \
          -e INSECURE_TLS=true -e SCENARIO=session -e VUS='"$LOGIN_VUS"' -e THINK_S=60 -e REFRESHES=2 -e LOGOUT=false \
          -e CHECKS_THRESHOLD="rate>0" -e DURATION="$chunk" -e SUMMARY_FILE="$dir/logins-$h.json" "$image" run -q bench.js > "$abs/logins-$h.txt" 2>&1 &
        logins=$!
        wait $api $logins
        echo "$(date -u +%FT%TZ) chunk $h done" >> "$abs/load.log"
        next=$((next + 1))
      done
    ' _ "$dir" "${COMPOSE_PROJECT_NAME}_default" "$idp" "$next" "$END_EPOCH" "$CHUNK" "$K6_IMAGE" "$ROOT" "$k6_cpus" $K6_ENV $provided &
    pids+=($!)
    echo $! > "$dir/load.pid"
  fi
  echo "${CONTAINERS}" > "$dir/containers.txt"
  unset "${loaded[@]}" "${stack_keys[@]}"
done

# Wait only on the load loops; the collectors and samplers run until the wrap-up stops them.
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"

# Wrap up: a last database sample and the final state of every stack, then stop everything but keep the data.
for profile in "$@"; do
  name="$(basename "$profile" .env)"; dir="$OUT/$name"
  stack="$(profile_value "$profile" STACK)"
  stop_groups "$dir/loops.pid"
  if [ -f "$dir/db-stats.args" ]; then
    ONCE=1 scripts/db-stats.sh "$dir/db.csv" 0 $(cat "$dir/db-stats.args")
  fi
  containers="$(cat "$dir/containers.txt" 2>/dev/null)"
  docker inspect $containers > "$dir/inspect.json" 2>/dev/null
  for c in $containers; do docker logs "$c" > "$dir/log-${c#soak-"$name"-}.txt" 2>&1; done
  stop_groups "$dir/collectors.pid"
  COMPOSE_PROJECT_NAME="soak-$name" PROFILE_FILE="$ROOT/$profile" \
    docker compose -f "stacks/$stack/compose.yml" --env-file "$ROOT/$profile" stop >/dev/null 2>&1
done
stop_groups "$OUT/events.pid"
echo "finished $(date -u +%FT%TZ)" >> "$OUT/soak.log"
