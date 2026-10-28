#!/usr/bin/env python3
"""Maintainer health of GitHub repos: how outside issues and PRs get answered, release cadence,
commit spread, security advisories and repo metadata, as one markdown table.

Issues and PRs are those created in [--since, --until), by default 194 to 14 days ago so each one
had two weeks to get an answer. Releases, commits and advisories count back from today.
Token: GITHUB_TOKEN, else `gh auth token`.
Usage: python3 -I tools/maintainer-health.py [--since YYYY-MM-DD --until YYYY-MM-DD] [--json out.json] owner/repo ...
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

API = 'https://api.github.com'
MAINTAINER = {'OWNER', 'MEMBER', 'COLLABORATOR'}
# Dependency bots open most PRs in some repos; bots are dropped anyway, so leave them out of search.
NOT_BOTS = '-author:app/dependabot -author:app/renovate'
WHO = 'login __typename'
ENTRIES = 'pageInfo { hasNextPage endCursor } nodes { createdAt authorAssociation author { %s } }' % WHO
# A review counts from when it was submitted; the alias gives reviews the shape of comments.
REVIEWS = 'pageInfo { hasNextPage endCursor } nodes { createdAt: submittedAt authorAssociation author { %s } }' % WHO
SEARCH = '''query($q: String!, $after: String) {
  search(query: $q, type: ISSUE, first: 100, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      __typename
      ... on Issue {
        id number createdAt state authorAssociation author { %(who)s }
        comments(first: 50) { %(entries)s }
        timelineItems(itemTypes: [CLOSED_EVENT], first: 5) { nodes { ... on ClosedEvent { createdAt actor { %(who)s } } } }
      }
      ... on PullRequest {
        id number createdAt state authorAssociation author { %(who)s } mergedBy { %(who)s }
        comments(first: 50) { %(entries)s }
        reviews(first: 50) { %(reviews)s }
      }
    }
  }
  rateLimit { cost }
}''' % {'who': WHO, 'entries': ENTRIES, 'reviews': REVIEWS}
MORE = 'query($id: ID!, $after: String) { node(id: $id) { ... on %s { %s(first: 100, after: $after) { %s } } } rateLimit { cost } }'
META = '''query($owner: String!, $name: String!, $discussions: String!) {
  repository(owner: $owner, name: $name) {
    stargazerCount forkCount isArchived createdAt hasIssuesEnabled hasDiscussionsEnabled
    licenseInfo { spdxId } defaultBranchRef { name }
    issues(states: OPEN) { totalCount } pullRequests(states: OPEN) { totalCount }
  }
  search(query: $discussions, type: DISCUSSION, first: 1) { discussionCount }
  rateLimit { cost }
}'''
TAGS = '''query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/tags/", first: 100, after: $after, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { target { ... on Commit { committedDate } ... on Tag { tagger { date } target { ... on Commit { committedDate } } } } }
    }
  }
  rateLimit { cost }
}'''
HEADERS = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
           'User-Agent': 'loginstorm-maintainer-health'}
calls = Counter()


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def ts(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def backoff(headers, text):
    """Seconds to wait out a 403/429, or None when it isn't a rate limit."""
    if headers.get('retry-after'):
        return int(headers['retry-after'])
    if headers.get('x-ratelimit-remaining') == '0':
        return max(0, int(headers.get('x-ratelimit-reset', 0)) - time.time()) + 1
    # A secondary limit without either header: GitHub asks for at least a minute.
    return 60 if 'rate limit' in text.lower() else None


def fetch(url, body=None):
    """(status, headers, decoded body) of one call; waits out rate limits, retries network and 5xx errors."""
    for attempt in range(8):
        req = urllib.request.Request(url, headers=HEADERS, data=None if body is None else json.dumps(body).encode())
        calls['graphql' if body else 'rest'] += 1
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                return res.status, res.headers, json.loads(res.read() or b'null')
        except urllib.error.HTTPError as e:
            status, headers, text = e.code, e.headers, e.read().decode(errors='replace')
        except OSError as e:
            status, headers, text = None, {}, str(e)
        wait = backoff(headers, text) if status in (403, 429) else None
        if wait is None and status is not None and status < 500:
            return status, headers, json.loads(text) if text.startswith(('{', '[')) else text
        wait = min(60, 2 ** attempt) if wait is None else wait
        log(f'  {url}: {status or text}, retrying in {wait:.0f}s')
        time.sleep(wait)
    sys.exit(f'giving up on {url}')


