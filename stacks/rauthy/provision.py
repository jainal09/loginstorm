#!/usr/bin/env python3
"""Creates the bench client and users in a fresh Rauthy through its admin API.

Prints a CLIENT_SECRET=... line for the bench; everything here is test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-https-port> [user-count]   (reads secrets/api-key.txt)
"""
import json
import os
import ssl
import sys
import urllib.request

# Only ever a stack on this machine.
base = f'https://127.0.0.1:{int(sys.argv[1])}'
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secrets', 'api-key.txt')
headers = {'Authorization': f'API-Key {open(key_file).read().strip()}', 'Content-Type': 'application/json'}
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE


def call(method, path, body=None):
    req = urllib.request.Request(f'{base}/auth/v1{path}', method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
        return json.loads(res.read() or b'null')


client = {'id': 'bench-client', 'name': 'Bench', 'confidential': True,
          'redirect_uris': ['http://bench.invalid/callback']}
call('POST', '/clients', client)
call('PUT', '/clients/bench-client', {
    **client, 'enabled': True, 'flows_enabled': ['authorization_code', 'refresh_token'],
    'access_token_alg': 'EdDSA', 'id_token_alg': 'EdDSA', 'auth_code_lifetime': 60,
    # Rauthy only accepts a refresh in the last 60s of an access token's life.
    'access_token_lifetime': 60, 'scopes': ['openid', 'email', 'profile', 'groups'],
    'default_scopes': ['openid'], 'challenges': ['S256'], 'force_mfa': False})
secret = call('POST', '/clients/bench-client/secret')['secret']

for i in range(1, count + 1):
    email = f'bench-user-{i:02d}@bench.test'
    user = call('POST', '/users', {'email': email, 'given_name': 'Bench', 'language': 'en',
                                   'roles': ['user'], 'groups': ['user']})
    call('PUT', f"/users/{user['id']}", {
        'email': email, 'given_name': 'Bench', 'language': 'en', 'roles': ['user'], 'groups': ['user'],
        'enabled': True, 'email_verified': True, 'password': password})
print(f"CLIENT_SECRET={secret}")
