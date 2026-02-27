"""
Feira (market event) management routes — FeirasWallet.

Routes:
    GET  /events/                    - List all events
    GET  /events/create              - Create event form
    POST /events/create              - Create new market event
    GET  /events/<event_id>          - Event detail + credential issuance
    POST /events/<event_id>/issue    - Issue credentials for all approved farmers
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from routes.admin_routes import require_admin

feira_bp = Blueprint('events', __name__, url_prefix='/events')


@feira_bp.route('/')
@require_admin
def list_events():
    from utils.database import get_supabase_client
    events = []
    try:
        supabase = get_supabase_client()
        result = supabase.table('market_events') \
            .select('*') \
            .order('event_date', desc=True) \
            .execute()
        events = result.data or []
    except Exception as e:
        flash(f'Erro ao carregar eventos: {str(e)}', 'error')
    return render_template('events/list.html', events=events)


@feira_bp.route('/create', methods=['GET', 'POST'])
@require_admin
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        event_date = request.form.get('event_date', '').strip()
        municipality = request.form.get('municipality', '').strip()
        state = request.form.get('state', '').strip()
        opening_time = request.form.get('opening_time', '06:00').strip()
        closing_time = request.form.get('closing_time', '14:00').strip()
        valid_from = request.form.get('valid_from', '').strip()
        valid_until = request.form.get('valid_until', '').strip()

        if not all([name, event_date, municipality, state, valid_from, valid_until]):
            flash('Preencha todos os campos obrigatórios', 'error')
            return render_template('events/create.html')

        try:
            from utils.database import get_supabase_client
            supabase = get_supabase_client()
            result = supabase.table('market_events').insert({
                'name': name,
                'event_date': event_date,
                'municipality': municipality,
                'state': state,
                'opening_time': opening_time,
                'closing_time': closing_time,
                'valid_from': valid_from,
                'valid_until': valid_until
            }).execute()

            event_id = result.data[0]['id']
            flash(f'Evento "{name}" criado com sucesso', 'success')
            return redirect(url_for('events.event_detail', event_id=event_id))

        except Exception as e:
            flash(f'Erro ao criar evento: {str(e)}', 'error')

    return render_template('events/create.html')


@feira_bp.route('/<event_id>')
@require_admin
def event_detail(event_id: str):
    from utils.database import get_supabase_client

    event = None
    farmers = []
    issued_credentials = []

    try:
        supabase = get_supabase_client()

        ev_result = supabase.table('market_events').select('*').eq('id', event_id).execute()
        if not ev_result.data:
            flash('Evento não encontrado', 'error')
            return redirect(url_for('events.list_events'))
        event = ev_result.data[0]

        farmers_result = supabase.table('registered_farmers') \
            .select('id, name, products, did, approved') \
            .eq('approved', True) \
            .execute()
        farmers = farmers_result.data or []

        creds_result = supabase.table('vendor_credentials') \
            .select('claim_id, farmer_id, stall_number, issued_at, claimed') \
            .eq('event_id', event_id) \
            .execute()
        issued_credentials = creds_result.data or []

    except Exception as e:
        flash(f'Erro: {str(e)}', 'error')

    issued_farmer_ids = {c['farmer_id'] for c in issued_credentials}

    return render_template(
        'events/detail.html',
        event=event,
        farmers=farmers,
        issued_credentials=issued_credentials,
        issued_farmer_ids=issued_farmer_ids
    )


@feira_bp.route('/<event_id>/issue', methods=['POST'])
@require_admin
def issue_credentials(event_id: str):
    """Issue VendorAccessCredentials for selected (or all) approved farmers."""
    from utils.database import get_supabase_client
    from utils.credential_feira import create_vendor_access_credential, generate_claim_id, credential_to_json

    try:
        supabase = get_supabase_client()

        ev_result = supabase.table('market_events').select('*').eq('id', event_id).execute()
        if not ev_result.data:
            flash('Evento não encontrado', 'error')
            return redirect(url_for('events.list_events'))
        event = ev_result.data[0]

        farmer_ids = request.form.getlist('farmer_ids')
        stall_numbers = request.form.to_dict()

        if not farmer_ids:
            farmers_result = supabase.table('registered_farmers') \
                .select('id, name, did, products') \
                .eq('approved', True) \
                .execute()
            all_farmers = farmers_result.data or []
        else:
            farmers_result = supabase.table('registered_farmers') \
                .select('id, name, did, products') \
                .in_('id', farmer_ids) \
                .execute()
            all_farmers = farmers_result.data or []

        issued = 0
        for i, farmer in enumerate(all_farmers):
            stall_key = f"stall_{farmer['id']}"
            stall_number = stall_numbers.get(stall_key, str(i + 1))
            claim_id = generate_claim_id()

            # Products can be overridden per event in the issuance form
            products_raw = request.form.get(f"products_{farmer['id']}", '').strip()
            if products_raw:
                products = [p.strip() for p in products_raw.split(',') if p.strip()]
            else:
                products = farmer.get('products') or []

            credential = create_vendor_access_credential(
                claim_id=claim_id,
                farmer_did=farmer['did'],
                farmer_name=farmer['name'],
                stall_number=stall_number,
                products=products,
                event_name=event['name'],
                event_date=event['event_date'],
                municipality=event['municipality'],
                state=event['state'],
                opening_time=event.get('opening_time', '06:00'),
                closing_time=event.get('closing_time', '14:00'),
                valid_until=event['valid_until']
            )

            supabase.table('vendor_credentials').insert({
                'claim_id': claim_id,
                'farmer_id': farmer['id'],
                'event_id': event_id,
                'stall_number': stall_number,
                'credential_json': credential_to_json(credential)
            }).execute()
            issued += 1

        flash(f'{issued} credencial(is) emitida(s) com sucesso', 'success')

    except Exception as e:
        flash(f'Erro ao emitir credenciais: {str(e)}', 'error')

    return redirect(url_for('events.event_detail', event_id=event_id))
