from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, UserStats, Achievement, Goal, OutreachLog, Lead, Task, XPLog, LevelReward, MilestoneReward, UnlockedReward, UserTokens, DailyMission, TokenTransaction, UserSettings
from datetime import datetime, date, timedelta
from sqlalchemy import func


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
    mission = DailyMission.query.filter_by(mission_date=today, mission_type=mission_type).first()
    if mission and not mission.is_completed:
        mission.progress_count += count
        db.session.commit()
        if mission.check_completion():
            flash(f'Mission complete! +{mission.reward_tokens} tokens!', 'success')


def add_xp(amount, reason=""):
    stats = UserStats.get_stats()
    old_level = stats.current_level
    stats.current_xp += amount
    new_level = get_level_from_xp(stats.current_xp)
    stats.current_level = new_level
    
    log = XPLog(amount=amount, reason=reason)
    db.session.add(log)
    db.session.commit()
    
    check_and_unlock_achievements()
    
    if new_level > old_level:
        flash(f'Level Up! You are now Level {new_level}!', 'success')
        check_level_interval_rewards(new_level)
        check_milestone_rewards(new_level)
    
    return stats.current_xp


def check_level_interval_rewards(current_level):
    level_rewards = LevelReward.query.filter_by(is_active=True).all()
    now = datetime.utcnow()
    
    for reward in level_rewards:
        if current_level % reward.level_interval == 0:
            existing = UnlockedReward.query.filter_by(
                reward_type='level',
                reward_reference_id=reward.id,
                level_achieved=current_level
            ).first()
            
            if not existing:
                unlocked = UnlockedReward(
                    reward_type='level',
                    reward_reference_id=reward.id,
                    level_achieved=current_level,
                    reward_text=reward.reward_text,
                    unlocked_at=now
                )
                db.session.add(unlocked)
                flash(f'You unlocked a reward: {reward.reward_text}!', 'success')
    
    db.session.commit()


def check_milestone_rewards(current_level):
    milestone_rewards = MilestoneReward.query.filter_by(is_active=True, unlocked_at=None).all()
    now = datetime.utcnow()
    
    for reward in milestone_rewards:
        if current_level >= reward.target_level:
            reward.unlocked_at = now
            
            unlocked = UnlockedReward(
                reward_type='milestone',
                reward_reference_id=reward.id,
                level_achieved=current_level,
                reward_text=reward.reward_text,
                unlocked_at=now
            )
            db.session.add(unlocked)
            flash(f'Milestone reward unlocked: {reward.reward_text}!', 'success')
    
    db.session.commit()


