from flask import Blueprint, render_template, request, jsonify
from models import db, Lead, Task, DailyMission, BossFight
from datetime import datetime, date, timedelta
from calendar import monthrange
from sqlalchemy import and_, or_

calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')

def get_month_data(year, month):
    first_day = date(year, month, 1)
    _, days_in_month = monthrange(year, month)
    last_day = date(year, month, days_in_month)
    
    start_weekday = first_day.weekday()
    
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    _, prev_days_in_month = monthrange(prev_year, prev_month)
    
    grid_start = first_day - timedelta(days=start_weekday)
    grid_end = grid_start + timedelta(days=41)
    
    tasks = Task.query.filter(
        Task.due_date >= grid_start,
        Task.due_date <= grid_end
    ).all()
    
    leads = Lead.query.filter(
        Lead.next_action_date >= grid_start,
        Lead.next_action_date <= grid_end,
        Lead.status.notin_(['closed_won', 'closed_lost']),
        Lead.converted_at.is_(None)
    ).all()
    
    missions = DailyMission.query.filter(
        DailyMission.mission_date >= grid_start,
        DailyMission.mission_date <= grid_end
    ).all()
    
    current_boss = BossFight.query.filter(
        BossFight.month == f"{year}-{month:02d}"
    ).first()
    
    task_dates = {}
    for task in tasks:
        d = task.due_date.isoformat()
        if d not in task_dates:
            task_dates[d] = []
        task_dates[d].append({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'type': 'task'
        })
    
    lead_dates = {}
    for lead in leads:
        d = lead.next_action_date.isoformat()
        if d not in lead_dates:
            lead_dates[d] = []
        lead_dates[d].append({
            'id': lead.id,
            'name': lead.name,
            'status': lead.status,
            'type': 'lead'
        })
    
    mission_dates = {}
    for mission in missions:
        d = mission.mission_date.isoformat()
        mission_dates[d] = {
            'id': mission.id,
            'description': mission.description,
            'is_completed': mission.is_completed,
            'type': 'mission'
        }
    
    calendar_days = []
    today = date.today()
    
    for i in range(start_weekday):
        day_num = prev_days_in_month - start_weekday + 1 + i
        cell_date = date(prev_year, prev_month, day_num)
        date_str = cell_date.isoformat()
        calendar_days.append({
            'day': day_num,
            'current_month': False,
            'date': date_str,
            'is_today': cell_date == today,
            'tasks': task_dates.get(date_str, []),
            'leads': lead_dates.get(date_str, []),
            'mission': mission_dates.get(date_str)
        })
    
    for day in range(1, days_in_month + 1):
        current_date = date(year, month, day)
        date_str = current_date.isoformat()
        calendar_days.append({
            'day': day,
            'current_month': True,
            'date': date_str,
            'is_today': current_date == today,
            'tasks': task_dates.get(date_str, []),
            'leads': lead_dates.get(date_str, []),
            'mission': mission_dates.get(date_str)
        })
    
    remaining = 42 - len(calendar_days)
    for day in range(1, remaining + 1):
        cell_date = date(next_year, next_month, day)
        date_str = cell_date.isoformat()
        calendar_days.append({
            'day': day,
            'current_month': False,
            'date': date_str,
            'is_today': cell_date == today,
            'tasks': task_dates.get(date_str, []),
            'leads': lead_dates.get(date_str, []),
            'mission': mission_dates.get(date_str)
        })
    
    return {
        'year': year,
        'month': month,
        'month_name': first_day.strftime('%B'),
        'days': calendar_days,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'current_boss': current_boss,
        'task_dates': task_dates,
        'lead_dates': lead_dates
    }

@calendar_bp.route('')
def index():
    year = request.args.get('year', type=int, default=date.today().year)
    month = request.args.get('month', type=int, default=date.today().month)
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    data = get_month_data(year, month)
    
    return render_template('calendar/index.html', **data)

@calendar_bp.route('/data')
def calendar_data():
    year = request.args.get('year', type=int, default=date.today().year)
    month = request.args.get('month', type=int, default=date.today().month)
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    data = get_month_data(year, month)
    
    boss_data = None
    if data['current_boss']:
        boss = data['current_boss']
        boss_data = {
            'description': boss.description,
            'progress': boss.progress_value,
            'target': boss.target_value,
            'is_completed': boss.is_completed,
            'reward_tokens': boss.reward_tokens
        }
    
    return jsonify({
        'year': year,
        'month': month,
        'month_name': data['month_name'],
        'days': data['days'],
        'boss': boss_data
    })

@calendar_bp.route('/day/<date_str>')
def day_detail(date_str):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400
    
    tasks = Task.query.filter(Task.due_date == target_date).all()
    leads = Lead.query.filter(
        Lead.next_action_date == target_date,
        Lead.status.notin_(['closed_won', 'closed_lost']),
        Lead.converted_at.is_(None)
    ).all()
    mission = DailyMission.query.filter(DailyMission.mission_date == target_date).first()
    
    return jsonify({
        'date': date_str,
        'date_formatted': target_date.strftime('%B %d, %Y'),
        'tasks': [{
            'id': t.id,
            'title': t.title,
            'status': t.status,
            'description': t.description or ''
        } for t in tasks],
        'leads': [{
            'id': l.id,
            'name': l.name,
            'business_name': l.business_name or '',
            'status': l.status
        } for l in leads],
        'mission': {
            'id': mission.id,
            'description': mission.description,
            'is_completed': mission.is_completed,
            'progress': mission.progress_count,
            'target': mission.target_count
        } if mission else None
    })

@calendar_bp.route('/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = 'done'
    db.session.commit()
    return jsonify({'success': True, 'task_id': task_id})

@calendar_bp.route('/mini')
def mini_data():
    year = request.args.get('year', type=int, default=date.today().year)
    month = request.args.get('month', type=int, default=date.today().month)
    data = get_month_data(year, month)
    
    mini_days = []
    for d in data['days']:
        has_tasks = len(d.get('tasks', [])) > 0 if d.get('current_month') else False
        has_leads = len(d.get('leads', [])) > 0 if d.get('current_month') else False
        has_mission = d.get('mission') is not None if d.get('current_month') else False
        
        mini_days.append({
            'day': d['day'],
            'current_month': d['current_month'],
            'date': d.get('date'),
            'is_today': d.get('is_today', False),
            'has_tasks': has_tasks,
            'has_leads': has_leads,
            'has_mission': has_mission
        })
    
    return jsonify({
        'year': year,
        'month': month,
        'month_name': data['month_name'],
        'days': mini_days,
        'prev_year': data['prev_year'],
        'prev_month': data['prev_month'],
        'next_year': data['next_year'],
        'next_month': data['next_month'],
        'has_boss': data['current_boss'] is not None
    })
