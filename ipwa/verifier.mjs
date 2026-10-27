const encoder = new TextEncoder();
const HASH_RE = /^sha256:[0-9a-f]{64}$/;
const HEX_KEY = /^[0-9a-f]{64}$/;
const HEX_SIG = /^[0-9a-f]{128}$/;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// Deterministic JSON subset: integers only (money must be a decimal string).
// This is NOT a claim of full RFC 8785 compatibility.
export function canonical(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') {
    assert(Number.isSafeInteger(value), 'non-integer or unsafe number in signed JSON');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  assert(value !== null && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype,
    'invalid signed JSON value');
  return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
}

function hexBytes(hex) {
  assert(typeof hex === 'string' && /^[0-9a-f]*$/.test(hex) && hex.length % 2 === 0, 'invalid hex');
  return Uint8Array.from(hex.match(/../g) || [], pair => parseInt(pair, 16));
}
function toHex(bytes) { return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join(''); }
function concat(...arrays) {
  const out = new Uint8Array(arrays.reduce((n, x) => n + x.length, 0));
  let offset = 0;
  for (const part of arrays) { out.set(part, offset); offset += part.length; }
  return out;
}
async function sha256(bytes) { return new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)); }
async function namedHash(prefix, bytes) { return sha256(concat(encoder.encode(prefix + '\0'), bytes)); }
export async function hashEvent(event) {
  const {event_hash, ...unsigned} = event;
  return `sha256:${toHex(await namedHash('i-pop-event-v1', encoder.encode(canonical(unsigned))))}`;
}
export async function merkleRoot(hashes) {
  assert(hashes.length > 0, 'empty evidence chain');
  let level = await Promise.all(hashes.map(async h => {
    assert(HASH_RE.test(h), 'bad event hash');
    return namedHash('i-pop-leaf-v1', hexBytes(h.slice(7)));
  }));
  while (level.length > 1) {
    const next = [];
    for (let i = 0; i < level.length; i += 2) {
      next.push(await namedHash('i-pop-node-v1', concat(level[i], level[i + 1] || level[i])));
    }
    level = next;
  }
  return `sha256:${toHex(level[0])}`;
}

export async function verifyEvidence(bundle, registry) {
  try {
    assert(bundle && typeof bundle === 'object' && !Array.isArray(bundle), 'bundle missing');
    assert(registry?.protocol === 'ITM-POP-TRUST-v1', 'external trust registry missing or invalid');
    assert(Array.isArray(registry.required_roles) && registry.required_roles.length >= 2,
      'at least two independently authorized roles required');
    assert(new Set(registry.required_roles).size === registry.required_roles.length, 'duplicate required role');
    assert(Array.isArray(registry.keys), 'trusted keys missing');
    assert(bundle.body?.protocol === 'ITM-POP-OFFLINE-v1', 'unsupported receipt protocol');
    const body = bundle.body;
    assert(HASH_RE.test(body.intent_hash), 'invalid intent hash');
    assert(Array.isArray(body.events) && body.events.length > 0 && body.events.length <= 10000,
      'invalid event count');
    assert(body.events[0]?.stage === 'INTENT', 'first event must be INTENT');
    assert(body.events[0]?.evidence_hash === body.intent_hash, 'intent hash binding mismatch');
    let previous = null;
    const hashes = [];
    for (let i = 0; i < body.events.length; i++) {
      const ev = body.events[i];
      assert(ev && typeof ev === 'object' && !Array.isArray(ev), `event ${i} malformed`);
      assert(ev.sequence === i && typeof ev.stage === 'string' && /^[A-Z_]{2,40}$/.test(ev.stage),
        `event ${i} sequence or stage invalid`);
      assert(HASH_RE.test(ev.evidence_hash), `event ${i} evidence hash invalid`);
      assert(ev.parent_hash === previous, `event ${i} parent hash broken`);
      assert(HASH_RE.test(ev.event_hash), `event ${i} hash absent`);
      assert(await hashEvent(ev) === ev.event_hash, `event ${i} hash mismatch`);
      previous = ev.event_hash;
      hashes.push(previous);
    }
    assert(await merkleRoot(hashes) === body.merkle_root, 'Merkle root mismatch');
    assert(Array.isArray(bundle.signatures), 'signatures missing');
    const usedKeyIds = new Set();
    const usedPubkeys = new Set();
    for (const role of registry.required_roles) {
      const matches = bundle.signatures.filter(s => s.role === role);
      assert(matches.length === 1, `missing or duplicate signature for ${role}`);
      const sig = matches[0];
      const keys = registry.keys.filter(k => k.role === role && k.key_id === sig.key_id);
      assert(keys.length === 1, `key not trusted for ${role}`);
      const key = keys[0];
      assert(HEX_KEY.test(key.public_key_hex) && HEX_SIG.test(sig.signature_hex), `invalid key/signature for ${role}`);
      assert(!usedKeyIds.has(key.key_id) && !usedPubkeys.has(key.public_key_hex),
        'required roles must use distinct signing keys');
      usedKeyIds.add(key.key_id);
      usedPubkeys.add(key.public_key_hex);
      const imported = await crypto.subtle.importKey('raw', hexBytes(key.public_key_hex),
        {name: 'Ed25519'}, false, ['verify']);
      const ok = await crypto.subtle.verify('Ed25519', imported, hexBytes(sig.signature_hex),
        encoder.encode(canonical(body)));
      assert(ok, `invalid signature for ${role}`);
    }
    // No OTS/Bitcoin SPV verifier or hardware quote validation is bundled.
    // A metadata assertion 'VERIFIED' must NEVER unlock a payment/actuator.
    return {
      status: 'LOCAL_CRYPTOGRAPHY_PASSED_ANCHOR_UNVERIFIED',
      authorized_for_disbursement: false,
      authorized_for_actuation: false,
      checked_signatures: registry.required_roles.length,
      checked_events: hashes.length,
      bitcoin_anchor_verified: false,
      warning: 'Signed statements prove key possession and record integrity, not service delivery, eligibility, hardware attestation, or Bitcoin anchoring.'
    };
  } catch (error) {
    return {
      status: 'REJECTED',
      authorized_for_disbursement: false,
      authorized_for_actuation: false,
      bitcoin_anchor_verified: false,
      error: error instanceof Error ? error.message : 'verification failed'
    };
  }
}
