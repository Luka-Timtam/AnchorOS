from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from db_supabase import (UserStats, Achievement, Goal, OutreachLog, Lead, Task, XPLog, 
                         LevelReward, MilestoneReward, UnlockedReward, UserTokens, DailyMission, 
                         TokenTransaction, UserSettings, ActivityLog, WinsLog, BossBattle, 
                         RewardItem, RevenueReward, Client, FreelancingIncome, get_supabase)
from datetime import datetime, date, timedelta
import timezone as tz


def is_paused():
    settings = UserSettings.get_settings()
    return settings.is_paused()

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

XP_RULES = {
    'outreach_log': 5,
    'lead_contacted': 4,
    'lead_call_booked': 8,
    'lead_proposal_sent': 12,
    'lead_closed_won': 30,
    'task_done': 8,
    'daily_goal_hit': 10,
    'weekly_goal_hit': 25,
    'monthly_revenue_goal_hit': 50,
    'streak_10': 20,
    'streak_30': 50,
}

TOKEN_RULES = {
    'outreach_log': 1,
    'lead_contacted': 1,
    'task_done': 1,
    'proposal_sent': 2,
    'daily_goal_hit': 3,
    'weekly_goal_hit': 7,
    'streak_3': 5,
    'streak_7': 10,
    'streak_14': 20,
    'streak_30': 30,
    'cold_lead_revived': 5,
}

LEVELS = [
    (1, 0),
    (2, 150),
    (3, 400),
    (4, 800),
    (5, 1400),
    (6, 2200),
    (7, 3200),
    (8, 4500),
    (9, 6500),
    (10, 9000),
    (11, 12000),
    (12, 16000),
    (13, 20000),
    (14, 25000),
    (15, 30000),
]

def get_level_from_xp(xp):
    level = 1
    for lvl, threshold in LEVELS:
        if xp >= threshold:
            level = lvl
        else:
            break
    return level

def get_xp_for_next_level(current_level):
    for lvl, threshold in LEVELS:
        if lvl == current_level + 1:
            return threshold
    return None


def add_tokens(amount, reason=""):
    return UserTokens.add_tokens(amount, reason)


def update_mission_progress(mission_type, count=1):
    today = date.today()
    mission = DailyMission.get_first({'mission_date': today.isoformat(), 'mission_type': mission_type})
    if mission and not getattr(mission, 'is_completed', False):
        new_progress = (getattr(mission, 'progress_count', 0) or 0) + count
        target = getattr(mission, 'target_count', 0) or 0
        is_completed = new_progress >= target
        DailyMission.update_by_id(mission.id, {'progress_count': new_progress, 'is_completed': is_completed})
        if is_completed:
            reward_tokens = getattr(mission, 'reward_tokens', 0) or 0
            add_tokens(reward_tokens, f'Mission completed: {mission_type}')
            flash(f'Mission complete! +{reward_tokens} tokens!', 'success')


def add_xp(amount, reason=""):
    stats = UserStats.get_stats()
    old_level = getattr(stats, 'current_level', 1) or 1
    current_xp = (getattr(stats, 'current_xp', 0) or 0) + amount
    new_level = get_level_from_xp(current_xp)
    
    UserStats.update_by_id(stats.id, {'current_xp': current_xp, 'current_level': new_level})
    XPLog.insert({'amount': amount, 'reason': reason, 'created_at': tz.now_iso()})
    
    check_and_unlock_achievements()
    
    if new_level > old_level:
        flash(f'Level Up! You are now Level {new_level}!', 'success')
        ActivityLog.log_activity('level_up', f'Leveled up to Level {new_level}!')
        WinsLog.insert({
            'title': f'Level Up to {new_level}',
            'description': f'Reached Level {new_level} after gaining XP.',
            'xp_value': amount,
            'token_value': 0,
            'timestamp': tz.now_iso()
        })
        check_level_interval_rewards(new_level)
        check_milestone_rewards(new_level)
    
    return current_xp


