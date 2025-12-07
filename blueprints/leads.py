from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Lead, OutreachLog, Client, ActivityLog
from datetime import datetime, date
from blueprints.gamification import add_xp, XP_RULES, TOKEN_RULES, add_tokens, update_mission_progress
from blueprints.boss import update_boss_progress

leads_bp = Blueprint('leads', __name__, url_prefix='/leads')

def parse_date(date_str):
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

@leads_bp.route('/')
def index():
    today = date.today()
    status_filter = request.args.get('status', '')
    niche_filter = request.args.get('niche', '')
    source_filter = request.args.get('source', '')
    search = request.args.get('search', '')
    next_action_filter = request.args.get('next_action', '')
    
    query = Lead.query.filter(Lead.converted_at.is_(None))
    
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if niche_filter:
        query = query.filter(Lead.niche == niche_filter)
    if source_filter:
        query = query.filter(Lead.source == source_filter)
    if search:
        query = query.filter(
            db.or_(
                Lead.name.ilike(f'%{search}%'),
                Lead.business_name.ilike(f'%{search}%')
            )
        )
    if next_action_filter == 'today':
        query = query.filter(
            Lead.next_action_date == today,
            Lead.status.notin_(['closed_won', 'closed_lost'])
        )
    elif next_action_filter == 'overdue':
        query = query.filter(
            Lead.next_action_date < today,
            Lead.status.notin_(['closed_won', 'closed_lost'])
        )
    
    leads = query.order_by(Lead.created_at.desc()).all()
    
    converted_leads = Lead.query.filter(Lead.converted_at.isnot(None)).order_by(Lead.converted_at.desc()).all()
    
    niches = db.session.query(Lead.niche).distinct().filter(Lead.niche.isnot(None), Lead.niche != '').all()
    sources = db.session.query(Lead.source).distinct().filter(Lead.source.isnot(None), Lead.source != '').all()
    
    return render_template('leads/index.html',
        leads=leads,
        converted_leads=converted_leads,
        statuses=Lead.status_choices(),
        niches=[n[0] for n in niches],
        sources=[s[0] for s in sources],
        current_status=status_filter,
        current_niche=niche_filter,
        current_source=source_filter,
        current_search=search,
        current_next_action=next_action_filter
    )

def get_existing_niches():
    niches = db.session.query(Lead.niche).distinct().filter(Lead.niche.isnot(None), Lead.niche != '').all()
    return [n[0] for n in niches]

def get_existing_sources():
    sources = db.session.query(Lead.source).distinct().filter(Lead.source.isnot(None), Lead.source != '').all()
    return [s[0] for s in sources]

