from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import Client, Lead
from datetime import datetime, date
from cache import invalidate_client_cache
import timezone as tz

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

def parse_date(date_str):
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

@clients_bp.route('/')
def index():
    status_filter = request.args.get('status', '')
    project_type_filter = request.args.get('project_type', '')
    hosting_filter = request.args.get('hosting_active', '')
    saas_filter = request.args.get('saas_active', '')
    
    filters = {}
    if status_filter:
        filters['status'] = status_filter
    if project_type_filter:
        filters['project_type'] = project_type_filter
    if hosting_filter:
        filters['hosting_active'] = hosting_filter == 'yes'
    if saas_filter:
        filters['saas_active'] = saas_filter == 'yes'
    
    clients = Client.query_filter(filters, order_by='created_at', order_desc=True) if filters else Client.query_all(order_by='created_at', order_desc=True)
    
    return render_template('clients/index.html',
        clients=clients,
        statuses=Client.status_choices(),
        project_types=Client.project_type_choices(),
        current_status=status_filter,
        current_project_type=project_type_filter,
        current_hosting=hosting_filter,
        current_saas=saas_filter
    )

@clients_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        start_date = parse_date(request.form.get('start_date')) or date.today()
        
        client = Client.insert({
            'name': request.form.get('name'),
            'business_name': request.form.get('business_name'),
            'contact_email': request.form.get('contact_email'),
            'phone': request.form.get('phone'),
            'project_type': request.form.get('project_type', 'website'),
            'start_date': start_date.isoformat(),
            'amount_charged': float(request.form.get('amount_charged') or 0),
            'status': request.form.get('status', 'active'),
            'hosting_active': request.form.get('hosting_active') == 'on',
            'monthly_hosting_fee': float(request.form.get('monthly_hosting_fee') or 0),
            'saas_active': request.form.get('saas_active') == 'on',
            'monthly_saas_fee': float(request.form.get('monthly_saas_fee') or 0),
            'notes': request.form.get('notes')
        })
        invalidate_client_cache()
        flash('Client created successfully!', 'success')
        return redirect(url_for('clients.index'))
    
    return render_template('clients/form.html',
        client=None,
        statuses=Client.status_choices(),
        project_types=Client.project_type_choices(),
        action='Create',
        today=date.today().isoformat()
    )

@clients_bp.route('/<int:id>')
def detail(id):
    client = Client.get_by_id(id)
    if not client:
        abort(404)
    related_lead = Lead.get_by_id(client.related_lead_id) if getattr(client, 'related_lead_id', None) else None
    return render_template('clients/detail.html', client=client, related_lead=related_lead)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    client = Client.get_by_id(id)
    if not client:
        abort(404)
    
    if request.method == 'POST':
        start_date = parse_date(request.form.get('start_date'))
        if not start_date:
            start_date = getattr(client, 'start_date', date.today())
            if isinstance(start_date, str):
                start_date = parse_date(start_date) or date.today()
        
        Client.update_by_id(id, {
            'name': request.form.get('name'),
            'business_name': request.form.get('business_name'),
            'contact_email': request.form.get('contact_email'),
            'phone': request.form.get('phone'),
            'project_type': request.form.get('project_type'),
            'start_date': start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            'amount_charged': float(request.form.get('amount_charged') or 0),
            'status': request.form.get('status'),
            'hosting_active': request.form.get('hosting_active') == 'on',
            'monthly_hosting_fee': float(request.form.get('monthly_hosting_fee') or 0),
            'saas_active': request.form.get('saas_active') == 'on',
            'monthly_saas_fee': float(request.form.get('monthly_saas_fee') or 0),
            'notes': request.form.get('notes'),
            'updated_at': tz.now_iso()
        })
        invalidate_client_cache()
        flash('Client updated successfully!', 'success')
        return redirect(url_for('clients.detail', id=id))
    
    return render_template('clients/form.html',
        client=client,
        statuses=Client.status_choices(),
        project_types=Client.project_type_choices(),
        action='Edit',
        today=date.today().isoformat()
    )

@clients_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    client = Client.get_by_id(id)
    if not client:
        abort(404)
    Client.delete_by_id(id)
    invalidate_client_cache()
    flash('Client deleted successfully!', 'success')
    return redirect(url_for('clients.index'))
