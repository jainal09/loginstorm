#!/usr/bin/env bash
# Logs start, stop, crash and OOM events of the stacks' containers (anything compose started) as JSON
# lines until the given time. A container with a restart policy comes back by itself after a crash; this
# keeps a record of each one (a "die" event carries the exit code, an "oom" event marks a kernel OOM kill).
# Usage: soak-events.sh <out.jsonl> <until, e.g. 2026-11-01T16:00:00Z>
#        SINCE=<time> replays the events Docker still holds from then; lines may repeat, dedupe on timeNano.
# Docker forgets its events when the daemon restarts, so restarts at boot only show in RestartCount.
set -uo pipefail
OUT="${1:?out.jsonl}"; UNTIL="${2:?until}"
filters=(--filter type=container --filter label=com.docker.compose.project)
for e in start die oom kill stop restart; do filters+=(--filter "event=$e"); done
exec docker events --since "${SINCE:-$(date -u +%FT%TZ)}" --until "$UNTIL" "${filters[@]}" --format '{{json .}}' >> "$OUT"
