#!/usr/bin/env python3
"""Creates the bench OAuth2 client, users and their group in a fresh Kanidm.

Resets idm_admin's password with `kanidmd recover-account` (through `docker exec`), logs in
with it, and works through the REST API. Kanidm doesn't let an admin set someone's password,
so each user gets a credential-update intent that is then used to set it, the way a user
redeems a reset link. Prints CLIENT_SECRET=... for the bench; everything here is test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-https-port> <kanidm-container> [user-count]
"""
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

# Only ever a stack on this machine.
base, container = f'https://127.0.0.1:{int(sys.argv[1])}', sys.argv[2]
count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE

out = subprocess.run(['docker', 'exec', container, 'kanidmd', 'recover-account', 'idm_admin'],
                     capture_output=True, text=True, check=True)
admin_password = re.search(r'new_password: "([^"]+)"', out.stdout + out.stderr).group(1)
headers = {'Content-Type': 'application/json'}


def call(method, path, body=None):
    req = urllib.request.Request(f'{base}{path}', method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
            # Each auth step answers with a signed session id that the next step must send back.
            session = res.headers.get('X-KANIDM-AUTH-SESSION-ID')
            if session:
                headers['X-KANIDM-AUTH-SESSION-ID'] = session
            return json.loads(res.read() or b'null')
    except urllib.error.HTTPError as e:
        sys.exit(f'{method} {path}: {e.code} {e.read()[:300]!r}')


# A privileged (read-write) session for idm_admin: init, pick password, send it.
call('POST', '/v1/auth', {'step': {'init2': {'username': 'idm_admin', 'issue': 'token', 'privileged': True}}})
call('POST', '/v1/auth', {'step': {'begin': 'password'}})
token = call('POST', '/v1/auth', {'step': {'cred': {'password': admin_password}}})['state']['success']
headers.pop('X-KANIDM-AUTH-SESSION-ID', None)
headers['Authorization'] = f'Bearer {token}'

# Kanidm requires MFA for every person by default (idm_all_persons). The other providers log in
# with a password alone, so the test users may too.
call('PUT', '/v1/group/idm_all_persons/_attr/credential_type_minimum', ['any'])

names = [f'bench-user-{i:02d}' for i in range(1, count + 1)]
call('POST', '/v1/group', {'attrs': {'name': ['bench_users']}})
for name in names:
    call('POST', '/v1/person', {'attrs': {'name': [name], 'displayname': [f'Bench {name}'],
                                          'mail': [f'{name}@bench.test']}})
    intent = call('GET', f'/v1/person/{name}/_credential/_update_intent/3600')
    session, _ = call('POST', '/v1/credential/_exchange_intent', intent['token'])
    call('POST', '/v1/credential/_update', [{'password': password}, session])
    call('POST', '/v1/credential/_commit', session)
call('POST', '/v1/group/bench_users/_attr/member', names)

call('POST', '/v1/oauth2/_basic', {'attrs': {'name': ['bench-client'], 'displayname': ['Bench'],
                                             'oauth2_rs_origin_landing': ['https://bench.invalid/']}})
call('POST', '/v1/oauth2/bench-client/_attr/oauth2_rs_origin', ['https://bench.invalid/callback'])
call('POST', '/v1/oauth2/bench-client/_scopemap/bench_users', ['openid', 'email', 'profile'])
print(f"CLIENT_SECRET={call('GET', '/v1/oauth2/bench-client/_basic_secret')}")
