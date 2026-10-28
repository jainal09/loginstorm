#!/usr/bin/env bash
# Samples a stack's database size (and a row count where it means something) to CSV until killed.
# Usage: db-stats.sh <out.csv> <interval_s> sqlite <volume> <table>
#        db-stats.sh <out.csv> <interval_s> postgres <container> <user> <database> <table>
#        db-stats.sh <out.csv> <interval_s> du <volume>
# ONCE=1 takes a single sample. Reads go through a throwaway container, so the page cache they
# touch is not charged to the service being measured.
set -uo pipefail
OUT="${1:?out csv}"; INTERVAL="${2:?interval}"; MODE="${3:?mode}"; shift 3
IMAGE="${SQLITE_IMAGE:-loginstorm/sqlite:1}"
[ -f "$OUT" ] || echo 'epoch,db_bytes,rows' > "$OUT"
while true; do
  case "$MODE" in
    sqlite)
      row=$(docker run --rm -v "$1:/data" "$IMAGE" sh -c \
        'printf "%s," "$(stat -c %s /data/db.sqlite3)"; sqlite3 -readonly /data/db.sqlite3 "SELECT count(*) FROM $1"' _ "$2" 2>/dev/null) ;;
    postgres)
      row=$(docker exec "$1" psql -U "$2" -d "$3" -Atc \
        "SELECT pg_database_size(current_database()) || ',' || (SELECT count(*) FROM $4)" 2>/dev/null) ;;
    du)
      row=$(docker run --rm -v "$1:/data:ro" "$IMAGE" du -sb /data 2>/dev/null | cut -f1)"," ;;
    *) echo "unknown mode $MODE" >&2; exit 2 ;;
  esac
  echo "$(date +%s),${row:-,}" >> "$OUT"
  [ -z "${ONCE:-}" ] || break
  sleep "$INTERVAL"
done
