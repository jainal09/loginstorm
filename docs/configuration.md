# Configuration

## The k6 script

`bench.js` reads everything from environment variables, so it can be pointed at any OpenID Connect provider, not only the bundled stacks:

```bash
docker run --rm -v "$PWD:/bench" -w /bench \
  -e IDP=keycloak -e ISSUER=https://auth.example.com/realms/test \
  -e CLIENT_ID=load-test -e CLIENT_SECRET=... \
  -e REDIRECT_URI=https://app.example.com/callback \
  -e USERS_FILE=users.csv -e VUS=10 -e DURATION=5m \
  grafana/k6:2.3.0 run bench.js
```

| Variable | Default | Meaning |
|---|---|---|
| `IDP` | `keycloak` | Login adapter: `keycloak`, `authentik`, `authelia`, `zitadel`, `rauthy`, `logto`, `casdoor`, `dex`, `kanidm`, `ory`, `pocket-id` |
| `ISSUER` | `$KC_URL/realms/$REALM` | Issuer URL; endpoints come from its discovery document |
| `CLIENT_ID`, `CLIENT_SECRET` | `bench-client`, empty | Without a secret the client is public, and introspection is skipped |
| `REDIRECT_URI` | `http://bench.invalid/callback` | Must be registered on the client. It is never followed |
| `SCOPE` | `openid`, plus `offline_access` where refresh tokens need it | |
| `USERS_FILE` | empty | CSV with a `username,password` header |
| `USER_PREFIX`, `USER_COUNT`, `USER_PASSWORD`, `USER_DOMAIN` | `bench-user-`, `25`, empty, empty | Without a users file: `bench-user-01` and up, one password. A domain turns the names into email addresses |
| `PASSKEYS_FILE` | empty | One passkey per user, in user order, for passkey-only providers (see `stacks/pocket-id/enroll.js`) |
| `INTROSPECT_URL` | from discovery | For providers that don't advertise one (Ory Hydra's is on its admin API) |
| `SCENARIO` | `session` | `session`, `login`, `api`, `lockout` or `client-credentials` |
| `API_CALL` | `introspect` | What the api scenario calls: `introspect` or `userinfo` |
| `VUS` | `1` | Virtual users; in the api scenario, the number of open sessions |
| `RATE` | `0` | Above 0, iterations per second (open model) instead of a fixed number of looping users |
| `DURATION` | `60s` | Test length |
| `REFRESHES`, `THINK_S` | `2`, `1` | Refreshes per session and the pause between steps |
| `LOGOUT` | `true` | `false` leaves sessions open, the way idle users do |
| `LOCKOUT_STEPS` | `5,20` | Wrong-password streaks for the lockout scenario, one account each |
| `CHECKS_THRESHOLD` | `rate>0.99` | The pass rate below which k6 exits with code 99 |
| `SUMMARY_FILE` | empty | Also write the full summary as JSON |
| `INSECURE_TLS` | `false` | Accept self-signed certificates |
| `CASDOOR_APPLICATION`, `CASDOOR_ORGANIZATION` | `bench` | The Casdoor application and organization of the users |
| `KC_URL`, `REALM` | `http://localhost:8080`, `bench` | Shorthand for a Keycloak issuer |

Only use test users against shared environments. The bench logs in for real: it creates sessions, events and failed-login counts, and the lockout scenario locks accounts on purpose.

## Profiles

A profile (`profiles/*.env`) is an env file that picks a stack and, optionally, changes it:

```ini
# Authelia with a plaintext client secret instead of the recommended hashed one.
STACK=authelia
BENCH_AUTHELIA_USERS=default
BENCH_AUTHELIA_CONFIG=configuration-plaintext-secret
```

| Key | Meaning |
|---|---|
| `STACK` | A folder under `stacks/` |
| `BENCH_*` | Stack variants used by its compose file, such as `BENCH_KC_IMAGE` or `BENCH_AUTHELIA_CONFIG` |
| `LIMIT_CPUS`, `LIMIT_MEM` | Limits on the identity provider's container alone (`0` means none); overrides the stack budget for that container |
| `RES_CPUS`, `RES_MEM` | Reservations (Keycloak) |
| `BENCH_CLEANUP_INTERVAL`, `BENCH_CLEANUP_RETENTION_MIN` | Soaks only: run Authelia's expired-token cleanup on this schedule |
| anything else | Passed to the provider's container as is, so `KC_*`, `ZITADEL_*`, `POW_DIFFICULTY` and the like work as usual |

Profiles aren't sourced by a shell, so values may contain spaces (`JAVA_OPTS=...`).

## The runners

### `scripts/run-matrix.sh [profiles...]`

Runs every given profile (default: `profiles/*.env`) on a fresh stack at each load level.

| Variable | Default | Meaning |
|---|---|---|
| `LEVEL_VAR` | `VUS` | What the levels set: `VUS`, `RATE` or `LOCKOUT_STEPS` |
| `LEVELS` | `1 5 15 50` | The levels, space-separated |
| `DURATION` | `60s` | Length of each level |
| `IDLE_S`, `REST_S` | `60`, `15` | Idle measurement before the first level, pause between levels |
| `BENCH_ENV` | empty | Extra variables for k6, such as `SCENARIO=login THINK_S=0` |
| `STACK_CPUS`, `STACK_MEM` | none | Budget for the whole stack, for example `1` and `1G` |
| `STACK_CPUSET`, `K6_CPUSET` | none | Cores for the stack and for k6, for example `4-7` and `0-3` |
| `K6_IMAGE` | `grafana/k6:2.3.0` | |
| `OUT` | `results/<UTC timestamp>` | Output folder |

### `scripts/perf-suite.sh [profiles...]`

The published suite: introspection, userinfo and logins, for each budget.

| Variable | Default |
|---|---|
| `BUDGETS` | `1:1G 2:2G` |
| `API_LEVELS` | `25 50 100 200 400 800 1600` |
| `LOGIN_LEVELS` | `1 4 16 32` |
| `STACK_CPUSET`, `K6_CPUSET` | `4-7`, `0-3` |
| `OUT` | `results/perf-<UTC timestamp>` |

### `scripts/soak.sh <profiles...>`

Covered in [Soak testing](soak-testing.md).

| Variable | Default | Meaning |
|---|---|---|
| `END_AT` or `HOURS` | `HOURS=60` | When to stop |
| `CHUNK` | `1h` | Length of each k6 run |
| `API_CALL`, `API_RATE`, `API_VUS` | `introspect`, `10`, `25` | Token checks per stack |
| `LOGIN_VUS` | `2` | Users cycling through logins per stack |
| `DB_STATS_EVERY` | `3600` | Seconds between database samples |
| `STACK_CPUS`, `STACK_MEM`, `STACK_CPUSET`, `K6_CPUSET` | none | As for the matrix |
| `RESUME`, `OUT` | empty | Continue an interrupted run in `OUT` |

## Generated secrets

`scripts/gen-secrets.sh` runs at the start of every runner and creates what's missing:

- the TLS certificate in `tls/`
- per-stack keys and secrets in `stacks/<name>/secrets/`: Authelia's JWKS key, Zitadel's master key, Rauthy's encryption keys and bootstrap API key, Pocket ID's static API key, and Ory's cookie and cipher secrets

Both folders are ignored by git. Delete them to regenerate. A stack's existing data volume won't open with new keys, but the runners always start from fresh volumes.
