<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/loginstorm-lockup-dark.svg">
    <img alt="loginstorm" src="docs/assets/loginstorm-lockup-light.svg" width="440">
  </picture>
</p>

<p align="center">Load and soak tests for open-source identity providers.</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-4F46E5"></a>
  <img alt="Providers: 13" src="https://img.shields.io/badge/providers-13-FFB020">
  <img alt="k6 2.3" src="https://img.shields.io/badge/k6-2.3-1E1B4B">
</p>

Loginstorm sends an OpenID Connect provider the same traffic a browser and an application backend would: logins through the provider's own login pages, token checks, refreshes and logouts. It measures how the provider holds up. How many token checks does it answer per CPU? How long does a login take? How much memory does the whole stack need, database included? Does any of that drift over a week?

It comes with disposable Docker Compose stacks for 13 providers, one k6 script with a login adapter for each, and three runners:

- a matrix for quick comparisons
- a fixed performance suite
- multi-day soaks that survive reboots

## Providers

| Provider | Version | Stack | Login flow driven by the bench |
|---|---|---|---|
| [Keycloak](https://www.keycloak.org) | 26.8.1 | pre-built image, Postgres 17 | login form |
| [authentik](https://goauthentik.io) | 2026.8.5 | server, worker, Postgres 17 | flow executor API |
| [Authelia](https://www.authelia.com) | 4.39.28 | users file, SQLite | first-factor API and consent |
| Authelia + [LLDAP](https://github.com/lldap/lldap) | 4.39.28 / 0.6.3 | LLDAP as the user directory | first-factor API and consent |
| [Zitadel](https://zitadel.com) | 4.20.0 | built-in login UI, Postgres 17 | login-name and password forms |
| [Rauthy](https://github.com/sebadob/rauthy) | 0.37.2 | embedded Hiqlite | proof of work, JSON login |
| [Logto](https://logto.io) | 1.45.0 | Postgres 17 | Experience API |
| [Casdoor](https://casdoor.org) | 4.24.0 | Postgres 17 | `/api/login` |
| [Dex](https://dexidp.io) | 2.46.1 | local password database, Postgres 17 | login form |
| [Kanidm](https://kanidm.com) | 1.11.2 | embedded database | username, password and consent forms |
| [Ory](https://www.ory.sh) Hydra + Kratos | 26.2.0 | reference login UI, Postgres 17 | Kratos login form |
| [Pocket ID](https://pocket-id.org) | 2.19.1 | SQLite | passkey, signed by a software authenticator |

Each stack runs the provider's documented defaults: password hashing, token format, signing keys and log level. The few deliberate exceptions are listed in [the methodology](docs/methodology.md#defaults-and-exceptions).

## Quick start

You need Docker with Compose v2, Python 3.10 or newer, OpenSSL and bash. Per-stack CPU and memory budgets also need Linux with systemd and `sudo`.

```bash
git clone https://github.com/jainal09/loginstorm.git && cd loginstorm

# One provider: login sessions at 1, 5, 15 and 50 concurrent users.
scripts/run-matrix.sh profiles/keycloak.env

# Two providers at the same budget (1 CPU, 1 GiB for the whole stack): token checks at rising rates.
STACK_CPUS=1 STACK_MEM=1G LEVEL_VAR=RATE LEVELS="50 200 800" DURATION=45s \
  BENCH_ENV="SCENARIO=api VUS=50" scripts/run-matrix.sh profiles/keycloak.env profiles/kanidm.env
```

Each run writes a folder under `results/` with a `report.md`, the raw k6 summaries, per-second container stats, startup times, storage sizes and logs. [Getting started](docs/getting-started.md) walks through the output, and shows how to run the full suite on a cloud VM.

## Documentation

- [Getting started](docs/getting-started.md): requirements, a first run, reading the report, running on Azure
- [Methodology](docs/methodology.md): what is measured, budgets, defaults, and how results are summarized
- [Configuration](docs/configuration.md): every variable of the k6 script and the runners, and the profile format
- [Soak testing](docs/soak-testing.md): week-long runs, crash and reboot handling, health checks
- [Provider notes](docs/providers.md): behavior and defaults worth knowing for each provider
- [Adding a provider](docs/adding-a-provider.md): the stack and adapter contract
- [Feature comparison](docs/feature-comparison.md): protocols, MFA, security defaults and operations, with sources
- [Maintainer health](docs/maintainer-health.md): measuring how projects answer outside issues and pull requests

## Contributing

Bug reports, provider updates and new providers are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[MIT](LICENSE). The providers under test have their own licenses; the stacks only pull their published images.
