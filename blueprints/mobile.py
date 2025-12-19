from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import date, datetime, timedelta
from models import db, Lead, Client, Task, OutreachLog, Note, FreelanceJob, UserStats, UserSettings

mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')


def is_mobile_device():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


@mobile_bp.route('/')
def index():
    today = date.today()
    stats = UserStats.get_stats()
    settings = UserSettings.get_settings()
    
    today_tasks = Task.query.filter(
        Task.due_date == today,
        Task.status != 'done'
    ).order_by(Task.created_at.desc()).limit(5).all()
    
    total_leads = Lead.query.filter(Lead.status.notin_(['closed_won', 'closed_lost'])).count()
    total_clients = Client.query.filter(Client.status == 'active').count()
    
    today_outreach = OutreachLog.query.filter(OutreachLog.date == today).count()
    
    pending_tasks = Task.query.filter(Task.status != 'done').count()
    
    follow_ups = Lead.query.filter(
        Lead.next_action_date <= today,
        Lead.status.notin_(['closed_won', 'closed_lost'])
    ).order_by(Lead.next_action_date).limit(3).all()
    
    return render_template('mobile/index.html',
        today_tasks=today_tasks,
        total_leads=total_leads,
        total_clients=total_clients,
        today_outreach=today_outreach,
        pending_tasks=pending_tasks,
        follow_ups=follow_ups,
        stats=stats,
        streak=stats.current_outreach_streak_days
    )


@mobile_bp.route('/leads')
def leads():
    status_filter = request.args.get('status', '')
    query = Lead.query.filter(Lead.status.notin_(['closed_won', 'closed_lost']))
    
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    
    leads = query.order_by(Lead.updated_at.desc()).limit(50).all()
    
    return render_template('mobile/leads.html', 
        leads=leads,
        status_filter=status_filter,
        status_choices=Lead.status_choices()
    )


