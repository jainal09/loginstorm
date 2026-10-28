// OIDC identity-provider API bench for k6.
//
// Drives the same HTTP calls a browser and an app backend make during an
// Authorization Code + PKCE login, then exercises the token lifecycle.
// Endpoints come from OIDC discovery; only the login itself is provider
// specific (IDP=keycloak | authelia | rauthy | zitadel | authentik ...). Every option is an
// environment variable; see README.md.
import http from 'k6/http';
import crypto from 'k6/crypto';
import encoding from 'k6/encoding';
import { check, sleep } from 'k6';
import { parseHTML } from 'k6/html';
import { SharedArray } from 'k6/data';
import { Trend } from 'k6/metrics';
import { passkeyAssertion } from './lib/passkey.js';

const env = (key, fallback) => (__ENV[key] !== undefined && __ENV[key] !== '' ? __ENV[key] : fallback);

const IDP = env('IDP', 'keycloak');
const KC_URL = env('KC_URL', 'http://localhost:8080').replace(/\/$/, '');
const REALM = env('REALM', 'bench');
const ISSUER = env('ISSUER', `${KC_URL}/realms/${encodeURIComponent(REALM)}`).replace(/\/$/, '');
const CLIENT_ID = env('CLIENT_ID', 'bench-client');
const CLIENT_SECRET = env('CLIENT_SECRET', '');
const REDIRECT_URI = env('REDIRECT_URI', 'http://bench.invalid/callback');
// These only issue refresh tokens for offline_access.
const DEFAULT_SCOPES = { authelia: 'openid offline_access groups', zitadel: 'openid offline_access',
  authentik: 'openid offline_access', dex: 'openid offline_access', ory: 'openid offline_access',
  'pocket-id': 'openid offline_access' };
const SCOPE = env('SCOPE', DEFAULT_SCOPES[IDP] || 'openid');
const SCENARIO = env('SCENARIO', 'session');
const VUS = Number(env('VUS', 1));
const DURATION = env('DURATION', '60s');
const RATE = Number(env('RATE', 0));
const REFRESHES = Number(env('REFRESHES', 2));
const THINK_S = Number(env('THINK_S', 1));
const LOGOUT = env('LOGOUT', 'true') === 'true';
const API_CALL = env('API_CALL', 'introspect');
// For providers whose introspection endpoint isn't in discovery (Ory Hydra's is on its admin API).
const INTROSPECT_URL = env('INTROSPECT_URL', '');
// Wrong-password streak lengths for the lockout check, each on its own test account.
const LOCKOUT_STEPS = env('LOCKOUT_STEPS', '5,20').split(',').map(Number);
const SUMMARY_FILE = env('SUMMARY_FILE', '');
// Casdoor logins name the application and organization the user belongs to.
const CASDOOR_APPLICATION = env('CASDOOR_APPLICATION', 'bench');
const CASDOOR_ORGANIZATION = env('CASDOOR_ORGANIZATION', 'bench');

const LOGINS = { keycloak: keycloakLogin, authelia: autheliaLogin, rauthy: rauthyLogin, zitadel: zitadelLogin,
  authentik: authentikLogin, logto: logtoLogin, casdoor: casdoorLogin, dex: dexLogin,
  kanidm: kanidmLogin, ory: oryLogin, 'pocket-id': pocketIdLogin };
const SCENARIOS = { session: 'session', login: 'loginOnly', api: 'apiCalls', lockout: 'lockout',
  'client-credentials': 'clientCredentials' };
if (!LOGINS[IDP]) throw new Error(`IDP must be one of: ${Object.keys(LOGINS).join(', ')}`);
if (!SCENARIOS[SCENARIO]) throw new Error(`SCENARIO must be one of: ${Object.keys(SCENARIOS).join(', ')}`);
if (SCENARIO === 'client-credentials' && !CLIENT_SECRET) throw new Error('client-credentials needs CLIENT_SECRET');
if (SCENARIO === 'api' && !(RATE > 0)) throw new Error('the api scenario needs RATE (calls per second)');
if (!['introspect', 'userinfo'].includes(API_CALL)) throw new Error('API_CALL must be introspect or userinfo');
if (API_CALL === 'introspect' && SCENARIO === 'api' && !CLIENT_SECRET) throw new Error('introspection needs CLIENT_SECRET');

