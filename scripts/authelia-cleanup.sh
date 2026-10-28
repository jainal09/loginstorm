#!/usr/bin/env bash
# Deletes Authelia's expired OAuth2 rows on a schedule. Authelia 4.39 keeps every token row it
# issues and looks tokens up by an unindexed column, so token checks slow down as rows pile up
# (https://github.com/authelia/authelia/issues/13038).
# A row goes once it is older than RETENTION_MIN, which must be longer than the longest token
# lifespan configured (Authelia's defaults: access token 1h, refresh token 90m, login code 1m).
# A consent goes once it is that old and no remaining row refers to it.
# Usage: authelia-cleanup.sh <volume> <log.csv> [interval_s] [retention_min]
#        ONCE=1 runs a single pass straight away; CUTOFF='<sql>' overrides the cutoff (tests).
set -uo pipefail
VOLUME="${1:?docker volume holding db.sqlite3}"
LOG="${2:?log csv}"
INTERVAL="${3:-3600}"
RETENTION_MIN="${4:-180}"
IMAGE="${SQLITE_IMAGE:-loginstorm/sqlite:1}"
[[ "$INTERVAL" =~ ^[0-9]+$ && "$RETENTION_MIN" =~ ^[0-9]+$ ]] || { echo "interval and retention must be whole numbers" >&2; exit 2; }
CUTOFF="${CUTOFF:-strftime('%Y-%m-%d %H:%M:%S', 'now', '-$RETENTION_MIN minutes')}"

TABLES='oauth2_access_token_session oauth2_refresh_token_session oauth2_authorization_code_session oauth2_pkce_request_session oauth2_openid_connect_session'
sql=".timeout 30000
CREATE TEMP TABLE cutoff AS SELECT $CUTOFF AS t;
BEGIN IMMEDIATE;"
for t in $TABLES; do
  sql+="
DELETE FROM $t WHERE requested_at < (SELECT t FROM cutoff);
SELECT changes();"
done
refs=''
for t in $TABLES oauth2_device_code_session; do
  refs+="${refs:+ UNION }SELECT challenge_id FROM $t WHERE challenge_id IS NOT NULL"
done
sql+="
DELETE FROM oauth2_consent_session WHERE requested_at < (SELECT t FROM cutoff) AND challenge_id NOT IN ($refs);
SELECT changes();
COMMIT;"

[ -f "$LOG" ] || echo 'epoch,access,refresh,code,pkce,oidc,consent,db_bytes,seconds,error' > "$LOG"
while true; do
  [ -n "${ONCE:-}" ] || sleep "$INTERVAL"
  start=$(date +%s.%N)
  out=$(printf '%s\n' "$sql" | docker run -i --rm -v "$VOLUME:/data" "$IMAGE" \
          sh -c 'sqlite3 -batch /data/db.sqlite3 && stat -c %s /data/db.sqlite3' 2>&1)
  rc=$?
  secs=$(python3 -c "import time; print(round(time.time() - $start, 2))")
  nums=$(grep -E '^[0-9]+$' <<< "$out" | tr '\n' ',' | sed 's/,$//')
  if [ "$rc" -eq 0 ] && [ "$(tr -cd , <<< "$nums" | wc -c)" -eq 6 ]; then
    echo "$(date +%s),$nums,$secs," >> "$LOG"
  else
    echo "$(date +%s),,,,,,,,$secs,$(tr '\n,' '  ' <<< "$out" | cut -c1-200)" >> "$LOG"
  fi
  [ -z "${ONCE:-}" ] || break
done
