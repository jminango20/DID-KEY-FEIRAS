"""
Admin panel routes — FeirasWallet.

Provides a web interface for the association admin to:
- Log in with admin credentials
- View dashboard: registered farmers, upcoming events, issued credentials
- Navigate to farmer management and event management
"""

import io
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from config import config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin(f):
    """Decorator: redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Credenciais incorretas', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@require_admin
def dashboard():
    from utils.database import get_supabase_client

    credentials = []
    total_farmers = 0
    approved_farmers = 0
    upcoming_events = 0

    try:
        supabase = get_supabase_client()

        creds_result = supabase.table('vendor_credentials') \
            .select('claim_id, event_id, issued_at, claimed') \
            .order('issued_at', desc=True) \
            .limit(20) \
            .execute()
        credentials = creds_result.data or []

        farmers_result = supabase.table('registered_farmers') \
            .select('id, approved') \
            .execute()
        farmers = farmers_result.data or []
        total_farmers = len(farmers)
        approved_farmers = sum(1 for f in farmers if f.get('approved'))

        from datetime import date
        events_result = supabase.table('market_events') \
            .select('id') \
            .gte('event_date', date.today().isoformat()) \
            .execute()
        upcoming_events = len(events_result.data or [])

    except Exception as e:
        flash(f'Erro no banco de dados: {str(e)}', 'error')

    return render_template(
        'admin/dashboard.html',
        credentials=credentials,
        total_farmers=total_farmers,
        approved_farmers=approved_farmers,
        upcoming_events=upcoming_events,
        association_did=config.ASSOCIATION_DID
    )


@admin_bp.route('/qr/<claim_id>')
@require_admin
def qr_code(claim_id: str):
    """Return QR code PNG for the claim URL."""
    import qrcode
    claim_url = request.host_url.rstrip('/') + f'/wallet/claim/{claim_id}'

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(claim_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#2E7D32', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')
