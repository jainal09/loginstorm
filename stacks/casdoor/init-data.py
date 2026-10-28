#!/usr/bin/env python3
"""Writes the init data Casdoor loads on its first start: the bench organization, OAuth application
and users, with a fresh client secret. With `--print`, prints CLIENT_ID=... and CLIENT_SECRET=...
from an existing file for the bench instead. Everything here is test-only.
Usage: BENCH_USER_PASSWORD=... init-data.py <init_data.json> [user-count]
       init-data.py --print <init_data.json>
"""
import json
import os
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The init data is one of this repository's test stacks' files.
path = os.path.realpath(sys.argv[2] if sys.argv[1] == '--print' else sys.argv[1])
if os.path.commonpath([ROOT, path]) != ROOT:
    sys.exit('the init data file must be inside the repository')

if sys.argv[1] == '--print':
    app = json.load(open(path))['applications'][0]
    print(f"CLIENT_ID={app['clientId']}")
    print(f"CLIENT_SECRET={app['clientSecret']}")
    sys.exit()

count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
password = os.environ.get('BENCH_USER_PASSWORD') or sys.exit('set BENCH_USER_PASSWORD')
organization = {
    'owner': 'admin', 'name': 'bench', 'displayName': 'Bench',
    # Casdoor's own defaults for its built-in organization.
    'passwordType': 'bcrypt', 'passwordOptions': ['AtLeast6'], 'defaultApplication': 'bench',
}
application = {
    'owner': 'admin', 'name': 'bench', 'displayName': 'Bench', 'organization': 'bench', 'cert': 'cert-built-in',
    'clientId': 'bench-client', 'clientSecret': secrets.token_hex(20),
    'redirectUris': ['http://bench.invalid/callback'], 'grantTypes': ['authorization_code', 'refresh_token'],
    'enablePassword': True, 'enableSignUp': False,
    'signinMethods': [{'name': 'Password', 'displayName': 'Password', 'rule': 'All'}],
    # Token lifetimes as for Casdoor's built-in application (7 days).
    'tokenFormat': 'JWT', 'expireInHours': 168, 'refreshExpireInHours': 168, 'cookieExpireInHours': 720,
}
users = [{'owner': 'bench', 'name': f'bench-user-{i:02d}', 'type': 'normal-user', 'password': password,
          'displayName': f'Bench User{i:02d}', 'email': f'bench-user-{i:02d}@bench.test',
          'signupApplication': 'bench'} for i in range(1, count + 1)]
with open(path, 'w') as f:
    json.dump({'organizations': [organization], 'applications': [application], 'users': users}, f, indent=1)