@leads_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        has_website = request.form.get('has_website') == 'yes'
        quality_issues = request.form.getlist('website_quality') if has_website else []
        website_quality = ','.join(quality_issues) if quality_issues else ('no_website' if not has_website else '')
        
        lead = Lead(
            name=request.form.get('name'),
            business_name=request.form.get('business_name'),
            niche=request.form.get('niche'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            source=request.form.get('source'),
            status=request.form.get('status', 'new'),
            notes=request.form.get('notes'),
            next_action_date=parse_date(request.form.get('next_action_date')),
            has_website=has_website,
            website_quality=website_quality,
            demo_site_built=request.form.get('demo_site_built') == 'on'
        )
        db.session.add(lead)
        db.session.commit()
        flash('Lead created successfully!', 'success')
        return redirect(url_for('leads.index'))
    
    return render_template('leads/form.html', 
        lead=None, 
        statuses=Lead.status_choices(),
        website_qualities=Lead.website_quality_choices(),
        niches=get_existing_niches(),
        sources=get_existing_sources(),
        action='Create'
    )

@leads_bp.route('/<int:id>')
def detail(id):
    lead = Lead.query.get_or_404(id)
    outreach_logs = OutreachLog.query.filter_by(lead_id=id).order_by(OutreachLog.date.desc()).all()
    return render_template('leads/detail.html', lead=lead, outreach_logs=outreach_logs)

@leads_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    lead = Lead.query.get_or_404(id)
    
    if request.method == 'POST':
        has_website = request.form.get('has_website') == 'yes'
        quality_issues = request.form.getlist('website_quality') if has_website else []
        website_quality = ','.join(quality_issues) if quality_issues else ('no_website' if not has_website else '')
        
        lead.name = request.form.get('name')
        lead.business_name = request.form.get('business_name')
        lead.niche = request.form.get('niche')
        lead.email = request.form.get('email')
        lead.phone = request.form.get('phone')
        lead.source = request.form.get('source')
        lead.status = request.form.get('status')
        lead.notes = request.form.get('notes')
        lead.next_action_date = parse_date(request.form.get('next_action_date'))
        lead.has_website = has_website
        lead.website_quality = website_quality
        lead.demo_site_built = request.form.get('demo_site_built') == 'on'
        lead.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Lead updated successfully!', 'success')
        return redirect(url_for('leads.detail', id=id))
    
    return render_template('leads/form.html', 
        lead=lead, 
        statuses=Lead.status_choices(),
        website_qualities=Lead.website_quality_choices(),
        niches=get_existing_niches(),
        sources=get_existing_sources(),
        action='Edit'
    )

@leads_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted successfully!', 'success')
    return redirect(url_for('leads.index'))

@leads_bp.route('/<int:id>/update-status', methods=['POST'])
def update_status(id):
    lead = Lead.query.get_or_404(id)
    old_status = lead.status
    new_status = request.form.get('status')
    if new_status in Lead.status_choices():
        if new_status == 'closed_won':
            flash('Lead marked as won! Convert to client below.', 'success')
            return redirect(url_for('leads.convert_to_client', id=id))
        lead.status = new_status
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        if old_status != new_status:
            if new_status == 'contacted':
                add_xp(XP_RULES['lead_contacted'], 'Lead contacted')
                add_tokens(TOKEN_RULES['lead_contacted'], 'Lead contacted')
                update_mission_progress('contact_lead')
                ActivityLog.log_activity('lead_contacted', f'Contacted {lead.name}', lead.id, 'lead')
                flash('Status updated! +4 XP, +1 token', 'success')
            elif new_status == 'call_booked':
                add_xp(XP_RULES['lead_call_booked'], 'Call booked')
                ActivityLog.log_activity('call_booked', f'Booked call with {lead.name}', lead.id, 'lead')
                flash('Status updated! +8 XP', 'success')
            elif new_status == 'proposal_sent':
                add_xp(XP_RULES['lead_proposal_sent'], 'Proposal sent')
                add_tokens(TOKEN_RULES['proposal_sent'], 'Proposal sent')
                update_boss_progress('proposals')
                ActivityLog.log_activity('proposal_sent', f'Sent proposal to {lead.name}', lead.id, 'lead')
                flash('Status updated! +12 XP, +2 tokens', 'success')
            elif new_status == 'closed_lost':
                flash('Lead marked as lost. Please select a reason.', 'info')
                return redirect(url_for('leads.close_lost', id=id))
            else:
                flash('Status updated!', 'success')
        else:
            flash('Status updated!', 'success')
    return redirect(request.referrer or url_for('leads.index'))

@leads_bp.route('/<int:id>/convert', methods=['GET', 'POST'])
def convert_to_client(id):
    lead = Lead.query.get_or_404(id)
    
    if request.method == 'POST':
        close_reasons = request.form.getlist('close_reason')
        other_reason = request.form.get('other_reason', '').strip()
        
        if not close_reasons:
            flash('Please select at least one reason for winning this deal.', 'error')
            return render_template('leads/convert.html',
                lead=lead,
                project_types=Client.project_type_choices(),
                today=date.today().isoformat(),
                win_reasons=Lead.win_reason_choices()
            )
        
        if 'Other' in close_reasons and other_reason:
            close_reasons = [r for r in close_reasons if r != 'Other']
            close_reasons.append(f'Other: {other_reason}')
        close_reason_str = ', '.join(close_reasons) if close_reasons else None
        
        client = Client(
            name=request.form.get('name'),
            business_name=request.form.get('business_name'),
            contact_email=request.form.get('contact_email'),
            phone=request.form.get('phone'),
            project_type=request.form.get('project_type', 'website'),
            start_date=parse_date(request.form.get('start_date')) or date.today(),
            amount_charged=request.form.get('amount_charged') or 0,
            status='active',
            hosting_active=request.form.get('hosting_active') == 'on',
            monthly_hosting_fee=request.form.get('monthly_hosting_fee') or 0,
            saas_active=request.form.get('saas_active') == 'on',
            monthly_saas_fee=request.form.get('monthly_saas_fee') or 0,
            notes=request.form.get('notes'),
            related_lead_id=lead.id
        )
        
        lead.status = 'closed_won'
        lead.converted_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        lead.close_reason = close_reason_str
        lead.closed_at = datetime.utcnow()
        
        db.session.add(client)
        db.session.commit()
        
        add_xp(XP_RULES['lead_closed_won'], 'Deal closed')
        update_boss_progress('close_deals')
        
        ActivityLog.log_activity('deal_closed_won', f'Closed {lead.name} (WON): {close_reason_str}', lead.id, 'lead')
        
        flash('Lead converted to client successfully!', 'success')
        return redirect(url_for('clients.detail', id=client.id))
    
    return render_template('leads/convert.html',
        lead=lead,
        project_types=Client.project_type_choices(),
        today=date.today().isoformat(),
        win_reasons=Lead.win_reason_choices()
    )

@leads_bp.route('/<int:id>/close-lost', methods=['GET', 'POST'])
def close_lost(id):
    lead = Lead.query.get_or_404(id)
    
    if request.method == 'POST':
        close_reasons = request.form.getlist('close_reason')
        other_reason = request.form.get('other_reason', '').strip()
        
        if not close_reasons:
            flash('Please select at least one reason for losing this deal.', 'error')
            return render_template('leads/close_lost.html',
                lead=lead,
                loss_reasons=Lead.loss_reason_choices()
            )
        
        if 'Other' in close_reasons and other_reason:
            close_reasons = [r for r in close_reasons if r != 'Other']
            close_reasons.append(f'Other: {other_reason}')
        close_reason_str = ', '.join(close_reasons) if close_reasons else None
        
        lead.status = 'closed_lost'
        lead.close_reason = close_reason_str
        lead.closed_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        ActivityLog.log_activity('deal_closed_lost', f'Closed {lead.name} (LOST): {close_reason_str}', lead.id, 'lead')
        
        flash('Lead marked as lost.', 'info')
        return redirect(url_for('leads.detail', id=id))
    
    return render_template('leads/close_lost.html',
        lead=lead,
        loss_reasons=Lead.loss_reason_choices()
    )
