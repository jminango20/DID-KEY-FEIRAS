"""
Wallet routes — farmer-facing PWA pages.

The wallet stores credentials in the browser's localStorage.
The server only serves HTML pages; all credential storage is client-side.

Routes:
    GET /wallet/              - Wallet home (list credentials)
    GET /wallet/claim/<id>   - Claim a credential by claim ID
    GET /wallet/view          - View a single credential
"""

from flask import Blueprint, render_template

wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')


@wallet_bp.route('/')
def index():
    return render_template('wallet/index.html')


@wallet_bp.route('/claim/<claim_id>')
def claim(claim_id: str):
    return render_template('wallet/claim.html', claim_id=claim_id)


@wallet_bp.route('/view')
def view_credential():
    return render_template('wallet/view_credential.html')
