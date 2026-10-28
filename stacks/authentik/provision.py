#!/usr/bin/env python3
"""Creates the bench OAuth2 provider, application and users in a fresh authentik.

Authenticates with the API token authentik's first start creates from AUTHENTIK_BOOTSTRAP_TOKEN
and prints CLIENT_ID=... and CLIENT_SECRET=... lines for the bench; test-only.
Usage: BENCH_USER_PASSWORD=... provision.py <local-https-port> [user-count]   (reads secrets/secrets.env)
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Only ever a stack on this machine.
base = f'https://127.0.0.1:{int(sys.argv[1])}'
count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
secrets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secrets', 'secrets.env')
secrets = dict(line.strip().split('=', 1) for line in open(secrets_file) if '=' in line)
headers = {'Authorization': f"Bearer {secrets['AUTHENTIK_BOOTSTRAP_TOKEN']}", 'Content-Type': 'application/json'}
ctx = ssl.create_default_context()
ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE


def call(method, path, body=None):
    req = urllib.request.Request(f'{base}/api/v3{path}', method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, context=ctx, timeout=120) as res:
        return json.loads(res.read() or b'null')


def find(path, **params):
    results = call('GET', f'{path}?{urllib.parse.urlencode({**params, "page_size": 100})}')['results']
    return results[0] if results else None


# The worker creates the bootstrap token, default flows, signing key and scope mappings from
# blueprints, one after another, after the server reports ready; wait until all of them exist.
FLOWS = ['default-provider-authorization-implicit-consent', 'default-provider-invalidation-flow']
SCOPES = [f'goauthentik.io/providers/oauth2/scope-{s}' for s in ('openid', 'email', 'profile', 'offline_access')]
for _ in range(300):
    try:
        flows = [find('/flows/instances/', slug=slug) for slug in FLOWS]
        key = find('/crypto/certificatekeypairs/', name='authentik Self-signed Certificate')
        scopes = {m['managed']: m['pk'] for m in call('GET', '/propertymappings/provider/scope/?page_size=100')['results']}
        if all(flows) and key and all(s in scopes for s in SCOPES):
            break
    except (urllib.error.URLError, ConnectionError):
        pass
    time.sleep(1)
else:
    sys.exit('authentik never finished its first-start setup')

provider = call('POST', '/providers/oauth2/', {
    'name': 'bench', 'client_type': 'confidential', 'client_id': 'bench-client',
    'grant_types': ['authorization_code', 'refresh_token'],
    'authorization_flow': flows[0]['pk'], 'invalidation_flow': flows[1]['pk'],
    'redirect_uris': [{'matching_mode': 'strict', 'url': 'http://bench.invalid/callback'}],
    # RS256-signed tokens like the other providers; without a key authentik signs with HS256.
    'signing_key': key['pk'],
    'property_mappings': [scopes[s] for s in SCOPES]})
call('POST', '/core/applications/', {'name': 'Bench', 'slug': 'bench', 'provider': provider['pk']})

for i in range(1, count + 1):
    user = call('POST', '/core/users/', {'username': f'bench-user-{i:02d}', 'name': f'Bench User{i:02d}',
                                         'email': f'bench-user-{i:02d}@bench.test', 'is_active': True})
    call('POST', f"/core/users/{user['pk']}/set_password/", {'password': password})
print(f"CLIENT_ID={provider['client_id']}")
print(f"CLIENT_SECRET={provider['client_secret']}")
