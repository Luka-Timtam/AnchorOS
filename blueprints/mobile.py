from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import date, datetime, timedelta
from db_supabase import (
    Lead, Client, Task, OutreachLog, Note, FreelancingIncome, 
    UserStats, UserSettings, ActivityLog, get_supabase
)
from blueprints.gamification import add_xp, add_tokens, update_mission_progress, XP_RULES, TOKEN_RULES

mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')


def is_mobile_device():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


@mobile_bp.route('/')
def index():
    today = date.today()
    today_str = today.isoformat()
    stats = UserStats.get_stats()
    settings = UserSettings.get_settings()
    
    client = get_supabase()
    
    tasks_result = client.table('tasks').select('*').eq('due_date', today_str).neq('status', 'done').order('created_at', desc=True).limit(5).execute()
    today_tasks = [Task._parse_row(row) for row in tasks_result.data]
    
    leads_result = client.table('leads').select('*').execute()
    active_leads = [row for row in leads_result.data if row.get('status') not in ['closed_won', 'closed_lost']]
    total_leads = len(active_leads)
    
    clients_result = client.table('clients').select('*').eq('status', 'active').execute()
    total_clients = len(clients_result.data)
    
    outreach_result = client.table('outreach_logs').select('*').eq('date', today_str).execute()
    today_outreach = len(outreach_result.data)
    
    pending_result = client.table('tasks').select('*').neq('status', 'done').execute()
    pending_tasks = len(pending_result.data)
    
    followups_result = client.table('leads').select('*').lte('next_action_date', today_str).order('next_action_date').execute()
    follow_ups = [Lead._parse_row(row) for row in followups_result.data if row.get('status') not in ['closed_won', 'closed_lost']][:3]
    
    first_of_month = today.replace(day=1).isoformat()
    freelance_result = client.table('freelance_jobs').select('*').gte('date_completed', first_of_month).execute()
    month_income = sum(float(row.get('amount', 0) or 0) for row in freelance_result.data)
    
    six_months_ago = (today - timedelta(days=180)).isoformat()
    freelance_6mo = client.table('freelance_jobs').select('*').gte('date_completed', six_months_ago).execute()
    total_6mo = sum(float(row.get('amount', 0) or 0) for row in freelance_6mo.data)
    avg_monthly = float(total_6mo) / 6 if total_6mo else 0
    
    clients_month = client.table('clients').select('*').gte('created_at', first_of_month).execute()
    clients_this_month = len(clients_month.data)
    
    active_clients = client.table('clients').select('*').eq('status', 'active').execute()
    mrr = sum(
        float(row.get('monthly_hosting_fee', 0) or 0) + float(row.get('monthly_saas_fee', 0) or 0)
        for row in active_clients.data
    )
    
    total_this_month = float(month_income) + float(mrr)
    
    streak = getattr(stats, 'current_outreach_streak_days', 0) if stats else 0
    
    return render_template('mobile/index.html',
        today_tasks=today_tasks,
        total_leads=total_leads,
        total_clients=total_clients,
        today_outreach=today_outreach,
        pending_tasks=pending_tasks,
        follow_ups=follow_ups,
        stats=stats,
        streak=streak,
        total_this_month=total_this_month,
        mrr=mrr,
        avg_monthly=avg_monthly,
        clients_this_month=clients_this_month
    )


@mobile_bp.route('/leads')
def leads():
    status_filter = request.args.get('status', '')
    client = get_supabase()
    
    result = client.table('leads').select('*').order('updated_at', desc=True).execute()
    
    # Filter out closed leads
    leads_list = [Lead._parse_row(row) for row in result.data if row.get('status') not in ['closed_won', 'closed_lost']]
    
    # Apply status filter if provided
    if status_filter:
        leads_list = [lead for lead in leads_list if getattr(lead, 'status', '') == status_filter]
    
    leads_list = leads_list[:50]
    
    status_choices = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('follow_up', 'Follow Up'),
        ('call_booked', 'Call Booked'),
        ('proposal_sent', 'Proposal Sent'),
        ('negotiation', 'Negotiation')
    ]
    
    return render_template('mobile/leads.html', 
        leads=leads_list,
        status_filter=status_filter,
        status_choices=status_choices
    )


