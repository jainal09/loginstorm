# Soak testing

Short tests show what a provider can do. A soak shows whether it keeps doing it. Some problems only appear after days of ordinary traffic:

- memory that grows by a megabyte an hour
- token tables that are never cleaned up, and the lookups that slow down as they grow
- a crash that needs a rare timing coincidence

## Running a soak

```bash
END_AT=2026-11-08T12:00:00Z STACK_CPUS=2 STACK_MEM=2G STACK_CPUSET=2-7 K6_CPUSET=0-1 \
  OUT=results/soak-1 scripts/soak.sh profiles/keycloak.env profiles/kanidm.env profiles/zitadel.env
```

Each profile gets:

- its own compose project, `soak-<profile>`, with its own containers, network, host ports and budget
- a restart policy, `unless-stopped`
- its own load loop: k6 runs in hourly chunks of introspection plus a trickle of logins

The runner also samples the stats described in [Getting started](getting-started.md#reading-the-output), each database's size and row count hourly (`db.csv`), and every container start, exit and OOM kill (`events.jsonl`).

On a machine with 8 vCPUs and 32 GB, 11 providers at 2 CPUs and 2 GiB each run comfortably. The soak load is light, and the budgets are limits, not reservations.

## Checking on it

```bash
python3 scripts/soak-status.py results/soak-1
```

For each stack, it prints:

- whether the identity provider's container is running, with its OOM flag and restart count
- the number of chunks done
- the worst pass rate of the last twelve chunks
- current memory, for the container and the whole stack
- the latest database sample

## Interruptions

A container that crashes comes back by itself, and `events.jsonl` keeps the exit code. One that the kernel OOM-killed comes back too, but the event log and the stack's OOM counter both record it.

If the runner itself stops (a reboot, a closed terminal), continue the same run:

```bash
RESUME=1 END_AT=2026-11-08T12:00:00Z STACK_CPUS=2 STACK_MEM=2G OUT=results/soak-1 scripts/soak.sh <same profiles, same order>
```

A resumed run:

- restarts stopped containers, except ones the kernel OOM-killed, since that is a result
- removes any k6 containers left from the interrupted chunk
- restarts the collectors
- carries on numbering chunks

The interrupted chunk keeps its partial output but has no summary.

### Resuming after a reboot automatically

On a dedicated VM, `infra/azure/loginstorm-soak.service` resumes the soak at boot. It expects the repository in `/home/bench/loginstorm`; edit the paths if yours differs.

```bash
sudo cp infra/azure/loginstorm-soak.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable loginstorm-soak
cat > results/soak-resume.env <<'EOF'
END_AT=2026-11-08T12:00:00Z
OUT=results/soak-1
STACK_CPUS=2
STACK_MEM=2G
STACK_CPUSET=2-7
K6_CPUSET=0-1
PROFILES="profiles/keycloak.env profiles/kanidm.env profiles/zitadel.env"
EOF
set -a; . results/soak-resume.env; set +a
setsid nohup scripts/soak.sh $PROFILES > results/soak-1.out 2>&1 < /dev/null &
```

Delete `results/soak-resume.env` when the soak is over, and the service does nothing at the next boot.

Budgets are written as persistent systemd properties, so restarted containers return to the same budget.

Two blind spots remain:

- Docker forgets its event history when its daemon restarts, so restarts that happen during boot show in `RestartCount` (in `inspect.json`) rather than in `events.jsonl`.
- `docker stats` streams end when the daemon restarts. The collectors start them again.

## At the end

At `END_AT` the runner:

1. takes a last database sample
2. saves each container's `docker inspect` and logs
3. stops the stacks without removing them

The volumes stay for inspection.

```bash
python3 scripts/soak-summary.py results/soak-1
```

The summary compares the first six hours with the last six for introspection p95, login p95, whole-stack memory and database size. It adds a memory trend in MiB per day, fitted over the second half of the run so warm-up doesn't count as growth, and lists every crash and OOM kill. `soak-summary.json` holds the hourly series for charts.

**Don't edit the scripts while a soak runs.** Bash reads a script as it executes it, so an edited file can break the running copy.
