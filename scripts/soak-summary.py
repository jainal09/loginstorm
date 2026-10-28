#!/usr/bin/env python3
"""Sums up a soak.sh run: per stack, how latency, memory and the database moved from the first
hours to the last, and every crash or OOM kill. Writes results/<run>/soak-summary.json with the
hourly series for charts.

Usage: python3 scripts/soak-summary.py results/<run>
"""
import csv
import json
import os
import statistics
import sys
from pathlib import Path

RESULTS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results'))
EDGE = 6  # chunks (hours) compared at each end of the run


def chunk_series(d, kind, metric):
    """One row per k6 chunk: the chunk number, its p95 for the metric, and the share of checks passed."""
    rows = []
    for f in sorted(d.glob(f'{kind}-[0-9][0-9][0-9].json')):
        try:
            m = json.loads(f.read_text())['metrics']
        except (ValueError, KeyError):
            continue
        rows.append({'chunk': int(f.stem.split('-')[1]),
                     'p95_ms': m.get(f'idp_{metric}', {}).get('values', {}).get('p(95)'),
                     'checks': m.get('checks', {}).get('values', {}).get('rate')})
    return rows


def hourly_memory(path):
    """Mean whole-stack memory (MiB) for each hour of the run."""
    hours = {}
    if path.exists():
        for r in csv.DictReader(path.open()):
            try:
                hours.setdefault(int(float(r['epoch']) // 3600), []).append(int(r['mem_bytes']) / 2**20)
            except (ValueError, KeyError, TypeError):
                continue
    return [{'hour': h, 'mib': statistics.mean(v)} for h, v in sorted(hours.items())]


def slope_per_day(points):
    """Least-squares slope (per day) over the second half, so warm-up doesn't count as growth."""
    pts = points[len(points) // 2:]
    if len(pts) < 6:
        return None
    xs, ys = [p[0] / 24 for p in pts], [p[1] for p in pts]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else None


def edges(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None, None
    n = min(EDGE, len(vals) // 2)
    return statistics.median(vals[:n]), statistics.median(vals[-n:])


def events(run):
    """Container events by name, deduplicated (a resumed logger replays what Docker still holds)."""
    seen, out = set(), {}
    path = run / 'events.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            key = (e.get('timeNano'), e.get('id'), e.get('Action') or e.get('status'))
            if key in seen:
                continue
            seen.add(key)
            name = e.get('Actor', {}).get('Attributes', {}).get('name', '')
            out.setdefault(name, []).append({'time': e.get('time'), 'action': e.get('Action') or e.get('status'),
                                             'exit_code': e.get('Actor', {}).get('Attributes', {}).get('exitCode')})
    return out


def fmt(v, digits=0, unit=''):
    return '-' if v is None else f'{v:,.{digits}f}{unit}'


def main(run):
    by_container = events(run)
    summary = {}
    for d in sorted(p for p in run.iterdir() if p.is_dir()):
        api, logins = chunk_series(d, 'api', 'introspect'), chunk_series(d, 'logins', 'login_total')
        if not api and not logins:
            continue
        memory = hourly_memory(d / 'stats-stack.csv')
        db = list(csv.DictReader((d / 'db.csv').open())) if (d / 'db.csv').exists() else []
        crashes = [e for name, evs in by_container.items() if name.startswith(f'soak-{d.name}-')
                   for e in evs if e['action'] in ('die', 'oom') and e['exit_code'] not in (None, '0')]
        ooms = [e for name, evs in by_container.items() if name.startswith(f'soak-{d.name}-')
                for e in evs if e['action'] == 'oom']
        first_mem, last_mem = edges([m['mib'] for m in memory])
        first_api, last_api = edges([r['p95_ms'] for r in api])
        first_login, last_login = edges([r['p95_ms'] for r in logins])
        h0 = memory[0]['hour'] if memory else 0
        summary[d.name] = {
            'chunks': len(api), 'worst_checks': min((r['checks'] for r in api + logins if r['checks'] is not None), default=None),
            'introspect_p95_first_ms': first_api, 'introspect_p95_last_ms': last_api,
            'login_p95_first_ms': first_login, 'login_p95_last_ms': last_login,
            'mem_first_mib': first_mem, 'mem_last_mib': last_mem,
            'mem_slope_mib_per_day': slope_per_day([(m['hour'] - h0, m['mib']) for m in memory]),
            'db_first': db[0] if db else None, 'db_last': db[-1] if db else None,
            'crashes': crashes, 'oom_kills': ooms,
            'series': {'api': api, 'logins': logins, 'memory': memory, 'db': db},
        }

    print(f'# Soak: {run.name}\n')
    print(f'First and last {EDGE} hours compared (medians of hourly values).\n')
    print('| Stack | Hours | Worst checks | Introspect p95 first / last | Login p95 first / last | Memory first / last | Memory trend | Database first / last | Crashes | OOM kills |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for name, s in summary.items():
        db = '-'
        if s['db_first'] and s['db_last']:
            size = lambda r: int(r['db_bytes']) / 2**20 if r.get('db_bytes', '').isdigit() else None
            db = f"{fmt(size(s['db_first']), 1, ' MiB')} / {fmt(size(s['db_last']), 1, ' MiB')}"
        print(f"| {name} | {s['chunks']} | {fmt(100 * s['worst_checks'] if s['worst_checks'] is not None else None, 2, '%')} | "
              f"{fmt(s['introspect_p95_first_ms'], 1, ' ms')} / {fmt(s['introspect_p95_last_ms'], 1, ' ms')} | "
              f"{fmt(s['login_p95_first_ms'], 0, ' ms')} / {fmt(s['login_p95_last_ms'], 0, ' ms')} | "
              f"{fmt(s['mem_first_mib'], 0, ' MiB')} / {fmt(s['mem_last_mib'], 0, ' MiB')} | "
              f"{fmt(s['mem_slope_mib_per_day'], 1, ' MiB/day')} | {db} | {len(s['crashes'])} | {len(s['oom_kills'])} |")
    (run / 'soak-summary.json').write_text(json.dumps(summary, indent=1))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    # Only run folders under results/ are read (and get the summary).
    target = os.path.realpath(sys.argv[1])
    if os.path.commonpath([RESULTS, target]) != RESULTS:
        sys.exit(f'{target} is not a folder under {RESULTS}')
    main(Path(target))
