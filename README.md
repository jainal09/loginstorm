# authbench

A load bench for open-source OpenID Connect identity providers, built on [k6](https://k6.io), with disposable stacks for 13 of them. It makes the same HTTP calls a browser and an app backend make during an Authorization Code + PKCE login, then uses the session the way an app would: token checks, refreshes, logout. No browsers are needed, so one load generator can drive far more users than a Playwright test.

Every stack can get one CPU and memory budget for all of its containers, database included, so a provider that needs Postgres and a worker is measured in the same box as one that is a single binary.

## Providers

| Stack | What runs | Login | Test users |
|---|---|---|---|
| `keycloak` | Keycloak 26.8.1 (pre-built image) + Postgres 17 | login form | `bench-user-01..50` / `bench-password` |
| `authentik` | authentik 2026.8.5 server + worker + Postgres 17 | flow executor API | `bench-user-01..50` / `bench-password` |
| `authelia` | Authelia 4.39.28, users file, SQLite | first-factor API + consent | `bench-user-01..50` / `bench-password` |
| `authelia-lldap` | Authelia 4.39.28 with LLDAP 0.6.3 as its user directory | first-factor API + consent | `bench-user-01..50` / `bench-password` |
| `zitadel` | Zitadel v4.20.0 + Postgres 17, built-in login UI | login-name and password forms | `bench-user-01..50` / `Bench-Password-1!` |
| `rauthy` | Rauthy 0.37.2, embedded Hiqlite | proof-of-work + JSON login | `bench-user-01..50@bench.test` / `bench-Password-123` |
| `logto` | Logto 1.45.0 + Postgres 17 | Experience API | `bench_user_01..50` / `bench-password` |
| `casdoor` | Casdoor v4.24.0 + Postgres 17 | `/api/login` | `bench-user-01..50` / `bench-password` |
| `dex` | Dex v2.46.1 + Postgres 17, local password database | login form | `bench-user-01..50@bench.test` / `bench-password` |
| `kanidm` | Kanidm 1.11.2, embedded database | username, password and consent forms | `bench-user-01..50` / `Bench-Quartz-Meadow-59-Lantern` |
| `ory` | Ory Hydra + Kratos v26.2.0, Ory's reference login UI (Node.js), Postgres 17 | Kratos login form through the UI | `bench-user-01..50@bench.test` / `bench-password` |
| `pocket-id` | Pocket ID v2.19.1, SQLite | passkey (a software authenticator) | `bench-user-01..50`, one passkey each |

Each stack runs the provider's documented defaults, including password hashing, token formats, signing algorithms and log levels. The exceptions are what a test can't run without, or a default that would measure the load generator instead of the provider:

- **Authelia:** the per-IP limit on the token and revocation endpoints (30 requests a minute) is raised. An app backend sends every user's code exchanges and refreshes from one IP, and so does the load generator. `authelia-plaintext-secret` is a second profile without the hashed client secret Authelia recommends (see the notes below).
- **Kanidm:** test users may log in with a password alone. Kanidm requires MFA for everyone by default.
- **Pocket ID:** per-IP rate limiting is off. It allows 100 API calls a second and one passkey login every 5 seconds per address, and the load generator is one address.
- **Rauthy:** the login proof-of-work drops from 19 to 10 bits, because solving it is client work. The bench client's access tokens last 60 s, because Rauthy only accepts a refresh in the last 60 s of a token's life.
- **Logto:** the client always gets refresh tokens, instead of only after a consent prompt.
- **TLS everywhere**, with one self-signed `*.bench.test` certificate, because Authelia and Rauthy only issue Secure cookies. Hydra, Kanidm and Pocket ID only accept `https` redirect URIs, so their clients use `https://bench.invalid/callback`. The redirect is never followed.

Test users, passwords, client secrets and keys are throwaway values for local test stacks. `scripts/gen-secrets.sh` generates the keys and secrets on first use into `tls/` and `stacks/*/secrets/` (both ignored by git).

## What one iteration does

Endpoints come from OIDC discovery (`$ISSUER/.well-known/openid-configuration`). Only the login is provider-specific.

| Step | Call | Metric |
|---|---|---|
| Login page | `GET` authorization endpoint (PKCE S256) | `idp_login_page` |
| Credential check | the request that checks the password or passkey (each adapter in `bench.js` says which) | `idp_login_submit` |
| Other login hops | consent, redirects, flow steps, proof-of-work challenge | `idp_login_extra` |
| Code exchange | `POST` token endpoint, `grant_type=authorization_code` | `idp_code_exchange` |
| Whole login | everything above, wall clock, minus client-side work | `idp_login_total` |
| Client-side work | Rauthy's proof-of-work, Pocket ID's passkey signature | `idp_client_work` |
| User info | `GET` userinfo endpoint | `idp_userinfo` |
| Refresh | `POST` token endpoint, `grant_type=refresh_token`, `REFRESHES` times | `idp_refresh` |
| Introspect | `POST` introspection endpoint (only with `CLIENT_SECRET`) | `idp_introspect` |
| Logout | Keycloak: back-channel `POST` to `end_session_endpoint`. Others: revoke the refresh token; skipped where there is no revocation endpoint (Dex, Pocket ID) | `idp_logout` |

Scenarios (`SCENARIO`):

- `session` (default): everything above, with `THINK_S` seconds between refreshes.
- `login`: login and logout only. Use `THINK_S=0` to stress password hashing.
- `api`: token checks the way an API backend makes them when it doesn't validate JWTs itself. `VUS` sessions are opened before the clock starts, each login on its own cookie jar. Then `RATE` calls per second of `API_CALL` (`introspect` or `userinfo`) run over them, refreshing tokens before they expire. Calls the sessions can't keep up with count as `dropped_iterations`.
- `lockout`: checks the lockout policy on throwaway test accounts. For each streak in `LOCKOUT_STEPS` (default `5,20`) it logs in correctly, sends that many wrong passwords, and tries the right one again. Then it tries an untouched account from the same client. Each attempt is its own iteration, so no SSO cookie carries over. **Only for disposable test stacks.**
- `client-credentials`: service-to-service tokens, no users.

The run fails (exit code 99) if more than 1% of checks fail. Change that with `CHECKS_THRESHOLD`, e.g. `rate>0.95`.

## Run it against any provider

```bash
docker run --rm -v "$PWD:/bench" -w /bench \
  -e IDP=keycloak -e ISSUER=https://auth.test.example.com/realms/myrealm \
  -e CLIENT_ID=my-client -e CLIENT_SECRET=... \
  -e REDIRECT_URI=https://app.test.example.com/callback \
  -e USERS_FILE=users.csv -e VUS=10 -e DURATION=5m \
  grafana/k6:2.3.0 run bench.js
```

| Variable | Default | Meaning |
|---|---|---|
| `IDP` | `keycloak` | Picks the login adapter: `keycloak`, `authentik`, `authelia`, `zitadel`, `rauthy`, `logto`, `casdoor`, `dex`, `kanidm`, `ory` or `pocket-id` |
| `ISSUER` | `$KC_URL/realms/$REALM` | The provider's issuer URL |
| `CLIENT_ID` / `CLIENT_SECRET` | `bench-client` / empty | Leave the secret empty for a public client (no introspection then) |
| `REDIRECT_URI` | `http://bench.invalid/callback` | Must be registered on the client; it is never followed |
| `SCOPE` | `openid`, plus `offline_access` where refresh tokens need it (Authelia also asks for `groups`) | |
| `USERS_FILE` | empty | CSV with a `username,password` header |
| `USER_PREFIX`, `USER_COUNT`, `USER_PASSWORD`, `USER_DOMAIN` | `bench-user-`, `25`, empty, empty | Used without `USERS_FILE`: `bench-user-01` and up, one shared password. `USER_DOMAIN` turns them into emails |
| `PASSKEYS_FILE` | empty | Passkeys for passkey-only providers, one per user in user order (written by `stacks/pocket-id/enroll.js`) |
| `INTROSPECT_URL` | from discovery | For providers that don't list it (Ory Hydra's is on its admin API) |
| `SCENARIO` | `session` | `session`, `login`, `api`, `lockout` or `client-credentials` |
| `API_CALL` | `introspect` | What the `api` scenario calls: `introspect` or `userinfo` |
| `LOCKOUT_STEPS` | `5,20` | Wrong-password streaks for the `lockout` scenario, one test account each |
| `VUS` | `1` | Concurrent virtual users (closed model) |
| `RATE` | `0` | When > 0, start this many iterations per second instead (open model) |
| `DURATION` | `60s` | Test length |
| `REFRESHES` / `THINK_S` | `2` / `1` | Refreshes per session, pause between steps |
| `LOGOUT` | `true` | End each session; `false` lets sessions pile up the way idle users do |
| `SUMMARY_FILE` | empty | Also write the full k6 summary as JSON here |
| `INSECURE_TLS` | `false` | Skip TLS verification for self-signed test servers |
| `CASDOOR_APPLICATION`, `CASDOOR_ORGANIZATION` | `bench` | The Casdoor application and organization the users belong to |
| `KC_URL`, `REALM` | `http://localhost:8080`, `bench` | Shorthand for a Keycloak `ISSUER` |

