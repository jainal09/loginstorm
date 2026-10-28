# Getting started

## Requirements

- Docker Engine with Compose v2. Docker Desktop works for single runs without budgets.
- Python 3.10 or newer (standard library only), OpenSSL, bash, curl.
- For per-stack budgets (`STACK_CPUS`, `STACK_MEM`): Linux with systemd, Docker's systemd cgroup driver (the default on current distributions) and `sudo`.
- About 15 GB of disk for all images, more for long soaks. Container logs are worth rotating; see `infra/azure/cloud-init.yaml`.

k6 runs in a container (`grafana/k6:2.3.0`), so it doesn't need installing.

## A first run

```bash
git clone https://github.com/jainal09/loginstorm.git && cd loginstorm
scripts/run-matrix.sh profiles/kanidm.env
```

The runner:

1. generates a self-signed `*.bench.test` certificate and the stacks' test secrets on first use (`scripts/gen-secrets.sh`; nothing secret is committed)
2. starts the stack and waits until it is ready
3. creates the test client and 50 test users
4. records a minute of idle footprint
5. runs `bench.js` at each load level
6. removes the stack and its volumes

A run takes a few minutes per profile. Kanidm and Dex start in seconds. authentik needs about a minute and a half for its first-start migrations.

## Reading the output

Each run creates `results/<timestamp>/`:

| File | What it holds |
|---|---|
| `report.md` | Footprint and load tables for every profile in the run |
| `runs.csv` | Start and end time of each idle window and load level |
| `<profile>/<level>.json` | The full k6 summary, including every `idp_*` latency metric |
| `<profile>/<level>.txt` | The short summary k6 printed |
| `<profile>/stats-<container>.csv` | `docker stats` every 0.5 to 1 s |
| `<profile>/stats-stack.csv` | The whole stack's CPU, memory and OOM kills every second, when it has a budget |
| `<profile>/meta.json` | Readiness, startup time, exit codes, restarts and OOM kills per container |
| `<profile>/storage.txt` | Image sizes, data-volume sizes and the database size |
| `<profile>/log-<container>.txt` | Container logs |

`python3 scripts/report.py results/<run>` rebuilds `report.md`. For a run of the performance suite, `python3 scripts/summarize.py results/<run>` builds one table per budget and test, and writes `summary.json` for charts.

## Budgets

A budget gives all of a stack's containers one CPU quota and one memory limit, with the database counted:

```bash
STACK_CPUS=2 STACK_MEM=2G STACK_CPUSET=4-7 K6_CPUSET=0-3 scripts/run-matrix.sh profiles/keycloak.env
```

- `STACK_CPUSET` and `K6_CPUSET` keep the provider and the load generator on separate cores. On a shared machine, this matters more than the budget itself.
- Without a budget, the stack can use the whole host, and the numbers are an upper bound rather than a comparison.
- [Methodology](methodology.md#budgets) explains how budgets are enforced.

## The performance suite

`scripts/perf-suite.sh` runs the same three tests for every profile and budget:

- token introspection at 25 to 1600 requests per second
- userinfo at the same rates
- logins with no pause between them, at 1 to 32 concurrent users

```bash
OUT=results/perf-$(date -u +%Y%m%d) scripts/perf-suite.sh
python3 scripts/summarize.py results/perf-$(date -u +%Y%m%d)
```

With 13 profiles and two budgets, it takes about 14 hours on an 8-vCPU machine.

## Running on Azure

`infra/azure/up.sh` creates a VM in its own resource group and installs Docker through cloud-init. SSH is open only to your current public IP.

```bash
AZ_SUBSCRIPTION=<subscription-id> infra/azure/up.sh loginstorm-1 Standard_D8as_v5
ssh -i ~/.ssh/loginstorm_ed25519 bench@<ip>
git clone https://github.com/jainal09/loginstorm.git && cd loginstorm
```

`az group delete -n loginstorm` removes everything it created. An 8-vCPU AMD VM (`Standard_D8as_v5`) is enough for the suite, and for a soak of all providers at 2 CPUs and 2 GiB each.

## Cleaning up

The matrix and the suite remove their stacks as they go. Soaks stop their stacks but keep the volumes for inspection. To remove everything:

```bash
docker ps -aq --filter label=com.docker.compose.project | xargs -r docker rm -f
docker volume ls -q --filter label=com.docker.compose.project | xargs -r docker volume rm
```
