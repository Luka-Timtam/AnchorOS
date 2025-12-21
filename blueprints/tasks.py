from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from db_supabase import Task, Lead, Client, ActivityLog, get_supabase
from datetime import datetime, date
from blueprints.gamification import add_xp, XP_RULES, TOKEN_RULES, add_tokens, update_mission_progress

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

def parse_date(date_str):
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

@tasks_bp.route('/')
def index():
    today = date.today()
    
    status_filter = request.args.get('status', '')
    due_filter = request.args.get('due', '')
    
    client = get_supabase()
    
    query = client.table('tasks').select('*').neq('status', 'done')
    
    if status_filter:
        query = query.eq('status', status_filter)
    
    if due_filter == 'overdue':
        query = query.lt('due_date', today.isoformat()).neq('status', 'done')
    elif due_filter == 'today':
        query = query.eq('due_date', today.isoformat())
    elif due_filter == 'upcoming':
        query = query.gt('due_date', today.isoformat())
    
    result = query.order('due_date', desc=False, nullsfirst=False).order('created_at', desc=True).execute()
    tasks = [Task._parse_row(row) for row in result.data]
    
    completed_result = client.table('tasks').select('*').eq('status', 'done').order('created_at', desc=True).execute()
    completed_tasks = [Task._parse_row(row) for row in completed_result.data]
    
    overdue_result = client.table('tasks').select('*').lt('due_date', today.isoformat()).neq('status', 'done').order('due_date', desc=False).execute()
    overdue_tasks = [Task._parse_row(row) for row in overdue_result.data]
    
    today_result = client.table('tasks').select('*').eq('due_date', today.isoformat()).order('created_at', desc=True).execute()
    today_tasks = [Task._parse_row(row) for row in today_result.data]
    
    leads = Lead.query_all(order_by='name')
    clients = Client.query_all(order_by='name')
    
    return render_template('tasks/index.html',
        tasks=tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        today_tasks=today_tasks,
        leads=leads,
        clients=clients,
        statuses=Task.status_choices(),
        current_status=status_filter,
        current_due=due_filter,
        today=today
    )

@tasks_bp.route('/create', methods=['POST'])
def create():
    due_date = parse_date(request.form.get('due_date'))
    
    task = Task.insert({
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'due_date': due_date.isoformat() if due_date else None,
        'status': request.form.get('status', 'open'),
        'related_lead_id': int(request.form.get('related_lead_id')) if request.form.get('related_lead_id') else None,
        'related_client_id': int(request.form.get('related_client_id')) if request.form.get('related_client_id') else None
    })
    
    ActivityLog.log_activity('task_created', f'Created task: {task.title}', task.id, 'task')
    
    flash('Task created successfully!', 'success')
    return redirect(url_for('tasks.index'))

@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    task = Task.get_by_id(id)
    if not task:
        abort(404)
    
    if request.method == 'POST':
        due_date = parse_date(request.form.get('due_date'))
        
        Task.update_by_id(id, {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'due_date': due_date.isoformat() if due_date else None,
            'status': request.form.get('status'),
            'related_lead_id': int(request.form.get('related_lead_id')) if request.form.get('related_lead_id') else None,
            'related_client_id': int(request.form.get('related_client_id')) if request.form.get('related_client_id') else None
        })
        flash('Task updated!', 'success')
        return redirect(url_for('tasks.index'))
    
    leads = Lead.query_all(order_by='name')
    clients = Client.query_all(order_by='name')
    
    return render_template('tasks/edit.html',
        task=task,
        leads=leads,
        clients=clients,
        statuses=Task.status_choices()
    )

@tasks_bp.route('/<int:id>/update-status', methods=['POST'])
def update_status(id):
    task = Task.get_by_id(id)
    if not task:
        abort(404)
    old_status = getattr(task, 'status', '')
    new_status = request.form.get('status')
    if new_status in Task.status_choices():
        Task.update_by_id(id, {'status': new_status})
        
        if new_status == 'done' and old_status != 'done':
            add_xp(XP_RULES['task_done'], 'Task completed')
            add_tokens(TOKEN_RULES['task_done'], 'Task completed')
            update_mission_progress('complete_tasks')
            ActivityLog.log_activity('task_completed', f'Completed task: {task.title}', task.id, 'task')
            message = 'Task completed! +8 XP, +1 token'
        else:
            message = 'Task status updated!'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': message})
    
    return redirect(request.referrer or url_for('tasks.index'))

@tasks_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    task = Task.get_by_id(id)
    if not task:
        abort(404)
    Task.delete_by_id(id)
    flash('Task deleted!', 'success')
    return redirect(url_for('tasks.index'))
