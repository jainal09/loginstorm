#!/usr/bin/env bash
# Creates the test stacks' TLS certificate and secrets on first use, so none are committed.
# All of them are throwaway values for local test stacks. Delete tls/*.pem or stacks/*/secrets/ to
# regenerate (a stack's existing data volume won't open with new keys; the runners start from fresh volumes).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
umask 022  # containers run as different non-root users and must read these
rand() { LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "$1" || true; }
# True (and creates the folder) when the file doesn't exist yet.
missing() { [ -f "$1" ] && return 1; mkdir -p "$(dirname "$1")"; }

# TLS everywhere, because Authelia and Rauthy only issue Secure cookies.
if missing tls/cert.pem; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj '/CN=bench.test' \
    -addext 'subjectAltName=DNS:*.bench.test,DNS:bench.test' \
    -keyout tls/key.pem -out tls/cert.pem 2>/dev/null
  chmod 644 tls/key.pem
fi

for stack in authelia authelia-lldap; do
  d=stacks/$stack/secrets
  if missing "$d/oidc-key.pem"; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$d/oidc-key.pem" 2>/dev/null
    chmod 644 "$d/oidc-key.pem"
    for f in jwt session storage hmac; do rand 64 > "$d/$f"; done
  fi
done
if missing stacks/authelia-lldap/secrets/lldap.env; then
  printf 'LLDAP_JWT_SECRET=%s\nLLDAP_KEY_SEED=%s\n' "$(rand 48)" "$(rand 48)" > stacks/authelia-lldap/secrets/lldap.env
fi

if missing stacks/rauthy/secrets/secrets.env; then
  key=$(rand 64)
  printf 'BOOTSTRAP_API_KEY_SECRET=%s\nHQL_SECRET_RAFT=%s\nHQL_SECRET_API=%s\nENC_KEYS=bench/%s\nENC_KEY_ACTIVE=bench\n' \
    "$key" "$(rand 48)" "$(rand 48)" "$(openssl rand -base64 32)" > stacks/rauthy/secrets/secrets.env
  # The admin-API key the provisioning script uses: <key name from config.toml>$<secret>.
  printf 'bench$%s' "$key" > stacks/rauthy/secrets/api-key.txt
fi

if missing stacks/authentik/secrets/secrets.env; then
  printf 'AUTHENTIK_SECRET_KEY=%s\nAUTHENTIK_BOOTSTRAP_PASSWORD=%s\nAUTHENTIK_BOOTSTRAP_TOKEN=%s\n' \
    "$(rand 60)" "$(rand 24)" "$(rand 60)" > stacks/authentik/secrets/secrets.env
fi

if missing stacks/ory/secrets/hydra.env; then
  printf 'SECRETS_SYSTEM=%s\nSECRETS_COOKIE=%s\n' "$(rand 48)" "$(rand 48)" > stacks/ory/secrets/hydra.env
  # Kratos' cipher secret must be exactly 32 characters.
  printf 'SECRETS_COOKIE=%s\nSECRETS_CIPHER=%s\n' "$(rand 48)" "$(rand 32)" > stacks/ory/secrets/kratos.env
  printf 'COOKIE_SECRET=%s\nCSRF_COOKIE_SECRET=%s\nCSRF_COOKIE_NAME=__Host-bench-x-csrf-token\n' \
    "$(rand 48)" "$(rand 48)" > stacks/ory/secrets/ui.env
fi

if missing stacks/pocket-id/secrets/secrets.env; then
  printf 'ENCRYPTION_KEY=%s\nSTATIC_API_KEY=%s\n' "$(rand 48)" "$(rand 48)" > stacks/pocket-id/secrets/secrets.env
fi

# Zitadel wants exactly 32 characters.
missing stacks/zitadel/secrets/masterkey.txt && rand 32 > stacks/zitadel/secrets/masterkey.txt
exit 0