// Either USERS_FILE (csv: username,password) or USER_PREFIX + USER_COUNT + USER_PASSWORD
// (+ USER_DOMAIN for providers that log in by email).
const users = new SharedArray('users', () => {
  if (SCENARIO === 'client-credentials') return [];
  const file = env('USERS_FILE', '');
  if (file) {
    const rows = open(file).split(/\r?\n/).filter(Boolean);
    if (/^username,password$/i.test(rows[0].trim())) rows.shift();
    return rows.map(line => {
      const i = line.indexOf(',');
      return { username: line.slice(0, i).trim(), password: line.slice(i + 1) };
    });
  }
  // Passkey-only providers (Pocket ID): one passkey per user, in user order, instead of a password.
  const passkeys = env('PASSKEYS_FILE', '') ? JSON.parse(open(env('PASSKEYS_FILE'))) : null;
  const password = env('USER_PASSWORD', '');
  if (!password && !passkeys) throw new Error('Set USERS_FILE, or USER_PASSWORD (+ USER_PREFIX, USER_COUNT)');
  const prefix = env('USER_PREFIX', 'bench-user-');
  const domain = env('USER_DOMAIN', '');
  return Array.from({ length: passkeys ? passkeys.length : Number(env('USER_COUNT', 25)) }, (_, i) => ({
    username: `${prefix}${String(i + 1).padStart(2, '0')}${domain ? `@${domain}` : ''}`, password,
    passkey: passkeys ? passkeys[i] : null }));
});

// login_submit is the request that checks the password; login_extra adds up the
// provider's other hops (PoW challenge, consent, redirects).
const trends = {};
for (const step of ['login_page', 'login_submit', 'login_extra', 'code_exchange', 'login_total',
  'userinfo', 'refresh', 'introspect', 'logout', 'client_credentials', 'client_work', 'lockout_wrong_ms']) {
  trends[step] = new Trend(`idp_${step}`, true);
}
// Lockout outcomes as 1 (login accepted) or 0 (refused), one sample each.
const lockoutOutcome = {};
for (const step of ['before', ...LOCKOUT_STEPS.map(n => `after_${n}`), 'other_user']) {
  lockoutOutcome[step] = new Trend(`idp_lockout_${step}`);
}

// Closed model (VUS loop as fast as THINK_S allows) unless RATE asks for an
// open model of RATE iterations per second. The api scenario keeps exactly VUS
// sessions; when they can't keep up, k6 counts dropped_iterations instead.
const sessionSeconds = SCENARIO === 'session' ? (REFRESHES + 1) * THINK_S + 5 : THINK_S + 5;
// The lockout check runs one login attempt per iteration: k6 resets cookies between
// iterations, so no SSO session carries over from one attempt to the next.
const LOCKOUT_PLAN = [];
if (SCENARIO === 'lockout') {
  LOCKOUT_STEPS.forEach((attempts, i) => {
    const target = users.length - 1 - i;
    LOCKOUT_PLAN.push({ user: target, record: 'before' });
    for (let n = 0; n < attempts; n++) LOCKOUT_PLAN.push({ user: target, record: 'wrong' });
    LOCKOUT_PLAN.push({ user: target, record: `after_${attempts}` });
  });
  LOCKOUT_PLAN.push({ user: users.length - 1 - LOCKOUT_STEPS.length, record: 'other_user' });
}
const executor = SCENARIO === 'lockout'
  ? { executor: 'per-vu-iterations', vus: 1, iterations: LOCKOUT_PLAN.length, maxDuration: '10m' }
  : SCENARIO === 'api'
  ? { executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: DURATION,
      preAllocatedVUs: VUS, maxVUs: VUS }
  : RATE > 0
    ? { executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: DURATION,
        preAllocatedVUs: Math.max(VUS, Math.ceil(RATE * sessionSeconds)),
        maxVUs: Math.max(VUS, Math.ceil(RATE * sessionSeconds * 4)) }
    : { executor: 'constant-vus', vus: VUS, duration: DURATION };

export const options = {
  scenarios: { [SCENARIO]: { ...executor, exec: SCENARIOS[SCENARIO] } },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  // The lockout check fails logins on purpose.
  thresholds: { checks: [env('CHECKS_THRESHOLD', SCENARIO === 'lockout' ? 'rate>=0' : 'rate>0.99')] },
  setupTimeout: '300s',
  insecureSkipTLSVerify: env('INSECURE_TLS', 'false') === 'true',
};

export async function setup() {
  const res = http.get(`${ISSUER}/.well-known/openid-configuration`);
  if (res.status !== 200) throw new Error(`discovery failed: ${res.status} ${ISSUER}`);
  const oidc = res.json();
  // The api scenario measures token validation, so its sessions open before the clock starts.
  const sessions = [];
  for (let i = 0; SCENARIO === 'api' && i < VUS; i++) {
    loginJar = new http.CookieJar();
    sessions.push({ tokens: await login(oidc, users[i % users.length]), issuedAt: Date.now() });
    loginJar = null;
  }
  return { oidc, sessions };
}

const query = params => Object.entries(params)
  .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
const queryParam = (url, name) => {
  const m = url.match(new RegExp(`[?&#]${name}=([^&#]*)`));
  return m ? decodeURIComponent(m[1]) : null;
};
const origin = url => url.match(/^https?:\/\/[^/]+/)[0];
const absolute = (url, base) => (/^https?:/.test(url) ? url : origin(base) + url);
const withClient = form => (CLIENT_SECRET
  ? { ...form, client_id: CLIENT_ID, client_secret: CLIENT_SECRET }
  : { ...form, client_id: CLIENT_ID });