Before pointing it at a shared environment:

- **Only use test users and a test realm.** The bench logs in for real, which creates sessions, events and failed-login counts.
- **Brute-force protection can lock users out** if credentials are wrong. Run one user (`VUS=1 DURATION=10s`) first.
- **Users are picked by index.** VU 1 always uses the first user, so with more VUs than users, one user holds several sessions.

## Compare providers locally

Needs Docker with Compose, Python 3 and OpenSSL. For per-stack budgets you also need Linux with systemd, Docker's systemd cgroup driver (the default there) and sudo. `infra/azure/up.sh` creates such a host on Azure.

`scripts/run-matrix.sh` starts a fresh stack for each profile in `profiles/`. For each one it:

- waits until the provider is ready, then provisions users and clients
- records the idle footprint
- runs the bench at each load level
- writes `report.md` when all profiles are done

It records:

- per-container CPU and memory every 0.5 to 1 s (`docker stats`)
- the whole stack's CPU, memory and OOM kills every second, when it has a budget
- startup time, image sizes, data-volume and database sizes
- the process command line, and Keycloak's garbage-collector stats
- each container's exit code, restarts and OOM kills, and its log

```bash
scripts/run-matrix.sh                                   # every profile, 1/5/15/50 VUs, 60s each
STACK_CPUS=1 STACK_MEM=1G STACK_CPUSET=4-7 K6_CPUSET=0-3 scripts/run-matrix.sh profiles/keycloak.env profiles/kanidm.env
LEVELS="1 4 16 32" DURATION=40s BENCH_ENV="SCENARIO=login THINK_S=0" scripts/run-matrix.sh
LEVEL_VAR=RATE LEVELS="50 200 800" DURATION=45s BENCH_ENV="SCENARIO=api VUS=50" scripts/run-matrix.sh
LEVEL_VAR=LOCKOUT_STEPS LEVELS="5,20" BENCH_ENV="SCENARIO=lockout" scripts/run-matrix.sh profiles/authelia.env
python3 scripts/report.py results/<run-folder>          # rebuild a report
```

