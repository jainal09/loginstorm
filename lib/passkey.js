// A software passkey for load tests: a WebAuthn platform authenticator with a P-256 key, "none"
// attestation, a discoverable credential and user verification. Test-only: keys live in a JSON file.
import encoding from 'k6/encoding';

const subtle = globalThis.crypto.subtle;
const P256 = { name: 'ECDSA', namedCurve: 'P-256' };

const concat = (...parts) => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
};
const utf8 = text => new Uint8Array(encoding.b64decode(encoding.b64encode(text), 'std'));
const b64url = bytes => encoding.b64encode(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length), 'rawurl');
const sha256 = async bytes => new Uint8Array(await subtle.digest('SHA-256', bytes));

// Just the CBOR WebAuthn needs: small integers, byte and text strings, and maps written as
// [key, value] pairs so integer keys keep their order.
const head = (major, n) => Uint8Array.from(n < 24 ? [major << 5 | n] : n < 256 ? [major << 5 | 24, n] : [major << 5 | 25, n >> 8, n & 255]);
function cbor(value) {
  if (typeof value === 'number') return value >= 0 ? head(0, value) : head(1, -1 - value);
  if (typeof value === 'string') { const b = utf8(value); return concat(head(3, b.length), b); }
  if (value instanceof Uint8Array) return concat(head(2, value.length), value);
  return concat(head(5, value.length), ...value.flatMap(([k, v]) => [cbor(k), cbor(v)]));
}

// WebCrypto signs ECDSA as r || s; WebAuthn wants the ASN.1 DER form.
function derSignature(raw) {
  const integer = bytes => {
    let i = 0;
    while (i < bytes.length - 1 && bytes[i] === 0) i++;
    const b = bytes[i] & 0x80 ? concat(Uint8Array.of(0), bytes.slice(i)) : bytes.slice(i);
    return concat(Uint8Array.of(0x02, b.length), b);
  };
  const r = integer(raw.slice(0, 32));
  const s = integer(raw.slice(32));
  return concat(Uint8Array.of(0x30, r.length + s.length), r, s);
}

// Answers a registration ceremony (navigator.credentials.create). Returns the credential to post
// back and the passkey to keep.
export async function createPasskey(options, origin) {
  const pk = options.publicKey || options;
  const keys = await subtle.generateKey(P256, true, ['sign', 'verify']);
  const point = new Uint8Array(await subtle.exportKey('raw', keys.publicKey));
  const id = globalThis.crypto.getRandomValues(new Uint8Array(16));
  const coseKey = cbor([[1, 2], [3, -7], [-1, 1], [-2, point.slice(1, 33)], [-3, point.slice(33)]]);
  // Flags: user present, user verified, attested credential data included. Zero AAGUID and counter.
  const authData = concat(await sha256(utf8(pk.rp.id)), Uint8Array.of(0x45, 0, 0, 0, 0), new Uint8Array(16),
    Uint8Array.of(0, id.length), id, coseKey);
  const clientData = utf8(JSON.stringify({ type: 'webauthn.create', challenge: pk.challenge, origin, crossOrigin: false }));
  return {
    credential: {
      id: b64url(id), rawId: b64url(id), type: 'public-key', authenticatorAttachment: 'platform', clientExtensionResults: {},
      response: { clientDataJSON: b64url(clientData), attestationObject: b64url(cbor([['fmt', 'none'], ['attStmt', []], ['authData', authData]])), transports: ['internal'] },
    },
    passkey: { id: b64url(id), userHandle: pk.user.id, rpId: pk.rp.id, jwk: await subtle.exportKey('jwk', keys.privateKey) },
  };
}

// Answers a login ceremony (navigator.credentials.get) with a stored passkey.
const imported = {};
export async function passkeyAssertion(passkey, options, origin) {
  const pk = options.publicKey || options;
  imported[passkey.id] = imported[passkey.id] || await subtle.importKey('jwk', passkey.jwk, P256, false, ['sign']);
  // Flags: user present and verified. The signature counter stays 0 (allowed: "no counter").
  const authData = concat(await sha256(utf8(pk.rpId || passkey.rpId)), Uint8Array.of(0x05, 0, 0, 0, 0));
  const clientData = utf8(JSON.stringify({ type: 'webauthn.get', challenge: pk.challenge, origin, crossOrigin: false }));
  const raw = new Uint8Array(await subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, imported[passkey.id],
    concat(authData, await sha256(clientData))));
  return {
    id: passkey.id, rawId: passkey.id, type: 'public-key', authenticatorAttachment: 'platform', clientExtensionResults: {},
    response: { authenticatorData: b64url(authData), clientDataJSON: b64url(clientData), signature: b64url(derSignature(raw)),
      userHandle: passkey.userHandle },
  };
}
