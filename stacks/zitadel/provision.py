#!/usr/bin/env python3
"""Creates the bench project, OIDC client and users in a fresh Zitadel.

Authenticates with the admin token Zitadel writes on first start (/pat/admin.pat in its
container, copied out with `docker cp`) and prints CLIENT_ID=... and CLIENT_SECRET=... lines
for the bench; test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-https-port> <zitadel-container> [user-count]
"""
import io
import json
import os
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request

# Only ever a stack on this machine.
base, container = f'https://127.0.0.1:{int(sys.argv[1])}', sys.argv[2]
count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
token = ''
for _ in range(120):
    # docker cp streams a tar archive holding the one file.
    out = subprocess.run(['docker', 'cp', f'{container}:/pat/admin.pat', '-'], capture_output=True)
    if out.returncode == 0:
        with tarfile.open(fileobj=io.BytesIO(out.stdout)) as tar:
            token = tar.extractfile('admin.pat').read().decode().strip()
    if token:
        break
    time.sleep(1)
else:
    sys.exit('Zitadel never wrote its admin token')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
           # Zitadel picks the instance from the Host header, not the address we dial.
           'Host': 'zitadel.bench.test:8443'}
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE


def call(path, body, attempts=1):
    for attempt in range(attempts):
        req = urllib.request.Request(f'{base}{path}', method='POST', headers=headers, data=json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as e:
            if e.code != 503 or attempt == attempts - 1:
                raise
            time.sleep(1)


# The API answers 503 for a few seconds after /debug/ready while first-start setup finishes.
project = call('/management/v1/projects', {'name': 'bench'}, attempts=120)['id']
app = call(f'/management/v1/projects/{project}/apps/oidc', {
    'name': 'bench-client', 'redirectUris': ['http://bench.invalid/callback'],
    'responseTypes': ['OIDC_RESPONSE_TYPE_CODE'],
    'grantTypes': ['OIDC_GRANT_TYPE_AUTHORIZATION_CODE', 'OIDC_GRANT_TYPE_REFRESH_TOKEN'],
    'appType': 'OIDC_APP_TYPE_WEB', 'authMethodType': 'OIDC_AUTH_METHOD_TYPE_POST',
    'devMode': True})  # allows the plain-http bench redirect URI
for i in range(1, count + 1):
    call('/v2/users/human', {
        'username': f'bench-user-{i:02d}', 'profile': {'givenName': 'Bench', 'familyName': f'User{i:02d}'},
        'email': {'email': f'bench-user-{i:02d}@bench.test', 'isVerified': True},
        'password': {'password': password, 'changeRequired': False}})
print(f"CLIENT_ID={app['clientId']}")
print(f"CLIENT_SECRET={app['clientSecret']}")
