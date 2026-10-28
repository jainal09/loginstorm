#!/usr/bin/env bash
# Streams docker stats for one container to CSV until killed.
# Usage: collect-stats.sh <container> <out.csv>
set -uo pipefail
CONTAINER="${1:?container}"
OUT="${2:?output csv}"
# Appends to an existing file, so a resumed soak keeps one continuous record.
[ -f "$OUT" ] || echo 'epoch,cpu_percent,mem_used,mem_limit,pids' > "$OUT"
# Streaming mode prints a sample every 0.5 to 1 s, depending on the Docker version; strip the screen-clear
# codes it emits. The stream ends when the Docker daemon restarts, so it starts again after a pause.
while true; do
  docker stats --format '{{.CPUPerc}},{{.MemUsage}},{{.PIDs}}' "$CONTAINER" 2>/dev/null \
    | sed -u 's/\x1b\[[0-9;]*[A-Za-z]//g' \
    | while IFS= read -r line; do
        [ -n "$line" ] && printf '%s,%s\n' "$(date +%s.%N)" "${line/ \/ /,}"
      done >> "$OUT"
  sleep 5
done