def check_level_interval_rewards(current_level):
    level_rewards = LevelReward.query_filter({'is_active': True})
    now = tz.now_iso()
    
    for reward in level_rewards:
        interval = getattr(reward, 'level_interval', 0) or 0
        if interval > 0 and current_level % interval == 0:
            existing = UnlockedReward.get_first({
                'reward_type': 'level',
                'reward_reference_id': reward.id,
                'level_achieved': current_level
            })
            
            if not existing:
                UnlockedReward.insert({
                    'reward_type': 'level',
                    'reward_reference_id': reward.id,
                    'level_achieved': current_level,
                    'reward_text': getattr(reward, 'reward_text', ''),
                    'unlocked_at': now
                })
                flash(f'You unlocked a reward: {reward.reward_text}!', 'success')


def check_milestone_rewards(current_level):
    milestone_rewards = MilestoneReward.query_filter({'is_active': True})
    now = tz.now_iso()
    
    for reward in milestone_rewards:
        if getattr(reward, 'unlocked_at', None):
            continue
        target = getattr(reward, 'target_level', 0) or 0
        if current_level >= target:
            MilestoneReward.update_by_id(reward.id, {'unlocked_at': now})
            
            UnlockedReward.insert({
                'reward_type': 'milestone',
                'reward_reference_id': reward.id,
                'level_achieved': current_level,
                'reward_text': getattr(reward, 'reward_text', ''),
                'unlocked_at': now
            })
            flash(f'Milestone reward unlocked: {reward.reward_text}!', 'success')


def get_lifetime_revenue():
    from cache import cache, CACHE_KEY_LIFETIME_REVENUE
    
    cached_value, hit = cache.get(CACHE_KEY_LIFETIME_REVENUE)
    if hit:
        return cached_value
    
    total_revenue = 0.0
    clients = Client.query_all()
    today = date.today()
    
    for client in clients:
        total_revenue += float(getattr(client, 'amount_charged', 0) or 0)
        
        start_date = getattr(client, 'start_date', None)
        if start_date:
            if isinstance(start_date, str):
                try:
                    start_date = date.fromisoformat(start_date.split('T')[0])
                except:
                    start_date = None
            
            if start_date:
                months_active = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                months_active = max(1, months_active)
                
                if getattr(client, 'hosting_active', False) and getattr(client, 'monthly_hosting_fee', 0):
                    total_revenue += float(client.monthly_hosting_fee) * months_active
                
                if getattr(client, 'saas_active', False) and getattr(client, 'monthly_saas_fee', 0):
                    total_revenue += float(client.monthly_saas_fee) * months_active
    
    freelance_income = FreelancingIncome.query_all()
    for income in freelance_income:
        total_revenue += float(getattr(income, 'amount', 0) or 0)
    
    cache.set(CACHE_KEY_LIFETIME_REVENUE, total_revenue, ttl=60)
    return total_revenue


def check_revenue_rewards():
    RevenueReward.seed_defaults()
    lifetime_revenue = get_lifetime_revenue()
    revenue_rewards = RevenueReward.query_filter({'is_active': True})
    now = tz.now_iso()
    
    for reward in revenue_rewards:
        if getattr(reward, 'unlocked_at', None):
            continue
        target = getattr(reward, 'target_revenue', 0) or 0
        if lifetime_revenue >= target:
            RevenueReward.update_by_id(reward.id, {'unlocked_at': now})
            flash(f'Revenue milestone unlocked: {reward.reward_text}!', 'success')


