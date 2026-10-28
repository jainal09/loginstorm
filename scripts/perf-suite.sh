#!/usr/bin/env bash
# The performance suite behind the published results. For each budget (CPUs:memory for a whole
# stack, database included), each profile gets three fresh stacks: token introspection at rising
# request rates, the same for userinfo, then logins with no pause between them at rising concurrency.
# Usage: scripts/perf-suite.sh [profiles/x.env ...]    (default: profiles/*.env)
#        BUDGETS="1:1G 2:2G" OUT=results/perf-<date>; STACK_CPUSET / K6_CPUSET as for run-matrix.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
BUDGETS="${BUDGETS:-1:1G 2:2G}"
API_LEVELS="${API_LEVELS:-25 50 100 200 400 800 1600}"
LOGIN_LEVELS="${LOGIN_LEVELS:-1 4 16 32}"
RUN="${OUT:-results/perf-$(date -u +%Y%m%dT%H%M%SZ)}"
profiles=("$@")
[ ${#profiles[@]} -gt 0 ] || profiles=(profiles/*.env)
# Stack and load generator on separate cores (an 8-vCPU host by default).
export STACK_CPUSET="${STACK_CPUSET:-4-7}" K6_CPUSET="${K6_CPUSET:-0-3}"

for budget in $BUDGETS; do
  export STACK_CPUS="${budget%%:*}" STACK_MEM="${budget#*:}"
  dir="$RUN/${STACK_CPUS}cpu-${STACK_MEM}"
  for call in introspect userinfo; do
    OUT="$dir/$call" LEVEL_VAR=RATE LEVELS="$API_LEVELS" DURATION=45s \
      BENCH_ENV="SCENARIO=api API_CALL=$call VUS=50" scripts/run-matrix.sh "${profiles[@]}"
  done
  OUT="$dir/login" LEVELS="$LOGIN_LEVELS" DURATION=40s BENCH_ENV="SCENARIO=login THINK_S=0" \
    scripts/run-matrix.sh "${profiles[@]}"
done
