from flask import Blueprint, render_template, request, jsonify, abort
from db_supabase import Lead, Task, DailyMission, BossBattle, get_supabase
from datetime import datetime, date, timedelta
from calendar import monthrange

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
    
    client = get_supabase()
    
    tasks_result = client.table('tasks').select('*').gte('due_date', grid_start.isoformat()).lte('due_date', grid_end.isoformat()).execute()
    tasks = [Task._parse_row(row) for row in tasks_result.data]
    
    leads_result = client.table('leads').select('*').gte('next_action_date', grid_start.isoformat()).lte('next_action_date', grid_end.isoformat()).not_.in_('status', ['closed_won', 'closed_lost']).is_('converted_at', 'null').execute()
    leads = [Lead._parse_row(row) for row in leads_result.data]
    
    missions_result = client.table('daily_missions').select('*').gte('mission_date', grid_start.isoformat()).lte('mission_date', grid_end.isoformat()).execute()
    missions = [DailyMission._parse_row(row) for row in missions_result.data]
    
    boss_result = client.table('boss_fights').select('*').eq('month', f"{year}-{month:02d}").execute()
    current_boss = BossBattle._parse_row(boss_result.data[0]) if boss_result.data else None
    
    task_dates = {}
    for task in tasks:
        due_date = getattr(task, 'due_date', '')
        if isinstance(due_date, str):
            d = due_date.split('T')[0]
        else:
            d = due_date.isoformat() if due_date else ''
        if d:
            if d not in task_dates:
                task_dates[d] = []
            task_dates[d].append({
                'id': getattr(task, 'id', 0),
                'title': getattr(task, 'title', ''),
                'status': getattr(task, 'status', ''),
                'type': 'task'
            })
    
    lead_dates = {}
    for lead in leads:
        next_action = getattr(lead, 'next_action_date', '')
        if isinstance(next_action, str):
            d = next_action.split('T')[0]
        else:
            d = next_action.isoformat() if next_action else ''
        if d:
            if d not in lead_dates:
                lead_dates[d] = []
            lead_dates[d].append({
                'id': getattr(lead, 'id', 0),
                'name': getattr(lead, 'name', ''),
                'status': getattr(lead, 'status', ''),
                'type': 'lead'
            })
    
    mission_dates = {}
    for mission in missions:
        mission_date = getattr(mission, 'mission_date', '')
        if isinstance(mission_date, str):
            d = mission_date.split('T')[0]
        else:
            d = mission_date.isoformat() if mission_date else ''
        if d:
            mission_dates[d] = {
                'id': getattr(mission, 'id', 0),
                'mission_type': getattr(mission, 'mission_type', ''),
                'is_completed': getattr(mission, 'is_completed', False),
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
            'boss_name': getattr(boss, 'boss_name', ''),
            'current_outreach': getattr(boss, 'current_outreach', 0),
            'target_outreach': getattr(boss, 'target_outreach', 0),
            'is_defeated': getattr(boss, 'is_defeated', False),
            'reward_tokens': getattr(boss, 'reward_tokens', 0)
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
    
    client = get_supabase()
    
    tasks_result = client.table('tasks').select('*').eq('due_date', target_date.isoformat()).execute()
    tasks = [Task._parse_row(row) for row in tasks_result.data]
    
    leads_result = client.table('leads').select('*').eq('next_action_date', target_date.isoformat()).not_.in_('status', ['closed_won', 'closed_lost']).is_('converted_at', 'null').execute()
    leads = [Lead._parse_row(row) for row in leads_result.data]
    
    mission_result = client.table('daily_missions').select('*').eq('mission_date', target_date.isoformat()).execute()
    mission = DailyMission._parse_row(mission_result.data[0]) if mission_result.data else None
    
    return jsonify({
        'date': date_str,
        'date_formatted': target_date.strftime('%B %d, %Y'),
        'tasks': [{
            'id': getattr(t, 'id', 0),
            'title': getattr(t, 'title', ''),
            'status': getattr(t, 'status', ''),
            'description': getattr(t, 'description', '') or ''
        } for t in tasks],
        'leads': [{
            'id': getattr(l, 'id', 0),
            'name': getattr(l, 'name', ''),
            'business_name': getattr(l, 'business_name', '') or '',
            'status': getattr(l, 'status', '')
        } for l in leads],
        'mission': {
            'id': getattr(mission, 'id', 0),
            'mission_type': getattr(mission, 'mission_type', ''),
            'is_completed': getattr(mission, 'is_completed', False),
            'progress_count': getattr(mission, 'progress_count', 0),
            'target_count': getattr(mission, 'target_count', 0)
        } if mission else None
    })

@calendar_bp.route('/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    Task.update_by_id(task_id, {'status': 'done'})
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
