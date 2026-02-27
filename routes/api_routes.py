"""
Public API endpoints — FeirasWallet.

Endpoints:
    GET  /api/credentials/<claim_id>           - Get credential by claim ID
    GET  /api/credentials/<claim_id>/qr-verify - QR code PNG for verification
    POST /api/credentials/<claim_id>/claim     - Mark credential as claimed
    POST /api/verify                           - Verify credential (JSON)
"""

import json as json_module
from functools import wraps
from flask import Blueprint, request, jsonify, send_file

api_bp = Blueprint('api', __name__, url_prefix='/api')


class ClaimNotFoundError(Exception):
    pass


def handle_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ClaimNotFoundError:
            return jsonify({"error": "Credencial não encontrada"}), 404
        except Exception as e:
            print(f"API error: {e}")
            return jsonify({"error": "Erro interno do servidor"}), 500
    return decorated


@api_bp.route('/credentials/<claim_id>', methods=['GET'])
@handle_errors
def get_credential(claim_id: str):
    from utils.database import get_supabase_client
    supabase = get_supabase_client()
    result = supabase.table('vendor_credentials') \
        .select('credential_json') \
        .eq('claim_id', claim_id) \
        .execute()

    if not result.data:
        raise ClaimNotFoundError()

    row = result.data[0]
    credential = json_module.loads(row['credential_json']) \
        if isinstance(row['credential_json'], str) else row['credential_json']

    return jsonify({"credential": credential})


@api_bp.route('/credentials/<claim_id>/qr-verify', methods=['GET'])
@handle_errors
def qr_verify(claim_id: str):
    import io
    import qrcode
    from utils.database import get_supabase_client

    supabase = get_supabase_client()
    result = supabase.table('vendor_credentials') \
        .select('claim_id') \
        .eq('claim_id', claim_id) \
        .execute()

    if not result.data:
        raise ClaimNotFoundError()

    verify_url = request.host_url.rstrip('/') + f'/verify?claim={claim_id}'

    qr = qrcode.QRCode(box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#2E7D32', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@api_bp.route('/credentials/<claim_id>/claim', methods=['POST'])
@handle_errors
def claim_credential(claim_id: str):
    from utils.database import get_supabase_client
    from datetime import datetime, timezone

    supabase = get_supabase_client()
    result = supabase.table('vendor_credentials') \
        .select('claimed') \
        .eq('claim_id', claim_id) \
        .execute()

    if not result.data:
        raise ClaimNotFoundError()

    if not result.data[0]['claimed']:
        supabase.table('vendor_credentials').update({
            'claimed': True,
            'claimed_at': datetime.now(timezone.utc).isoformat()
        }).eq('claim_id', claim_id).execute()

    return jsonify({"success": True})


@api_bp.route('/verify', methods=['POST'])
@handle_errors
def verify_credential():
    from utils.crypto import verify_credential_signature, is_credential_expired
    from utils.did_key import resolve_did_key

    data = request.get_json(silent=True) or {}
    credential = data.get('credential')

    if not credential:
        return jsonify({"error": "Nenhuma credencial fornecida"}), 400

    issuer_did = credential.get('issuer', '')
    if not issuer_did.startswith("did:key:"):
        return jsonify({"error": "Método DID não suportado"}), 400

    did_doc = resolve_did_key(issuer_did)
    public_key = did_doc['verificationMethod'][0]['publicKeyMultibase']
    signature_valid = verify_credential_signature(credential, public_key)
    expired = is_credential_expired(credential)

    return jsonify({
        "valid": signature_valid and not expired,
        "signatureValid": signature_valid,
        "expired": expired,
        "message": "Credencial válida" if (signature_valid and not expired) else
                   ("Expirada" if expired else "Assinatura inválida")
    })
