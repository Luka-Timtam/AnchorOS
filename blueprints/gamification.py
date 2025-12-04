from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, UserStats, Achievement, Goal, OutreachLog, Lead, Task, XPLog
from datetime import datetime, date, timedelta
from sqlalchemy import func

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

XP_RULES = {
    'outreach_log': 5,
    'lead_contacted': 3,
    'lead_call_booked': 7,
    'lead_proposal_sent': 10,
    'lead_closed_won': 20,
    'task_done': 8,
}

def add_xp(amount, reason=""):
    stats = UserStats.get_stats()
    stats.current_xp += amount
    stats.current_level = stats.get_level_from_xp()
    
    log = XPLog(amount=amount, reason=reason)
    db.session.add(log)
    db.session.commit()
    
    check_and_unlock_achievements()
    return stats.current_xp

def update_outreach_streak():
    stats = UserStats.get_stats()
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    if stats.last_outreach_date == today:
        return stats.current_outreach_streak_days
    
    if stats.last_outreach_date == yesterday:
        stats.current_outreach_streak_days += 1
    elif stats.last_outreach_date is None or stats.last_outreach_date < yesterday:
        stats.current_outreach_streak_days = 1
    
    stats.last_outreach_date = today
    
    if stats.current_outreach_streak_days > stats.longest_outreach_streak_days:
        stats.longest_outreach_streak_days = stats.current_outreach_streak_days
    
    db.session.commit()
    check_and_unlock_achievements()
    return stats.current_outreach_streak_days

def calculate_consistency_score():
    stats = UserStats.get_stats()
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    daily_goal = Goal.query.filter_by(goal_type='daily_outreach').first()
    daily_target = daily_goal.target_value if daily_goal and daily_goal.target_value > 0 else get_recommended_goal('daily_outreach')
    if daily_target == 0:
        daily_target = 3
    
    outreach_count = OutreachLog.query.filter(OutreachLog.date >= week_ago).count()
    outreach_goal = daily_target * 7
    outreach_pct = min(100, (outreach_count / outreach_goal * 100)) if outreach_goal > 0 else 0
    
    leads_with_followup = Lead.query.filter(
        Lead.next_action_date.isnot(None),
        Lead.next_action_date >= week_ago,
        Lead.next_action_date <= today,
        Lead.status.notin_(['closed_won', 'closed_lost'])
    ).count()
    
    leads_contacted = Lead.query.filter(
        Lead.last_contacted_at.isnot(None),
        Lead.last_contacted_at >= week_ago
    ).count()
    
    followup_pct = min(100, (leads_contacted / max(1, leads_with_followup) * 100))
    
    tasks_due = Task.query.filter(
        Task.due_date >= week_ago,
        Task.due_date <= today
    ).count()
    
    tasks_done = Task.query.filter(
        Task.due_date >= week_ago,
        Task.due_date <= today,
        Task.status == 'done'
    ).count()
    
    task_pct = min(100, (tasks_done / max(1, tasks_due) * 100))
    
    consistency_score = int((outreach_pct + followup_pct + task_pct) / 3)
    
    stats.last_consistency_score = consistency_score
    stats.last_consistency_calculated_at = datetime.utcnow()
    db.session.commit()
    
    return {
        'score': consistency_score,
        'outreach_pct': int(outreach_pct),
        'followup_pct': int(followup_pct),
        'task_pct': int(task_pct),
        'outreach_count': outreach_count,
        'outreach_goal': outreach_goal,
        'tasks_done': tasks_done,
        'tasks_due': tasks_due
    }

