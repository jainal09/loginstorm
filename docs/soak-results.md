# Soak results: soak-1

Eleven providers ran side by side for seven days, from 2026-10-28 03:15Z to 2026-11-04 04:05Z. **None of them crashed, restarted or ran out of memory.** The differences are in what slowed down or kept growing.

## Setup

- One Azure D8as_v5 VM (8 vCPU, 32 GB). Each stack, its database included, had its own systemd slice of 2 CPU and 2 GiB, on six shared cores. k6 ran on the other two.
- Every hour, k6 ran 10 token introspections a second, plus two simulated users who signed in, refreshed their tokens and paused 60 s between steps. That is about 6 million token checks and 38,000 to 54,000 login checks per stack over the week.
- Each provider ran its defaults, with the exceptions in [the methodology](methodology.md#defaults-and-exceptions). Authelia ran with a plaintext client secret, because a hashed one cannot sustain 10 introspections a second.
- How the runner works, and how to repeat it: [Soak testing](soak-testing.md).

## Results

Latency and memory compare the medians of the first six and the last six hourly runs. Process memory is the whole stack's anonymous memory, without page cache. The database is its size on disk at the start and at the end.

| Stack | Version | Token checks failed | Login checks failed | Token check p95 | Login p95 | Process memory, MiB | Database, MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| Authelia (plaintext client secret) | 4.39.28 | 175 (0.0029%) | 10 (0.019%) | 1.1 ms → 22 ms | 745 ms → 910 ms | 124 → 188 | 0.3 → 138 |
| authentik | 2026.8.5 | 580 (0.0098%) | 4 (0.011%) | 441 ms → 475 ms | 13 s → 19 s | 959 → 978 | 30 → 328 |
| Casdoor | v4.24.0 | 17 (0.00028%) | 0 | 17 ms → 19 ms | 297 ms → 349 ms | 44 → 50 | 9.8 → 2,317 |
| Dex | v2.46.1 | 0 | 467 (0.97%) | 2.4 ms → 2.5 ms | 144 ms → 126 ms | 25 → 28 | 7.7 → 8.0 |
| Kanidm | 1.11.2 | 0 | 1,566 (3.1%) | 1.3 ms → 1.4 ms | 53 ms → 727 ms | 38 → 86 | 5.7 → 23 |
| Keycloak | 26.8.1 | 0 | 0 | 2.6 ms → 2.3 ms | 93 ms → 77 ms | 612 → 638 | 13 → 14 |
| Logto | 1.45.0 | 0 | 0 | 9.3 ms → 22 ms | 772 ms → 900 ms | 269 → 280 | 11 → 230 |
| Ory Hydra + Kratos | v26.2.0 | 0 | 0 | 2.6 ms → 2.7 ms | 601 ms → 589 ms | 137 → 150 | 8.7 → 120 |
| Pocket ID (passkeys only) | v2.19.1 | 0 | 3 (0.0064%) | 3.3 ms → 3.5 ms | 277 ms → 563 ms | 22 → 28 | 4.8 → 147 |
| Rauthy | 0.37.2 | 0 | 1 (0.0019%) | 1.9 ms → 1.9 ms | 298 ms → 350 ms | 34 → 39 | 9.3 → 211 |
| Zitadel | v4.20.0 | 0 | 0 | 6.7 ms → 9.4 ms | 1.6 s → 1.9 s | 162 → 182 | 15 → 86 |

## What stood out

- **Keycloak, Dex, Ory and Rauthy stayed flat.** Their token checks were as fast at the end as at the start.
- **Authelia slowed down as its token tables grew.** It never deletes expired OAuth2 tokens ([authelia#13038](https://github.com/authelia/authelia/issues/13038); a cleanup command is proposed in [authelia#13128](https://github.com/authelia/authelia/pull/13128)), so token-check p95 rose about 19-fold and the database grew from almost nothing to 138 MiB.
- **Logto's token checks more than doubled** as its database grew to 230 MiB. On every introspection, userinfo call and refresh, Logto's OIDC provider confirms that the token's login session still exists, looking it up by `payload->>'uid'` in `oidc_model_instances`.
  - Logto queries Postgres as a tenant role under row-level security. `jsonb_object_field_text` is not leakproof, so Postgres won't use the index on that expression, and each lookup scans every stored session. On the week-old database it read 10,938 sessions to keep one, in 5.7 ms. As a superuser, with no row-level security, the index is used.
  - Sessions last 14 days, so the scan grows with every login.
  - Side by side under the soak load, introspection p95 was 17.5 ms on the week-old copy and 11.3 ms on a fresh one.
  - A shorter session lifetime (`PATCH /api/configs/oidc/session`) caps it. Upstream already tracks the index problem in [logto#9886](https://github.com/logto-io/logto/issues/9886) and is moving the ID into its own indexed column. Code: [oidc-model-instance.ts](https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/queries/oidc-model-instance.ts#L74-L77), [_after_each.sql](https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/_after_each.sql#L6-L10).
- **Casdoor's database reached 2.3 GB.** Every POST API call, each token introspection included, is stored as an audit record, and records are kept forever by default. Casdoor v4.24.0 can expire them with `recordRetentionDays`.
- **Kanidm's logins got 14 times slower (53 to 727 ms) while its token checks stayed flat.** Kanidm stores OAuth2 sessions inside the user's own entry, and an ended session is only marked revoked; it is removed after seven days.
  - The two login users built up about 4,000 sessions each, a 1.1 MB entry. Users that logged in once an hour held about 167.
  - Every token grant rewrites the whole entry, so writes to those two accounts took 0.4 to 0.6 s. Reads were unaffected.
  - Side by side, login p95 was 747 ms on the week-old database and 77 ms on a fresh one. On the same week-old database, an account that had never logged in refreshed in 8 ms (median), against 209 ms for a busy one.
  - Neither the seven-day retention nor the 48-session cap is configurable. Code: [oauth2.rs](https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L2148-L2179), [valueset/session.rs](https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/valueset/session.rs#L756-L816).
- **Pocket ID's slowest logins doubled (p95 277 to 563 ms), while the median stayed near 80 ms.** This one is likely, not confirmed.
  - Every write starts with `BEGIN IMMEDIATE` on its SQLite database, so overlapping logins queue for the write lock. About 2.5% of writes took more than 250 ms on every day that still had logs.
  - A fresh copy and the week-old one behaved the same under identical load (setup-login p95 524 vs 569 ms), so the data it built up is not the cause. Why the tail rose during the soak was not reproduced.
- **A 40-second disk stall on 2026-10-28 at 21:41Z caused most of the token-check failures.** Postgres fsyncs took up to 11 s. Authelia's SQLite answered "database is locked", so valid tokens read as inactive: all 175 of its failed token checks and all 10 failed login checks came in that hour. Casdoor, on Postgres, failed all 17 of its token checks in the same hour. Pocket ID, on SQLite, logged one "database is busy" and failed 2 of its 3 login checks then. The other stacks failed no more checks that hour than in any other.
- **authentik answered 580 token checks with an HTTP 503 "authentik starting",** one to seven an hour through the whole run. By default authentik restarts each Python web worker after about 1,000 requests (`web.max_requests`). Since 2026.8, its front server returns that 503, without retrying, when it sends a request on a pooled connection the retiring worker has just closed ([authentik#26274](https://github.com/goauthentik/authentik/issues/26274)).
  - Evidence: in 164 of 165 chunks the failed checks equal k6's failed HTTP requests. authentik's own request log has no non-200 introspections, because the 503 never reaches the Python side.
  - We reproduced it on the same image. With `AUTHENTIK_WEB__MAX_REQUESTS=0` the 503s stopped.
  - A fix is merged but unreleased as of 2026.8.5 ([authentik#27275](https://github.com/goauthentik/authentik/pull/27275)), and it retries only requests without a body, so POST endpoints such as introspection can still see it.
  - The bench first reported these as inactive tokens. `bench.js` now checks `introspect ok` (HTTP 200) and `token active` separately.
- **Kanidm's failed checks are token refreshes lost on the connection:** of 1,566, 1,262 were EOF, 278 connection resets and 26 "server closed idle connection", and none was an HTTP refusal. Kanidm closes connections after about 60 s idle, the same length as the soak's pause between steps, so k6 sometimes sent on a closed connection. Later soaks should pause for less than 60 s.
- **Dex failed about 1% of login checks.** The first ones checked were Postgres serialization errors that Dex does not retry ([dex#1341](https://github.com/dexidp/dex/issues/1341)).
- **Rauthy failed one login:** two logins for the same user in the same millisecond collided on the primary key of `user_login_states` ([rauthy#1865](https://github.com/sebadob/rauthy/issues/1865)).

## Notes on the numbers

- The soak ended when each stack finished the hourly chunk it was running at `END_AT`, so stacks have 165 to 168 hourly runs.
- When the runner stops a stack at the end, some containers exit with a non-zero code (Keycloak exits 143 on SIGTERM). `soak-summary.py` counts those as stops, not crashes.