const randomToken = bytes => encoding.b64encode(crypto.randomBytes(bytes), 'rawurl');
const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' };

// Logins send their requests on loginJar when one is set: setup opens many sessions
// in one context, where a shared jar would turn every login after the first into SSO.
let loginJar = null;
const web = {
  get: (url, params = {}) => http.get(url, loginJar ? { ...params, jar: loginJar } : params),
  post: (url, body, params = {}) => http.post(url, body, loginJar ? { ...params, jar: loginJar } : params),
  request: (method, url, body, params = {}) => http.request(method, url, body, loginJar ? { ...params, jar: loginJar } : params),
};

function timed(step, response) {
  trends[step].add(response.timings.duration);
  return response;
}

// GETs a provider page and follows its redirects (but not the one back to the app), timing every hop.
function getFollowing(url, name) {
  let res = web.get(url, { redirects: 0, tags: { name } });
  let ms = res.timings.duration;
  for (let hop = 0; hop < 8 && res.status >= 300 && res.status < 400; hop++) {
    const location = res.headers.Location || '';
    if (!location || location.startsWith(REDIRECT_URI)) break;
    res = web.get(absolute(location, res.url), { redirects: 0, tags: { name } });
    ms += res.timings.duration;
  }
  return { res, ms };
}

// Returns the authorization code from a redirect to REDIRECT_URI, or null.
function codeFrom(res, state) {
  const location = res.headers.Location || '';
  return location.startsWith(REDIRECT_URI) && queryParam(location, 'state') === state
    ? queryParam(location, 'code') : null;
}

// Each adapter starts at the authorization URL and returns
// { code, extraMs, clientMs } once the provider redirects back with a code.
function keycloakLogin(authUrl, user, state) {
  const page = timed('login_page', web.get(authUrl, { tags: { name: 'login_page' } }));
  const action = page.status === 200 ? parseHTML(page.body).find('#kc-form-login').attr('action') : undefined;
  if (!check(page, { 'login page served': () => !!action })) return null;
  // Don't follow the redirect: the code in Location is all a real app backend needs.
  const submit = timed('login_submit', web.post(action,
    { username: user.username, password: user.password, credentialId: '' },
    { redirects: 0, tags: { name: 'login_submit' } }));
  return { code: codeFrom(submit, state), extraMs: 0, clientMs: 0 };
}

// Authelia: authorize -> portal flow id -> /api/firstfactor -> consent -> code.
function autheliaLogin(authUrl, user, state) {
  const base = origin(authUrl);
  const start = timed('login_page', web.get(authUrl, { redirects: 0, tags: { name: 'login_page' } }));
  const flowId = queryParam(start.headers.Location || '', 'flow_id');
  if (!check(start, { 'login page served': () => !!flowId })) return null;

  const submit = timed('login_submit', web.post(`${base}/api/firstfactor`, JSON.stringify({
    username: user.username, password: user.password, keepMeLoggedIn: false,
    flow: 'openid_connect', flowID: flowId,
  }), { headers: JSON_HEADERS, tags: { name: 'login_submit' } }));
  let next = submit.status === 200 ? submit.json('data.redirect') : null;
  if (!check(submit, { 'first factor accepted': () => !!next })) return null;

  let extraMs = 0;
  for (let hop = 0; hop < 4; hop++) {
    const res = web.get(next, { redirects: 0, tags: { name: 'login_extra' } });
    extraMs += res.timings.duration;
    const location = res.headers.Location || '';
    if (location.startsWith(REDIRECT_URI)) return { code: codeFrom(res, state), extraMs, clientMs: 0 };
    const consentFlow = location.includes('/consent/') ? queryParam(location, 'flow_id') : null;
    if (!consentFlow) return null;
    // Ask Authelia to remember the approval. It ignores that for offline_access, so consent repeats each login.
    const consent = web.post(`${base}/api/oidc/consent`, JSON.stringify({
      flow_id: consentFlow, client_id: CLIENT_ID, consent: true, pre_configure: true,
    }), { headers: JSON_HEADERS, tags: { name: 'login_extra' } });
    extraMs += consent.timings.duration;
    next = consent.status === 200 ? consent.json('data.redirect_uri') : null;
    if (!next) return null;
  }
  return null;
}

