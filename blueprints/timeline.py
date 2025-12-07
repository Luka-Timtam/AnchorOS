from flask import Blueprint, render_template, request
from models import ActivityLog
from datetime import date, timedelta

timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')

@timeline_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    pagination = ActivityLog.get_paginated(page=page, per_page=per_page)
    activities = pagination.items
    
    grouped = group_activities_by_day(activities)
    
    return render_template('timeline/index.html', 
                         activities=activities,
                         grouped=grouped,
                         pagination=pagination,
                         page=page)


def group_activities_by_day(activities):
    today = date.today()
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
        activity_date = activity.timestamp.date()
        
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
