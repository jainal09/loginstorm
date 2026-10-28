#!/usr/bin/env bash
# Runs bench.js against a fresh identity provider for each profile and load level,
# collecting container stats, idle footprint, storage, JVM facts (Keycloak) and
# OOM/restart status, then writes report.md.
# Usage: scripts/run-matrix.sh [profiles/x.env ...]   (default: all profiles/*.env)
#
# LEVEL_VAR picks what the levels set: VUS (default), RATE for the api scenario,
# or LOCKOUT_STEPS for the lockout check.
# STACK_CPUS and STACK_MEM (e.g. 1 and 1G) give each stack one budget shared by all of its
# containers, database included (scripts/envelope.sh: Linux with systemd only). STACK_CPUSET and
# K6_CPUSET (e.g. 4-7 and 0-3) keep the stack and the load generator on separate cores.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$PWD"

LEVEL_VAR="${LEVEL_VAR:-VUS}"
LEVELS="${LEVELS:-${VUS_LEVELS:-1 5 15 50}}"
DURATION="${DURATION:-60s}"
IDLE_S="${IDLE_S:-60}"
REST_S="${REST_S:-15}"
BENCH_ENV="${BENCH_ENV:-}"   # extra k6 env, e.g. "SCENARIO=login THINK_S=0"
K6_IMAGE="${K6_IMAGE:-grafana/k6:2.3.0}"
OUT="${OUT:-results/$(date -u +%Y%m%dT%H%M%SZ)}"
profiles=("$@")
[ ${#profiles[@]} -gt 0 ] || profiles=(profiles/*.env)
export COMPOSE_PROJECT_NAME=loginstorm BENCH_NAME=bench
IDP_CONTAINER=bench-idp
k6_cpus=(); [ -z "${K6_CPUSET:-}" ] || k6_cpus=(--cpuset-cpus "$K6_CPUSET")

scripts/gen-secrets.sh
docker image inspect loginstorm/sqlite:1 >/dev/null 2>&1 || docker build -q -t loginstorm/sqlite:1 tools/sqlite >/dev/null
mkdir -p "$OUT"
echo 'profile,level_var,level,start_epoch,end_epoch,k6_exit' > "$OUT/runs.csv"
level_name="$(echo "$LEVEL_VAR" | tr 'A-Z' 'a-z')"

running() { [ "$(docker inspect -f '{{.State.Running}}' "$IDP_CONTAINER" 2>/dev/null)" = true ]; }

for profile in "${profiles[@]}"; do
  name="$(basename "$profile" .env)"
  dir="$OUT/$name"
  mkdir -p "$dir"
  export PROFILE_FILE="$ROOT/$profile"
  # Profiles aren't shell-safe (JAVA_OPTS has spaces), so only STACK and the
  # BENCH_* compose knobs are read here; the whole file goes to the container.
  loaded=()
  while IFS='=' read -r key value; do
    case "$key" in STACK|BENCH_*) export "$key=$value"; loaded+=("$key");; esac
  done < <(grep -E '^[A-Z0-9_]+=' "$PROFILE_FILE")
  stack_keys=($(grep -oE '^[A-Z0-9_]+' "stacks/$STACK/stack.env"))
  set -a; . "stacks/$STACK/stack.env"; set +a
  compose=(docker compose -f "stacks/$STACK/compose.yml" --env-file "$PROFILE_FILE")
  echo "=== $name ($STACK)"

  docker rm -f $CONTAINERS >/dev/null 2>&1 || true
  for v in $VOLUMES; do docker volume rm "$v" >/dev/null 2>&1 || true; done
  [ -n "${PRESTART:-}" ] && eval "$PRESTART"
  collectors=()
  if [ -n "${STACK_CPUS:-}" ] && [ -n "${STACK_MEM:-}" ]; then
    BENCH_SLICE="$(scripts/envelope.sh "matrix-$name" "$STACK_CPUS" "$STACK_MEM" "${STACK_CPUSET:-}")"
    export BENCH_SLICE
    setsid scripts/collect-cgroup.sh "$BENCH_SLICE" "$dir/stats-stack.csv" &
    collectors+=($!)
  fi
  "${compose[@]}" up -d --quiet-pull > "$dir/compose.log" 2>&1 || echo "compose up failed; see $dir/compose.log"
  started=$(date +%s.%N)
  for c in $CONTAINERS; do
    # Own process group, so the whole docker-stats pipeline can be stopped at once.
    setsid scripts/collect-stats.sh "$c" "$dir/stats-${c#bench-}.csv" &
    collectors+=($!)
  done

  ready=false
  for _ in $(seq 1 900); do
    if curl -skf "$READY_URL" >/dev/null 2>&1; then ready=true; break; fi
    running || break
    sleep 1
  done
  startup_s=$(python3 -c "import time; print(round(time.time() - $started, 1))")
  echo "ready=$ready startup=${startup_s}s"

  # PROVISION prints KEY=VALUE lines (CLIENT_ID, CLIENT_SECRET) for k6.
  provisioned=true
  provided_env=()
  if $ready && [ -n "${PROVISION:-}" ]; then
    if out="$($PROVISION 2>"$dir/provision.err")"; then
      while IFS= read -r line; do [ -n "$line" ] && provided_env+=(-e "$line"); done <<< "$out"
    else
      provisioned=false
    fi
    echo "provisioned=$provisioned"
  fi

  if $ready && $provisioned; then
    s=$(date +%s.%N); sleep "$IDLE_S"
    echo "$name,idle,0,$s,$(date +%s.%N),0" >> "$OUT/runs.csv"
    for level in $LEVELS; do
      running || { echo "container stopped; skipping $LEVEL_VAR=$level"; break; }
      s=$(date +%s.%N)
      k6_env=(-e INSECURE_TLS=true -e DURATION="$DURATION" -e SUMMARY_FILE="$dir/$level_name-$level.json")
      for kv in $K6_ENV $BENCH_ENV; do k6_env+=(-e "$kv"); done
      k6_env+=("${provided_env[@]}" -e "$LEVEL_VAR=$level")
      set +e
      docker run --rm "${k6_cpus[@]}" --user "$(id -u):$(id -g)" --network "${COMPOSE_PROJECT_NAME}_default" \
        -v "$ROOT:/bench" -w /bench "${k6_env[@]}" "$K6_IMAGE" run -q bench.js 2>&1 | tee "$dir/$level_name-$level.txt"
      rc=${PIPESTATUS[0]}
      set -e
      # Quoted: LOCKOUT_STEPS levels such as 5,20 contain a comma.
      echo "$name,$level_name,\"$level\",$s,$(date +%s.%N),$rc" >> "$OUT/runs.csv"
      sleep "$REST_S"
    done
    [ -n "${METRICS_URL:-}" ] && { curl -skf "$METRICS_URL" > "$dir/metrics.txt" || true; }
  fi

  docker top "$IDP_CONTAINER" -eo pid,args 2>/dev/null | sed 1d > "$dir/process.txt" || true
  # The IdP comes first in CONTAINERS, so it is the first entry here.
  docker inspect --size $CONTAINERS > "$dir/inspect.json" 2>/dev/null || true
  for c in $CONTAINERS; do docker logs "$c" > "$dir/log-${c#bench-}.txt" 2>&1 || true; done
  : > "$dir/storage.txt"
  for v in $VOLUMES; do
    echo "volume $v $(docker run --rm -v "$v:/v:ro" alpine du -sk /v | cut -f1)" >> "$dir/storage.txt"
  done
  if [ -n "${DB_STATS:-}" ]; then
    ONCE=1 scripts/db-stats.sh "$dir/db.csv" 0 $DB_STATS
    echo "db_bytes $(tail -1 "$dir/db.csv" | cut -d, -f2)" >> "$dir/storage.txt"
  fi
  for img in $IMAGES; do echo "image $img $(docker image inspect -f '{{.Size}}' "$img")" >> "$dir/storage.txt"; done
  python3 - "$dir" "$startup_s" "$ready" "$provisioned" "$STACK" "${STACK_CPUS:-}" "${STACK_MEM:-}" <<'PY'
import csv, json, sys
d, startup, ready, provisioned, stack, stack_cpus, stack_mem = sys.argv[1:8]
meta = {}
try:
    containers = json.load(open(f'{d}/inspect.json'))
    c = containers[0]
    state, host = c['State'], c['HostConfig']
    meta = {'oom_killed': state['OOMKilled'], 'running': state['Running'], 'exit_code': state['ExitCode'],
            'restart_count': c['RestartCount'], 'nano_cpus': host['NanoCpus'], 'memory': host['Memory'],
            'size_rw': c.get('SizeRw'),
            'containers': [{'name': x['Name'].lstrip('/'), 'oom_killed': x['State']['OOMKilled'],
                            'exit_code': x['State']['ExitCode'], 'restart_count': x['RestartCount']}
                           for x in containers]}
except Exception as e:
    meta = {'inspect_error': str(e)}
try:
    rows = list(csv.DictReader(open(f'{d}/stats-stack.csv')))
    # The slice outlives the run, so its counter includes earlier runs. The first sample is taken
    # before compose up, which makes it this run's baseline.
    meta['stack_oom_kills'] = int(rows[-1]['oom_kills']) - int(rows[0]['oom_kills']) if rows else None
except OSError:
    pass
meta.update(stack=stack, startup_s=float(startup), ready=ready == 'true', provisioned=provisioned == 'true',
            stack_cpus=stack_cpus or None, stack_mem=stack_mem or None)
json.dump(meta, open(f'{d}/meta.json', 'w'), indent=2)
PY
  for pid in "${collectors[@]}"; do kill -- -"$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; done
  "${compose[@]}" down -v >/dev/null 2>&1 || true
  unset "${loaded[@]}" "${stack_keys[@]}" BENCH_SLICE
done

python3 scripts/report.py "$OUT" | tee "$OUT/report.md"