- **`STACK_CPUS` and `STACK_MEM`** (e.g. `1` and `1G`) put all of a stack's containers in one systemd slice with that CPU quota and memory limit (`scripts/envelope.sh`). Each container also gets the budget as its own limit, so the JVM, Node.js and Go size themselves as they would on a VM of that size.
- **`STACK_CPUSET` and `K6_CPUSET`** pin the stack and the load generator to separate cores, so k6 doesn't compete with the provider.

`scripts/perf-suite.sh` is the suite behind the published comparison. For each budget (`BUDGETS`, default `1:1G 2:2G`), each profile gets three fresh stacks: introspection at rising request rates, then userinfo, then logins with no pause between them at rising concurrency.

A profile is an env file:

- `STACK` picks the stack.
- `BENCH_*` lines choose stack variants, such as Keycloak's image or Authelia's config.
- `LIMIT_CPUS`, `LIMIT_MEM`, `RES_CPUS` and `RES_MEM` set limits on the identity provider's container alone (`0` means none).
- Every line also goes into the provider's container, so its own settings (`KC_*`, `ZITADEL_*`, `POW_DIFFICULTY`, ...) work as usual.

`profiles/small-host/` holds variants from a study of hosts with 0.5 CPU and 512 MiB per provider: Keycloak squeezed into 512 MiB, hashing matched to Keycloak's default, and Authelia with a scheduled token cleanup.

## Long soaks

`scripts/soak.sh` runs several profiles side by side for days, each in its own stack with its own ports and budget. The day-to-day load is 10 introspections/s over 25 sessions, plus 2 users logging in about every 3 minutes whose sessions are left to expire. It runs in hourly k6 chunks, so latency can be tracked over time. It samples stats as `run-matrix.sh` does, plus each database's size hourly (`db.csv`).