@mobile_bp.route('/leads/<int:lead_id>')
def lead_detail(lead_id):
    lead = Lead.get_by_id(lead_id)
    if not lead:
        flash('Lead not found', 'error')
        return redirect(url_for('mobile.leads'))
    
    client = get_supabase()
    outreach_result = client.table('outreach_logs').select('*').eq('lead_id', lead_id).order('date', desc=True).limit(5).execute()
    recent_outreach = [OutreachLog._parse_row(row) for row in outreach_result.data]
    
    return render_template('mobile/lead_detail.html', lead=lead, recent_outreach=recent_outreach)


@mobile_bp.route('/leads/new', methods=['GET', 'POST'])
def lead_new():
    if request.method == 'POST':
        lead = Lead.insert({
            'name': request.form.get('name'),
            'business_name': request.form.get('business_name', ''),
            'niche': request.form.get('niche', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'source': request.form.get('source', ''),
            'status': 'new',
            'notes': request.form.get('notes', ''),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        ActivityLog.log_activity('lead_created', f'Created lead: {request.form.get("name")}', lead.id if lead else None, 'lead')
        flash('Lead added successfully', 'success')
        return redirect(url_for('mobile.leads'))
    
    return render_template('mobile/lead_form.html')


@mobile_bp.route('/leads/<int:lead_id>/outreach', methods=['GET', 'POST'])
def lead_outreach(lead_id):
    lead = Lead.get_by_id(lead_id)
    if not lead:
        flash('Lead not found', 'error')
        return redirect(url_for('mobile.leads'))
    
    if request.method == 'POST':
        OutreachLog.insert({
            'lead_id': lead_id,
            'type': request.form.get('type', 'email'),
            'outcome': request.form.get('outcome', 'contacted'),
            'notes': request.form.get('notes', ''),
            'date': date.today().isoformat()
        })
        
        update_data = {
            'last_contacted_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if request.form.get('outcome') == 'booked_call':
            update_data['status'] = 'call_booked'
        elif request.form.get('outcome') == 'follow_up_set':
            update_data['status'] = 'follow_up'
        
        Lead.update_by_id(lead_id, update_data)
        
        add_xp(XP_RULES.get('outreach_log', 5), 'Outreach logged')
        add_tokens(TOKEN_RULES.get('outreach_log', 1), 'Outreach logged')
        update_mission_progress('outreach')
        
        flash('Outreach logged', 'success')
        return redirect(url_for('mobile.lead_detail', lead_id=lead_id))
    
    type_choices = [('email', 'Email'), ('dm', 'DM'), ('call', 'Call'), ('in_person', 'In Person')]
    outcome_choices = [('contacted', 'Contacted'), ('no_response', 'No Response'), ('booked_call', 'Booked Call'), ('follow_up_set', 'Follow Up Set')]
    
    return render_template('mobile/outreach_form.html', 
        lead=lead,
        type_choices=type_choices,
        outcome_choices=outcome_choices
    )


@mobile_bp.route('/clients')
def clients():
    client = get_supabase()
    result = client.table('clients').select('*').eq('status', 'active').order('updated_at', desc=True).limit(50).execute()
    clients_list = [Client._parse_row(row) for row in result.data]
    return render_template('mobile/clients.html', clients=clients_list)


@mobile_bp.route('/clients/<int:client_id>')
def client_detail(client_id):
    client_obj = Client.get_by_id(client_id)
    if not client_obj:
        flash('Client not found', 'error')
        return redirect(url_for('mobile.clients'))
    return render_template('mobile/client_detail.html', client=client_obj)


@mobile_bp.route('/clients/new', methods=['GET', 'POST'])
def client_new():
    if request.method == 'POST':
        client_obj = Client.insert({
            'name': request.form.get('name'),
            'business_name': request.form.get('business_name', ''),
            'contact_email': request.form.get('contact_email', ''),
            'phone': request.form.get('phone', ''),
            'project_type': request.form.get('project_type', 'website'),
            'status': 'active',
            'notes': request.form.get('notes', ''),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        ActivityLog.log_activity('client_created', f'Created client: {request.form.get("name")}', client_obj.id if client_obj else None, 'client')
        flash('Client added successfully', 'success')
        return redirect(url_for('mobile.clients'))
    
    project_types = [('website', 'Website'), ('webapp', 'Web App'), ('mobile', 'Mobile App'), ('other', 'Other')]
    return render_template('mobile/client_form.html', project_types=project_types)


@mobile_bp.route('/tasks')
def tasks():
    today = date.today()
    today_str = today.isoformat()
    filter_type = request.args.get('filter', 'today')
    client = get_supabase()
    
    if filter_type == 'today':
        result = client.table('tasks').select('*').eq('due_date', today_str).neq('status', 'done').order('created_at', desc=True).execute()
    elif filter_type == 'overdue':
        result = client.table('tasks').select('*').lt('due_date', today_str).neq('status', 'done').order('due_date').execute()
    else:
        result = client.table('tasks').select('*').neq('status', 'done').order('due_date').limit(50).execute()
    
    task_list = [Task._parse_row(row) for row in result.data]
    
    return render_template('mobile/tasks.html', tasks=task_list, filter_type=filter_type, today=today)


@mobile_bp.route('/tasks/new', methods=['GET', 'POST'])
def task_new():
    if request.method == 'POST':
        due_date = request.form.get('due_date')
        if due_date:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date().isoformat()
        else:
            due_date = date.today().isoformat()
        
        task = Task.insert({
            'title': request.form.get('title'),
            'description': request.form.get('description', ''),
            'due_date': due_date,
            'status': 'open',
            'created_at': datetime.utcnow().isoformat()
        })
        ActivityLog.log_activity('task_created', f'Created task: {request.form.get("title")}', task.id if task else None, 'task')
        flash('Task added', 'success')
        return redirect(url_for('mobile.tasks'))
    
    return render_template('mobile/task_form.html')


@mobile_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
def task_complete(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        flash('Task not found', 'error')
        return redirect(url_for('mobile.tasks'))
    
    old_status = getattr(task, 'status', '')
    Task.update_by_id(task_id, {'status': 'done'})
    
    if old_status != 'done':
        add_xp(XP_RULES.get('task_done', 8), 'Task completed')
        add_tokens(TOKEN_RULES.get('task_done', 1), 'Task completed')
        update_mission_progress('complete_tasks')
        ActivityLog.log_activity('task_completed', f'Completed task: {getattr(task, "title", "")}', task_id, 'task')
        flash('Task completed! +8 XP, +1 token', 'success')
    else:
        flash('Task already completed', 'success')
    
    return redirect(request.referrer or url_for('mobile.tasks'))


@mobile_bp.route('/calendar')
def calendar():
    today = date.today()
    today_str = today.isoformat()
    client = get_supabase()
    
    tasks_result = client.table('tasks').select('*').gte('due_date', today_str).neq('status', 'done').order('due_date').limit(10).execute()
    upcoming_tasks = [Task._parse_row(row) for row in tasks_result.data]
    
    leads_result = client.table('leads').select('*').gte('next_action_date', today_str).order('next_action_date').execute()
    follow_ups = [Lead._parse_row(row) for row in leads_result.data if row.get('status') not in ['closed_won', 'closed_lost']][:10]
    
    return render_template('mobile/calendar.html',
        today=today,
        upcoming_tasks=upcoming_tasks,
        follow_ups=follow_ups
    )


@mobile_bp.route('/notes')
def notes():
    client = get_supabase()
    result = client.table('notes').select('*').order('updated_at', desc=True).limit(30).execute()
    notes_list = [Note._parse_row(row) for row in result.data]
    return render_template('mobile/notes.html', notes=notes_list)


@mobile_bp.route('/notes/new', methods=['GET', 'POST'])
def note_new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('Note content is required', 'error')
            return render_template('mobile/note_form.html', title=title, content=content)
        
        note = Note.insert({
            'title': title if title else 'Quick Note',
            'content': content,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        ActivityLog.log_activity('note_created', f'Created note: {title if title else "Quick Note"}', note.id if note else None, 'note')
        flash('Note saved', 'success')
        
        return redirect(url_for('mobile.notes'))
    
    return render_template('mobile/note_form.html')


@mobile_bp.route('/notes/<int:note_id>')
def note_detail(note_id):
    note = Note.get_by_id(note_id)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('mobile.notes'))
    return render_template('mobile/note_detail.html', note=note)


@mobile_bp.route('/notes/<int:note_id>/edit', methods=['GET', 'POST'])
def note_edit(note_id):
    note = Note.get_by_id(note_id)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('mobile.notes'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('Note content is required', 'error')
            return render_template('mobile/note_edit_form.html', note=note, title=title, content=content)
        
        Note.update_by_id(note_id, {
            'title': title if title else 'Quick Note',
            'content': content,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        ActivityLog.log_activity('note_updated', f'Updated note: {title if title else "Quick Note"}', note_id, 'note')
        flash('Note updated', 'success')
        return redirect(url_for('mobile.note_detail', note_id=note_id))
    
    return render_template('mobile/note_edit_form.html', note=note)


@mobile_bp.route('/notes/<int:note_id>/delete', methods=['POST'])
def note_delete(note_id):
    note = Note.get_by_id(note_id)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('mobile.notes'))
    
    title = getattr(note, 'title', 'Note')
    Note.delete_by_id(note_id)
    
    ActivityLog.log_activity('note_deleted', f'Deleted note: {title}', note_id, 'note')
    flash('Note deleted', 'success')
    return redirect(url_for('mobile.notes'))


@mobile_bp.route('/freelancing')
def freelancing():
    today = date.today()
    current_month_start = today.replace(day=1).isoformat()
    client = get_supabase()
    
    result = client.table('freelance_jobs').select('*').gte('date_completed', current_month_start).order('date_completed', desc=True).execute()
    entries = [FreelancingIncome._parse_row(row) for row in result.data]
    
    month_total = sum(float(getattr(e, 'amount', 0) or 0) for e in entries)
    
    all_result = client.table('freelance_jobs').select('*').execute()
    all_time_total = sum(float(row.get('amount', 0) or 0) for row in all_result.data)
    
    return render_template('mobile/freelancing.html',
        entries=entries,
        month_total=month_total,
        all_time_total=float(all_time_total)
    )


@mobile_bp.route('/freelancing/new', methods=['GET', 'POST'])
def freelancing_new():
    if request.method == 'POST':
        date_completed = request.form.get('date')
        if date_completed:
            date_completed = datetime.strptime(date_completed, '%Y-%m-%d').date().isoformat()
        else:
            date_completed = date.today().isoformat()
        
        entry = FreelancingIncome.insert({
            'title': request.form.get('title', 'Freelance Work'),
            'description': request.form.get('description', ''),
            'amount': float(request.form.get('amount', 0)),
            'client_name': request.form.get('client_name', ''),
            'category': request.form.get('category', 'other'),
            'date_completed': date_completed
        })
        ActivityLog.log_activity('income_logged', f'Logged income: {request.form.get("title")} - ${request.form.get("amount")}', entry.id if entry else None, 'freelance')
        flash('Income logged', 'success')
        return redirect(url_for('mobile.freelancing'))
    
    categories = [('photography', 'Photography'), ('consulting', 'Consulting'), ('side_project', 'Side Project'), ('cash_work', 'Cash Work'), ('other', 'Other')]
    return render_template('mobile/freelancing_form.html', categories=categories)


@mobile_bp.route('/outreach/quick', methods=['GET', 'POST'])
def quick_outreach():
    client = get_supabase()
    
    if request.method == 'POST':
        lead_id = request.form.get('lead_id')
        
        OutreachLog.insert({
            'lead_id': int(lead_id) if lead_id else None,
            'type': request.form.get('type', 'email'),
            'outcome': request.form.get('outcome', 'contacted'),
            'notes': request.form.get('notes', ''),
            'date': date.today().isoformat()
        })
        
        if lead_id:
            Lead.update_by_id(int(lead_id), {
                'last_contacted_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        add_xp(XP_RULES.get('outreach_log', 5), 'Outreach logged')
        add_tokens(TOKEN_RULES.get('outreach_log', 1), 'Outreach logged')
        update_mission_progress('outreach')
        
        flash('Outreach logged', 'success')
        return redirect(url_for('mobile.index'))
    
    result = client.table('leads').select('*').order('updated_at', desc=True).execute()
    leads_list = [Lead._parse_row(row) for row in result.data if row.get('status') not in ['closed_won', 'closed_lost']][:20]
    
    type_choices = [('email', 'Email'), ('dm', 'DM'), ('call', 'Call'), ('in_person', 'In Person')]
    outcome_choices = [('contacted', 'Contacted'), ('no_response', 'No Response'), ('booked_call', 'Booked Call'), ('follow_up_set', 'Follow Up Set')]
    
    return render_template('mobile/quick_outreach.html',
        leads=leads_list,
        type_choices=type_choices,
        outcome_choices=outcome_choices
    )