// Rauthy: login page (CSRF token) -> proof-of-work challenge -> JSON login -> 202 with code.
function rauthyLogin(authUrl, user, state, nonce, challenge, verifier) {
  const base = origin(authUrl);
  const page = timed('login_page', web.get(authUrl, { tags: { name: 'login_page' } }));
  const csrf = page.status === 200 ? (page.body.match(/id="tpl_csrf_token">([^<]+)</) || [])[1] : null;
  if (!check(page, { 'login page served': () => !!csrf })) return null;
  const headers = { ...JSON_HEADERS, 'x-csrf-token': csrf };

  const pow = web.post(`${base}/auth/v1/pow`, null, { headers, tags: { name: 'login_extra' } });
  if (!check(pow, { 'pow challenge issued': r => r.status === 200 })) return null;
  const solveStarted = Date.now();
  const solution = solvePow(pow.body);
  const clientMs = Date.now() - solveStarted;

  const submit = timed('login_submit', web.post(authUrl.split('?')[0], JSON.stringify({
    email: user.username, password: user.password, pow: solution, client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI, state, nonce, scopes: SCOPE.split(' '),
    code_challenge: challenge, code_challenge_method: 'S256',
  }), { headers, redirects: 0, tags: { name: 'login_submit' } }));
  return { code: codeFrom(submit, state), extraMs: pow.timings.duration, clientMs };
}

// Zitadel's built-in login UI: login-name form, then password form, then redirects
// back through the authorize callback.
function zitadelLogin(authUrl, user, state) {
  let res = timed('login_page', web.get(authUrl, { redirects: 0, tags: { name: 'login_page' } }));
  let extraMs = 0;
  let passwordSent = false;
  for (let hop = 0; hop < 8; hop++) {
    const location = res.headers.Location || '';
    if (location.startsWith(REDIRECT_URI)) return { code: codeFrom(res, state), extraMs, clientMs: 0 };
    if (res.status >= 300 && res.status < 400) {
      res = web.get(absolute(location, res.url), { redirects: 0, tags: { name: 'login_extra' } });
      extraMs += res.timings.duration;
      continue;
    }
    const form = res.status === 200 ? parseHTML(res.body).find('form').first() : null;
    const action = form ? form.attr('action') : null;
    if (!action) return null;
    const fields = {};
    form.find('input').each((_, el) => {
      const attrs = el.attributes();
      if (attrs.name) fields[attrs.name.value] = attrs.value ? attrs.value.value : '';
    });
    const checksPassword = 'password' in fields;
    // The password form coming back means the password was refused.
    if (checksPassword && passwordSent) return null;
    passwordSent = passwordSent || checksPassword;
    if ('loginName' in fields) fields.loginName = user.username;
    if (checksPassword) fields.password = user.password;
    res = web.post(absolute(action, res.url), fields,
      { redirects: 0, tags: { name: checksPassword ? 'login_submit' : 'login_extra' } });
    if (checksPassword) trends.login_submit.add(res.timings.duration);
    else extraMs += res.timings.duration;
  }
  return null;
}

// authentik: the login page is a single-page app that drives each flow through the flow executor
// API, one JSON challenge per stage (identification, password, consent). The login flow ends in a
// redirect back to the authorize endpoint, whose authorization flow then redirects to the app.
const authentikExecutor = (base, flow) =>
  `${base}/api/v3/flows/executor/${flow.slug}/?query=${encodeURIComponent(flow.query)}`;
function authentikLogin(authUrl, user, state) {
  const base = origin(authUrl);
  let res = timed('login_page', web.get(authUrl, { redirects: 0, tags: { name: 'login_page' } }));
  let extraMs = 0;
  let flow = null;
  let challenge = null;
  const answers = {
    'ak-stage-identification': () => ({ uid_field: user.username }),
    'ak-stage-password': () => ({ password: user.password }),
    'ak-stage-consent': c => ({ token: c.token }),
  };
  for (let hop = 0; hop < 16; hop++) {
    if (challenge) {
      const c = challenge;
      challenge = null;
      if (c.component === 'xak-flow-redirect') {
        if (c.to.startsWith(REDIRECT_URI)) {
          return { code: queryParam(c.to, 'state') === state ? queryParam(c.to, 'code') : null, extraMs, clientMs: 0 };
        }
        res = web.get(absolute(c.to, base), { redirects: 0, tags: { name: 'login_extra' } });
        extraMs += res.timings.duration;
        continue;
      }
      // Anything else (access denied, an unexpected stage) ends the login.
      if (!answers[c.component]) return null;
      const checksPassword = c.component === 'ak-stage-password';
      const answer = web.post(authentikExecutor(base, flow),
        JSON.stringify({ component: c.component, ...answers[c.component](c) }),
        { headers: JSON_HEADERS, redirects: 0, tags: { name: checksPassword ? 'login_submit' : 'login_extra' } });
      if (checksPassword) trends.login_submit.add(answer.timings.duration);
      else extraMs += answer.timings.duration;
      // The answer redirects to the executor again, which then serves the next challenge.
      const next = answer.status === 302
        ? web.get(absolute(answer.headers.Location, base), { headers: JSON_HEADERS, tags: { name: 'login_extra' } })
        : answer;
      if (next !== answer) extraMs += next.timings.duration;
      if (next.status !== 200) return null;
      challenge = next.json();
      // A refused answer (such as a wrong password) brings the same stage back with errors.
      if (challenge.component === c.component && challenge.response_errors) return null;
      continue;
    }
    const location = res.headers.Location || '';
    if (!(res.status >= 300 && res.status < 400)) return null;
    if (location.startsWith(REDIRECT_URI)) return { code: codeFrom(res, state), extraMs, clientMs: 0 };
    const page = location.match(/\/if\/flow\/([^/?]+)\/?\??(.*)$/);
    if (page) {
      flow = { slug: page[1], query: page[2] };
      const first = web.get(authentikExecutor(base, flow), { headers: JSON_HEADERS, tags: { name: 'login_extra' } });
      extraMs += first.timings.duration;
      if (first.status !== 200) return null;
      challenge = first.json();
      continue;
    }
    res = web.get(absolute(location, res.url), { redirects: 0, tags: { name: 'login_extra' } });
    extraMs += res.timings.duration;
  }
  return null;
}

