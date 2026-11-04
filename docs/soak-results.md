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
- **Logto's token checks more than doubled** as its database grew to 230 MiB. The cause was not investigated.
- **Casdoor's database reached 2.3 GB.** Every POST API call, each token introspection included, is stored as an audit record, and records are kept forever by default. Casdoor v4.24.0 can expire them with `recordRetentionDays`.
- **Logins got slower on Kanidm (53 to 727 ms) and Pocket ID (277 to 563 ms).** The causes were not investigated.
- **A 40-second disk stall on 2026-10-28 at 21:41Z caused most of the token-check failures.** Postgres fsyncs took up to 11 s. Authelia's SQLite answered "database is locked", so valid tokens read as inactive: all 175 of its failed token checks and all 10 failed login checks came in that hour. Casdoor, on Postgres, failed all 17 of its token checks in the same hour. Pocket ID, on SQLite, logged one "database is busy" and failed 2 of its 3 login checks then. The other stacks failed no more checks that hour than in any other.
- **authentik reported 580 valid tokens as inactive,** one to seven an hour through the whole run. The cause was not investigated.
- **Kanidm's failed checks are token refreshes.** The ones checked were connections Kanidm closed after about 60 s idle, the same length as the soak's pause between steps, so k6 sent on a closed connection. In the first hour, every refresh that reached Kanidm got a 200. Later soaks should pause for less than 60 s.
- **Dex failed about 1% of login checks.** The first ones checked were Postgres serialization errors that Dex does not retry ([dex#1341](https://github.com/dexidp/dex/issues/1341)).
- **Rauthy failed one login:** two code exchanges for the same user in the same millisecond collided on a primary key.

## Notes on the numbers

- The soak ended when each stack finished the hourly chunk it was running at `END_AT`, so stacks have 165 to 168 hourly runs.
- When the runner stops a stack at the end, some containers exit with a non-zero code (Keycloak exits 143 on SIGTERM). `soak-summary.py` counts those as stops, not crashes.