def graphql(query, **variables):
    for attempt in range(5):
        status, headers, res = fetch(f'{API}/graphql', {'query': query, 'variables': variables})
        data = res.get('data') if isinstance(res, dict) else None
        if status == 200 and data and all(v is not None for v in data.values()):
            calls['points'] += data['rateLimit']['cost']
            return data
        errors = res.get('errors') or [res] if isinstance(res, dict) else [{'message': res}]
        if any(e.get('type') == 'RATE_LIMITED' for e in errors):
            time.sleep(backoff(headers, 'rate limit'))
        elif status == 200 and not any(e.get('type') for e in errors):
            # Untyped errors on a 200 are timeouts on GitHub's side.
            time.sleep(10 * (attempt + 1))
        else:
            sys.exit(f"GraphQL: {errors[0].get('message')}")
    sys.exit(f"GraphQL kept failing: {errors[0].get('message')}")


def rest(repo, tail):
    # quote() keeps the owner/repo slash and escapes anything that could change the URL.
    return f'{API}/repos/{urllib.parse.quote(repo)}/{tail}'


def listing(url, enough=lambda page: False):
    """All items of a paginated REST list, or None if the endpoint fails; stops early once enough(page)."""
    items = []
    while url:
        status, headers, page = fetch(url)
        if status != 200:
            log(f'  {url}: HTTP {status}')
            return None
        items += page
        if enough(page):
            break
        # Only follow next links back to the API itself.
        m = re.search(r'<(https://api\.github\.com/[^>]+)>;\s*rel="next"', headers.get('link') or '')
        url = m and m.group(1)
    return items


def actor(a):
    """Login of a person; None for bots and deleted accounts."""
    if a and a['__typename'] != 'Bot' and not a['login'].endswith('[bot]'):
        return a['login']


def entries(conn):
    return [(e['createdAt'], actor(e['author']), e['authorAssociation']) for e in conn['nodes'] if e['createdAt']]


def cursor(conn):
    return conn['pageInfo']['endCursor'] if conn['pageInfo']['hasNextPage'] else None


def item(n):
    it = {'id': n['id'], 'number': n['number'], 'pr': n['__typename'] == 'PullRequest', 'created': n['createdAt'],
          'state': n['state'], 'author': actor(n['author']), 'bot': bool(n['author']) and not actor(n['author']),
          'assoc': n['authorAssociation'], 'comments': entries(n['comments']), 'more_comments': cursor(n['comments'])}
    if it['pr']:
        it.update(merged_by=actor(n['mergedBy']), reviews=entries(n['reviews']), more_reviews=cursor(n['reviews']))
    else:
        closes = n['timelineItems']['nodes']
        it.update(closes=[(e['createdAt'], actor(e['actor'])) for e in closes],
                  bot_closed=any(e['actor'] and not actor(e['actor']) for e in closes))
    return it


def stamp(d):
    return f'{d:%Y-%m-%dT%H:%M:%S}+00:00'


def search(repo, start, end):
    """(items, count search reported) for issues and PRs created in [start, end). Search stops at 1000
    results, so a busy range is cut into slices of about 800 and each slice checked again."""
    q = f'repo:{repo} created:{stamp(start)}..{stamp(end - timedelta(seconds=1))} {NOT_BOTS} sort:created-asc'
    found, after = [], None
    while True:
        page = graphql(SEARCH, q=q, after=after)['search']
        if after is None and page['issueCount'] > 1000 and end - start > timedelta(hours=1):
            slices = page['issueCount'] // 800 + 1
            cuts = [(start + (end - start) * i / slices).replace(microsecond=0) for i in range(slices)] + [end]
            parts = [search(repo, a, b) for a, b in zip(cuts, cuts[1:])]
            return [it for p, _ in parts for it in p], sum(c for _, c in parts)
        found += [item(n) for n in page['nodes'] if n]
        if not page['pageInfo']['hasNextPage']:
            return found, page['issueCount']
        after = page['pageInfo']['endCursor']


def maintainers(items):
    """Logins seen with a maintainer association, and the others that merged a PR or closed someone
    else's issue. Both of those need write or triage rights, and org members who keep their
    membership private show up as CONTRIBUTOR, so the second set is how they get found."""
    assoc, rights = set(), set()
    for it in items:
        for _, who, a in [(None, it['author'], it['assoc'])] + it['comments'] + it.get('reviews', []):
            if who and a in MAINTAINER:
                assoc.add(who)
        rights |= {who for _, who in it.get('closes', []) if who and who != it['author']}
        if it.get('merged_by'):
            rights.add(it['merged_by'])
    return assoc, rights - assoc


def first(events, maint):
    return min((e[0] for e in events if e[1] in maint), default=None)