// Logto: authorize (sets the interaction cookie), then the sign-in page's Experience API: start a
// sign-in, verify the password, identify the user with that verification, submit, and resume the
// OIDC interaction, which redirects back with the code.
function logtoLogin(authUrl, user, state) {
  const base = origin(authUrl);
  const start = timed('login_page', web.get(authUrl, { redirects: 0, tags: { name: 'login_page' } }));
  if (!check(start, { 'login page served': r => r.status === 303 || r.status === 302 })) return null;
  let extraMs = 0;
  const experience = (method, path, body) => {
    const res = web.request(method, `${base}/api/experience${path}`, body ? JSON.stringify(body) : null,
      { headers: JSON_HEADERS, tags: { name: 'login_extra' } });
    extraMs += res.timings.duration;
    return res;
  };
  if (experience('PUT', '', { interactionEvent: 'SignIn' }).status !== 204) return null;
  const verify = timed('login_submit', web.post(`${base}/api/experience/verification/password`, JSON.stringify({
    identifier: { type: 'username', value: user.username }, password: user.password,
  }), { headers: JSON_HEADERS, tags: { name: 'login_submit' } }));
  const verificationId = verify.status === 200 ? verify.json('verificationId') : null;
  if (!verificationId) return null;
  if (experience('POST', '/identification', { verificationId }).status !== 204) return null;
  const submit = experience('POST', '/submit');
  let next = submit.status === 200 ? submit.json('redirectTo') : null;
  for (let hop = 0; next && hop < 6; hop++) {
    const res = web.get(next, { redirects: 0, tags: { name: 'login_extra' } });
    extraMs += res.timings.duration;
    const location = res.headers.Location || '';
    if (location.startsWith(REDIRECT_URI)) return { code: codeFrom(res, state), extraMs, clientMs: 0 };
    next = location ? absolute(location, res.url) : null;
  }
  return null;
}

// Casdoor: the authorize URL serves its single-page app, which posts the credentials together with
// the OAuth parameters to /api/login and gets the code back in the JSON answer.
function casdoorLogin(authUrl, user, state, nonce, challenge) {
  const page = timed('login_page', web.get(authUrl, { tags: { name: 'login_page' } }));
  if (!check(page, { 'login page served': r => r.status === 200 })) return null;
  const oauth = query({ clientId: CLIENT_ID, responseType: 'code', redirectUri: REDIRECT_URI, type: 'code',
    scope: SCOPE, state, nonce, code_challenge_method: 'S256', code_challenge: challenge });
  const submit = timed('login_submit', web.post(`${origin(authUrl)}/api/login?${oauth}`, JSON.stringify({
    application: CASDOOR_APPLICATION, organization: CASDOOR_ORGANIZATION, username: user.username,
    password: user.password, autoSignin: true, signinMethod: 'Password', type: 'code',
  }), { headers: JSON_HEADERS, tags: { name: 'login_submit' } }));
  const code = submit.status === 200 && submit.json('status') === 'ok' ? submit.json('data') : null;
  return { code, extraMs: 0, clientMs: 0 };
}

// Dex: authorize redirects to the local connector's login form; posting it redirects through the
// approval step (skipped for this first-party client) back to the app with the code.
function dexLogin(authUrl, user, state) {
  const page = getFollowing(authUrl, 'login_page');
  trends.login_page.add(page.ms);
  const form = page.res.status === 200 ? parseHTML(page.res.body).find('form').first() : null;
  const action = form ? form.attr('action') : null;
  if (!check(page.res, { 'login page served': () => !!action })) return null;
  const submit = timed('login_submit', web.post(absolute(action, page.res.url),
    { login: user.username, password: user.password }, { redirects: 0, tags: { name: 'login_submit' } }));
  const location = submit.headers.Location || '';
  if (!location) return null;
  const approval = getFollowing(absolute(location, submit.url), 'login_extra');
  return { code: codeFrom(approval.res, state) || codeFrom(submit, state), extraMs: approval.ms, clientMs: 0 };
}

