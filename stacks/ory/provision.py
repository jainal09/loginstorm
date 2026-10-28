#!/usr/bin/env python3
"""Creates the bench OAuth2 client in a fresh Ory Hydra and the users in Ory Kratos.

Both admin APIs need no credentials (they are meant to stay on an internal network); test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-hydra-admin-port> <local-kratos-admin-port> [user-count]
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Only ever a stack on this machine; both admin APIs speak plain HTTP inside it.
hydra, kratos = f'http://127.0.0.1:{int(sys.argv[1])}', f'http://127.0.0.1:{int(sys.argv[2])}'
count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')


def call(method, url, body=None):
    req = urllib.request.Request(url, method=method, headers={'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read() or b'null')


for url in (f'{hydra}/health/ready', f'{kratos}/health/ready'):
    for _ in range(120):
        try:
            call('GET', url)
            break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)
    else:
        sys.exit(f'{url} never became ready')

call('POST', f'{hydra}/admin/clients', {
    'client_id': 'bench-client', 'client_secret': 'bench-secret', 'client_name': 'Bench',
    'grant_types': ['authorization_code', 'refresh_token'], 'response_types': ['code'],
    'scope': 'openid offline_access email profile', 'redirect_uris': ['https://bench.invalid/callback'],
    'token_endpoint_auth_method': 'client_secret_post',
    # A first-party app: the login UI accepts consent without showing it.
    'skip_consent': True})
for i in range(1, count + 1):
    call('POST', f'{kratos}/admin/identities', {
        'schema_id': 'default', 'traits': {'email': f'bench-user-{i:02d}@bench.test'},
        'credentials': {'password': {'config': {'password': password}}}})
