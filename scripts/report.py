#!/usr/bin/env python3
"""Turns a run-matrix.sh output folder into a markdown comparison."""
import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

UNITS = {'B': 1, 'kB': 1e3, 'KB': 1e3, 'MB': 1e6, 'GB': 1e9,
         'KiB': 2**10, 'MiB': 2**20, 'GiB': 2**30, 'TiB': 2**40}


def mib(text):
    m = re.fullmatch(r'\s*([0-9.]+)\s*([A-Za-z]+)\s*', text)
    return float(m.group(1)) * UNITS[m.group(2)] / 2**20 if m and m.group(2) in UNITS else None


def p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))] if ordered else None


def load_stats(path):
    rows = []
    if path.exists():
        for r in csv.DictReader(path.open()):
            try:
                rows.append((float(r['epoch']), float(r['cpu_percent'].rstrip('%')), mib(r['mem_used'])))
            except (ValueError, KeyError, AttributeError):
                continue
    return rows


def load_stack(path):
    """Whole-stack samples from collect-cgroup.sh as (epoch, cpu %, MiB), like load_stats."""
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


def window(stats, run):
    return [s for s in stats if float(run['start_epoch']) <= s[0] <= float(run['end_epoch'])]


def mem_trend(rows):
    """Least-squares memory slope in MiB per hour over the window's second half, so warm-up
    after start doesn't read as growth; None for short windows."""
    pts = [(s[0], s[2]) for s in rows if s[2] is not None]
    pts = pts[len(pts) // 2:]
    if len(pts) < 30 or pts[-1][0] - pts[0][0] < 300:
        return None
    t0 = pts[0][0]
    xs, ys = [(t - t0) / 3600 for t, _ in pts], [m for _, m in pts]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else None


def seconds(duration):
    m = re.fullmatch(r'(\d+)(ms|s|m|h)', duration or '')
    return int(m.group(1)) * {'ms': 0.001, 's': 1, 'm': 60, 'h': 3600}[m.group(2)] if m else None


def summarize(rows):
    cpu = [s[1] for s in rows]
    mem = [s[2] for s in rows if s[2] is not None]
    return {'cpu_mean': statistics.mean(cpu) if cpu else None, 'cpu_p95': p95(cpu),
            'mem_mean': statistics.mean(mem) if mem else None, 'mem_max': max(mem) if mem else None}


def jvm_gc(path):
    gcs = defaultdict(float)
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r'jvm_gc_pause_seconds_count\{([^}]*)\}\s+(\S+)', line)
            if m:
                gcs[re.search(r'gc="([^"]+)"', m.group(1)).group(1)] += float(m.group(2))
    return ', '.join(f'{k} x{int(v)}' for k, v in gcs.items())


def storage(path):
    out = {'image_mb': 0.0, 'volume_mb': 0.0, 'db_mb': None}
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if parts[0] == 'image' and len(parts) == 3 and parts[2].isdigit():
                out['image_mb'] += int(parts[2]) / 1e6
            elif parts[0] == 'volume' and len(parts) == 3 and parts[2].isdigit():
                out['volume_mb'] += int(parts[2]) / 1024
            elif parts[0] == 'db_bytes' and len(parts) == 2 and parts[1].isdigit():
                out['db_mb'] = int(parts[1]) / 2**20
    return out


def metric(metrics, step):
    return (metrics.get(f'idp_{step}') or metrics.get(f'kc_{step}') or {}).get('values', {})


def fmt(value, unit='', digits=0):
    return '-' if value is None else f'{value:.{digits}f}{unit}'


RESULTS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results'))