The containers get a restart policy, the way production ones would. `scripts/soak-events.sh` logs every start, exit code and OOM kill to `events.jsonl`. Profiles that set `BENCH_CLEANUP_INTERVAL` (seconds) and `BENCH_CLEANUP_RETENTION_MIN` get `scripts/authelia-cleanup.sh`, which deletes Authelia's expired OAuth2 rows on that schedule (Authelia 4.39 never deletes them).

```bash
END_AT=2026-11-08T12:00:00Z STACK_CPUS=2 STACK_MEM=2G OUT=results/soak-1 scripts/soak.sh profiles/keycloak.env profiles/kanidm.env ...
python3 scripts/soak-status.py results/soak-1          # one-screen health check
# After a reboot or a closed terminal, continue the same run (same profiles, same END_AT):
RESUME=1 END_AT=2026-11-08T12:00:00Z STACK_CPUS=2 STACK_MEM=2G OUT=results/soak-1 scripts/soak.sh <same profiles>
```

A resumed run:

- restarts stopped containers, but not ones the kernel OOM-killed
- removes k6 containers left over from the interrupted chunk
- carries on numbering chunks

At the end the stacks are stopped, not removed, so their volumes can still be inspected. **Don't edit the scripts while a soak runs:** bash reads them as it goes.

## Provider notes

Things the stacks encode, and things worth knowing before choosing one of these.

**Keycloak**

- **A stock image re-runs its build step on every `start`.** The stack builds a pre-built image (`kc.sh build`, then `start --optimized`), as Keycloak's docs recommend.
- **`kc.sh` reads `JAVA_OPTS`, `JAVA_OPTS_KC_HEAP` and `JAVA_OPTS_APPEND`.** There is no `KC_JVM_ARGUMENTS`, and any unknown `KC_*` variable is dropped without a warning.
- **Appending `-XX:+UseSerialGC` stops the JVM from starting** ("Multiple garbage collectors selected"), because the default `JAVA_OPTS` already has `-XX:+UseG1GC`. Replace `JAVA_OPTS` whole instead.
- **A client can only introspect tokens that list it in `aud`.** The realm adds an audience mapper.

**authentik**

- **The first start runs hundreds of database migrations**, about 1.5 minutes on 2 vCPUs.
- **An OAuth2 provider created through the API allows no grant types** until `grant_types` is set ("Invalid grant_type for provider").
- **The login page is a single-page app driving the flow executor API**: one JSON challenge per stage. Each answer redirects back to the executor, which then serves the next challenge.
- **Without a signing key, tokens are HS256**. The bench picks the self-signed RSA key, as the admin UI does.

**Authelia**

