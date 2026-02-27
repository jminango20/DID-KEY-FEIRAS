"""
DID:KEY implementation for FeirasWallet.

DID:KEY encodes the public key directly in the identifier using multibase
(base58btc with 'z' prefix) and multicodec (0xed01 prefix for Ed25519).

Key property: DID Document is derived mathematically from the DID itself.
No HTTP request, no server, no infrastructure — works 100% offline.

    DID:KEY resolution:
        did:key:z6Mk...  →  derive DID Document  (no network call)

    vs DID:WEB:
        did:web:domain:path  →  GET https://domain/path/did.json  (requires server)
"""

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

# Multicodec prefix for Ed25519 public key (0xed 0x01)
MULTICODEC_ED25519_PREFIX = b'\xed\x01'


def generate_did_key() -> tuple:
    """
    Generate a new Ed25519 keypair and derive a DID:KEY.

    Works completely offline. No server, no file I/O.

    Returns:
        (did_string, private_key_raw_bytes)
        did_string: e.g. "did:key:z6MkhaXgBZDvotzL8L7XYKn..."
        private_key_raw_bytes: 32 raw bytes (store securely, never share)
    """
    private_key = Ed25519PrivateKey.generate()
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    priv_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

    multibase = _pub_bytes_to_multibase(pub_bytes)
    did = f"did:key:{multibase}"
    return did, priv_bytes


def did_from_private_bytes(priv_bytes: bytes) -> str:
    """Derive DID:KEY string from raw Ed25519 private key bytes."""
    private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    multibase = _pub_bytes_to_multibase(pub_bytes)
    return f"did:key:{multibase}"


def resolve_did_key(did: str) -> dict:
    """
    Derive the DID Document from a DID:KEY — no HTTP, no server, offline.

    The DID Document is fully deterministic: given the same DID:KEY,
    the same document is always produced. The public key is embedded
    in the DID identifier itself.

    Args:
        did: A DID:KEY string, e.g. "did:key:z6MkhaXgBZDvotzL8L7XYKn..."

    Returns:
        W3C DID Document dict with verificationMethod, authentication,
        and assertionMethod sections.

    Raises:
        ValueError: If the DID is not a valid did:key string.
    """
    if not did.startswith("did:key:"):
        raise ValueError(f"Not a did:key: {did}")

    multibase = did[len("did:key:"):]
    vm_id = f"{did}#{multibase}"

    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1"
        ],
        "id": did,
        "verificationMethod": [
            {
                "id": vm_id,
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": multibase
            }
        ],
        "authentication": [vm_id],
        "assertionMethod": [vm_id]
    }


def _pub_bytes_to_multibase(pub_bytes: bytes) -> str:
    """Encode raw Ed25519 public key bytes as multibase base58btc."""
    return 'z' + base58.b58encode(MULTICODEC_ED25519_PREFIX + pub_bytes).decode('utf-8')