def main(out):
    # Only run folders under results/ are read.
    out = os.path.realpath(out)
    if os.path.commonpath([RESULTS, out]) != RESULTS:
        sys.exit(f'{out} is not a folder under {RESULTS}')
    out = Path(out)
    runs = defaultdict(list)
    for r in csv.DictReader((out / 'runs.csv').open()):
        # Older runs.csv files only had a vus column.
        if 'level' not in r:
            r = {**r, 'level_var': 'idle' if r['vus'] == '0' else 'vus', 'level': r['vus']}
        # runs.csv names files below; accept only what run-matrix.sh writes.
        if re.fullmatch(r'[\w.-]+', r['profile']) and re.fullmatch(r'[\w.,-]+', r['level']) \
                and re.fullmatch(r'[a-z_]+', r['level_var']):
            runs[r['profile']].append(r)
    profiles = sorted(p.name for p in out.iterdir() if p.is_dir())

    print(f'# Identity provider bench: {out.name}\n')
    print('## Footprint\n')
    print('| Profile | Limit | Startup | Idle CPU | Idle mem | Peak mem | DB container idle / peak | Stack idle / peak '
          '| Image | Data on disk | OOM killed | Notes |')
    print('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|')
    for name in profiles:
        d = out / name
        meta = json.loads((d / 'meta.json').read_text()) if (d / 'meta.json').exists() else {}
        idp = load_stats(d / 'stats-idp.csv')
        db = load_stats(d / 'stats-db.csv')
        stack = load_stack(d / 'stats-stack.csv')
        idle = next((r for r in runs.get(name, []) if r['level_var'] == 'idle'), None)
        idle_idp = summarize(window(idp, idle)) if idle else summarize([])
        idle_db = summarize(window(db, idle)) if idle and db else None
        idle_stack = summarize(window(stack, idle)) if idle and stack else None
        peak = max((s[2] for s in idp if s[2] is not None), default=None)
        db_peak = max((s[2] for s in db if s[2] is not None), default=None)
        cpus, mem = meta.get('nano_cpus', 0) / 1e9, meta.get('memory', 0) / 2**20
        limit = f'{cpus:g} CPU / {mem:.0f} MiB' if cpus or mem else 'none'
        if meta.get('stack_cpus'):
            limit = f"stack {meta['stack_cpus']} CPU / {meta['stack_mem']}"
        st = storage(d / 'storage.txt')
        data = st['volume_mb'] + (meta.get('size_rw') or 0) / 2**20
        db_cell = f"{fmt(idle_db['mem_mean'], ' MiB')} / {fmt(db_peak, ' MiB')}" if idle_db else '-'
        stack_peak = max((s[2] for s in stack), default=None)
        stack_cell = f"{fmt(idle_stack['mem_mean'], ' MiB')} / {fmt(stack_peak, ' MiB')}" if idle_stack else '-'
        notes = []
        if st['db_mb'] is not None:
            notes.append(f"database {st['db_mb']:.0f} MiB")
        gc = jvm_gc(d / 'metrics.txt')
        if gc:
            notes.append(gc)
        if not meta.get('ready', True):
            notes.append('never became ready')
        if not meta.get('provisioned', True):
            notes.append('provisioning failed')
        if meta.get('exit_code'):
            notes.append(f"exit {meta['exit_code']}")
        if meta.get('stack_oom_kills'):
            notes.append(f"{meta['stack_oom_kills']} OOM kills in the stack")
        print(f"| {name} | {limit} | {fmt(meta.get('startup_s'), 's', 1)} | {fmt(idle_idp['cpu_mean'], '%', 1)} | "
              f"{fmt(idle_idp['mem_mean'], ' MiB')} | {fmt(peak, ' MiB')} | {db_cell} | {stack_cell} | {fmt(st['image_mb'], ' MB')} | "
              f"{fmt(data, ' MiB', 1)} | {meta.get('oom_killed', '-')} | {'; '.join(notes)} |")

    load, api, lockout = [], [], []
    for name in profiles:
        idp = load_stats(out / name / 'stats-idp.csv')
        db = load_stats(out / name / 'stats-db.csv')
        stack = load_stack(out / name / 'stats-stack.csv')
        for r in runs.get(name, []):
            if r['level_var'] == 'idle':
                continue
            summary_path = out / name / f"{r['level_var']}-{r['level']}.json"
            if not summary_path.exists():
                load.append(f"| {name} | {r['level']} | no summary (k6 exit {r['k6_exit']}) | | | | | | | | | | | | | |")
                continue
            summary = json.loads(summary_path.read_text())
            metrics, scenario = summary['metrics'], summary.get('config', {}).get('scenario', 'session')
            s = summarize(window(idp, r))
            dbs = summarize(window(db, r)) if db else None
            ss = summarize(window(stack, r)) if stack else None
            res = f"{fmt(s['cpu_mean'], '%')} | {fmt(s['cpu_p95'], '%')} | {fmt(s['mem_mean'], ' MiB')} | " \
                  f"{fmt(s['mem_max'], ' MiB')} | {fmt(dbs['mem_max'] if dbs else None, ' MiB')} | " \
                  f"{fmt(ss['cpu_mean'] if ss else None, '%')} | {fmt(ss['mem_max'] if ss else None, ' MiB')}"
            checks = fmt(100 * metrics['checks']['values']['rate'], '%', 1) if 'checks' in metrics else '-'
            if scenario == 'lockout':
                def outcome(key):
                    v = metric(metrics, key).get('min')
                    return '-' if v is None else ('accepted' if v == 1 else '**refused**')
                steps = [k[len('idp_lockout_after_'):] for k in metrics if k.startswith('idp_lockout_after_')]
                wrong = metric(metrics, 'lockout_wrong_ms')
                lockout.append(f"| {name} | {outcome('lockout_before')} | "
                               + ' | '.join(f"after {n} wrong: {outcome(f'lockout_after_{n}')}" for n in sorted(steps, key=int))
                               + f" | {outcome('lockout_other_user')} | {fmt(wrong.get('med'), 'ms')} / "
                               f"{fmt(wrong.get('max'), 'ms')} |")
            elif scenario == 'api':
                call = summary['config'].get('api_call', 'introspect')
                v = metric(metrics, call)
                dur = seconds(summary['config'].get('duration'))
                done = metrics['iterations']['values']['count'] if 'iterations' in metrics else 0
                dropped = metrics.get('dropped_iterations', {}).get('values', {}).get('count', 0)
                api.append(f"| {name} | {call} | {r['level']} | {fmt(done / dur if dur else None, '', 1)} | "
                           f"{dropped} | {fmt(v.get('med'), 'ms')} | {fmt(v.get('p(95)'), 'ms')} | "
                           f"{fmt(v.get('max'), 'ms')} | {checks} | {res} | "
                           f"{fmt(mem_trend(window(idp, r)), ' MiB/h', 1)} |")
            else:
                login, submit, refresh = metric(metrics, 'login_total'), metric(metrics, 'login_submit'), metric(metrics, 'refresh')
                load.append(f"| {name} | {r['level']} | {fmt(login.get('med'), 'ms')} | {fmt(login.get('p(95)'), 'ms')} | "
                            f"{fmt(login.get('max'), 'ms')} | {fmt(submit.get('p(95)'), 'ms')} | "
                            f"{fmt(refresh.get('p(95)'), 'ms')} | {fmt(metrics['iterations']['values']['rate'], '', 2)} | "
                            f"{checks} | {res} |")
    if load:
        print('\n## Load\n')
        print('| Profile | VUs | Login p50 | Login p95 | Login max | Password check p95 | Refresh p95 | Sessions/s '
              '| Checks ok | CPU mean | CPU p95 | Mem mean | Mem max | DB mem max | Stack CPU mean | Stack mem max |')
        print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        print('\n'.join(load))
    if api:
        print('\n## API token validation\n')
        print('| Profile | Call | Target/s | Achieved/s | Dropped | p50 | p95 | Max | Checks ok '
              '| CPU mean | CPU p95 | Mem mean | Mem max | DB mem max | Stack CPU mean | Stack mem max | Mem trend, 2nd half |')
        print('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        print('\n'.join(api))
    if lockout:
        print('\n## Lockout check\n')
        print('| Profile | Correct login before | Streaks | Untouched user, same IP | Wrong attempt med / max |')
        print('|---|---|---|---|---|')
        print('\n'.join(lockout))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else sorted(Path('results').iterdir())[-1])
