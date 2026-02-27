"""
Generate a new association DID:KEY pair.

Run this once to create the association's signing identity:
    python generate_keys.py

Output:
    - DID:KEY identifier (public, safe to share)
    - ASSOCIATION_PRIVATE_KEY_B64 value to add to .env

Warning: Re-running this creates a new identity. Any previously issued
credentials will still verify against the old key stored in .env.
"""

import base64
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.did_key import generate_did_key

if __name__ == '__main__':
    did, priv_bytes = generate_did_key()
    priv_b64 = base64.b64encode(priv_bytes).decode('utf-8')

    print("=" * 60)
    print("Association DID:KEY generated successfully")
    print("=" * 60)
    print()
    print(f"DID (public identifier):")
    print(f"  {did}")
    print()
    print(f"Add to your .env file:")
    print(f"  ASSOCIATION_PRIVATE_KEY_B64={priv_b64}")
    print()
    print("Keep ASSOCIATION_PRIVATE_KEY_B64 secret.")
    print("=" * 60)
