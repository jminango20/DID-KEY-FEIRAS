"""
Farmer management routes — FeirasWallet.

Routes:
    GET  /farmers/register           - Registration form
    POST /farmers/register           - Register new farmer (generates DID:KEY)
    GET  /farmers/                   - List all farmers
    POST /farmers/<id>/approve       - Approve a farmer
    POST /farmers/<id>/reject        - Reject / deactivate a farmer
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from routes.admin_routes import require_admin

farmer_bp = Blueprint('farmers', __name__, url_prefix='/farmers')


@farmer_bp.route('/register', methods=['GET', 'POST'])
@require_admin
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        cpf = request.form.get('cpf', '').strip()
        products_raw = request.form.get('products', '').strip()

        if not name:
            flash('Nome é obrigatório', 'error')
            return render_template('farmers/register.html')

        products = [p.strip() for p in products_raw.split(',') if p.strip()]

        # Normalize CPF: keep only digits, then format as 000.000.000-00
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        if cpf_digits:
            if len(cpf_digits) != 11:
                flash('CPF deve ter 11 dígitos', 'error')
                return render_template('farmers/register.html')
            cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
        else:
            cpf = None

        try:
            from utils.did_key import generate_did_key
            from utils.database import get_supabase_client

            supabase = get_supabase_client()

            # Block duplicate CPF
            if cpf:
                existing = supabase.table('registered_farmers') \
                    .select('id') \
                    .eq('cpf', cpf) \
                    .execute()
                if existing.data:
                    flash(f'CPF {cpf} já está cadastrado', 'error')
                    return render_template('farmers/register.html')

            did, _priv_bytes = generate_did_key()
            multibase = did[len("did:key:"):]

            supabase.table('registered_farmers').insert({
                'name': name,
                'cpf': cpf or None,
                'did': did,
                'public_key_multibase': multibase,
                'products': products,
                'approved': False
            }).execute()

            flash(f'Agricultor {name} registrado. DID: {did[:30]}...', 'success')
            return redirect(url_for('farmers.list_farmers'))

        except Exception as e:
            flash(f'Erro ao registrar agricultor: {str(e)}', 'error')

    return render_template('farmers/register.html')


@farmer_bp.route('/')
@require_admin
def list_farmers():
    from utils.database import get_supabase_client
    farmers = []
    try:
        supabase = get_supabase_client()
        result = supabase.table('registered_farmers') \
            .select('*') \
            .order('created_at', desc=True) \
            .execute()
        farmers = result.data or []
    except Exception as e:
        flash(f'Erro ao carregar agricultores: {str(e)}', 'error')

    return render_template('farmers/list.html', farmers=farmers)


@farmer_bp.route('/<farmer_id>/approve', methods=['POST'])
@require_admin
def approve(farmer_id: str):
    try:
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        supabase.table('registered_farmers').update({'approved': True}).eq('id', farmer_id).execute()
        flash('Agricultor aprovado com sucesso', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'error')
    return redirect(url_for('farmers.list_farmers'))


@farmer_bp.route('/<farmer_id>/reject', methods=['POST'])
@require_admin
def reject(farmer_id: str):
    try:
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        supabase.table('registered_farmers').update({'approved': False}).eq('id', farmer_id).execute()
        flash('Agricultor desativado', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'error')
    return redirect(url_for('farmers.list_farmers'))
