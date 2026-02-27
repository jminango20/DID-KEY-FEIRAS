"""
Ed25519 cryptography utilities for FeirasWallet.

Signing: JWS detached payload (RFC 7797) with EdDSA algorithm.
Verification: supports DID:KEY publicKeyMultibase format
              (base58btc with 'z' prefix + multicodec 0xed01 header).
"""

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

MULTICODEC_ED25519_PREFIX_LEN = 2  # 0xed 0x01


def private_key_from_bytes(raw_bytes: bytes) -> Ed25519PrivateKey:
    """Load Ed25519PrivateKey from raw 32-byte private key."""
    return Ed25519PrivateKey.from_private_bytes(raw_bytes)


def sign_credential(credential_without_proof: Dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    """
    Sign a credential dict and return a JWS string (detached payload format).

    The credential is canonicalized (sorted keys, no spaces) before signing.

    Args:
        credential_without_proof: Credential dict with NO 'proof' field.
        private_key: Ed25519PrivateKey to sign with.

    Returns:
        JWS string: base64url(header)..base64url(signature)
    """
    canonical = json.dumps(credential_without_proof, sort_keys=True, separators=(',', ':'))
    signature_bytes = private_key.sign(canonical.encode('utf-8'))

    header = {"alg": "EdDSA", "b64": False, "crit": ["b64"]}
    header_b64 = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    signature_b64 = _b64url_encode(signature_bytes)

    return f"{header_b64}..{signature_b64}"


def verify_credential_signature(credential: Dict[str, Any], public_key_multibase: str) -> bool:
    """
    Verify the Ed25519 signature on a W3C Verifiable Credential.

    Handles DID:KEY publicKeyMultibase format:
        'z' + base58btc(0xed01_multicodec_prefix + 32_byte_public_key)

    Args:
        credential: Full credential dict including 'proof'.
        public_key_multibase: From DID Document verificationMethod.

    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        proof = credential.get('proof', {})
        jws = proof.get('jws', '')
        if not jws:
            return False

        credential_copy = {k: v for k, v in credential.items() if k != 'proof'}
        canonical = json.dumps(credential_copy, sort_keys=True, separators=(',', ':'))

        parts = jws.split('.')
        if len(parts) != 3:
            return False

        signature_bytes = _b64url_decode(parts[2])

        # Decode DID:KEY publicKeyMultibase:
        #   'z' = base58btc multibase prefix
        #   next 2 bytes = multicodec prefix (0xed 0x01 for Ed25519)
        #   remaining 32 bytes = raw Ed25519 public key
        raw = base58.b58decode(public_key_multibase[1:])  # remove 'z'
        public_key_bytes = raw[MULTICODEC_ED25519_PREFIX_LEN:]

        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, canonical.encode('utf-8'))
        return True

    except (InvalidSignature, Exception):
        return False


def is_credential_expired(credential: Dict[str, Any]) -> bool:
    """
    Check if the credential's expirationDate has passed.

    Critical for short-lived VendorAccessCredentials (24-48h validity).

    Returns:
        True if expired, False if still valid or no expiration set.
    """
    expiration = credential.get('expirationDate')
    if not expiration:
        return False
    try:
        exp_dt = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > exp_dt
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _b64url_decode(s: str) -> bytes:
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + '=' * padding)