- **The token endpoint allows 30 requests a minute per IP by default.** One busy app backend can hit that.
- **A hashed client secret (pbkdf2-sha512, 310,000 rounds, as the docs recommend) costs one hash on every client authentication**, introspection included. `authelia-plaintext-secret` shows the difference.
- **It pads first-factor responses with a moving-average delay** (about 300 ms once warm, about 1 s at first) to stop timing attacks. That time is a sleep, not CPU.
- **`offline_access`, which refresh tokens need, asks for consent at every login**, even with `pre_configured` consent ("Ignored saving pre-configuration").
- **It never deletes expired OAuth2 rows** and looks tokens up by an unindexed column, so introspection slows down as the table grows ([#13038](https://github.com/authelia/authelia/issues/13038)). `scripts/authelia-cleanup.sh` is a stopgap.
- **There is no `end_session_endpoint`**, so RP-initiated logout isn't supported.
- **Default access tokens are opaque** (`authelia_at_…`).

**LLDAP**

- **Passwords use OPAQUE**, so they can only be set with `lldap_set_password` (in the image), not plain GraphQL. Password checks run on about one core.

**Zitadel**

- **Login V2 is the default for new v4 instances.** `config.yaml` turns it off to use the built-in login UI instead of a separate Node.js container.
- **The admin API answers 503 for a few seconds after `/debug/ready`** on first start; `provision.py` retries.
- **Default hashing is bcrypt cost 14**, about 1 s of CPU per login.
- **Account lockout is off by default.**

**Rauthy**

- **Login requires a proof-of-work.** Get a challenge from `POST /auth/v1/pow` (with the login page's CSRF token as `x-csrf-token`), then find a nonce so that `sha256(challenge + nonce)` has `difficulty` leading zero bits. This is client work only: the server checks one hash.
- **A refresh token only works in the last 60 s of its access token's life** (`nbf = iat + lifetime − 60`).
- **Rauthy panics if its configured SMTP server is unreachable.** Leave `smtp_url` unset for tests.
- **Default hashing is argon2id with 128 MiB, t=4, p=8**, but at most `MAX_HASH_THREADS` (default 2) hashes run at once.
- **0.37.2 can exit under a handful of concurrent logins** ("overflow when subtracting durations").

**Logto**

- **There is no bootstrap credential for the Management API**, and a new install's only way in is the admin console's sign-up page. `provision.py` inserts a machine-to-machine app with Logto's built-in "Logto Management API access" role into the database.
- **Usernames can't contain dashes.**
- **Client secrets live in their own table**: an app created through the API comes back without one.

**Casdoor**

- **The built-in admin's password is `123`, and the shipped `conf/app.conf` runs in dev mode.** The stack's `app.conf` sets production mode, Postgres and TLS (Casdoor's web framework serves HTTPS itself).
- **Data comes from `init_data.json` on first start**, with `initDataNewOnly = true` so that a restart doesn't recreate the users.
- **Access tokens last 7 days by default.**

**Dex**

- **There is no revocation or logout endpoint**, so sessions are left to expire.
- **On Postgres, concurrent logins fail now and then** with "could not serialize access" (SQLSTATE 40001). Dex doesn't retry them: about 3% of logins failed at 4 concurrent users.
- **Static passwords are bcrypt hashes in the config**, the way Dex's docs show (`htpasswd -bnBC 10`).

**Kanidm**

- **It only serves HTTPS, and requires MFA for every person by default** (`idm_all_persons`). The stack allows password-only logins for the test users.
- **It rejects weak passwords**, and an admin can't set someone's password: `provision.py` redeems a credential-reset intent for each user.
- **Login is server-rendered forms**: username, password, then a consent page the first time a user signs in to a client.

**Ory**

- **Hydra serves plain HTTP unless TLS is enabled explicitly** (`serve.public.tls.enabled`). Kratos's config schema has no such key.
- **Hydra's introspection is on its admin API, which has no authentication** and isn't in its discovery document. Neither does Kratos's admin API; keep both off public networks.
- **The reference UI breaks on a trailing slash in `HYDRA_ADMIN_URL`** (a double slash, then a 500 at consent).
- **Kratos hashes with bcrypt, cost 12.**

**Pocket ID**

- **Logins are passkeys only.** `lib/passkey.js` is a software authenticator for k6 (P-256, "none" attestation, discoverable credentials). `stacks/pocket-id/enroll.js` registers one per user with a one-time access token, the way a new user would.
- **Rate limits apply per IP by default**: 100 API calls a second and one passkey login every 5 seconds (burst 10). An app backend checking tokens from one IP gets 100 a second at most.
- **There is no revocation endpoint.**

**Load generator**

- **k6 shares the host.** Pin it to its own cores (`K6_CPUSET`), or treat stacks without a budget as an upper bound.

## Add a provider

Add `stacks/<name>/compose.yml` and `stacks/<name>/stack.env`, then a login adapter in `bench.js` if its login isn't a plain form.

- In `compose.yml`, every service merges the `x-bench` block (restart policy and budget). Containers are named `${BENCH_NAME:-bench}-idp` and `-db`, plus other roles. Host ports come from `${BENCH_PORT:-...}` (and `BENCH_PORT2`, `BENCH_PORT3`). Limits follow `LIMIT_*`, else `STACK_*`.
- `stack.env` sets:
  - `READY_URL`, `K6_ENV`, `IMAGES`, `CONTAINERS` (the identity provider first), `VOLUMES` and `DB_STATS` (the arguments for `scripts/db-stats.sh`)
  - optionally `PRESTART`, `PROVISION` (prints `KEY=VALUE` lines such as `CLIENT_SECRET=...` for k6), `METRICS_URL` and `CLEANUP_VOLUME`
- Secrets go in `scripts/gen-secrets.sh`.

## Project health and features

- `tools/maintainer-health.py` measures from GitHub data how the projects treat outside contributors: answer times for outside issues, outside PRs merged, release cadence, how concentrated commits are, and published security advisories.
- `docs/features.md` compares protocols, token handling, admin, MFA, security defaults and operations across the providers, with a source for every cell.

## License

MIT
