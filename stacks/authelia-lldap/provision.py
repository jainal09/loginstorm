#!/usr/bin/env python3
"""Creates the bench users and their group in LLDAP (test-only values).

Users and the group go through LLDAP's GraphQL API; passwords through the
lldap_set_password tool in its image, because LLDAP stores them with OPAQUE.
Usage: BENCH_USER_PASSWORD=... BENCH_LDAP_ADMIN_PASSWORD=... provision.py [user-count]
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get('LLDAP_URL', 'http://127.0.0.1:17170')
CONTAINER = os.environ.get('LLDAP_CONTAINER', 'bench-db')
count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
ADMIN_PASSWORD = os.environ.get('BENCH_LDAP_ADMIN_PASSWORD') or sys.exit('set BENCH_LDAP_ADMIN_PASSWORD')


def post(path, body, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(f'{BASE}{path}', data=json.dumps(body).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read())


for _ in range(60):
    try:
        token = post('/auth/simple/login', {'username': 'admin', 'password': ADMIN_PASSWORD})['token']
        break
    except (urllib.error.URLError, ConnectionError):
        time.sleep(1)
else:
    sys.exit('LLDAP did not come up')


def gql(query, variables):
    out = post('/api/graphql', {'query': query, 'variables': variables}, token)
    if out.get('errors'):
        sys.exit(f"GraphQL error: {out['errors']}")
    return out['data']


group = gql('mutation($name: String!) { createGroup(name: $name) { id } }', {'name': 'users'})['createGroup']['id']
for i in range(1, count + 1):
    uid = f'bench-user-{i:02d}'
    gql('mutation($u: CreateUserInput!) { createUser(user: $u) { id } }',
        {'u': {'id': uid, 'email': f'{uid}@bench.test', 'displayName': f'Bench User{i:02d}'}})
    gql('mutation($u: String!, $g: Int!) { addUserToGroup(userId: $u, groupId: $g) { ok } }', {'u': uid, 'g': group})
    subprocess.run(['docker', 'exec', CONTAINER, '/app/lldap_set_password', '--base-url', 'http://localhost:17170',
                    '--admin-username', 'admin', '--admin-password', ADMIN_PASSWORD,
                    '--username', uid, '--password', password], check=True, capture_output=True)
