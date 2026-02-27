"""
Verifier routes — offline credential verification for FeirasWallet.

The gate operator (porteiro) uses this page to verify VendorAccessCredentials.
Verification resolves DID:KEY offline (no HTTP calls required).

Routes:
    GET  /verify/        - Verifier landing page (gate app)
    POST /verify/check   - Verify credential signature + expiration
"""

from flask import Blueprint, render_template, request, jsonify

from utils.crypto import verify_credential_signature, is_credential_expired
from utils.did_key import resolve_did_key

verifier_bp = Blueprint('verifier', __name__, url_prefix='/verify')


@verifier_bp.route('/')
def index():
    return render_template('verifier/index.html')


@verifier_bp.route('/check', methods=['POST'])
def check_credential():
    """
    Verify a VendorAccessCredential.

    Accepts JSON body: { "credential": { ...W3C VC... } }

    Checks:
    1. Ed25519 signature validity (DID:KEY resolved offline)
    2. expirationDate — critical for 24-48h credentials
    3. credential type is VendorAccessCredential

    Returns verification result with event and farmer details.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'JSON é necessário no corpo da solicitação'}), 400

        credential = data.get('credential')
        if not credential:
            return jsonify({'error': 'Nenhuma credencial fornecida'}), 400

        issuer_did = credential.get('issuer', '')
        if not issuer_did:
            return jsonify({'error': 'Credencial inválida: emissor ausente'}), 400

        if not issuer_did.startswith("did:key:"):
            return jsonify({
                'valid': False,
                'error': 'Método DID não suportado. Esperado: did:key',
                'message': 'Método DID inválido'
            }), 200

        # Resolve DID:KEY offline — no HTTP call needed
        try:
            did_document = resolve_did_key(issuer_did)
        except Exception as e:
            return jsonify({
                'valid': False,
                'error': f'Não foi possível resolver o DID do emissor: {str(e)}',
                'message': 'DID inválido'
            }), 200

        verification_methods = did_document.get('verificationMethod', [])
        if not verification_methods:
            return jsonify({'valid': False, 'error': 'Documento DID sem chaves de verificação'}), 200

        public_key_multibase = verification_methods[0].get('publicKeyMultibase')
        if not public_key_multibase:
            return jsonify({'valid': False, 'error': 'Chave pública não encontrada'}), 200

        # Verify Ed25519 signature
        signature_valid = verify_credential_signature(credential, public_key_multibase)

        # Check expiration — just as important as signature for 24-48h credentials
        expired = is_credential_expired(credential)

        is_valid = signature_valid and not expired

        subject = credential.get('credentialSubject', {})
        event = subject.get('event', {})

        # Determine status message
        if not signature_valid:
            message = 'Assinatura inválida — credencial falsificada ou adulterada'
        elif expired:
            message = 'Credencial expirada — não é válida para este evento'
        else:
            message = 'Credencial válida'

        result = {
            'valid': is_valid,
            'signatureValid': signature_valid,
            'expired': expired,
            'message': message,
            'credential': {
                'id': credential.get('id'),
                'type': credential.get('type', []),
                'issuer': issuer_did,
                'issuanceDate': credential.get('issuanceDate'),
                'expirationDate': credential.get('expirationDate'),
                'credentialSubject': {
                    'id': subject.get('id'),
                    'farmerName': subject.get('farmerName'),
                    'stallNumber': subject.get('stallNumber'),
                    'products': subject.get('products', []),
                    'event': {
                        'name': event.get('name'),
                        'date': event.get('date'),
                        'municipality': event.get('municipality'),
                        'state': event.get('state'),
                        'openingTime': event.get('openingTime'),
                        'closingTime': event.get('closingTime')
                    }
                }
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
