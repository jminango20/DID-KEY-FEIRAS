"""Tests for VendorAccessCredential creation and Ed25519 verification."""
import json
import pytest
from datetime import datetime, timezone, timedelta

from utils.did_key import generate_did_key, resolve_did_key
from utils.crypto import (
    sign_credential, verify_credential_signature,
    is_credential_expired, private_key_from_bytes
)
from utils.credential_feira import create_vendor_access_credential, generate_claim_id


@pytest.fixture(autouse=True)
def setup_association_keys(monkeypatch):
    """Set up a fresh association DID:KEY for each test."""
    from config import config
    did, priv = generate_did_key()
    monkeypatch.setattr(config, 'ASSOCIATION_DID', did)
    monkeypatch.setattr(config, 'ASSOCIATION_PRIVATE_KEY_BYTES', priv)


@pytest.fixture
def farmer_did():
    did, _ = generate_did_key()
    return did


@pytest.fixture
def valid_until_future():
    return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


@pytest.fixture
def valid_until_past():
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


@pytest.fixture
def sample_credential(farmer_did, valid_until_future):
    return create_vendor_access_credential(
        claim_id=generate_claim_id(),
        farmer_did=farmer_did,
        farmer_name='José Pereira da Silva',
        stall_number='7',
        products=['Mel', 'Café', 'Doces Artesanais'],
        event_name='Feira Orgânica de Lavras',
        event_date='2024-06-07',
        municipality='Lavras',
        state='MG',
        opening_time='06:00',
        closing_time='14:00',
        valid_until=valid_until_future
    )


class TestGenerateClaimId:
    def test_length(self):
        cid = generate_claim_id()
        assert len(cid) == 16

    def test_uppercase_hex(self):
        cid = generate_claim_id()
        assert cid == cid.upper()

    def test_uniqueness(self):
        ids = {generate_claim_id() for _ in range(50)}
        assert len(ids) == 50


class TestCreateVendorAccessCredential:
    def test_returns_dict(self, sample_credential):
        assert isinstance(sample_credential, dict)

    def test_type(self, sample_credential):
        assert 'VerifiableCredential' in sample_credential['type']
        assert 'VendorAccessCredential' in sample_credential['type']

    def test_issuer_is_did_key(self, sample_credential):
        assert sample_credential['issuer'].startswith('did:key:z')

    def test_has_expiration_date(self, sample_credential):
        assert 'expirationDate' in sample_credential
        assert sample_credential['expirationDate'] is not None

    def test_credential_subject_fields(self, sample_credential, farmer_did):
        sub = sample_credential['credentialSubject']
        assert sub['id'] == farmer_did
        assert sub['farmerName'] == 'José Pereira da Silva'
        assert sub['stallNumber'] == '7'
        assert 'Mel' in sub['products']
        assert sub['event']['name'] == 'Feira Orgânica de Lavras'
        assert sub['event']['municipality'] == 'Lavras'
        assert sub['event']['state'] == 'MG'

    def test_has_proof(self, sample_credential):
        proof = sample_credential.get('proof', {})
        assert proof.get('type') == 'Ed25519Signature2020'
        assert proof.get('proofPurpose') == 'assertionMethod'
        assert '..' in proof.get('jws', '')

    def test_verification_method_format(self, sample_credential):
        proof = sample_credential['proof']
        vm = proof['verificationMethod']
        issuer = sample_credential['issuer']
        multibase = issuer[len('did:key:'):]
        assert vm == f"{issuer}#{multibase}"

    def test_context(self, sample_credential):
        ctx = sample_credential['@context']
        assert 'https://www.w3.org/2018/credentials/v1' in ctx
        assert 'https://w3id.org/security/suites/ed25519-2020/v1' in ctx


class TestSignatureVerification:
    def test_valid_signature_verifies(self, sample_credential):
        issuer_did = sample_credential['issuer']
        doc = resolve_did_key(issuer_did)
        public_key_multibase = doc['verificationMethod'][0]['publicKeyMultibase']
        assert verify_credential_signature(sample_credential, public_key_multibase) is True

    def test_tampered_credential_fails(self, sample_credential):
        issuer_did = sample_credential['issuer']
        doc = resolve_did_key(issuer_did)
        public_key_multibase = doc['verificationMethod'][0]['publicKeyMultibase']

        tampered = json.loads(json.dumps(sample_credential))
        tampered['credentialSubject']['stallNumber'] = '999'

        assert verify_credential_signature(tampered, public_key_multibase) is False

    def test_wrong_key_fails(self, sample_credential):
        other_did, _ = generate_did_key()
        other_doc = resolve_did_key(other_did)
        other_key = other_doc['verificationMethod'][0]['publicKeyMultibase']

        assert verify_credential_signature(sample_credential, other_key) is False

    def test_missing_proof_fails(self, sample_credential):
        no_proof = {k: v for k, v in sample_credential.items() if k != 'proof'}
        issuer_did = sample_credential['issuer']
        doc = resolve_did_key(issuer_did)
        public_key_multibase = doc['verificationMethod'][0]['publicKeyMultibase']

        assert verify_credential_signature(no_proof, public_key_multibase) is False

    def test_empty_jws_fails(self, sample_credential):
        cred = json.loads(json.dumps(sample_credential))
        cred['proof']['jws'] = ''
        issuer_did = sample_credential['issuer']
        doc = resolve_did_key(issuer_did)
        public_key_multibase = doc['verificationMethod'][0]['publicKeyMultibase']

        assert verify_credential_signature(cred, public_key_multibase) is False


class TestIsCredentialExpired:
    def test_future_expiration_not_expired(self, sample_credential):
        assert is_credential_expired(sample_credential) is False

    def test_past_expiration_is_expired(self, farmer_did, valid_until_past):
        cred = create_vendor_access_credential(
            claim_id=generate_claim_id(),
            farmer_did=farmer_did,
            farmer_name='Maria',
            stall_number='3',
            products=['Alface'],
            event_name='Feira Test',
            event_date='2024-01-01',
            municipality='Belo Horizonte',
            state='MG',
            opening_time='06:00',
            closing_time='12:00',
            valid_until=valid_until_past
        )
        assert is_credential_expired(cred) is True

    def test_no_expiration_not_expired(self):
        cred = {'type': ['VerifiableCredential']}
        assert is_credential_expired(cred) is False

    def test_signature_valid_but_expired_is_still_expired(self, farmer_did, valid_until_past):
        """Expired credential: signature valid but credential must be rejected at gate."""
        cred = create_vendor_access_credential(
            claim_id=generate_claim_id(),
            farmer_did=farmer_did,
            farmer_name='Maria',
            stall_number='3',
            products=['Alface'],
            event_name='Feira Test',
            event_date='2024-01-01',
            municipality='Belo Horizonte',
            state='MG',
            opening_time='06:00',
            closing_time='12:00',
            valid_until=valid_until_past
        )
        from config import config
        doc = resolve_did_key(config.ASSOCIATION_DID)
        pub_key_multibase = doc['verificationMethod'][0]['publicKeyMultibase']

        sig_valid = verify_credential_signature(cred, pub_key_multibase)
        expired = is_credential_expired(cred)

        assert sig_valid is True    # signature still valid
        assert expired is True      # but credential is expired
        # Gate logic: valid = sig_valid AND NOT expired
        assert not (sig_valid and not expired)
