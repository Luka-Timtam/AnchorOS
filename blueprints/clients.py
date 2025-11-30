from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Client, Lead
from datetime import datetime, date

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
    
    query = Client.query
    
    if status_filter:
        query = query.filter(Client.status == status_filter)
    if project_type_filter:
        query = query.filter(Client.project_type == project_type_filter)
    if hosting_filter:
        query = query.filter(Client.hosting_active == (hosting_filter == 'yes'))
    if saas_filter:
        query = query.filter(Client.saas_active == (saas_filter == 'yes'))
    
    clients = query.order_by(Client.created_at.desc()).all()
    
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
        client = Client(
            name=request.form.get('name'),
            business_name=request.form.get('business_name'),
            contact_email=request.form.get('contact_email'),
            phone=request.form.get('phone'),
            project_type=request.form.get('project_type', 'website'),
            start_date=parse_date(request.form.get('start_date')) or date.today(),
            amount_charged=request.form.get('amount_charged') or 0,
            status=request.form.get('status', 'active'),
            hosting_active=request.form.get('hosting_active') == 'on',
            monthly_hosting_fee=request.form.get('monthly_hosting_fee') or 0,
            saas_active=request.form.get('saas_active') == 'on',
            monthly_saas_fee=request.form.get('monthly_saas_fee') or 0,
            notes=request.form.get('notes')
        )
        db.session.add(client)
        db.session.commit()
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
    client = Client.query.get_or_404(id)
    related_lead = Lead.query.get(client.related_lead_id) if client.related_lead_id else None
    return render_template('clients/detail.html', client=client, related_lead=related_lead)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    client = Client.query.get_or_404(id)
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.business_name = request.form.get('business_name')
        client.contact_email = request.form.get('contact_email')
        client.phone = request.form.get('phone')
        client.project_type = request.form.get('project_type')
        client.start_date = parse_date(request.form.get('start_date')) or client.start_date
        client.amount_charged = request.form.get('amount_charged') or 0
        client.status = request.form.get('status')
        client.hosting_active = request.form.get('hosting_active') == 'on'
        client.monthly_hosting_fee = request.form.get('monthly_hosting_fee') or 0
        client.saas_active = request.form.get('saas_active') == 'on'
        client.monthly_saas_fee = request.form.get('monthly_saas_fee') or 0
        client.notes = request.form.get('notes')
        client.updated_at = datetime.utcnow()
        
        db.session.commit()
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
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully!', 'success')
    return redirect(url_for('clients.index'))
