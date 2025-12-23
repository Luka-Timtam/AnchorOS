from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import Lead, OutreachLog, Client, ActivityLog, WinsLog, get_supabase
from datetime import datetime, date
from blueprints.gamification import add_xp, XP_RULES, TOKEN_RULES, add_tokens, update_mission_progress
from blueprints.boss import update_boss_progress
import timezone as tz

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
    
    client = get_supabase()
    query = client.table('leads').select('*').is_('converted_at', 'null').is_('archived_at', 'null')
    
    if status_filter:
        query = query.eq('status', status_filter)
    if niche_filter:
        query = query.eq('niche', niche_filter)
    if source_filter:
        query = query.eq('source', source_filter)
    if search:
        query = query.or_(f'name.ilike.%{search}%,business_name.ilike.%{search}%')
    if next_action_filter == 'today':
        query = query.eq('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")')
    elif next_action_filter == 'overdue':
        query = query.lt('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")')
    
    result = query.order('created_at', desc=True).execute()
    leads = [Lead._parse_row(row) for row in result.data]
    
    converted_result = client.table('leads').select('*').filter('converted_at', 'not.is', 'null').order('converted_at', desc=True).execute()
    converted_leads = [Lead._parse_row(row) for row in converted_result.data]
    
    archived_result = client.table('leads').select('*').filter('archived_at', 'not.is', 'null').order('archived_at', desc=True).execute()
    archived_leads = [Lead._parse_row(row) for row in archived_result.data]
    
    all_leads = client.table('leads').select('niche,source').execute()
    niches = list(set([l['niche'] for l in all_leads.data if l.get('niche')]))
    sources = list(set([l['source'] for l in all_leads.data if l.get('source')]))
    
    return render_template('leads/index.html',
        leads=leads,
        converted_leads=converted_leads,
        archived_leads=archived_leads,
        statuses=Lead.status_choices(),
        niches=niches,
        sources=sources,
        current_status=status_filter,
        current_niche=niche_filter,
        current_source=source_filter,
        current_search=search,
        current_next_action=next_action_filter
    )

def get_existing_niches():
    client = get_supabase()
    result = client.table('leads').select('niche').filter('niche', 'not.is', 'null').neq('niche', '').execute()
    return list(set([r['niche'] for r in result.data if r.get('niche')]))

def get_existing_sources():
    client = get_supabase()
    result = client.table('leads').select('source').filter('source', 'not.is', 'null').neq('source', '').execute()
    return list(set([r['source'] for r in result.data if r.get('source')]))

@leads_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        has_website = request.form.get('has_website') == 'yes'
        quality_issues = request.form.getlist('website_quality') if has_website else []
        website_quality = ','.join(quality_issues) if quality_issues else ('no_website' if not has_website else '')
        
        next_action = parse_date(request.form.get('next_action_date'))
        
        # Truncate fields to database limits to prevent VARCHAR overflow errors
        lead = Lead.insert({
            'name': (request.form.get('name') or '')[:100],
            'business_name': (request.form.get('business_name') or '')[:100],
            'niche': (request.form.get('niche') or '')[:50],
            'email': (request.form.get('email') or '')[:100],
            'phone': (request.form.get('phone') or '')[:20],
            'source': (request.form.get('source') or '')[:50],
            'status': request.form.get('status', 'new')[:50],
            'notes': request.form.get('notes'),
            'next_action_date': next_action.isoformat() if next_action else None,
            'has_website': has_website,
            'website_quality': website_quality,
            'demo_site_built': request.form.get('demo_site_built') == 'on'
        })
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
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    outreach_logs = OutreachLog.query_filter({'lead_id': id}, order_by='date', order_desc=True)
    return render_template('leads/detail.html', lead=lead, outreach_logs=outreach_logs)

