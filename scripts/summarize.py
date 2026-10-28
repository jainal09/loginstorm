#!/usr/bin/env python3
"""Sums up a perf-suite.sh run (results/<run>/<budget>/<introspect|userinfo|login>/<profile>/) as one
markdown table per budget and test, and writes all the numbers to results/<run>/summary.json for charts.

Usage: python3 scripts/summarize.py results/<run>
"""
import csv
import json
import os
import re
import statistics
import sys
from pathlib import Path

RESULTS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results'))


def runs(folder):
    """runs.csv rows of one run-matrix.sh folder, by profile."""
    out = {}
    path = folder / 'runs.csv'
    if path.exists():
        for r in csv.DictReader(path.open()):
            out.setdefault(r['profile'], []).append(r)
    return out


def stack_samples(path):
    """(epoch, cpu %, MiB) of a whole stack from collect-cgroup.sh."""
    rows, prev = [], None
    if path.exists():
        for r in csv.DictReader(path.open()):
            try:
                t, usec, mem = float(r['epoch']), int(r['cpu_usec']), int(r['mem_bytes']) / 2**20
            except (ValueError, KeyError, TypeError):
                continue
            if prev and t > prev[0]:
                rows.append((t, 100 * (usec - prev[1]) / 1e6 / (t - prev[0]), mem))
            prev = (t, usec)
    return rows


def between(samples, run):
    return [s for s in samples if float(run['start_epoch']) <= s[0] <= float(run['end_epoch'])]


def level_result(summary_path, step):
    s = json.loads(summary_path.read_text())
    m, cfg = s['metrics'], s['config']
    seconds = int(re.fullmatch(r'(\d+)s', cfg['duration']).group(1))
    trend = m.get(f'idp_{step}', {}).get('values', {})
    return {
        'achieved_per_s': m.get('iterations', {}).get('values', {}).get('count', 0) / seconds,
        'dropped': m.get('dropped_iterations', {}).get('values', {}).get('count', 0),
        'checks': m.get('checks', {}).get('values', {}).get('rate'),
        'p50_ms': trend.get('med'), 'p95_ms': trend.get('p(95)'), 'p99_ms': trend.get('p(99)'),
    }


def profile_result(folder, name, profile_runs, test):
    d = folder / name
    meta = json.loads((d / 'meta.json').read_text()) if (d / 'meta.json').exists() else {}
    samples = stack_samples(d / 'stats-stack.csv')
    out = {'ready': meta.get('ready'), 'provisioned': meta.get('provisioned'), 'startup_s': meta.get('startup_s'),
           'oom_kills': meta.get('stack_oom_kills'), 'levels': {}}
    idle = next((r for r in profile_runs if r['level_var'] == 'idle'), None)
    idle_samples = between(samples, idle) if idle else []
    out['idle_mib'] = statistics.mean(s[2] for s in idle_samples) if idle_samples else None
    out['peak_mib'] = max((s[2] for s in samples), default=None)
    step = 'login_total' if test == 'login' else test
    for r in profile_runs:
        if r['level_var'] == 'idle':
            continue
        path = d / f"{r['level_var']}-{r['level']}.json"
        if not path.exists():
            out['levels'][r['level']] = {'error': f"no summary (k6 exit {r['k6_exit']})"}
            continue
        result = level_result(path, step)
        window = between(samples, r)
        result['stack_cpu_pct'] = statistics.mean(s[1] for s in window) if window else None
        result['stack_mem_mib'] = max((s[2] for s in window), default=None)
        out['levels'][r['level']] = result
    good = [v for v in out['levels'].values() if v.get('checks') is not None and v['checks'] >= 0.99]
    out['best_per_s'] = max((v['achieved_per_s'] for v in good), default=None)
    return out


def fmt(v, digits=0, unit=''):
    return '-' if v is None else f'{v:,.{digits}f}{unit}'


def main(run):
    data = {}
    for budget in sorted(p for p in run.iterdir() if p.is_dir()):
        for test in ('introspect', 'userinfo', 'login'):
            folder = budget / test
            if not folder.is_dir():
                continue
            # Every profile folder counts, including stacks that never got as far as a load level.
            by_profile = runs(folder)
            for name in sorted(p.name for p in folder.iterdir() if (p / 'meta.json').exists()):
                data.setdefault(budget.name, {}).setdefault(test, {})[name] = \
                    profile_result(folder, name, by_profile.get(name, []), test)

    for budget, tests in data.items():
        print(f'## {budget}\n')
        for test, profiles in tests.items():
            levels = sorted({lvl for p in profiles.values() for lvl in p['levels']}, key=float)
            unit = 'VUs' if test == 'login' else '/s'
            print(f"### {test}: {'sessions per second' if test == 'login' else 'calls per second achieved'}, p95 in brackets\n")
            print('| Profile | Idle stack | Best | ' + ' | '.join(f'{lvl} {unit}' for lvl in levels) + ' |')
            print('|---|---:|---:|' + '---:|' * len(levels))
            for name, p in profiles.items():
                cells = []
                for lvl in levels:
                    v = p['levels'].get(lvl)
                    if not v:
                        cells.append('-')
                    elif 'error' in v:
                        cells.append(v['error'])
                    else:
                        bad = '' if v['checks'] is not None and v['checks'] >= 0.99 else f", checks {100 * (v['checks'] or 0):.0f}%"
                        cells.append(f"{fmt(v['achieved_per_s'], 1)} ({fmt(v['p95_ms'], 0, ' ms')}{bad})")
                state = '' if p['provisioned'] is not False else ' (provisioning failed)'
                if p['oom_kills']:
                    state += f" ({p['oom_kills']} OOM kills)"
                print(f"| {name}{state} | {fmt(p['idle_mib'], 0, ' MiB')} | {fmt(p['best_per_s'], 1)} | " + ' | '.join(cells) + ' |')
            print()
    (run / 'summary.json').write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    # Only run folders under results/ are read (and get the summary).
    target = os.path.realpath(sys.argv[1])
    if os.path.commonpath([RESULTS, target]) != RESULTS:
        sys.exit(f'{target} is not a folder under {RESULTS}')
    main(Path(target))