def get_upcoming_rewards(current_level):
    upcoming = []
    
    level_rewards = LevelReward.query.filter_by(is_active=True).order_by(LevelReward.level_interval).all()
    for reward in level_rewards:
        next_level = ((current_level // reward.level_interval) + 1) * reward.level_interval
        upcoming.append({
            'type': 'level',
            'level': next_level,
            'reward_text': reward.reward_text,
            'interval': reward.level_interval
        })
    
    milestone_rewards = MilestoneReward.query.filter_by(is_active=True, unlocked_at=None).order_by(MilestoneReward.target_level).all()
    for reward in milestone_rewards:
        if reward.target_level > current_level:
            upcoming.append({
                'type': 'milestone',
                'level': reward.target_level,
                'reward_text': reward.reward_text
            })
    
    upcoming.sort(key=lambda x: x['level'])
    return upcoming[:5]

def update_outreach_streak():
    stats = UserStats.get_stats()
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    if stats.last_outreach_date == today:
        return stats.current_outreach_streak_days
    
    old_streak = stats.current_outreach_streak_days
    
    if is_paused():
        stats.last_outreach_date = today
        db.session.commit()
        return stats.current_outreach_streak_days
    
    if stats.last_outreach_date == yesterday:
        stats.current_outreach_streak_days += 1
    elif stats.last_outreach_date is None or stats.last_outreach_date < yesterday:
        stats.current_outreach_streak_days = 1
    
    stats.last_outreach_date = today
    
    if stats.current_outreach_streak_days > stats.longest_outreach_streak_days:
        stats.longest_outreach_streak_days = stats.current_outreach_streak_days
    
    db.session.commit()
    
    new_streak = stats.current_outreach_streak_days
    
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
            existing = TokenTransaction.query.filter(
                TokenTransaction.reason == reason
            ).first()
            if not existing:
                add_tokens(TOKEN_RULES[rule_key], reason)
                flash(f'{reason}: +{TOKEN_RULES[rule_key]} tokens!', 'success')
    
    check_and_unlock_achievements()
    return stats.current_outreach_streak_days


def check_daily_goal():
    today = date.today()
    
    daily_goal = Goal.query.filter_by(goal_type='daily_outreach').first()
    if not daily_goal or daily_goal.target_value <= 0:
        return False
    
    today_outreach = OutreachLog.query.filter(OutreachLog.date == today).count()
    
    existing_log = XPLog.query.filter(
        XPLog.reason == "Daily outreach goal hit!",
        func.date(XPLog.created_at) == today
    ).first()
    
    if today_outreach >= daily_goal.target_value and not existing_log:
        add_xp(XP_RULES['daily_goal_hit'], "Daily outreach goal hit!")
        add_tokens(TOKEN_RULES['daily_goal_hit'], "Daily goal hit!")
        flash('Daily goal hit: +10 XP, +3 tokens!', 'success')
        return True
    
    return False


def check_weekly_goal():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    weekly_goal = Goal.query.filter_by(goal_type='weekly_outreach').first()
    if not weekly_goal or weekly_goal.target_value <= 0:
        return False
    
    week_outreach = OutreachLog.query.filter(OutreachLog.date >= week_start).count()
    
    existing_log = XPLog.query.filter(
        XPLog.reason == "Weekly outreach goal hit!",
        func.date(XPLog.created_at) >= week_start
    ).first()
    
    if week_outreach >= weekly_goal.target_value and not existing_log:
        add_xp(XP_RULES['weekly_goal_hit'], "Weekly outreach goal hit!")
        add_tokens(TOKEN_RULES['weekly_goal_hit'], "Weekly goal hit!")
        flash('Weekly goal hit: +25 XP, +7 tokens!', 'success')
        return True
    
    return False


def check_monthly_revenue_goal():
    today = date.today()
    month_start = today.replace(day=1)
    
    from models import Client
    
    monthly_goal = Goal.query.filter_by(goal_type='monthly_revenue').first()
    if not monthly_goal or monthly_goal.target_value <= 0:
        return False
    
    monthly_revenue = db.session.query(func.sum(Client.amount_charged)).filter(
        Client.start_date >= month_start,
        Client.start_date <= today
    ).scalar() or 0
    
    existing_log = XPLog.query.filter(
        XPLog.reason == "Monthly revenue goal hit!",
        func.date(XPLog.created_at) >= month_start
    ).first()
    
    if float(monthly_revenue) >= monthly_goal.target_value and not existing_log:
        add_xp(XP_RULES['monthly_revenue_goal_hit'], "Monthly revenue goal hit!")
        flash('Monthly revenue goal hit: +50 XP!', 'success')
        return True
    
    return False


def check_all_goals():
    check_daily_goal()
    check_weekly_goal()
    check_monthly_revenue_goal()

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
    
    if not is_paused():
        stats.last_consistency_score = consistency_score
        stats.last_consistency_calculated_at = datetime.utcnow()
        db.session.commit()
    else:
        consistency_score = stats.last_consistency_score or consistency_score
    
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
    LevelReward.seed_defaults()
    MilestoneReward.seed_defaults()
    
    check_all_goals()
    
    achievements = Achievement.query.all()
    unlocked = [a for a in achievements if a.unlocked_at]
    locked = [a for a in achievements if not a.unlocked_at]
    
    consistency = calculate_consistency_score()
    
    xp_this_week = get_xp_this_week()
    
    current_level = stats.get_level_from_xp()
    xp_for_next = stats.xp_for_next_level()
    current_level_xp = stats.xp_for_current_level()
    
    xp_progress = 0
    if xp_for_next:
        xp_in_level = stats.current_xp - current_level_xp
        xp_needed = xp_for_next - current_level_xp
        xp_progress = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100
    
    upcoming_rewards = get_upcoming_rewards(current_level)
    unlocked_rewards = UnlockedReward.query.order_by(UnlockedReward.unlocked_at.desc()).limit(10).all()
    
    level_rewards = LevelReward.query.order_by(LevelReward.level_interval).all()
    milestone_rewards = MilestoneReward.query.order_by(MilestoneReward.target_level).all()
    
    max_level = 15
    
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
        milestone_rewards=milestone_rewards
    )


@gamification_bp.route('/rewards/level/new', methods=['POST'])
def add_level_reward():
    interval = request.form.get('level_interval', type=int)
    text = request.form.get('reward_text', '')
    
    if interval and text:
        reward = LevelReward(level_interval=interval, reward_text=text)
        db.session.add(reward)
        db.session.commit()
        flash('Level reward added successfully!', 'success')
    
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/new', methods=['POST'])
def add_milestone_reward():
    target = request.form.get('target_level', type=int)
    text = request.form.get('reward_text', '')
    
    if target and text:
        existing = MilestoneReward.query.filter_by(target_level=target).first()
        if not existing:
            reward = MilestoneReward(target_level=target, reward_text=text)
            db.session.add(reward)
            db.session.commit()
            flash('Milestone reward added successfully!', 'success')
        else:
            flash('A milestone reward for this level already exists.', 'error')
    
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/level/<int:id>/toggle', methods=['POST'])
def toggle_level_reward(id):
    reward = LevelReward.query.get_or_404(id)
    reward.is_active = not reward.is_active
    db.session.commit()
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/<int:id>/toggle', methods=['POST'])
def toggle_milestone_reward(id):
    reward = MilestoneReward.query.get_or_404(id)
    reward.is_active = not reward.is_active
    db.session.commit()
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/level/<int:id>/delete', methods=['POST'])
def delete_level_reward(id):
    reward = LevelReward.query.get_or_404(id)
    db.session.delete(reward)
    db.session.commit()
    flash('Level reward deleted.', 'success')
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/rewards/milestone/<int:id>/delete', methods=['POST'])
def delete_milestone_reward(id):
    reward = MilestoneReward.query.get_or_404(id)
    db.session.delete(reward)
    db.session.commit()
    flash('Milestone reward deleted.', 'success')
    return redirect(url_for('gamification.index'))
