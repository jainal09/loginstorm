#!/usr/bin/env bash
# Gives a whole stack (IdP, database, sidecars) one shared CPU and memory budget: a systemd slice that
# the stack's containers are nested in through compose's cgroup_parent. Prints the slice's name.
# Needs Linux with systemd, Docker's systemd cgroup driver (the default there) and sudo.
# Usage: envelope.sh <name> <cpus> <memory, e.g. 1G> [cpuset, e.g. 4-7]
set -euo pipefail
NAME="${1:?name}"; CPUS="${2:?cpus}"; MEM="${3:?memory}"; CPUSET="${4:-}"
# A dash in a slice name means nesting (a-b.slice lives inside a.slice), so other dashes become underscores.
slice="loginstorm-${NAME//-/_}.slice"
props=("CPUQuota=$(awk -v c="$CPUS" 'BEGIN { printf "%d", c * 100 }')%" "MemoryMax=$MEM" MemorySwapMax=0)
[ -z "$CPUSET" ] || props+=("AllowedCPUs=$CPUSET")
# Drop what an earlier run set, such as a cpuset this run doesn't want. The new budget is kept across
# reboots, so containers that come back with a restart policy land in the same budget.
sudo systemctl revert "$slice" >/dev/null 2>&1 || true
sudo systemctl set-property "$slice" "${props[@]}"
echo "$slice"
