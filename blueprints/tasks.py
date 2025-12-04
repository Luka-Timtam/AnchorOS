from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Task, Lead, Client
from datetime import datetime, date
from blueprints.gamification import add_xp, XP_RULES

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
    
    query = Task.query.filter(Task.status != 'done')
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if due_filter == 'overdue':
        query = query.filter(Task.due_date < today, Task.status != 'done')
    elif due_filter == 'today':
        query = query.filter(Task.due_date == today)
    elif due_filter == 'upcoming':
        query = query.filter(Task.due_date > today)
    
    tasks = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    
    completed_tasks = Task.query.filter(Task.status == 'done').order_by(Task.created_at.desc()).all()
    
    overdue_tasks = Task.query.filter(
        Task.due_date < today,
        Task.status != 'done'
    ).order_by(Task.due_date.asc()).all()
    
    today_tasks = Task.query.filter(
        Task.due_date == today
    ).order_by(Task.created_at.desc()).all()
    
    leads = Lead.query.order_by(Lead.name).all()
    clients = Client.query.order_by(Client.name).all()
    
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
    task = Task(
        title=request.form.get('title'),
        description=request.form.get('description'),
        due_date=parse_date(request.form.get('due_date')),
        status=request.form.get('status', 'open'),
        related_lead_id=request.form.get('related_lead_id') or None,
        related_client_id=request.form.get('related_client_id') or None
    )
    db.session.add(task)
    db.session.commit()
    flash('Task created successfully!', 'success')
    return redirect(url_for('tasks.index'))

@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    task = Task.query.get_or_404(id)
    
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.due_date = parse_date(request.form.get('due_date'))
        task.status = request.form.get('status')
        task.related_lead_id = request.form.get('related_lead_id') or None
        task.related_client_id = request.form.get('related_client_id') or None
        
        db.session.commit()
        flash('Task updated!', 'success')
        return redirect(url_for('tasks.index'))
    
    leads = Lead.query.order_by(Lead.name).all()
    clients = Client.query.order_by(Client.name).all()
    
    return render_template('tasks/edit.html',
        task=task,
        leads=leads,
        clients=clients,
        statuses=Task.status_choices()
    )

@tasks_bp.route('/<int:id>/update-status', methods=['POST'])
def update_status(id):
    task = Task.query.get_or_404(id)
    old_status = task.status
    new_status = request.form.get('status')
    if new_status in Task.status_choices():
        task.status = new_status
        db.session.commit()
        
        if new_status == 'done' and old_status != 'done':
            add_xp(XP_RULES['task_done'], 'Task completed')
        
        flash('Task status updated!', 'success')
    return redirect(request.referrer or url_for('tasks.index'))

@tasks_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted!', 'success')
    return redirect(url_for('tasks.index'))