def get_upcoming_rewards(current_level):
    upcoming = []
    
    level_rewards = LevelReward.query_filter({'is_active': True}, order_by='level_interval')
    for reward in level_rewards:
        interval = getattr(reward, 'level_interval', 0) or 1
        next_level = ((current_level // interval) + 1) * interval
        upcoming.append({
            'type': 'level',
            'level': next_level,
            'reward_text': getattr(reward, 'reward_text', ''),
            'interval': interval
        })
    
    milestone_rewards = MilestoneReward.query_filter({'is_active': True}, order_by='target_level')
    for reward in milestone_rewards:
        if getattr(reward, 'unlocked_at', None):
            continue
        target = getattr(reward, 'target_level', 0)
        if target > current_level:
            upcoming.append({
                'type': 'milestone',
                'level': target,
                'reward_text': getattr(reward, 'reward_text', '')
            })
    
    upcoming.sort(key=lambda x: x['level'])
    return upcoming[:5]

def update_outreach_streak():
    stats = UserStats.get_stats()
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    last_outreach = getattr(stats, 'last_outreach_date', None)
    if last_outreach:
        if isinstance(last_outreach, str):
            try:
                last_outreach = date.fromisoformat(last_outreach.split('T')[0])
            except:
                last_outreach = None
    
    if last_outreach == today:
        return getattr(stats, 'current_outreach_streak_days', 0) or 0
    
    old_streak = getattr(stats, 'current_outreach_streak_days', 0) or 0
    
    if is_paused():
        UserStats.update_by_id(stats.id, {'last_outreach_date': today.isoformat()})
        return old_streak
    
    if last_outreach == yesterday:
        new_streak = old_streak + 1
    elif last_outreach is None or last_outreach < yesterday:
        new_streak = 1
    else:
        new_streak = old_streak
    
    longest = getattr(stats, 'longest_outreach_streak_days', 0) or 0
    if new_streak > longest:
        longest = new_streak
    
    UserStats.update_by_id(stats.id, {
        'current_outreach_streak_days': new_streak,
        'longest_outreach_streak_days': longest,
        'last_outreach_date': today.isoformat()
    })
    
    if new_streak > old_streak:
        ActivityLog.log_activity('streak_increased', f'Streak increased to {new_streak} days!')
    
    if old_streak < 10 and new_streak >= 10:
        add_xp(XP_RULES['streak_10'], "10-day outreach streak!")
        flash('10-day streak bonus: +20 XP!', 'success')
    if old_streak < 30 and new_streak >= 30:
        add_xp(XP_RULES['streak_30'], "30-day outreach streak!")
        flash('30-day streak bonus: +50 XP!', 'success')
    
    streak_token_milestones = [
        (3, 'streak_3', '3-day streak bonus'),
        (7, 'streak_7', '7-day streak bonus'),
        (14, 'streak_14', '14-day streak bonus'),
        (30, 'streak_30', '30-day streak bonus'),
    ]
    
    for milestone, rule_key, reason in streak_token_milestones:
        if old_streak < milestone and new_streak >= milestone:
            existing = TokenTransaction.get_first({'reason': reason})
            if not existing:
                add_tokens(TOKEN_RULES[rule_key], reason)
                flash(f'{reason}: +{TOKEN_RULES[rule_key]} tokens!', 'success')
                if milestone in [7, 14, 30]:
                    WinsLog.insert({
                        'title': f'{milestone}-Day Streak!',
                        'description': f'Reached a {milestone}-day outreach streak. Keep it up!',
                        'xp_value': XP_RULES.get(f'streak_{milestone}', 0) if milestone in [10, 30] else 0,
                        'token_value': TOKEN_RULES[rule_key]
                    })
    
    check_and_unlock_achievements()
    return new_streak


def check_daily_goal():
    today = date.today()
    
    daily_goal = Goal.get_first({'goal_type': 'daily_outreach'})
    if not daily_goal or (getattr(daily_goal, 'target_value', 0) or 0) <= 0:
        return False
    
    client = get_supabase()
    result = client.table('outreach_logs').select('id', count='exact').eq('date', today.isoformat()).execute()
    today_outreach = result.count if result.count else len(result.data)
    
    xp_logs = XPLog.query_filter({'reason': 'Daily outreach goal hit!'})
    today_start = f'{today.isoformat()}T00:00:00'
    existing_log = None
    for log in xp_logs:
        created = getattr(log, 'created_at', '')
        if isinstance(created, str) and created >= today_start:
            existing_log = log
            break
    
    target = getattr(daily_goal, 'target_value', 0) or 0
    if today_outreach >= target and not existing_log:
        add_xp(XP_RULES['daily_goal_hit'], "Daily outreach goal hit!")
        add_tokens(TOKEN_RULES['daily_goal_hit'], "Daily goal hit!")
        flash('Daily goal hit: +10 XP, +3 tokens!', 'success')
        return True
    
    return False


def check_weekly_goal():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    weekly_goal = Goal.get_first({'goal_type': 'weekly_outreach'})
    if not weekly_goal or (getattr(weekly_goal, 'target_value', 0) or 0) <= 0:
        return False
    
    client = get_supabase()
    result = client.table('outreach_logs').select('id', count='exact').gte('date', week_start.isoformat()).execute()
    week_outreach = result.count if result.count else len(result.data)
    
    xp_logs = XPLog.query_filter({'reason': 'Weekly outreach goal hit!'})
    week_start_ts = f'{week_start.isoformat()}T00:00:00'
    existing_log = None
    for log in xp_logs:
        created = getattr(log, 'created_at', '')
        if isinstance(created, str) and created >= week_start_ts:
            existing_log = log
            break
    
    target = getattr(weekly_goal, 'target_value', 0) or 0
    if week_outreach >= target and not existing_log:
        add_xp(XP_RULES['weekly_goal_hit'], "Weekly outreach goal hit!")
        add_tokens(TOKEN_RULES['weekly_goal_hit'], "Weekly goal hit!")
        WinsLog.insert({
            'title': 'Weekly Goal Hit',
            'description': f'Completed {week_outreach} outreach activities this week, hitting the weekly target of {target}.',
            'xp_value': XP_RULES['weekly_goal_hit'],
            'token_value': TOKEN_RULES['weekly_goal_hit']
        })
        flash('Weekly goal hit: +25 XP, +7 tokens!', 'success')
        return True
    
    return False


def check_monthly_revenue_goal():
    today = date.today()
    month_start = today.replace(day=1)
    
    monthly_goal = Goal.get_first({'goal_type': 'monthly_revenue'})
    if not monthly_goal or (getattr(monthly_goal, 'target_value', 0) or 0) <= 0:
        return False
    
    clients = Client.query_all()
    monthly_revenue = 0
    for c in clients:
        start_date = getattr(c, 'start_date', None)
        if start_date:
            if isinstance(start_date, str):
                try:
                    start_date = date.fromisoformat(start_date.split('T')[0])
                except:
                    continue
            if month_start <= start_date <= today:
                monthly_revenue += float(getattr(c, 'amount_charged', 0) or 0)
    
    xp_logs = XPLog.query_filter({'reason': 'Monthly revenue goal hit!'})
    month_start_ts = f'{month_start.isoformat()}T00:00:00'
    existing_log = None
    for log in xp_logs:
        created = getattr(log, 'created_at', '')
        if isinstance(created, str) and created >= month_start_ts:
            existing_log = log
            break
    
    target = getattr(monthly_goal, 'target_value', 0) or 0
    if monthly_revenue >= target and not existing_log:
        add_xp(XP_RULES['monthly_revenue_goal_hit'], "Monthly revenue goal hit!")
        flash('Monthly revenue goal hit: +50 XP!', 'success')
        return True
    
    return False


def check_all_goals():
    check_daily_goal()
    check_weekly_goal()
    check_monthly_revenue_goal()

def count_weekdays_in_range(start_date, end_date):
    """Count weekdays (Mon-Fri) in a date range, inclusive"""
    weekdays = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0 through Friday=4
            weekdays += 1
        current += timedelta(days=1)
    return weekdays

def calculate_consistency_score():
    stats = UserStats.get_stats()
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Count only weekdays in the past 7 days for consistency calculations
    weekdays_in_range = count_weekdays_in_range(week_ago, today)
    
    daily_goal = Goal.get_first({'goal_type': 'daily_outreach'})
    daily_target = (getattr(daily_goal, 'target_value', 0) or 0) if daily_goal else 0
    if daily_target == 0:
        daily_target = get_recommended_goal('daily_outreach')
    if daily_target == 0:
        daily_target = 3
    
    client = get_supabase()
    result = client.table('outreach_logs').select('id', count='exact').gte('date', week_ago.isoformat()).execute()
    outreach_count = result.count if result.count else len(result.data)
    # Use weekdays instead of full 7 days for outreach goal
    outreach_goal = daily_target * weekdays_in_range
    outreach_pct = min(100, (outreach_count / outreach_goal * 100)) if outreach_goal > 0 else 0
    
    leads_result = client.table('leads').select('id', count='exact').filter('next_action_date', 'not.is', 'null').gte('next_action_date', week_ago.isoformat()).lte('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")').execute()
    leads_with_followup = leads_result.count if leads_result.count else len(leads_result.data)
    
    contacted_result = client.table('leads').select('id', count='exact').filter('last_contacted_at', 'not.is', 'null').gte('last_contacted_at', f'{week_ago.isoformat()}T00:00:00').execute()
    leads_contacted = contacted_result.count if contacted_result.count else len(contacted_result.data)
    
    followup_pct = min(100, (leads_contacted / max(1, leads_with_followup) * 100))
    
    tasks_due_result = client.table('tasks').select('id', count='exact').gte('due_date', week_ago.isoformat()).lte('due_date', today.isoformat()).execute()
    tasks_due = tasks_due_result.count if tasks_due_result.count else len(tasks_due_result.data)
    
    tasks_done_result = client.table('tasks').select('id', count='exact').gte('due_date', week_ago.isoformat()).lte('due_date', today.isoformat()).eq('status', 'done').execute()
    tasks_done = tasks_done_result.count if tasks_done_result.count else len(tasks_done_result.data)
    
    task_pct = min(100, (tasks_done / max(1, tasks_due) * 100))
    
    consistency_score = int((outreach_pct + followup_pct + task_pct) / 3)
    
    if not is_paused():
        UserStats.update_by_id(stats.id, {
            'last_consistency_score': consistency_score,
            'last_consistency_calculated_at': tz.now_iso()
        })
    else:
        consistency_score = getattr(stats, 'last_consistency_score', 0) or consistency_score
    
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
    now = tz.now_iso()
    
    streak = getattr(stats, 'current_outreach_streak_days', 0) or 0
    xp = getattr(stats, 'current_xp', 0) or 0
    
    streak_7 = Achievement.get_first({'key': 'streak_7'})
    if streak_7 and not getattr(streak_7, 'unlocked_at', None) and streak >= 7:
        Achievement.update_by_id(streak_7.id, {'unlocked_at': now})
    
    streak_30 = Achievement.get_first({'key': 'streak_30'})
    if streak_30 and not getattr(streak_30, 'unlocked_at', None) and streak >= 30:
        Achievement.update_by_id(streak_30.id, {'unlocked_at': now})
    
    xp_1000 = Achievement.get_first({'key': 'xp_1000'})
    if xp_1000 and not getattr(xp_1000, 'unlocked_at', None) and xp >= 1000:
        Achievement.update_by_id(xp_1000.id, {'unlocked_at': now})
    
    xp_5000 = Achievement.get_first({'key': 'xp_5000'})
    if xp_5000 and not getattr(xp_5000, 'unlocked_at', None) and xp >= 5000:
        Achievement.update_by_id(xp_5000.id, {'unlocked_at': now})
    
    outreach_100 = Achievement.get_first({'key': 'outreach_100'})
    if outreach_100 and not getattr(outreach_100, 'unlocked_at', None):
        total_outreach = OutreachLog.count()
        if total_outreach >= 100:
            Achievement.update_by_id(outreach_100.id, {'unlocked_at': now})
    
    deals_10 = Achievement.get_first({'key': 'deals_10'})
    if deals_10 and not getattr(deals_10, 'unlocked_at', None):
        total_deals = Lead.count({'status': 'closed_won'})
        if total_deals >= 10:
            Achievement.update_by_id(deals_10.id, {'unlocked_at': now})

def get_recommended_goal(goal_type):
    today = date.today()
    client = get_supabase()
    
    if goal_type == 'daily_outreach':
        month_ago = today - timedelta(days=30)
        result = client.table('outreach_logs').select('id', count='exact').gte('date', month_ago.isoformat()).execute()
        total = result.count if result.count else len(result.data)
        avg = total / 30
        return max(1, int(avg) + 1)
    
    elif goal_type == 'weekly_outreach':
        eight_weeks_ago = today - timedelta(weeks=8)
        result = client.table('outreach_logs').select('id', count='exact').gte('date', eight_weeks_ago.isoformat()).execute()
        total = result.count if result.count else len(result.data)
        avg = total / 8
        return max(5, int(avg) + 1)
    
    elif goal_type == 'monthly_revenue':
        three_months_ago = today - timedelta(days=90)
        clients = Client.query_all()
        total = 0
        for c in clients:
            start_date = getattr(c, 'start_date', None)
            if start_date:
                if isinstance(start_date, str):
                    try:
                        start_date = date.fromisoformat(start_date.split('T')[0])
                    except:
                        continue
                if start_date >= three_months_ago:
                    total += float(getattr(c, 'amount_charged', 0) or 0)
        avg = total / 3
        return max(100, int(avg) + 100)
    
    elif goal_type == 'monthly_deals':
        three_months_ago = today - timedelta(days=90)
        result = client.table('leads').select('id', count='exact').eq('status', 'closed_won').gte('converted_at', f'{three_months_ago.isoformat()}T00:00:00').execute()
        total = result.count if result.count else len(result.data)
        avg = total / 3
        return max(1, int(avg) + 1)
    
    return 0

def get_xp_this_week():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    client = get_supabase()
    result = client.table('xp_logs').select('*').gte('created_at', f'{week_start.isoformat()}T00:00:00').execute()
    logs = result.data if result.data else []
    
    daily_xp = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        daily_xp[day.isoformat()] = 0
    
    for log in logs:
        created = log.get('created_at', '')
        if created:
            if isinstance(created, str):
                log_date = created.split('T')[0]
            elif hasattr(created, 'isoformat'):
                log_date = created.isoformat().split('T')[0]
            else:
                continue
            if log_date in daily_xp:
                daily_xp[log_date] += log.get('amount', 0) or 0
    
    return list(daily_xp.values())

def get_streak_history(days=30):
    return []

def get_consistency_history(days=30):
    return []

@gamification_bp.route('/')
def index():
    stats = UserStats.get_stats()
    Achievement.seed_defaults()
    LevelReward.seed_defaults()
    MilestoneReward.seed_defaults()
    
    check_all_goals()
    
    achievements = Achievement.query_all()
    unlocked = [a for a in achievements if getattr(a, 'unlocked_at', None)]
    locked = [a for a in achievements if not getattr(a, 'unlocked_at', None)]
    
    consistency = calculate_consistency_score()
    
    xp_this_week = get_xp_this_week()
    
    current_level = stats.get_level_from_xp()
    xp_for_next = stats.xp_for_next_level()
    current_level_xp = stats.xp_for_current_level()
    
    xp_progress = 0
    if xp_for_next:
        xp_in_level = (getattr(stats, 'current_xp', 0) or 0) - current_level_xp
        xp_needed = xp_for_next - current_level_xp
        xp_progress = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100
    
    upcoming_rewards = get_upcoming_rewards(current_level)
    unlocked_rewards = UnlockedReward.query_all(order_by='unlocked_at', order_desc=True, limit=10)
    
    level_rewards = LevelReward.query_all(order_by='level_interval')
    milestone_rewards = MilestoneReward.query_all(order_by='target_level')
    
    wins = WinsLog.query_all(order_by='id', order_desc=True)
    
    max_level = 15
    
    token_balance = UserTokens.get_balance()
    RewardItem.seed_defaults()
    available_rewards = RewardItem.count({'is_active': True})
    
    current_boss = BossBattle.get_current_battle()
    boss_progress = 0
    if current_boss:
        target = getattr(current_boss, 'target_outreach', 0) or 0
        progress = getattr(current_boss, 'current_outreach', 0) or 0
        if target > 0:
            boss_progress = min(100, int((progress / target) * 100))
    
    goals = Goal.query_all()
    active_goals_count = len(goals)
    
    return render_template('gamification/index.html',
        stats=stats,
        unlocked_achievements=unlocked,
        locked_achievements=locked,
        consistency=consistency,
        xp_this_week=xp_this_week,
        xp_for_next=xp_for_next,
        xp_progress=xp_progress,
        current_level=current_level,
        max_level=max_level,
        upcoming_rewards=upcoming_rewards,
        unlocked_rewards=unlocked_rewards,
        level_rewards=level_rewards,
        milestone_rewards=milestone_rewards,
        wins=wins,
        token_balance=token_balance,
        available_rewards=available_rewards,
        current_boss=current_boss,
        boss_progress=boss_progress,
        active_goals_count=active_goals_count
    )


@gamification_bp.route('/rewards/level/new', methods=['POST'])
def add_level_reward():
    interval = request.form.get('level_interval', type=int)
    text = request.form.get('reward_text', '')
    
    if interval and text:
        LevelReward.insert({'level_interval': interval, 'reward_text': text, 'is_active': True})
        flash('Level reward added successfully!', 'success')
    
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/new', methods=['POST'])
def add_milestone_reward():
    target = request.form.get('target_level', type=int)
    text = request.form.get('reward_text', '')
    
    if target and text:
        existing = MilestoneReward.get_first({'target_level': target})
        if not existing:
            MilestoneReward.insert({'target_level': target, 'reward_text': text, 'is_active': True})
            flash('Milestone reward added successfully!', 'success')
        else:
            flash('A milestone reward for this level already exists.', 'error')
    
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/level/<int:id>/toggle', methods=['POST'])
def toggle_level_reward(id):
    reward = LevelReward.get_by_id(id)
    if reward:
        LevelReward.update_by_id(id, {'is_active': not getattr(reward, 'is_active', True)})
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/<int:id>/toggle', methods=['POST'])
def toggle_milestone_reward(id):
    reward = MilestoneReward.get_by_id(id)
    if reward:
        MilestoneReward.update_by_id(id, {'is_active': not getattr(reward, 'is_active', True)})
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/level/<int:id>/delete', methods=['POST'])
def delete_level_reward(id):
    LevelReward.delete_by_id(id)
    flash('Level reward deleted successfully!', 'success')
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/<int:id>/delete', methods=['POST'])
def delete_milestone_reward(id):
    MilestoneReward.delete_by_id(id)
    flash('Milestone reward deleted successfully!', 'success')
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/wins/add', methods=['POST'])
def add_win():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if title:
        WinsLog.insert({
            'title': title,
            'description': description or None,
        })
        flash('Win added successfully!', 'success')
    else:
        flash('Win title is required.', 'error')
    
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/<int:id>/claim', methods=['POST'])
def claim_reward(id):
    reward = UnlockedReward.get_by_id(id)
    if reward and not getattr(reward, 'claimed_at', None):
        UnlockedReward.update_by_id(id, {'claimed_at': tz.now_iso()})
        flash('Reward claimed!', 'success')
    return redirect(url_for('gamification.index'))
