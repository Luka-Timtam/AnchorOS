from flask import Blueprint, render_template, request
from db_supabase import ActivityLog, get_supabase
from datetime import date, timedelta
import timezone as tz

timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')

@timeline_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    client = get_supabase()
    
    count_result = client.table('activity_log').select('id', count='exact').execute()
    total = count_result.count if count_result.count else len(count_result.data)
    
    result = client.table('activity_log').select('*').order('id', desc=True).range(offset, offset + per_page - 1).execute()
    activities = [ActivityLog._parse_row(row) for row in result.data]
    
    grouped = group_activities_by_day(activities)
    
    has_next = offset + per_page < total
    has_prev = page > 1
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_next': has_next,
        'has_prev': has_prev,
        'next_num': page + 1 if has_next else None,
        'prev_num': page - 1 if has_prev else None
    }
    
    return render_template('timeline/index.html', 
                         activities=activities,
                         grouped=grouped,
                         pagination=pagination,
                         page=page)


def group_activities_by_day(activities):
    today = tz.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    
    groups = {
        'Today': [],
        'Yesterday': [],
        'Earlier this week': [],
        'Last week': [],
        'Older': []
    }
    
    for activity in activities:
        created = getattr(activity, 'timestamp', '')
        if isinstance(created, str):
            activity_date = date.fromisoformat(created.split('T')[0])
        else:
            activity_date = created.date() if hasattr(created, 'date') else today
        
        if activity_date == today:
            groups['Today'].append(activity)
        elif activity_date == yesterday:
            groups['Yesterday'].append(activity)
        elif activity_date >= week_start:
            groups['Earlier this week'].append(activity)
        elif activity_date >= last_week_start:
            groups['Last week'].append(activity)
        else:
            groups['Older'].append(activity)
    
    return groups
