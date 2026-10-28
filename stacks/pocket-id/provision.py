#!/usr/bin/env python3
"""Creates the bench OIDC client and users in a fresh Pocket ID and enrolls a passkey for each.

Uses the STATIC_API_KEY from secrets/secrets.env next to this script. Pocket ID only logs in with passkeys, so each
user gets a one-time access token, and stacks/pocket-id/enroll.js (in a k6 container on the
stack's network) redeems it and registers a software passkey. Prints CLIENT_ID=...,
CLIENT_SECRET=... and PASSKEYS_FILE=... for the bench; everything here is test-only.
Usage: provision.py <local-https-port> <docker-network> <passkeys-file> [user-count]
"""
import json
import os
import ssl
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Only ever a stack on this machine.
base, network = f'https://127.0.0.1:{int(sys.argv[1])}', sys.argv[2]
# The keys go to a file in this repository, where k6 (which sees it at /bench) can read them.
passkeys_path = os.path.realpath(sys.argv[3])
if os.path.commonpath([ROOT, passkeys_path]) != ROOT:
    sys.exit('the passkeys file must be inside the repository')
passkeys_file = os.path.relpath(passkeys_path, ROOT)
count = int(sys.argv[4]) if len(sys.argv) > 4 else 50
secrets_file = os.path.join(ROOT, 'stacks', 'pocket-id', 'secrets', 'secrets.env')
secrets = dict(line.strip().split('=', 1) for line in open(secrets_file) if '=' in line)
headers = {'X-API-Key': secrets['STATIC_API_KEY'], 'Content-Type': 'application/json'}
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE


def call(method, path, body=None):
    req = urllib.request.Request(f'{base}/api{path}', method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
        return json.loads(res.read() or b'null')


client = call('POST', '/oidc/clients', {
    'name': 'bench-client', 'callbackURLs': ['https://bench.invalid/callback'], 'isPublic': False,
    # A first-party app: no consent screen.
    'pkceEnabled': True, 'skipConsent': True})
secret = call('POST', f"/oidc/clients/{client['id']}/secrets", {})['secret']
tokens = []
for i in range(1, count + 1):
    user = call('POST', '/users', {'username': f'bench-user-{i:02d}', 'email': f'bench-user-{i:02d}@bench.test',
                                   'emailVerified': True, 'firstName': 'Bench', 'lastName': f'User{i:02d}'})
    tokens.append(call('POST', f"/users/{user['id']}/one-time-access-token", {'ttl': '1h'})['token'])

subprocess.run(['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}', '--network', network,
                '-v', f'{ROOT}:/bench', '-w', '/bench', '-e', 'BASE=https://pocketid.bench.test:1411',
                '-e', f"TOKENS={','.join(tokens)}", '-e', f'OUT={passkeys_file}',
                os.environ.get('K6_IMAGE', 'grafana/k6:2.3.0'), 'run', '-q', 'stacks/pocket-id/enroll.js'],
               check=True, stdout=subprocess.DEVNULL)
print(f"CLIENT_ID={client['id']}")
print(f'CLIENT_SECRET={secret}')
print(f'PASSKEYS_FILE={passkeys_file}')
