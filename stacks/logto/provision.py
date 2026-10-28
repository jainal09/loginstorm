#!/usr/bin/env python3
"""Creates the bench application and users in a fresh Logto through its Management API.

Logto has no bootstrap credential for that API, and a new install's only way in is the admin
console's sign-up page, so this first inserts a machine-to-machine app with Logto's built-in
"Logto Management API access" role straight into the database (through `docker exec` on the
Postgres container), then works through the API as that app. Prints CLIENT_ID=... and
CLIENT_SECRET=... lines for the bench; everything here is test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-https-port> <postgres-container> [user-count]
"""
import base64
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Only ever a stack on this machine.
base, db_container = f'https://127.0.0.1:{int(sys.argv[1])}', sys.argv[2]
count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE

m2m_id, m2m_secret = 'bench-provisioner', secrets.token_urlsafe(32)
sql = f"""
insert into applications (tenant_id, id, name, secret, type, oidc_client_metadata)
  values ('default', '{m2m_id}', 'bench provisioner', '{m2m_secret}', 'MachineToMachine',
          '{{"redirectUris": [], "postLogoutRedirectUris": []}}');
insert into application_secrets (tenant_id, application_id, name, value)
  values ('default', '{m2m_id}', 'bench', '{m2m_secret}');
insert into applications_roles (tenant_id, id, application_id, role_id)
  select 'default', '{m2m_id}', '{m2m_id}', id from roles
  where tenant_id = 'default' and name = 'Logto Management API access';
"""
subprocess.run(['docker', 'exec', '-i', db_container, 'psql', '-U', 'postgres', '-d', 'logto', '-v', 'ON_ERROR_STOP=1'],
               input=sql.encode(), check=True, capture_output=True)


def request(method, path, body=None, headers=None, form=False):
    data = None
    if body is not None:
        data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
    req = urllib.request.Request(f'{base}{path}', method=method, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
        return json.loads(res.read() or b'null')


basic = base64.b64encode(f'{m2m_id}:{m2m_secret}'.encode()).decode()
for _ in range(60):
    try:
        token = request('POST', '/oidc/token', {'grant_type': 'client_credentials', 'scope': 'all',
                                                 'resource': 'https://default.logto.app/api'},
                        {'Authorization': f'Basic {basic}'}, form=True)['access_token']
        break
    except (urllib.error.URLError, ConnectionError):
        time.sleep(1)
else:
    sys.exit('could not get a Management API token')
auth = {'Authorization': f'Bearer {token}'}

app = request('POST', '/api/applications', {
    'name': 'bench-client', 'type': 'Traditional',
    'oidcClientMetadata': {'redirectUris': ['http://bench.invalid/callback'], 'postLogoutRedirectUris': []},
    # Refresh tokens without asking for consent at every login, like the other providers.
    'customClientMetadata': {'alwaysIssueRefreshToken': True}}, auth)
for i in range(1, count + 1):
    request('POST', '/api/users', {'username': f'bench_user_{i:02d}', 'password': password,
                                   'name': f'Bench User{i:02d}'}, auth)
# Client secrets live in their own table; the app comes back without one.
secret = request('POST', f"/api/applications/{app['id']}/secrets", {'name': 'bench'}, auth)['value']
print(f"CLIENT_ID={app['id']}")
print(f"CLIENT_SECRET={secret}")
