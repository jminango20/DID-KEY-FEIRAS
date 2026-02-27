"""Tests for utils/did_key.py — DID:KEY generation and resolution."""
import pytest
import base58
from utils.did_key import generate_did_key, did_from_private_bytes, resolve_did_key

MULTICODEC_ED25519_PREFIX = b'\xed\x01'


class TestGenerateDidKey:
    def test_returns_tuple(self):
        result = generate_did_key()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_did_format(self):
        did, priv = generate_did_key()
        assert did.startswith('did:key:z')

    def test_private_key_bytes(self):
        did, priv = generate_did_key()
        assert isinstance(priv, bytes)
        assert len(priv) == 32

    def test_multibase_decodes_correctly(self):
        did, _ = generate_did_key()
        multibase = did[len('did:key:'):]
        assert multibase[0] == 'z', "Must use base58btc (z prefix)"
        raw = base58.b58decode(multibase[1:])
        assert raw[:2] == MULTICODEC_ED25519_PREFIX, "Must have 0xed01 multicodec prefix"
        assert len(raw) == 34, "Prefix (2) + Ed25519 pub key (32)"

    def test_uniqueness(self):
        did1, _ = generate_did_key()
        did2, _ = generate_did_key()
        assert did1 != did2

    def test_deterministic_from_private_bytes(self):
        did, priv = generate_did_key()
        did2 = did_from_private_bytes(priv)
        assert did == did2


class TestDidFromPrivateBytes:
    def test_roundtrip(self):
        did, priv = generate_did_key()
        reconstructed = did_from_private_bytes(priv)
        assert reconstructed == did

    def test_invalid_length_raises(self):
        with pytest.raises(Exception):
            did_from_private_bytes(b'\x00' * 31)  # too short


class TestResolveDidKey:
    def test_returns_dict(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        assert isinstance(doc, dict)

    def test_id_matches(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        assert doc['id'] == did

    def test_has_verification_method(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        vms = doc.get('verificationMethod', [])
        assert len(vms) == 1
        vm = vms[0]
        assert vm['type'] == 'Ed25519VerificationKey2020'
        assert vm['publicKeyMultibase'].startswith('z')
        assert vm['controller'] == did

    def test_verification_method_id(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        vm_id = doc['verificationMethod'][0]['id']
        multibase = did[len('did:key:'):]
        assert vm_id == f"{did}#{multibase}"

    def test_assertion_method_references_vm(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        vm_id = doc['verificationMethod'][0]['id']
        assert vm_id in doc['assertionMethod']

    def test_public_key_matches_private(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        did, priv = generate_did_key()
        doc = resolve_did_key(did)
        multibase = doc['verificationMethod'][0]['publicKeyMultibase']
        raw = base58.b58decode(multibase[1:])
        pub_from_doc = raw[2:]  # strip multicodec prefix

        private_key = Ed25519PrivateKey.from_private_bytes(priv)
        pub_from_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        assert pub_from_doc == pub_from_key

    def test_context_includes_ed25519_2020(self):
        did, _ = generate_did_key()
        doc = resolve_did_key(did)
        assert 'https://w3id.org/security/suites/ed25519-2020/v1' in doc['@context']

    def test_invalid_did_raises(self):
        with pytest.raises(Exception):
            resolve_did_key("did:web:example.com")