// Kanidm's server-rendered login: the authorize page is the username form, then comes the password
// form, a resume step, and a consent page the first time a user signs in to this client.
function kanidmLogin(authUrl, user, state) {
  const base = origin(authUrl);
  const page = timed('login_page', web.get(authUrl, { tags: { name: 'login_page' } }));
  if (!check(page, { 'login page served': r => r.status === 200 && r.body.includes('/ui/login/begin') })) return null;
  const begin = web.post(`${base}/ui/login/begin`, { username: user.username, password: '', totp: '' },
    { tags: { name: 'login_extra' } });
  let extraMs = begin.timings.duration;
  if (begin.status !== 200 || !begin.body.includes('/ui/login/pw')) return null;
  const submit = timed('login_submit', web.post(`${base}/ui/login/pw`, { password: user.password },
    { redirects: 0, tags: { name: 'login_submit' } }));
  // A refused password renders the form again instead of redirecting.
  if (submit.status !== 303) return null;
  let res = web.get(absolute(submit.headers.Location, base), { redirects: 0, tags: { name: 'login_extra' } });
  extraMs += res.timings.duration;
  const consent = res.status === 200 ? (res.body.match(/name="consent_token" value="([^"]+)"/) || [])[1] : null;
  if (consent) {
    res = web.post(`${base}/ui/oauth2/consent`, { consent_token: consent }, { redirects: 0, tags: { name: 'login_extra' } });
    extraMs += res.timings.duration;
  }
  return { code: codeFrom(res, state), extraMs, clientMs: 0 };
}

// Ory: Hydra sends the browser to the login UI, which starts a Kratos login flow and renders its
// form; the form posts to Kratos, which accepts the login at Hydra. Hydra then goes through the UI's
// consent step (accepted without a page for this first-party client) and back with the code.
function oryLogin(authUrl, user, state) {
  const page = getFollowing(authUrl, 'login_page');
  trends.login_page.add(page.ms);
  const forms = page.res.status === 200 ? parseHTML(page.res.body).find('form') : null;
  let form = null;
  for (let i = 0; forms && i < forms.size(); i++) {
    if (forms.eq(i).find('input[name="password"]').size()) form = forms.eq(i);
  }
  const action = form ? form.attr('action') : null;
  if (!check(page.res, { 'login page served': () => !!action })) return null;
  const fields = {};
  form.find('input').each((_, el) => {
    const attrs = el.attributes();
    if (attrs.name) fields[attrs.name.value] = attrs.value ? attrs.value.value : '';
  });
  Object.assign(fields, { identifier: user.username, password: user.password, method: 'password' });
  const submit = timed('login_submit', web.post(absolute(action, page.res.url), fields,
    { redirects: 0, headers: { Accept: 'text/html' }, tags: { name: 'login_submit' } }));
  const location = submit.headers.Location || '';
  // A refused password renders the login form again (through a redirect to the UI's own page).
  if (!location || location.includes('/login?flow=')) return null;
  const rest = getFollowing(absolute(location, submit.url), 'login_extra');
  return { code: codeFrom(rest.res, state), extraMs: rest.ms, clientMs: 0 };
}

// Pocket ID logs in with passkeys only. Authorize opens an interaction; the login page asks for a
// passkey assertion, which the bench signs with the user's software passkey (client work, reported
// as idp_client_work and left out of idp_login_total like Rauthy's proof-of-work). Completing the
// interaction's steps then leads back to authorize, which redirects to the app with the code.
async function pocketIdLogin(authUrl, user, state) {
  const base = origin(authUrl);
  const start = timed('login_page', web.get(authUrl, { redirects: 0, tags: { name: 'login_page' } }));
  const interaction = queryParam(start.headers.Location || '', 'interaction');
  if (!check(start, { 'login page served': () => !!interaction })) return null;
  const options = web.get(`${base}/api/webauthn/login/start`, { tags: { name: 'login_extra' } });
  let extraMs = options.timings.duration;
  if (options.status !== 200 || !user.passkey) return null;
  const signStarted = Date.now();
  const assertion = await passkeyAssertion(user.passkey, options.json(), base);
  const clientMs = Date.now() - signStarted;
  const submit = timed('login_submit', web.post(`${base}/api/webauthn/login/finish`, JSON.stringify(assertion),
    { headers: JSON_HEADERS, tags: { name: 'login_submit' } }));
  if (submit.status !== 200) return null;
  let step = 'authenticate';
  for (let hop = 0; hop < 4 && step; hop++) {
    const done = web.post(`${base}/api/oidc/interactions/${interaction}/complete`, JSON.stringify({ step }),
      { headers: JSON_HEADERS, tags: { name: 'login_extra' } });
    extraMs += done.timings.duration;
    if (done.status !== 200) return null;
    const next = done.json();
    if (next.redirectUrl) {
      const back = getFollowing(absolute(next.redirectUrl, base), 'login_extra');
      return { code: codeFrom(back.res, state), extraMs: extraMs + back.ms, clientMs };
    }
    step = next.interaction && next.interaction.currentStep;
  }
  return null;
}