def complete(items, maint):
    """Pages through long threads that have no maintainer comment or review in the first page."""
    for it in items:
        for field, shape in (('comments', ENTRIES), ('reviews', REVIEWS)):
            while it.get('more_' + field) and first(it[field], maint) is None:
                kind = 'PullRequest' if it['pr'] else 'Issue'
                conn = graphql(MORE % (kind, field, shape), id=it['id'], after=it['more_' + field])['node'][field]
                it[field] += entries(conn)
                it['more_' + field] = cursor(conn)


def pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def median(values):
    return round(statistics.median(values), 1) if values else None


def elapsed(created, when, unit):
    return (ts(when) - ts(created)).total_seconds() / unit if when else None


def issue_stats(items, maint):
    rows, by_maintainers = [], 0
    for it in items:
        if it['pr'] or it['bot']:
            continue
        if it['author'] in maint:
            by_maintainers += 1
            continue
        answer = min(filter(None, [first(it['comments'], maint), first(it['closes'], maint)]), default=None)
        rows.append({'number': it['number'], 'author': it['author'], 'created': it['created'], 'state': it['state'],
                     'first_answer': answer, 'hours': elapsed(it['created'], answer, 3600),
                     'bot_closed': it['bot_closed']})
    hours = [r['hours'] for r in rows if r['hours'] is not None]
    n = len(rows)
    for r in rows:
        r['hours'] = r['hours'] if r['hours'] is None else round(r['hours'], 1)
    return {'outside': n, 'answered_7d_pct': pct(sum(h <= 168 for h in hours), n), 'median_hours': median(hours),
            'open_pct': pct(sum(r['state'] == 'OPEN' for r in rows), n), 'never_answered_pct': pct(n - len(hours), n),
            'bot_closed': sum(r['bot_closed'] for r in rows), 'by_maintainers': by_maintainers, 'items': rows}


def pr_stats(items, maint):
    rows = []
    for it in items:
        if it['pr'] and not it['bot'] and it['author'] not in maint:
            answer = first(it['comments'] + it['reviews'], maint)
            rows.append({'number': it['number'], 'author': it['author'], 'created': it['created'], 'state': it['state'],
                         'first_review': answer, 'days': elapsed(it['created'], answer, 86400)})
    days = [r['days'] for r in rows if r['days'] is not None]
    n = len(rows)
    for r in rows:
        r['days'] = r['days'] if r['days'] is None else round(r['days'], 2)
    states = Counter(r['state'] for r in rows)
    return {'outside': n, 'merged_pct': pct(states['MERGED'], n), 'closed_unmerged_pct': pct(states['CLOSED'], n),
            'open_pct': pct(states['OPEN'], n), 'median_days_to_review': median(days), 'reviewed': len(days),
            'items': rows}


def tag_dates(repo, year):
    """Tag dates (tagger date for annotated tags), newest first, back to a year ago."""
    owner, name = repo.split('/')
    dates, after = [], None
    while True:
        refs = graphql(TAGS, owner=owner, name=name, after=after)['repository']['refs']
        for t in (n['target'] for n in refs['nodes']):
            d = (t.get('tagger') or {}).get('date') or t.get('committedDate') or (t.get('target') or {}).get('committedDate')
            if d:
                dates.append(ts(d))
        if not refs['pageInfo']['hasNextPage'] or (dates and min(dates) < year):
            return dates
        after = refs['pageInfo']['endCursor']


def releases(repo, now):
    year = now - timedelta(days=365)
    found = listing(rest(repo, 'releases?per_page=100'), lambda page: all(ts(r['created_at']) < year for r in page))
    dates = [ts(r['published_at']) for r in found or [] if not r['draft'] and r['published_at']]
    source = 'releases' if dates else 'tags'
    if not dates:
        dates = tag_dates(repo, year)
    recent = sorted(d for d in dates if d >= year)
    gaps = [(b - a).total_seconds() / 86400 for a, b in zip(recent, recent[1:])]
    return {'source': source, 'last_365d': len(recent), 'latest': max(dates).date().isoformat() if dates else None,
            'median_days_between': median(gaps)}


