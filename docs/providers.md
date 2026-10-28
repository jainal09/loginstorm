# Provider notes

What each stack does, and what is worth knowing about the provider before reading its numbers or running it yourself. The versions are the ones pinned in `stacks/`.

## Keycloak 26.8.1

- The stack builds a pre-built image (`kc.sh build`, then `start --optimized`), as Keycloak's container guide recommends. A stock image repeats its build step on every start, which costs tens of seconds on a small CPU.
- `kc.sh` reads `JAVA_OPTS`, `JAVA_OPTS_KC_HEAP` and `JAVA_OPTS_APPEND`. There is no `KC_JVM_ARGUMENTS`, and unknown `KC_*` variables are ignored without a warning.
- Appending `-XX:+UseSerialGC` stops the JVM from starting ("Multiple garbage collectors selected"), because the default `JAVA_OPTS` already selects G1. Replace `JAVA_OPTS` instead.
- A client can only introspect tokens that list it in their audience, so the realm adds an audience mapper.
- Brute-force detection is off by default. `profiles/small-host/keycloak-bruteforce.env` turns it on.
- Login uses its classic HTML form; the adapter posts it directly.

## authentik 2026.8.5

- Server and worker run from one image, next to Postgres, following authentik's own compose file (which no longer includes Redis).
- The first start runs several hundred database migrations: about a minute and a half on 2 vCPUs. The worker then creates the default flows, signing key and scope mappings from blueprints, after the server already reports ready, so provisioning waits for those objects.
- An OAuth2 provider created through the API allows no grant types until `grant_types` is set ("Invalid grant_type for provider").
- Without a signing key, tokens are HS256-signed. The stack picks the self-signed RSA key, as the admin UI does.
- The login page is a single-page app that drives the flow executor API: one JSON challenge per stage, and each answer redirects back to the executor for the next challenge. The adapter speaks that API.
- Passwords are hashed by Django's PBKDF2-SHA256.

## Authelia 4.39.28