// Rauthy's spow: append a decimal nonce until sha256(challenge + nonce) has
// `difficulty` leading zero bits. This is client work; the server checks one hash.
function solvePow(challenge) {
  const difficulty = Number(challenge.split(':')[1]);
  const fullNibbles = Math.floor(difficulty / 4);
  const zeros = '0'.repeat(fullNibbles);
  const maxNextNibble = 2 ** (4 - (difficulty % 4)) - 1;
  for (let n = 0; ; n++) {
    const hex = crypto.sha256(challenge + n, 'hex');
    if (hex.startsWith(zeros) && parseInt(hex[fullNibbles], 16) <= maxNextNibble) return challenge + n;
  }
}

async function login(oidc, user) {
  const verifier = randomToken(32);
  const state = randomToken(12);
  const nonce = randomToken(12);
  const challenge = crypto.sha256(verifier, 'base64rawurl');
  const started = Date.now();
  const authUrl = `${oidc.authorization_endpoint}?${query({
    client_id: CLIENT_ID, redirect_uri: REDIRECT_URI, response_type: 'code', scope: SCOPE,
    state, nonce, code_challenge: challenge, code_challenge_method: 'S256',
  })}`;

  const result = await LOGINS[IDP](authUrl, user, state, nonce, challenge, verifier);
  if (!check(result, { 'credentials accepted': r => !!(r && r.code) })) return null;
  trends.login_extra.add(result.extraMs);
  if (IDP === 'rauthy' || IDP === 'pocket-id') trends.client_work.add(result.clientMs);

  const tokens = timed('code_exchange', http.post(oidc.token_endpoint, withClient({
    grant_type: 'authorization_code', code: result.code, redirect_uri: REDIRECT_URI, code_verifier: verifier,
  }), { tags: { name: 'code_exchange' } }));
  if (!check(tokens, { 'code exchanged': r => r.status === 200 })) return null;

  // Server-side latency: leave out the client's own proof-of-work time.
  trends.login_total.add(Date.now() - started - result.clientMs);
  return tokens.json();
}

function refresh(oidc, refreshToken) {
  const res = timed('refresh', http.post(oidc.token_endpoint,
    withClient({ grant_type: 'refresh_token', refresh_token: refreshToken }), { tags: { name: 'refresh' } }));
  return check(res, { 'token refreshed': r => r.status === 200 }) ? res.json() : null;
}

function userinfo(oidc, accessToken) {
  const res = timed('userinfo', http.get(oidc.userinfo_endpoint,
    { headers: { Authorization: `Bearer ${accessToken}` }, tags: { name: 'userinfo' } }));
  check(res, { 'userinfo ok': r => r.status === 200 });
}

function introspect(oidc, accessToken) {
  // Rauthy wants HTTP Basic client auth here, as does any provider that doesn't list client_secret_post.
  const methods = oidc.introspection_endpoint_auth_methods_supported;
  const basic = IDP === 'rauthy'
    || (methods && methods.includes('client_secret_basic') && !methods.includes('client_secret_post'));
  const params = basic
    ? { headers: { Authorization: `Basic ${encoding.b64encode(`${CLIENT_ID}:${CLIENT_SECRET}`)}` } }
    : {};
  const body = basic ? { token: accessToken } : withClient({ token: accessToken });
  const res = timed('introspect', http.post(INTROSPECT_URL || oidc.introspection_endpoint, body,
    { ...params, tags: { name: 'introspect' } }));
  check(res, { 'token active': r => r.status === 200 && r.json('active') === true });
}

// Keycloak ends the session with a back-channel logout; the others revoke the refresh token.
function logout(oidc, refreshToken) {
  const keycloak = IDP === 'keycloak';
  const url = keycloak ? oidc.end_session_endpoint : oidc.revocation_endpoint;
  // Dex has neither, so its sessions are left to expire.
  if (!url) return;
  const res = timed('logout', http.post(url,
    withClient(keycloak ? { refresh_token: refreshToken }
      : { token: refreshToken, token_type_hint: 'refresh_token' }), { tags: { name: 'logout' } }));
  check(res, { 'logged out': r => r.status === 204 || r.status === 200 });
}

const pickUser = () => users[(__VU - 1) % users.length];

// Login, use the session the way an app would, then end it.
export async function session({ oidc }) {
  let tokens = await login(oidc, pickUser());
  if (!tokens) return sleep(1);
  userinfo(oidc, tokens.access_token);
  for (let i = 0; i < REFRESHES && tokens; i++) {
    sleep(THINK_S);
    tokens = refresh(oidc, tokens.refresh_token) || null;
  }
  if (!tokens) return sleep(1);
  if (CLIENT_SECRET && (INTROSPECT_URL || oidc.introspection_endpoint)) introspect(oidc, tokens.access_token);
  if (LOGOUT) logout(oidc, tokens.refresh_token);
  sleep(THINK_S);
}

