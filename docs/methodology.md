# Methodology

Loginstorm answers four questions about an identity provider:

1. How much does it cost to run: memory, CPU, disk, image size and startup time, for the whole stack including its database?
2. How many token checks can it answer, and how fast, for a given CPU and memory budget?
3. How many logins can it handle, and how long does each take?
4. Does it stay healthy for days under ordinary load, or do memory, storage and latency drift?

## What the bench does

`bench.js` discovers the provider's endpoints from `/.well-known/openid-configuration`, then plays both sides of an OpenID Connect login:

- **the browser**: opening the authorization URL with PKCE (S256), getting through the provider's login pages, answering consent
- **the application backend**: exchanging the code, calling userinfo, refreshing, introspecting, revoking

Only the login itself differs between providers, so each has a small adapter that follows its real login flow rather than a shortcut API. Adapters never follow the final redirect back to the application; the code in the `Location` header is all a backend needs.

| Step | Request | Metric |
|---|---|---|
| Login page | `GET` authorization endpoint | `idp_login_page` |
| Credential check | the one request that checks the password or passkey | `idp_login_submit` |
| Other login steps | consent, redirects, flow steps, challenges | `idp_login_extra` |
| Code exchange | `POST` token endpoint, `authorization_code` | `idp_code_exchange` |
| Whole login | all of the above, wall clock, minus client-side work | `idp_login_total` |
| Client-side work | Rauthy's proof of work, signing a Pocket ID passkey assertion | `idp_client_work` |
| User info | `GET` userinfo endpoint | `idp_userinfo` |
| Refresh | `POST` token endpoint, `refresh_token` | `idp_refresh` |
| Introspection | `POST` introspection endpoint | `idp_introspect` |
| Logout | revocation, or Keycloak's back-channel logout; skipped where neither exists | `idp_logout` |

Every k6 check (credentials accepted, code exchanged, token active, and so on) counts toward a pass rate. A run fails when fewer than 99% pass, unless a scenario says otherwise.

### Scenarios

- **`session`**: a full session per iteration: login, userinfo, refreshes with think time, introspection, logout.
- **`login`**: login and logout only. With `THINK_S=0` it measures how many password checks a provider sustains, which is mostly a function of its password hashing.
- **`api`**: the steady-state work of an application backend that doesn't validate tokens locally. `VUS` sessions are opened before measurement starts, then `RATE` introspection or userinfo calls per second are spread across them. Tokens are refreshed shortly before they expire. Calls that can't start on time count as dropped, so a provider that can't keep up shows dropped iterations and rising latency rather than silently lowering the rate.
- **`lockout`**: checks brute-force protection on throwaway accounts (correct login, a streak of wrong passwords, correct login again, then an untouched account from the same address).
- **`client-credentials`**: service-to-service tokens only.

## Budgets

A comparison is only fair if each provider gets the same resources, and that includes its database. Some providers are a single binary with an embedded store; others need Postgres, a worker or a login UI next to them. Loginstorm gives each stack one budget:

- `scripts/envelope.sh` creates a systemd slice, `loginstorm-<name>.slice`, with `CPUQuota`, `MemoryMax` and `MemorySwapMax=0`, and optionally `AllowedCPUs`. Every container of the stack is placed in it through Compose's `cgroup_parent`. The budget is persistent, so containers that restart after a reboot land in the same budget.
- Each container also gets the budget as its own limit. Runtimes that size themselves from the container's limit (the JVM, Node.js, Go) then behave as they would on a VM of that size, while the slice keeps the total within the budget.
- `scripts/collect-cgroup.sh` reads the slice every second:
  - CPU time
  - memory in use, excluding reclaimable page cache (the same figure `docker stats` reports)
  - the kernel's OOM-kill counter

  Per-container `docker stats` are recorded next to it.
- The load generator runs outside the budget, pinned to its own cores (`K6_CPUSET`), so it neither borrows from the provider nor competes with it.

The published comparison uses two budgets: 1 CPU with 1 GiB, a small VM or a sidecar-sized deployment, and 2 CPUs with 2 GiB.

## Defaults and exceptions

Each stack runs the configuration the project documents or recommends, on its supported database, with TLS. That covers password hashing, token formats, signing algorithms, session lifetimes, rate limits and log levels. The bench changes a default only when the test can't run without the change, or when the default would measure the load generator rather than the provider:

| Provider | Change | Why |
|---|---|---|
| Authelia | Per-IP limit on the token and revocation endpoints raised from 30 to 6000 a minute | An application backend makes every user's code exchanges and refreshes from one IP, as the load generator does |
| Kanidm | The test users may log in with a password alone | Kanidm requires MFA for every person by default; the other providers are measured with passwords |
| Pocket ID | Per-IP rate limiting off | It allows 100 API calls a second and one passkey login every 5 seconds per address, and the load generator is one address |
| Rauthy | Login proof of work at 10 bits instead of 19; client access tokens last 60 s | Solving the proof of work is client work. Rauthy only accepts a refresh in the last 60 s of a token's life |
| Logto | The client always receives refresh tokens | Otherwise refresh tokens need a consent prompt at every login |
| Hydra, Kanidm, Pocket ID | `https://bench.invalid/callback` as the redirect URI | They reject plain-HTTP redirect URIs |

Two variants make a default's cost visible instead of hiding it:

- `authelia` uses a hashed client secret (pbkdf2-sha512), as Authelia's documentation recommends.
- `authelia-plaintext-secret` uses a plaintext secret, which Authelia still supports but has deprecated. A hashed secret costs one hash on every client authentication, introspection included.

Hostnames are `<provider>.bench.test` inside each stack's Docker network, with one self-signed certificate. Every provider terminates TLS itself; none sits behind a proxy.

## Test data

- Each stack gets one confidential client and 50 users with the same password. Passwords meet each provider's policy.
- Kanidm and Zitadel reject the weak password the others use, so they get stronger ones. Pocket ID users get one software passkey each.
- Users are created through each provider's admin API, or declaratively where the project offers that (Casdoor's init data, Dex's static passwords). The provider stores them with its default hashing.
- The api scenario opens its sessions with real logins before measurement starts, so login cost never mixes into token-check results.

## The performance suite

`scripts/perf-suite.sh` runs each profile three times per budget, each time on a fresh stack:

| Test | Load | Duration |
|---|---|---|
| Introspection | 25, 50, 100, 200, 400, 800 and 1600 calls/s over 50 sessions | 45 s per level |
| Userinfo | the same rates | 45 s per level |
| Logins | 1, 4, 16 and 32 concurrent users, no pause | 40 s per level |

- Each test starts with a minute of idle measurement, and levels are 15 s apart.
- `scripts/summarize.py` reports, for every level, the rate actually achieved and the p95 latency. A provider's best is the highest achieved rate at a level where at least 99% of checks passed.
- Achieved rates include every check. A rate reached with failing checks doesn't count.

## The soak

`scripts/soak.sh` runs providers side by side for days, each in its own stack and budget:

- **Load per stack:** 10 introspections a second over 25 sessions, plus 2 users logging in about every 2.5 minutes, refreshing twice with 50 s pauses and never logging out. Their sessions pile up the way real users' do.
- **Chunks:** k6 runs in hourly chunks, so latency can be compared hour by hour.
- **Restarts:** the containers restart after a crash, as production ones would, and every crash and OOM kill is logged.
- **Summary:** `scripts/soak-summary.py` compares the first six hours with the last six. It covers latency, whole-stack memory (with a trend fitted over the second half, so warm-up doesn't read as growth) and database size, and counts crashes.

## Limits of the method

- **One load generator, one source address.** Per-IP rate limits and lockouts behave differently from real traffic spread across many clients. Defaults that only affect per-IP behavior are noted in the table above.
- **Single instances only.** Clustering, replicas and external caches are out of scope. So are external user directories, other than LLDAP for Authelia.
- **Local JWT validation isn't measured.** An API that verifies signed access tokens itself never calls the provider. The api scenario measures the providers' own token-check endpoints, which opaque tokens and revocation checks depend on.
- **Defaults are not tuned settings.** Every provider can be made faster or smaller. `profiles/small-host/` shows how far a few of them go on 0.5 CPU and 512 MiB.
- **Results are from one machine type** (published runs: Azure `Standard_D8as_v5`, AMD EPYC 7763, Ubuntu 24.04, Docker 29). Absolute numbers will differ elsewhere; the comparison between providers is the point.