def commits(repo, now, status, data):
    # GitHub computes these in the background and answers 202 until they are ready.
    for wait in (5, 10, 20, 30, 30, 60, 60):
        if status != 202:
            break
        time.sleep(wait)
        status, _, data = fetch(rest(repo, 'stats/contributors'))
    if status != 200 or not isinstance(data, list):
        return None
    cutoff = now.timestamp() - 52 * 7 * 86400
    per = Counter()
    for c in data:
        a = c.get('author') or {}
        if a.get('type') != 'Bot' and not a.get('login', '').endswith('[bot]'):
            per[a.get('login', '?')] += sum(w['c'] for w in c['weeks'] if w['w'] >= cutoff)
    per = +per
    total, top = sum(per.values()), [n for _, n in per.most_common(3)]
    # The list holds only the top contributors (100, or 500 for some big repos), so totals are a floor.
    return {'total': total, 'authors': len(per), 'top_author_pct': pct(top[0], total) if top else None,
            'top3_pct': pct(sum(top), total), 'top': per.most_common(5), 'listed': len(data), 'capped': len(data) >= 100}


def advisories(repo, now):
    found = listing(rest(repo, 'security-advisories?state=published&per_page=100'))
    cutoff = now - timedelta(days=730)
    recent = [a for a in found or [] if a.get('published_at') and ts(a['published_at']) >= cutoff]
    return {'last_24m': len(recent), 'by_severity': dict(Counter(a['severity'] or 'unknown' for a in recent)),
            'published_total': len(found or []), 'endpoint_ok': found is not None,
            'items': [{'ghsa': a['ghsa_id'], 'cve': a['cve_id'], 'severity': a['severity'],
                       'published': a['published_at'][:10], 'summary': a['summary']} for a in recent]}


def metadata(repo, since, until):
    owner, name = repo.split('/')
    d = graphql(META, owner=owner, name=name,
                discussions=f'repo:{repo} created:{stamp(since)}..{stamp(until - timedelta(seconds=1))}')
    r = d['repository']
    return {'stars': r['stargazerCount'], 'forks': r['forkCount'], 'license': (r['licenseInfo'] or {}).get('spdxId'),
            'archived': r['isArchived'], 'default_branch': (r['defaultBranchRef'] or {}).get('name'),
            'open_issues': r['issues']['totalCount'], 'open_prs': r['pullRequests']['totalCount'],
            'created': r['createdAt'][:10], 'has_issues': r['hasIssuesEnabled'],
            'has_discussions': r['hasDiscussionsEnabled'], 'discussions_opened': d['search']['discussionCount']}


def analyze(repo, since, until, now, meta, stats):
    started = time.time()
    items, expected = search(repo, since, until)
    assoc, rights = maintainers(items)
    complete([it for it in items if not it['bot'] and it['author'] not in assoc | rights], assoc | rights)
    assoc, rights = maintainers(items)
    # The literal definition (association only), for comparison.
    strict = {'issues': issue_stats(items, assoc), 'prs': pr_stats(items, assoc)}
    for s in strict.values():
        del s['items']
    r = {'repo': meta, 'maintainers': {'by_association': sorted(assoc), 'by_merge_or_close': sorted(rights)},
         'issues': issue_stats(items, assoc | rights), 'prs': pr_stats(items, assoc | rights),
         'association_only': strict, 'releases': releases(repo, now), 'commits': commits(repo, now, *stats),
         'advisories': advisories(repo, now), 'search': {'found': len(items), 'reported': expected}}
    notes = []
    if meta['archived']:
        notes.append('archived')
    if not meta['has_issues']:
        notes.append('issues disabled')
    if r['releases']['source'] == 'tags':
        notes.append('no GitHub releases, tag dates used')
    if rights:
        notes.append(f'{len(rights)} maintainers found only by merges/closes')
    if r['issues']['bot_closed']:
        notes.append(f"{r['issues']['bot_closed']} outside issues closed by a bot")
    if meta['discussions_opened']:
        notes.append(f"{meta['discussions_opened']} discussions opened")
    if r['commits'] is None:
        notes.append('no contributor stats')
    if not r['advisories']['endpoint_ok']:
        notes.append('advisories endpoint failed')
    elif not r['advisories']['published_total']:
        notes.append('no GitHub advisories (some projects publish elsewhere)')
    if len(items) < expected:
        notes.append(f'search returned {len(items)} of {expected}')
    r['notes'] = notes
    log(f'{repo}: {len(items)} issues and PRs, {time.time() - started:.0f}s')
    return r


def fmt(value, unit='', digits=0):
    return '-' if value is None else f'{value:.{digits}f}{unit}'