// Token validation the way an API backend does it when it doesn't verify JWTs
// locally: each VU holds one session, reuses it for every call and refreshes it
// shortly before it expires. Logins only happen once per VU (or after a failure).
let apiSession = null;
export async function apiCalls({ oidc, sessions }) {
  const now = Date.now();
  if (!apiSession) {
    const opened = sessions[(__VU - 1) % sessions.length];
    if (opened && opened.tokens) {
      apiSession = { tokens: opened.tokens, expiresAt: opened.issuedAt + opened.tokens.expires_in * 1000 };
    }
  }
  if (apiSession && apiSession.expiresAt - now < 15000) {
    const renewed = refresh(oidc, apiSession.tokens.refresh_token);
    apiSession = renewed ? { tokens: renewed, expiresAt: now + renewed.expires_in * 1000 } : null;
  }
  if (!apiSession) {
    const tokens = await login(oidc, pickUser());
    if (!tokens) return;
    apiSession = { tokens, expiresAt: now + tokens.expires_in * 1000 };
  }
  if (API_CALL === 'userinfo') userinfo(oidc, apiSession.tokens.access_token);
  else introspect(oidc, apiSession.tokens.access_token);
}

// Checks the provider's lockout policy on dedicated test accounts: for each
// LOCKOUT_STEPS streak, a correct login, that many wrong passwords on the same
// account, then the correct password again. Last, an untouched account from the
// same client: if it is refused too, blocking is per IP rather than per account.
// Only for disposable test stacks.
export async function lockout({ oidc }) {
  const step = LOCKOUT_PLAN[__ITER];
  const user = users[step.user];
  if (step.record !== 'wrong') {
    lockoutOutcome[step.record].add(await login(oidc, user) ? 1 : 0);
    return;
  }
  const started = Date.now();
  await login(oidc, { username: user.username, password: `${user.password}-wrong` });
  trends.lockout_wrong_ms.add(Date.now() - started);
}

// Login throughput only; the expensive part is password hashing.
export async function loginOnly({ oidc }) {
  const tokens = await login(oidc, pickUser());
  if (!tokens) return sleep(1);
  if (LOGOUT && tokens.refresh_token) logout(oidc, tokens.refresh_token);
  sleep(THINK_S);
}

// Service-to-service tokens; no users or password hashing involved.
export function clientCredentials({ oidc }) {
  const res = timed('client_credentials', http.post(oidc.token_endpoint,
    withClient({ grant_type: 'client_credentials' }), { tags: { name: 'client_credentials' } }));
  check(res, { 'client token issued': r => r.status === 200 });
  sleep(THINK_S);
}

export function handleSummary(data) {
  const ms = v => (v === undefined ? '-' : `${Math.round(v)}ms`);
  const lines = [`\nidp=${IDP} scenario=${SCENARIO}${SCENARIO === 'api' ? `/${API_CALL}` : ''} vus=${VUS} `
    + `rate=${RATE || '-'} duration=${DURATION}`];
  for (const [name, metric] of Object.entries(data.metrics)) {
    if (!name.startsWith('idp_')) continue;
    const v = metric.values;
    if (name.startsWith('idp_lockout_') && name !== 'idp_lockout_wrong_ms') {
      lines.push(`  ${name.padEnd(22)} ${v.min === 1 ? 'login accepted' : 'login refused'}`);
      continue;
    }
    lines.push(`  ${name.padEnd(22)} med=${ms(v.med).padStart(7)}`
      + `  p95=${ms(v['p(95)']).padStart(7)}  max=${ms(v.max).padStart(7)}`);
  }
  const it = data.metrics.iterations ? data.metrics.iterations.values : { count: 0, rate: 0 };
  const dropped = data.metrics.dropped_iterations ? data.metrics.dropped_iterations.values.count : 0;
  lines.push(`  iterations=${it.count} (${it.rate.toFixed(2)}/s)  dropped=${dropped}  checks_ok=${
    (100 * (data.metrics.checks ? data.metrics.checks.values.rate : 0)).toFixed(2)}%`);
  for (const c of data.root_group.checks) if (c.fails) lines.push(`  FAILED ${c.name}: ${c.fails}`);

  const out = { stdout: `${lines.join('\n')}\n` };
  if (SUMMARY_FILE) {
    out[SUMMARY_FILE] = JSON.stringify({
      config: { idp: IDP, scenario: SCENARIO, api_call: API_CALL, vus: VUS, rate: RATE, duration: DURATION,
        refreshes: REFRESHES, think_s: THINK_S, logout: LOGOUT, issuer: ISSUER, client_id: CLIENT_ID, scope: SCOPE },
      metrics: data.metrics, checks: data.root_group.checks,
    }, null, 2);
  }
  return out;
}
