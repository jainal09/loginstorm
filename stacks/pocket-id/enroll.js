// Registers one software passkey per test user in a fresh Pocket ID, through the calls its web UI
// makes: redeem a one-time access token, then register a passkey. Writes the keys for bench.js.
// Test-only. Env: BASE (Pocket ID's URL), TOKENS (one-time tokens in user order, comma-separated),
// OUT (keys file, relative to the repository root).
import http from 'k6/http';
import { createPasskey } from '../../lib/passkey.js';

export const options = { insecureSkipTLSVerify: true, setupTimeout: '300s',
  scenarios: { enroll: { executor: 'shared-iterations', vus: 1, iterations: 1 } } };
const JSON_HEADERS = { 'Content-Type': 'application/json' };

export async function setup() {
  const passkeys = [];
  for (const token of __ENV.TOKENS.split(',')) {
    const jar = new http.CookieJar();
    const redeem = http.post(`${__ENV.BASE}/api/one-time-access-token/${token}`, null, { jar });
    const start = redeem.status === 200 ? http.get(`${__ENV.BASE}/api/webauthn/register/start`, { jar }) : redeem;
    if (start.status !== 200) throw new Error(`enrollment refused: ${start.status} ${start.body}`);
    const { credential, passkey } = await createPasskey(start.json(), __ENV.BASE);
    const finish = http.post(`${__ENV.BASE}/api/webauthn/register/finish`, JSON.stringify(credential), { jar, headers: JSON_HEADERS });
    if (finish.status >= 300) throw new Error(`passkey refused: ${finish.status} ${finish.body}`);
    passkeys.push(passkey);
  }
  return { passkeys };
}

export default function () {}

export function handleSummary(data) {
  return { [__ENV.OUT]: JSON.stringify(data.setup_data.passkeys) };
}
