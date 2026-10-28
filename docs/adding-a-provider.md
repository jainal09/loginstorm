# Adding a provider

A provider needs three things:

- a stack: a compose file and its settings
- a profile that selects it
- a login adapter in `bench.js`, if its login isn't one the existing adapters already speak

Look at `stacks/dex` for a small example and `stacks/ory` for a large one.

## The stack

`stacks/<name>/compose.yml` follows a few conventions so that the matrix and the soak runners can start several copies side by side.

```yaml
x-bench: &bench
  restart: ${BENCH_RESTART:-no}      # the soak sets unless-stopped
  cgroup_parent: ${BENCH_SLICE:-}    # the stack's budget, when there is one
name: loginstorm                     # the runners override this with COMPOSE_PROJECT_NAME
services:
  db:
    <<: *bench
    image: postgres:17-alpine
    container_name: ${BENCH_NAME:-bench}-db
    deploy:
      resources:
        limits: {cpus: "${STACK_CPUS:-0}", memory: "${STACK_MEM:-0}"}
  idp:
    <<: *bench
    image: example/idp:1.2.3                         # pin an exact version
    container_name: ${BENCH_NAME:-bench}-idp
    env_file: ["${PROFILE_FILE:?set PROFILE_FILE}"]  # profile lines reach the provider
    networks:
      default:
        aliases: [example.bench.test]                # the hostname k6 uses
    ports: ["127.0.0.1:${BENCH_PORT:-18443}:8443"]   # for readiness checks and provisioning
    deploy:
      resources:
        limits: {cpus: "${LIMIT_CPUS:-${STACK_CPUS:-0}}", memory: "${LIMIT_MEM:-${STACK_MEM:-0}}"}
```

- Name the identity provider's container `-idp` and its database `-db`. Other services get their own role names (`-worker`, `-ui`, ...).
- Every service merges `x-bench` and gets a limit, so the whole stack lives in its budget. One-shot jobs such as migrations set `restart: "no"` explicitly.
- Serve TLS with the shared certificate in `../../tls` if the provider can. Put generated secrets in `stacks/<name>/secrets/` (ignored by git), and add their creation to `scripts/gen-secrets.sh`.
- Use further host ports through `BENCH_PORT2` and `BENCH_PORT3`.

`stacks/<name>/stack.env` is sourced by the runners after they set the `BENCH_*` and `COMPOSE_PROJECT_NAME` variables:

| Key | Required | Meaning |
|---|---|---|
| `READY_URL` | yes | Polled until it answers 2xx |
| `K6_ENV` | yes | k6 variables: `IDP`, `ISSUER`, user settings, and `REDIRECT_URI` if the default isn't accepted |
| `IMAGES` | yes | Images whose sizes go into the report |
| `CONTAINERS` | yes | Containers to sample, the identity provider first |
| `VOLUMES` | yes | Volumes to measure and remove, prefixed with `${COMPOSE_PROJECT_NAME:-loginstorm}_` |
| `DB_STATS` | yes | Arguments for `scripts/db-stats.sh`: `postgres <container> <user> <db> <table>`, `sqlite <volume> <table>` or `du <volume>` |
| `PROVISION` | no | A command that creates the client and users and prints `KEY=VALUE` lines (`CLIENT_ID=...`, `CLIENT_SECRET=...`) for k6 |
| `PRESTART` | no | Runs before the stack starts, for example to build an image or write init data |
| `METRICS_URL` | no | Saved after the run, such as a Prometheus endpoint |
| `CLEANUP_VOLUME` | no | The volume `scripts/authelia-cleanup.sh` works on |

Provisioning scripts use only the Python standard library and run with `python3 -I`:

- They take the local port as an argument and build `https://127.0.0.1:<port>` themselves.
- They read any secrets from fixed paths in their own folder.
- They create one confidential client with the redirect URI from `K6_ENV`, and 50 users. Use the provider's admin API, or its declarative configuration if it has one.

Finally, add `profiles/<name>.env` with `STACK=<name>`. Add a comment that names the defaults, and anything changed from them, with the reason.

## The login adapter

An adapter takes the authorization URL and returns `{ code, extraMs, clientMs }`, or `null` when the login fails:

```js
function exampleLogin(authUrl, user, state) {
  const page = timed('login_page', web.get(authUrl, { tags: { name: 'login_page' } }));
  // ... find the form or API the login page uses ...
  const submit = timed('login_submit', web.post(action, { username: user.username, password: user.password },
    { redirects: 0, tags: { name: 'login_submit' } }));
  return { code: codeFrom(submit, state), extraMs: 0, clientMs: 0 };
}
```

- Use `web.get`, `web.post` and `web.request` rather than `http.*`. The api scenario gives every session its own cookie jar.
- Time exactly one request as `login_submit`: the one that checks the credentials. Add the other steps' durations to `extraMs`, and any client-side computation to `clientMs`.
- Don't follow the final redirect to `REDIRECT_URI`. `codeFrom(response, state)` reads the code from its `Location` header and checks `state`. `getFollowing(url, name)` follows a provider's own redirects and times them.
- Return `null` when the provider answers a wrong password with its login form, so the lockout scenario and the failure counts stay meaningful.
- An adapter may be `async`. Pocket ID's is, because WebCrypto signing returns promises.

Register the adapter in `LOGINS`. If the provider only issues refresh tokens for `offline_access`, add it to `DEFAULT_SCOPES`.

Before opening a pull request, check that the stack passes `scripts/run-matrix.sh profiles/<name>.env` with 100% checks in the session scenario and in the api scenario (`LEVEL_VAR=RATE LEVELS=20 BENCH_ENV="SCENARIO=api VUS=10"`).