def row(repo, r):
    m, i, p, rel, c, a = r['repo'], r['issues'], r['prs'], r['releases'], r['commits'], r['advisories']
    plus = '+' if c and c['capped'] else ''
    sev = ' '.join(f"{a['by_severity'][k]}{k[0].upper()}" for k in ('critical', 'high', 'medium', 'low', 'unknown')
                   if a['by_severity'].get(k))
    cells = [repo, f"{m['stars'] / 1000:.1f}k" if m['stars'] >= 1000 else m['stars'], m['license'] or '-',
             i['outside'], fmt(i['answered_7d_pct'], '%'), fmt(i['median_hours'], ' h', 1), fmt(i['open_pct'], '%'),
             fmt(i['never_answered_pct'], '%'), i['by_maintainers'],
             p['outside'], fmt(p['merged_pct'], '%'), fmt(p['closed_unmerged_pct'], '%'),
             fmt(p['median_days_to_review'], '', 1),
             rel['last_365d'], rel['latest'] or '-', fmt(rel['median_days_between'], '', 1),
             f"{c['total']}{plus}" if c else '-', f"{c['authors']}{plus}" if c else '-',
             fmt(c and c['top_author_pct'], '%'), fmt(c and c['top3_pct'], '%'),
             f"{a['last_24m']} ({sev})" if sev else a['last_24m'], '; '.join(r['notes'])]
    return '| ' + ' | '.join(str(x) for x in cells) + ' |'


def utc_date(text):
    return datetime.strptime(text, '%Y-%m-%d').replace(tzinfo=timezone.utc)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--since', type=utc_date, help='earliest creation date, inclusive (default: 194 days ago)')
    p.add_argument('--until', type=utc_date, help='creation date to stop before (default: 14 days ago)')
    p.add_argument('--json', help='also write the full per-repo data to this file, inside the current directory')
    p.add_argument('repos', nargs='+', metavar='owner/repo')
    args = p.parse_args()
    bad = [r for r in args.repos if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', r)]
    if bad:
        sys.exit(f'not owner/repo: {" ".join(bad)}')
    path = None
    if args.json:
        # Writes stay inside the current directory, checked now so a bad path doesn't waste a run.
        here, path = os.path.realpath(os.getcwd()), os.path.realpath(args.json)
        if os.path.commonpath([here, path]) != here or not os.path.isdir(os.path.dirname(path)):
            sys.exit('--json must be a file in an existing directory inside the current one')
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since, until = args.since or today - timedelta(days=194), args.until or today - timedelta(days=14)
    if since >= until:
        sys.exit('--since must be before --until')
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        try:
            token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
        except FileNotFoundError:
            pass
    if not token:
        sys.exit('set GITHUB_TOKEN or log in with gh')
    HEADERS['Authorization'] = f'Bearer {token}'
    started = time.time()

    # Ask for contributor stats first so GitHub computes them while the rest runs.
    stats = {}
    for repo in args.repos:
        status, _, data = fetch(rest(repo, 'stats/contributors'))
        stats[repo] = status, data
    # Metadata for every repo up front, so a wrong name fails before the long part.
    meta = {repo: metadata(repo, since, until) for repo in args.repos}
    results = {repo: analyze(repo, since, until, now, meta[repo], stats[repo]) for repo in args.repos}

    last = until - timedelta(days=1)
    print(f'# Maintainer health: issues and PRs opened {since:%Y-%m-%d} to {last:%Y-%m-%d}\n')
    print(f'Run {now:%Y-%m-%d}. Maintainers: authorAssociation OWNER, MEMBER or COLLABORATOR, plus anyone who '
          'merged a PR or closed someone else\'s issue (org members with private membership show up as '
          'CONTRIBUTOR). Bots are left out. Outside means opened by anyone else. An answer is the first '
          'maintainer comment or a close by a maintainer; for PRs, the first maintainer review or comment. '
          'Releases count back 365 days, commits 52 weeks and advisories 24 months. Commits come from '
          'GitHub\'s top-contributor list; + marks a list that may be cut off. Advisory severities: '
          'C critical, H high, M medium, L low.\n')
    print('| Repo | Stars | License | Outside issues | Answered in 7 days | Median first answer | Still open '
          '| Never answered | Maintainer issues | Outside PRs | Merged | Closed unmerged | Median days to first review '
          '| Releases, 365 days | Latest release | Median days between releases | Commits, 52 weeks | Commit authors '
          '| Top author | Top 3 authors | Advisories, 24 months | Notes |')
    print('|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|')
    for repo, r in results.items():
        print(row(repo, r))

    took = time.time() - started
    if path:
        with open(path, 'w') as f:
            json.dump({'since': f'{since:%Y-%m-%d}', 'until_exclusive': f'{until:%Y-%m-%d}',
                       'run_at': now.isoformat(timespec='seconds'), 'calls': dict(calls), 'seconds': round(took),
                       'repos': results}, f, indent=1)
    log(f"{calls['rest']} REST and {calls['graphql']} GraphQL calls ({calls['points']} points) in {took / 60:.1f} min")


if __name__ == '__main__':
    main()
