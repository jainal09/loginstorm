#!/usr/bin/env bash
# Samples a stack's slice, all of its containers together, to CSV every second until killed: total CPU
# time, memory in use without reclaimable page cache (what docker stats reports), and OOM kills so far.
# Usage: collect-cgroup.sh <slice> <out.csv>
set -uo pipefail
dir="/sys/fs/cgroup/authbench.slice/${1:?slice}"; OUT="${2:?out csv}"
[ -f "$OUT" ] || echo 'epoch,cpu_usec,mem_bytes,anon_bytes,file_bytes,oom_kills,pids' > "$OUT"
while true; do
  # The folder only exists while one of the stack's containers runs.
  [ -r "$dir/cpu.stat" ] && awk -v t="$(date +%s.%N)" '
    FILENAME ~ /cpu.stat$/ && $1 == "usage_usec" { cpu = $2 }
    FILENAME ~ /memory.current$/ { cur = $1 }
    FILENAME ~ /memory.stat$/ { s[$1] = $2 }
    FILENAME ~ /memory.events$/ && $1 == "oom_kill" { oom = $2 }
    FILENAME ~ /pids.current$/ { pids = $1 }
    END { printf "%s,%s,%d,%d,%d,%d,%d\n", t, cpu, cur - s["inactive_file"], s["anon"], s["file"], oom, pids }' \
    "$dir/cpu.stat" "$dir/memory.current" "$dir/memory.stat" "$dir/memory.events" "$dir/pids.current" >> "$OUT" 2>/dev/null
  sleep 1
done