@mobile_bp.route('/leads/<int:lead_id>')
def lead_detail(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    recent_outreach = OutreachLog.query.filter_by(lead_id=lead_id).order_by(OutreachLog.date.desc()).limit(5).all()
    return render_template('mobile/lead_detail.html', lead=lead, recent_outreach=recent_outreach)


@mobile_bp.route('/leads/new', methods=['GET', 'POST'])
def lead_new():
    if request.method == 'POST':
        lead = Lead(
            name=request.form.get('name'),
            business_name=request.form.get('business_name', ''),
            niche=request.form.get('niche', ''),
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            source=request.form.get('source', ''),
            status='new',
            notes=request.form.get('notes', '')
        )
        db.session.add(lead)
        db.session.commit()
        flash('Lead added successfully', 'success')
        return redirect(url_for('mobile.leads'))
    
    return render_template('mobile/lead_form.html')


@mobile_bp.route('/leads/<int:lead_id>/outreach', methods=['GET', 'POST'])
def lead_outreach(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    
    if request.method == 'POST':
        outreach = OutreachLog(
            lead_id=lead_id,
            type=request.form.get('type', 'email'),
            outcome=request.form.get('outcome', 'contacted'),
            notes=request.form.get('notes', ''),
            date=date.today()
        )
        lead.last_contacted_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        if request.form.get('outcome') == 'booked_call':
            lead.status = 'call_booked'
        elif request.form.get('outcome') == 'follow_up_set':
            lead.status = 'follow_up'
        
        db.session.add(outreach)
        db.session.commit()
        
        from blueprints.gamification import award_outreach_xp
        award_outreach_xp()
        
        flash('Outreach logged', 'success')
        return redirect(url_for('mobile.lead_detail', lead_id=lead_id))
    
    return render_template('mobile/outreach_form.html', 
        lead=lead,
        type_choices=OutreachLog.type_choices(),
        outcome_choices=OutreachLog.outcome_choices()
    )


@mobile_bp.route('/clients')
def clients():
    clients = Client.query.filter(Client.status == 'active').order_by(Client.updated_at.desc()).limit(50).all()
    return render_template('mobile/clients.html', clients=clients)


@mobile_bp.route('/clients/<int:client_id>')
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    return render_template('mobile/client_detail.html', client=client)


@mobile_bp.route('/clients/new', methods=['GET', 'POST'])
def client_new():
    if request.method == 'POST':
        client = Client(
            name=request.form.get('name'),
            business_name=request.form.get('business_name', ''),
            contact_email=request.form.get('contact_email', ''),
            phone=request.form.get('phone', ''),
            project_type=request.form.get('project_type', 'website'),
            status='active',
            notes=request.form.get('notes', '')
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully', 'success')
        return redirect(url_for('mobile.clients'))
    
    return render_template('mobile/client_form.html', project_types=Client.project_type_choices())


@mobile_bp.route('/tasks')
def tasks():
    today = date.today()
    filter_type = request.args.get('filter', 'today')
    
    if filter_type == 'today':
        task_list = Task.query.filter(Task.due_date == today, Task.status != 'done').order_by(Task.created_at.desc()).all()
    elif filter_type == 'overdue':
        task_list = Task.query.filter(Task.due_date < today, Task.status != 'done').order_by(Task.due_date).all()
    else:
        task_list = Task.query.filter(Task.status != 'done').order_by(Task.due_date).limit(50).all()
    
    return render_template('mobile/tasks.html', tasks=task_list, filter_type=filter_type, today=today)


@mobile_bp.route('/tasks/new', methods=['GET', 'POST'])
def task_new():
    if request.method == 'POST':
        task = Task(
            title=request.form.get('title'),
            description=request.form.get('description', ''),
            due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else date.today(),
            status='open'
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added', 'success')
        return redirect(url_for('mobile.tasks'))
    
    return render_template('mobile/task_form.html')


@mobile_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
def task_complete(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = 'done'
    db.session.commit()
    flash('Task completed', 'success')
    return redirect(request.referrer or url_for('mobile.tasks'))


@mobile_bp.route('/calendar')
def calendar():
    today = date.today()
    
    upcoming_tasks = Task.query.filter(
        Task.due_date >= today,
        Task.status != 'done'
    ).order_by(Task.due_date).limit(10).all()
    
    follow_ups = Lead.query.filter(
        Lead.next_action_date >= today,
        Lead.status.notin_(['closed_won', 'closed_lost'])
    ).order_by(Lead.next_action_date).limit(10).all()
    
    return render_template('mobile/calendar.html',
        today=today,
        upcoming_tasks=upcoming_tasks,
        follow_ups=follow_ups
    )


@mobile_bp.route('/notes')
def notes():
    notes = Note.query.order_by(Note.updated_at.desc()).limit(30).all()
    return render_template('mobile/notes.html', notes=notes)


@mobile_bp.route('/notes/new', methods=['GET', 'POST'])
def note_new():
    if request.method == 'POST':
        note = Note(
            title=request.form.get('title', 'Quick Note'),
            content=request.form.get('content', ''),
            note_type='general'
        )
        db.session.add(note)
        db.session.commit()
        flash('Note saved', 'success')
        return redirect(url_for('mobile.notes'))
    
    return render_template('mobile/note_form.html')


@mobile_bp.route('/notes/<int:note_id>')
def note_detail(note_id):
    note = Note.query.get_or_404(note_id)
    return render_template('mobile/note_detail.html', note=note)


@mobile_bp.route('/freelancing')
def freelancing():
    today = date.today()
    current_month_start = today.replace(day=1)
    
    entries = FreelanceJob.query.filter(
        FreelanceJob.date_completed >= current_month_start
    ).order_by(FreelanceJob.date_completed.desc()).all()
    
    month_total = sum(float(e.amount) for e in entries)
    
    all_time_total = db.session.query(db.func.sum(FreelanceJob.amount)).scalar() or 0
    
    return render_template('mobile/freelancing.html',
        entries=entries,
        month_total=month_total,
        all_time_total=float(all_time_total)
    )


@mobile_bp.route('/freelancing/new', methods=['GET', 'POST'])
def freelancing_new():
    if request.method == 'POST':
        entry = FreelanceJob(
            title=request.form.get('title', 'Freelance Work'),
            description=request.form.get('description', ''),
            amount=float(request.form.get('amount', 0)),
            client_name=request.form.get('client_name', ''),
            category=request.form.get('category', 'other'),
            date_completed=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date() if request.form.get('date') else date.today()
        )
        db.session.add(entry)
        db.session.commit()
        flash('Income logged', 'success')
        return redirect(url_for('mobile.freelancing'))
    
    return render_template('mobile/freelancing_form.html', categories=FreelanceJob.category_choices())


@mobile_bp.route('/outreach/quick', methods=['GET', 'POST'])
def quick_outreach():
    if request.method == 'POST':
        lead_id = request.form.get('lead_id')
        outreach = OutreachLog(
            lead_id=int(lead_id) if lead_id else None,
            type=request.form.get('type', 'email'),
            outcome=request.form.get('outcome', 'contacted'),
            notes=request.form.get('notes', ''),
            date=date.today()
        )
        
        if lead_id:
            lead = Lead.query.get(int(lead_id))
            if lead:
                lead.last_contacted_at = datetime.utcnow()
                lead.updated_at = datetime.utcnow()
        
        db.session.add(outreach)
        db.session.commit()
        
        from blueprints.gamification import award_outreach_xp
        award_outreach_xp()
        
        flash('Outreach logged', 'success')
        return redirect(url_for('mobile.index'))
    
    leads = Lead.query.filter(
        Lead.status.notin_(['closed_won', 'closed_lost'])
    ).order_by(Lead.updated_at.desc()).limit(20).all()
    
    return render_template('mobile/quick_outreach.html',
        leads=leads,
        type_choices=OutreachLog.type_choices(),
        outcome_choices=OutreachLog.outcome_choices()
    )