@leads_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    
    if request.method == 'POST':
        has_website = request.form.get('has_website') == 'yes'
        quality_issues = request.form.getlist('website_quality') if has_website else []
        website_quality = ','.join(quality_issues) if quality_issues else ('no_website' if not has_website else '')
        
        next_action = parse_date(request.form.get('next_action_date'))
        
        Lead.update_by_id(id, {
            'name': (request.form.get('name') or '')[:100],
            'business_name': (request.form.get('business_name') or '')[:100],
            'niche': (request.form.get('niche') or '')[:50],
            'email': (request.form.get('email') or '')[:100],
            'phone': (request.form.get('phone') or '')[:20],
            'source': (request.form.get('source') or '')[:50],
            'status': (request.form.get('status') or '')[:50],
            'notes': request.form.get('notes'),
            'next_action_date': next_action.isoformat() if next_action else None,
            'has_website': has_website,
            'website_quality': website_quality,
            'demo_site_built': request.form.get('demo_site_built') == 'on',
            'updated_at': tz.now_iso()
        })
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

@leads_bp.route('/<int:id>/archive', methods=['POST'])
def archive(id):
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    Lead.update_by_id(id, {'archived_at': tz.now_iso()})
    flash('Lead archived successfully!', 'success')
    return redirect(url_for('leads.index'))

@leads_bp.route('/<int:id>/unarchive', methods=['POST'])
def unarchive(id):
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    Lead.update_by_id(id, {'archived_at': None})
    flash('Lead restored from archive!', 'success')
    return redirect(url_for('leads.index'))

@leads_bp.route('/<int:id>/update-status', methods=['POST'])
def update_status(id):
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    old_status = getattr(lead, 'status', '')
    new_status = request.form.get('status')
    if new_status in Lead.status_choices():
        if new_status == 'closed_won':
            flash('Lead marked as won! Convert to client below.', 'success')
            return redirect(url_for('leads.convert_to_client', id=id))
        
        Lead.update_by_id(id, {
            'status': new_status,
            'updated_at': tz.now_iso()
        })
        
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
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    
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
        
        start_date = parse_date(request.form.get('start_date')) or date.today()
        
        client = Client.insert({
            'name': request.form.get('name'),
            'business_name': request.form.get('business_name'),
            'contact_email': request.form.get('contact_email'),
            'phone': request.form.get('phone'),
            'project_type': request.form.get('project_type', 'website'),
            'start_date': start_date.isoformat(),
            'amount_charged': float(request.form.get('amount_charged') or 0),
            'status': 'active',
            'hosting_active': request.form.get('hosting_active') == 'on',
            'monthly_hosting_fee': float(request.form.get('monthly_hosting_fee') or 0),
            'saas_active': request.form.get('saas_active') == 'on',
            'monthly_saas_fee': float(request.form.get('monthly_saas_fee') or 0),
            'notes': request.form.get('notes'),
            'related_lead_id': lead.id
        })
        
        now = tz.now_iso()
        Lead.update_by_id(id, {
            'status': 'closed_won',
            'converted_at': now,
            'updated_at': now,
            'close_reason': close_reason_str,
            'closed_at': now
        })
        
        add_xp(XP_RULES['lead_closed_won'], 'Deal closed')
        update_boss_progress('close_deals')
        
        ActivityLog.log_activity('deal_closed_won', f'Closed {lead.name} (WON): {close_reason_str}', lead.id, 'lead')
        
        WinsLog.insert({
            'title': f'Deal Won: {lead.name}',
            'description': f'Closed deal with {getattr(lead, "business_name", "") or lead.name}. Reason: {close_reason_str}',
            'xp_value': XP_RULES['lead_closed_won'],
            'token_value': 0
        })
        
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
    lead = Lead.get_by_id(id)
    if not lead:
        abort(404)
    
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
        
        now = tz.now_iso()
        Lead.update_by_id(id, {
            'status': 'closed_lost',
            'close_reason': close_reason_str,
            'closed_at': now,
            'updated_at': now
        })
        
        ActivityLog.log_activity('deal_closed_lost', f'Closed {lead.name} (LOST): {close_reason_str}', lead.id, 'lead')
        
        flash('Lead marked as lost.', 'info')
        return redirect(url_for('leads.detail', id=id))
    
    return render_template('leads/close_lost.html',
        lead=lead,
        loss_reasons=Lead.loss_reason_choices()
    )
