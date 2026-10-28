#!/usr/bin/env python3
"""One-screen health check of a running or finished soak.sh run.

Usage: python3 scripts/soak-status.py results/<run>
"""
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def last_line(path):
    try:
        with path.open() as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines[-1] if len(lines) > 1 else ''
    except OSError:
        return ''


def container(name):
    out = subprocess.run(['docker', 'inspect', '-f', '{{.State.Status}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}', name],
                         capture_output=True, text=True).stdout.strip()
    return out or 'missing'


RESULTS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results'))


def main(run):
    # Only soak folders under results/ are read.
    run = os.path.realpath(run)
    if os.path.commonpath([RESULTS, run]) != RESULTS:
        sys.exit(f'{run} is not a folder under {RESULTS}')
    run = Path(run)
    print((run / 'soak.log').read_text().strip().splitlines()[0])
    for line in (run / 'soak.log').read_text().strip().splitlines()[1:]:
        if line.startswith(('resumed', 'finished')) or 'OOM' in line:
            print(line)
    print(f"now {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    for d in sorted(p for p in run.iterdir() if p.is_dir()):
        log = (d / 'load.log').read_text().splitlines() if (d / 'load.log').exists() else []
        done = [line for line in log if line.endswith(' done')]
        worst = None
        for f in sorted(d.glob('*-[0-9][0-9][0-9].json'))[-12:]:
            rate = json.loads(f.read_text())['metrics'].get('checks', {}).get('values', {}).get('rate')
            if rate is not None:
                worst = rate if worst is None else min(worst, rate)
        mem = last_line(d / 'stats-idp.csv').split(',')
        print(f"{d.name}: {container('soak-' + d.name + '-idp')}")
        print(f"  chunks done {len(done)}; last: {log[-1] if log else '-'}")
        print(f"  worst checks in the last 12 summaries: {'-' if worst is None else f'{100 * worst:.2f}%'}")
        stack = last_line(d / 'stats-stack.csv').split(',')
        stack_mem = f'; whole stack {int(stack[2]) / 2**20:.0f} MiB, {stack[5]} OOM kills' if len(stack) > 5 else ''
        print(f"  memory now: {mem[2] if len(mem) > 2 else '-'}{stack_mem}; database: {last_line(d / 'db.csv') or '-'}")
        if (d / 'cleanup.csv').exists():
            print(f"  last cleanup: {last_line(d / 'cleanup.csv') or 'none yet'}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else sorted(Path('results').glob('soak-*'))[-1])
