"""
VendorAccessCredential — W3C Verifiable Credential for farmer market access.

Creates credentials of type VendorAccessCredential following W3C VC Data Model 1.1.
The association signs credentials with its DID:KEY private key.
Credentials have a short expirationDate (24-48h) matching the market event window.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from utils.crypto import sign_credential, private_key_from_bytes
from config import config


def generate_claim_id() -> str:
    return str(uuid.uuid4()).replace('-', '')[:16].upper()


def create_vendor_access_credential(
    claim_id: str,
    farmer_did: str,
    farmer_name: str,
    stall_number: str,
    products: list,
    event_name: str,
    event_date: str,
    municipality: str,
    state: str,
    opening_time: str,
    closing_time: str,
    valid_until: str,
) -> dict:
    """
    Create and sign a VendorAccessCredential for a farmer to access a market event.

    The credential structure:
    {
        "@context": [...],
        "id": "{issuer_did}/credentials/{claim_id}",
        "type": ["VerifiableCredential", "VendorAccessCredential"],
        "issuer": "{association_did:key}",
        "issuanceDate": "{now_iso}",
        "expirationDate": "{valid_until_iso}",
        "credentialSubject": {
            "id": "{farmer_did:key}",
            "farmerName": "{farmer_name}",
            "stallNumber": "{stall_number}",
            "products": [...],
            "event": {
                "name": "{event_name}",
                "date": "{event_date}",
                "municipality": "{municipality}",
                "state": "{state}",
                "openingTime": "{opening_time}",
                "closingTime": "{closing_time}"
            }
        },
        "proof": {
            "type": "Ed25519Signature2020",
            "verificationMethod": "{association_did:key}#{multibase}",
            "jws": "..."
        }
    }

    Args:
        claim_id: Pre-generated unique identifier for this credential.
        farmer_did: The farmer's DID:KEY identifier.
        farmer_name: Display name of the farmer.
        stall_number: Assigned stall/banca number at the market.
        products: List of product names (e.g. ["Mel", "Café"]).
        event_name: Name of the market event.
        event_date: Date string (YYYY-MM-DD).
        municipality: City where the market takes place.
        state: Brazilian state abbreviation (e.g. "MG").
        opening_time: Market opening time (HH:MM).
        closing_time: Market closing time (HH:MM).
        valid_until: ISO datetime string — credential expiration.

    Returns:
        Signed credential dict (W3C VC with proof).
    """
    now = datetime.now(timezone.utc).isoformat()
    issuer_did = config.ASSOCIATION_DID

    # verificationMethod ID: did:key:{multibase}#{multibase}
    multibase = issuer_did[len("did:key:"):]
    verification_method_id = f"{issuer_did}#{multibase}"

    credential = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1"
        ],
        "id": f"{issuer_did}/credentials/{claim_id}",
        "type": ["VerifiableCredential", "VendorAccessCredential"],
        "issuer": issuer_did,
        "issuanceDate": now,
        "expirationDate": valid_until,
        "credentialSubject": {
            "id": farmer_did,
            "farmerName": farmer_name,
            "stallNumber": stall_number,
            "products": products,
            "event": {
                "name": event_name,
                "date": event_date,
                "municipality": municipality,
                "state": state,
                "openingTime": opening_time,
                "closingTime": closing_time
            }
        }
    }

    private_key = private_key_from_bytes(config.ASSOCIATION_PRIVATE_KEY_BYTES)
    jws = sign_credential(credential, private_key)

    credential["proof"] = {
        "type": "Ed25519Signature2020",
        "created": now,
        "verificationMethod": verification_method_id,
        "proofPurpose": "assertionMethod",
        "jws": jws
    }

    return credential


def credential_to_json(credential: dict) -> str:
    """Serialize credential to canonical JSON (sort_keys=True).
    Must use TEXT storage in DB — never JSONB — to preserve key order for signature verification."""
    return json.dumps(credential, sort_keys=True, separators=(',', ':'))
