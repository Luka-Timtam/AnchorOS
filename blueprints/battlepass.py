from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db_supabase import get_supabase
from datetime import datetime
from blueprints.gamification import check_revenue_rewards, get_lifetime_revenue

battlepass_bp = Blueprint('battlepass', __name__, url_prefix='/battlepass')

ICON_CHOICES = [
    ('racecar', '🏎️ Race Car'),
    ('plane', '✈️ Plane'),
    ('car', '🚗 Car'),
    ('crown', '👑 Crown'),
    ('rocket', '🚀 Rocket'),
    ('watch', '⌚ Watch'),
    ('laptop', '💻 Laptop'),
    ('home', '🏠 Home'),
    ('chart', '📈 Chart'),
    ('star', '⭐ Star'),
    ('dinner', '🍽️ Dinner'),
    ('hourglass', '⏳ Hourglass'),
    ('camera', '📸 Camera'),
    ('cityscape', '🏙️ Cityscape'),
]


def get_level_from_xp(xp):
    level = 1
    xp_needed = 100
    total_xp = 0
    while total_xp + xp_needed <= xp:
        total_xp += xp_needed
        level += 1
        xp_needed = 100 + (level - 1) * 25
    return level


@battlepass_bp.route('/')
def index():
    client = get_supabase()
    check_revenue_rewards()
    
    stats_result = client.table('user_stats').select('*').execute()
    stats = stats_result.data[0] if stats_result.data else {'current_xp': 0}
    current_level = get_level_from_xp(stats.get('current_xp', 0))
    lifetime_revenue = get_lifetime_revenue()
    
    level_rewards_result = client.table('level_rewards').select('*').eq('is_active', True).order('level_interval').execute()
    level_rewards = level_rewards_result.data
    
    milestone_rewards_result = client.table('milestone_rewards').select('*').order('target_level').execute()
    milestone_rewards = milestone_rewards_result.data
    
    revenue_rewards_result = client.table('revenue_rewards').select('*').eq('is_active', True).order('target_revenue').execute()
    revenue_rewards = revenue_rewards_result.data
    
    unlocked_rewards_result = client.table('unlocked_rewards').select('*').order('unlocked_at', desc=True).execute()
    unlocked_rewards = unlocked_rewards_result.data
    
    upcoming_level = []
    for reward in level_rewards:
        interval = reward.get('level_interval', 5)
        next_level = ((current_level // interval) + 1) * interval
        upcoming_level.append({
            'id': reward['id'],
            'type': 'level',
            'level': next_level,
            'reward_text': reward.get('reward_text', ''),
            'interval': interval,
            'progress': (current_level % interval) / interval * 100 if interval > 0 else 0
        })
    
    upcoming_milestone = []
    unlocked_milestone = []
    for reward in milestone_rewards:
        target_level = reward.get('target_level', 0)
        item = {
            'id': reward['id'],
            'type': 'milestone',
            'level': target_level,
            'reward_text': reward.get('reward_text', ''),
            'unlocked_at': reward.get('unlocked_at'),
            'progress': min(100, (current_level / target_level) * 100) if target_level > 0 else 0
        }
        if reward.get('unlocked_at'):
            unlocked_milestone.append(item)
        else:
            upcoming_milestone.append(item)
    
    all_revenue_rewards = []
    for reward in revenue_rewards:
        status = 'locked'
        if reward.get('claimed_at'):
            status = 'claimed'
        elif reward.get('unlocked_at'):
            status = 'unlocked'
        
        target_revenue = reward.get('target_revenue', 0)
        all_revenue_rewards.append({
            'id': reward['id'],
            'type': 'revenue',
            'target': target_revenue,
            'reward_text': reward.get('reward_text', ''),
            'reward_icon': reward.get('reward_icon', 'gift'),
            'unlocked_at': reward.get('unlocked_at'),
            'claimed_at': reward.get('claimed_at'),
            'status': status,
            'progress': min(100, (lifetime_revenue / target_revenue) * 100) if target_revenue > 0 else 0
        })
    
    unlocked_level_rewards = [r for r in unlocked_rewards if r.get('reward_type') == 'level']
    claimed_level_rewards = [r for r in unlocked_rewards if r.get('reward_type') == 'level' and r.get('claimed_at')]
    unclaimed_level_rewards = [r for r in unlocked_rewards if r.get('reward_type') == 'level' and not r.get('claimed_at')]
    
    unlocked_milestone_from_log = [r for r in unlocked_rewards if r.get('reward_type') == 'milestone']
    claimed_milestone_rewards = [r for r in unlocked_rewards if r.get('reward_type') == 'milestone' and r.get('claimed_at')]
    unclaimed_milestone_rewards = [r for r in unlocked_rewards if r.get('reward_type') == 'milestone' and not r.get('claimed_at')]
    
    return render_template('battlepass/index.html',
        current_level=current_level,
        lifetime_revenue=lifetime_revenue,
        upcoming_level=upcoming_level,
        upcoming_milestone=upcoming_milestone,
        unlocked_milestone=unlocked_milestone,
        all_revenue_rewards=all_revenue_rewards,
        unlocked_level_rewards=unlocked_level_rewards,
        claimed_level_rewards=claimed_level_rewards,
        unclaimed_level_rewards=unclaimed_level_rewards,
        unlocked_milestone_from_log=unlocked_milestone_from_log,
        claimed_milestone_rewards=claimed_milestone_rewards,
        unclaimed_milestone_rewards=unclaimed_milestone_rewards
    )


@battlepass_bp.route('/claim/level/<int:id>', methods=['POST'])
def claim_level_reward(id):
    client = get_supabase()
    result = client.table('unlocked_rewards').select('*').eq('id', id).execute()
    if not result.data:
        flash('Reward not found.', 'error')
        return redirect(url_for('battlepass.index'))
    
    reward = result.data[0]
    if reward.get('claimed_at'):
        flash('This reward has already been claimed.', 'error')
    else:
        client.table('unlocked_rewards').update({
            'claimed_at': datetime.utcnow().isoformat()
        }).eq('id', id).execute()
        flash(f"Claimed: {reward.get('reward_text', 'Reward')}! Enjoy your reward!", 'success')
    return redirect(url_for('battlepass.index'))


@battlepass_bp.route('/claim/revenue/<int:id>', methods=['POST'])
def claim_revenue_reward(id):
    client = get_supabase()
    result = client.table('revenue_rewards').select('*').eq('id', id).execute()
    if not result.data:
        flash('Reward not found.', 'error')
        return redirect(url_for('battlepass.index'))
    
    reward = result.data[0]
    if not reward.get('unlocked_at'):
        flash('This reward has not been unlocked yet.', 'error')
    elif reward.get('claimed_at'):
        flash('This reward has already been claimed.', 'error')
    else:
        client.table('revenue_rewards').update({
            'claimed_at': datetime.utcnow().isoformat()
        }).eq('id', id).execute()
        flash(f"Claimed: {reward.get('reward_text', 'Reward')}! Enjoy your reward!", 'success')
    return redirect(url_for('battlepass.index'))


@battlepass_bp.route('/milestones')
def manage_milestones():
    client = get_supabase()
    result = client.table('revenue_rewards').select('*').order('target_revenue').execute()
    revenue_rewards = result.data
    return render_template('battlepass/milestones.html',
        revenue_rewards=revenue_rewards,
        icon_choices=ICON_CHOICES
    )


@battlepass_bp.route('/milestones/add', methods=['GET', 'POST'])
def add_milestone():
    if request.method == 'POST':
        try:
            target_revenue = float(request.form.get('target_revenue', 0))
        except (ValueError, TypeError):
            flash('Please enter a valid revenue amount.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Add',
                icon_choices=ICON_CHOICES
            )
        reward_text = request.form.get('reward_text', '').strip()
        reward_icon = request.form.get('reward_icon', 'gift')
        
        if not reward_text:
            flash('Please enter a reward description.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Add',
                icon_choices=ICON_CHOICES
            )
        
        client = get_supabase()
        client.table('revenue_rewards').insert({
            'target_revenue': target_revenue,
            'reward_text': reward_text,
            'reward_icon': reward_icon,
            'is_active': True
        }).execute()
        flash(f'Revenue milestone "${target_revenue:,.0f}" added!', 'success')
        return redirect(url_for('battlepass.manage_milestones'))
    
    return render_template('battlepass/milestone_form.html',
        action='Add',
        icon_choices=ICON_CHOICES
    )


@battlepass_bp.route('/milestones/<int:id>/edit', methods=['GET', 'POST'])
def edit_milestone(id):
    client = get_supabase()
    result = client.table('revenue_rewards').select('*').eq('id', id).execute()
    if not result.data:
        flash('Milestone not found.', 'error')
        return redirect(url_for('battlepass.manage_milestones'))
    
    reward = result.data[0]
    
    if request.method == 'POST':
        try:
            target_revenue = float(request.form.get('target_revenue', 0))
        except (ValueError, TypeError):
            flash('Please enter a valid revenue amount.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Edit',
                reward=reward,
                icon_choices=ICON_CHOICES
            )
        reward_text = request.form.get('reward_text', '').strip()
        reward_icon = request.form.get('reward_icon', 'gift')
        
        if not reward_text:
            flash('Please enter a reward description.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Edit',
                reward=reward,
                icon_choices=ICON_CHOICES
            )
        
        client.table('revenue_rewards').update({
            'target_revenue': target_revenue,
            'reward_text': reward_text,
            'reward_icon': reward_icon
        }).eq('id', id).execute()
        flash('Revenue milestone updated!', 'success')
        return redirect(url_for('battlepass.manage_milestones'))
    
    return render_template('battlepass/milestone_form.html',
        action='Edit',
        reward=reward,
        icon_choices=ICON_CHOICES
    )


@battlepass_bp.route('/milestones/<int:id>/delete', methods=['POST'])
def delete_milestone(id):
    client = get_supabase()
    client.table('revenue_rewards').delete().eq('id', id).execute()
    flash('Revenue milestone deleted.', 'info')
    return redirect(url_for('battlepass.manage_milestones'))