def check_and_unlock_achievements():
    stats = UserStats.get_stats()
    now = datetime.utcnow()
    
    streak_7 = Achievement.query.filter_by(key='streak_7').first()
    if streak_7 and not streak_7.unlocked_at and stats.current_outreach_streak_days >= 7:
        streak_7.unlocked_at = now
    
    streak_30 = Achievement.query.filter_by(key='streak_30').first()
    if streak_30 and not streak_30.unlocked_at and stats.current_outreach_streak_days >= 30:
        streak_30.unlocked_at = now
    
    xp_1000 = Achievement.query.filter_by(key='xp_1000').first()
    if xp_1000 and not xp_1000.unlocked_at and stats.current_xp >= 1000:
        xp_1000.unlocked_at = now
    
    xp_5000 = Achievement.query.filter_by(key='xp_5000').first()
    if xp_5000 and not xp_5000.unlocked_at and stats.current_xp >= 5000:
        xp_5000.unlocked_at = now
    
    outreach_100 = Achievement.query.filter_by(key='outreach_100').first()
    if outreach_100 and not outreach_100.unlocked_at:
        total_outreach = OutreachLog.query.count()
        if total_outreach >= 100:
            outreach_100.unlocked_at = now
    
    deals_10 = Achievement.query.filter_by(key='deals_10').first()
    if deals_10 and not deals_10.unlocked_at:
        total_deals = Lead.query.filter_by(status='closed_won').count()
        if total_deals >= 10:
            deals_10.unlocked_at = now
    
    db.session.commit()

def get_recommended_goal(goal_type):
    today = date.today()
    
    if goal_type == 'daily_outreach':
        month_ago = today - timedelta(days=30)
        total = OutreachLog.query.filter(OutreachLog.date >= month_ago).count()
        avg = total / 30
        return max(1, int(avg) + 1)
    
    elif goal_type == 'weekly_outreach':
        eight_weeks_ago = today - timedelta(weeks=8)
        total = OutreachLog.query.filter(OutreachLog.date >= eight_weeks_ago).count()
        avg = total / 8
        return max(5, int(avg) + 1)
    
    elif goal_type == 'monthly_revenue':
        from models import Client
        three_months_ago = today - timedelta(days=90)
        total = db.session.query(func.sum(Client.amount_charged)).filter(
            Client.start_date >= three_months_ago
        ).scalar() or 0
        avg = float(total) / 3
        return max(100, int(avg) + 100)
    
    elif goal_type == 'monthly_deals':
        three_months_ago = today - timedelta(days=90)
        total = Lead.query.filter(
            Lead.status == 'closed_won',
            Lead.converted_at >= three_months_ago
        ).count()
        avg = total / 3
        return max(1, int(avg) + 1)
    
    return 0

def get_xp_this_week():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    logs = XPLog.query.filter(
        func.date(XPLog.created_at) >= week_start
    ).all()
    
    daily_xp = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        daily_xp[day.isoformat()] = 0
    
    for log in logs:
        log_date = log.created_at.date().isoformat()
        if log_date in daily_xp:
            daily_xp[log_date] += log.amount
    
    return list(daily_xp.values())

def get_streak_history(days=30):
    return []

def get_consistency_history(days=30):
    return []

@gamification_bp.route('/')
def index():
    stats = UserStats.get_stats()
    Achievement.seed_defaults()
    
    achievements = Achievement.query.all()
    unlocked = [a for a in achievements if a.unlocked_at]
    locked = [a for a in achievements if not a.unlocked_at]
    
    consistency = calculate_consistency_score()
    
    xp_this_week = get_xp_this_week()
    
    xp_for_next = stats.xp_for_next_level()
    levels = [0, 200, 500, 1000, 1500, 2500, 3500, 5000, 7500, 10000]
    current_level = stats.get_level_from_xp()
    current_level_xp = levels[current_level - 1] if current_level > 1 else 0
    xp_progress = 0
    if xp_for_next:
        xp_in_level = stats.current_xp - current_level_xp
        xp_needed = xp_for_next - current_level_xp
        xp_progress = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100
    
    return render_template('gamification/index.html',
        stats=stats,
        unlocked_achievements=unlocked,
        locked_achievements=locked,
        consistency=consistency,
        xp_this_week=xp_this_week,
        xp_for_next=xp_for_next,
        xp_progress=xp_progress,
        current_level=current_level
    )