- The stack uses the users file and SQLite. Authelia + LLDAP is a separate stack.
- The token endpoint allows 30 requests a minute per client IP by default (introspection and userinfo have no default limit). An application backend makes all of its users' token calls from one IP, so the stack raises the token and revocation limits.
- The documentation recommends a hashed client secret (pbkdf2-sha512, 310,000 rounds). Every client authentication then costs one hash, at the introspection endpoint as well as the token endpoint. `profiles/authelia-plaintext-secret.env` uses a plaintext secret for comparison.
- User passwords are hashed with argon2id at 64 MiB, t=3, p=4, the documented default, and every login's hash runs at once, so each login in progress needs 64 MiB. `profiles/authelia-light-hash.env` and `profiles/authelia-plaintext-light-hash.env` use 7 MiB, t=5, p=1 instead.
- Expired OAuth2 sessions are never deleted, and tokens are looked up by an unindexed column, so introspection slows down as the table grows. See [authelia/authelia#13038](https://github.com/authelia/authelia/issues/13038). `scripts/authelia-cleanup.sh` deletes old rows on a schedule as a stopgap.
- First-factor responses are padded to a moving average (about 300 ms once warm) to resist timing attacks. That time is a sleep, not CPU.
- Requesting `offline_access`, which refresh tokens need, asks for consent at every login, even with pre-configured consent.
- There is no `end_session_endpoint`.

## Authelia with LLDAP 0.6.3

- LLDAP stores passwords with OPAQUE, so they can only be set with the `lldap_set_password` tool in its image, not through GraphQL.
- Each password check runs on roughly one core, which caps logins at a few per second.

## Zitadel 4.20.0

- New v4 instances default to Login V2, a separate Node.js app. The stack uses the built-in login UI instead, which keeps the deployment to one container plus Postgres.
- Password hashing is bcrypt with cost 14 by default: about a second of CPU per login.
- Access tokens are opaque by default.
- The admin API answers 503 for a few seconds after `/debug/ready` on the first start; provisioning retries.
- Account lockout is off by default.

## Rauthy 0.37.2

- Logins require a proof of work. Get a challenge from `POST /auth/v1/pow`, with the login page's CSRF token as `x-csrf-token`, then find a nonce such that `sha256(challenge + nonce)` has `difficulty` leading zero bits. The server checks a single hash, so the work falls on the client.
- A refresh token only works in the last 60 seconds of its access token's life (`nbf = iat + lifetime - 60`).
- The default hashing is argon2id with 128 MiB, t=4, p=8, with at most `MAX_HASH_THREADS` (default 2) hashes running at once.
- Login timing uses the wall clock: `src/service/src/login_delay.rs` subtracts two `SystemTime` readings. A clock that steps backwards during a login, as virtualized clocks sometimes do, makes the subtraction panic ("overflow when subtracting durations") and the process exit.
- Rauthy panics at startup if its SMTP server is unreachable, so leave `smtp_url` unset in tests.

## Logto 1.45.0

- The Management API has no bootstrap credential; a new install's only way in is the admin console's sign-up page. Provisioning inserts a machine-to-machine app with Logto's built-in "Logto Management API access" role straight into the database, then uses the API.
- Usernames can't contain dashes, so the test users are `bench_user_01` and up.
- Client secrets live in a separate table, so an application created through the API comes back without one.
- The sign-in page is an app on top of the Experience API, which the adapter uses directly.
- Passwords are hashed with Argon2i.

## Casdoor 4.24.0

- The built-in admin account's password is `123`, and the shipped `conf/app.conf` runs in development mode. The stack's `app.conf` sets production mode, Postgres, and TLS through the web framework's own HTTPS server.
- Test data comes from `init_data.json` on the first start, with `initDataNewOnly = true`, so a restart doesn't delete and recreate the users.
- Access tokens last seven days by default.
- The login page posts the credentials and the OAuth parameters to `/api/login`, which returns the code in its JSON answer.

## Dex 2.46.1

- The stack uses Postgres and Dex's local password database with static users. Dex's documentation shows bcrypt hashes made with `htpasswd -bnBC 10`.
- On Postgres, concurrent logins sometimes fail with "could not serialize access due to read/write dependencies among transactions" (SQLSTATE 40001). Dex runs those transactions as serializable and doesn't retry them. In this bench, about 3% of logins failed at 4 concurrent users. The issue has been open since 2018: [dexidp/dex#1341](https://github.com/dexidp/dex/issues/1341).
- There is no revocation or logout endpoint, so sessions simply expire.
- Introspection needs no client authentication.

## Kanidm 1.11.2

- Kanidm only serves HTTPS, and requires MFA for every person by default (the `idm_all_persons` account policy). The stack lowers that to password-only for the test users.
- It rejects weak passwords, and administrators can't set a user's password. Provisioning creates a credential-update intent for each user and redeems it, the way a user follows a reset link.
- Login is a set of server-rendered forms: username, password, then a consent page the first time a user signs in to a client.
- Its Argon2 parameters come from a benchmark at startup.

## Ory Hydra and Kratos 26.2.0

- The stack is Ory's open-source pairing: Hydra for OAuth2 and OpenID Connect, Kratos for identities and logins, and Ory's reference login and consent UI (`kratos-selfservice-ui-node`), all on one Postgres.
- Hydra serves plain HTTP unless `serve.public.tls.enabled` is set. Kratos's configuration schema has no such key.
- Hydra's introspection endpoint is on its admin API. It needs no authentication and isn't in the discovery document, so the bench is given its URL. The admin APIs of both services are unauthenticated by design and must stay off public networks.
- Hydra only accepts `https` redirect URIs, except for hosts ending in `localhost`.
- The reference UI fails at consent if `HYDRA_ADMIN_URL` ends with a slash: it requests `//admin/...` and returns a 500.
- Kratos hashes passwords with bcrypt, cost 12.

## Pocket ID 2.19.1

- Pocket ID only logs in with passkeys.
  - `lib/passkey.js` is a software authenticator for k6: P-256 keys, "none" attestation, discoverable credentials and user verification.
  - `stacks/pocket-id/enroll.js` registers one passkey per test user, using a one-time access token as a new user would.
- Rate limits apply per client IP by default: 100 API calls a second, and one passkey login every 5 seconds (bursts of 10). An application backend that checks tokens from one address gets at most 100 checks a second. The stack turns rate limiting off.
- Pocket ID serves TLS itself (`TLS_CERT_FILE`, `TLS_KEY_FILE`), and accepts only `https` redirect URIs unless told otherwise.
- There is no revocation endpoint.
