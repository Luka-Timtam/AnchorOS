from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, UnlockedReward, LevelReward, MilestoneReward, RevenueReward, UserStats, Client
from datetime import datetime
from sqlalchemy import func
from blueprints.gamification import check_revenue_rewards, get_lifetime_revenue

battlepass_bp = Blueprint('battlepass', __name__, url_prefix='/battlepass')

ICON_CHOICES = [
    ('car', '🏎️ Car'),
    ('plane', '✈️ Plane'),
    ('globe', '🌍 Globe'),
    ('crown', '👑 Crown'),
    ('rocket', '🚀 Rocket'),
    ('watch', '⌚ Watch'),
    ('laptop', '💻 Laptop'),
    ('home', '🏠 Home'),
    ('chart', '📈 Chart'),
    ('star', '⭐ Star'),
    ('spa', '🧖 Spa'),
    ('shoe', '👟 Shoe'),
    ('utensils', '🍽️ Dinner'),
    ('gift', '🎁 Gift'),
]


@battlepass_bp.route('/')
def index():
    check_revenue_rewards()
    
    stats = UserStats.get_stats()
    current_level = stats.get_level_from_xp()
    lifetime_revenue = get_lifetime_revenue()
    
    level_rewards = LevelReward.query.filter_by(is_active=True).order_by(LevelReward.level_interval).all()
    milestone_rewards = MilestoneReward.query.order_by(MilestoneReward.target_level).all()
    revenue_rewards = RevenueReward.query.filter_by(is_active=True).order_by(RevenueReward.target_revenue).all()
    unlocked_rewards = UnlockedReward.query.order_by(UnlockedReward.unlocked_at.desc()).all()
    
    upcoming_level = []
    for reward in level_rewards:
        next_level = ((current_level // reward.level_interval) + 1) * reward.level_interval
        upcoming_level.append({
            'id': reward.id,
            'type': 'level',
            'level': next_level,
            'reward_text': reward.reward_text,
            'interval': reward.level_interval,
            'progress': (current_level % reward.level_interval) / reward.level_interval * 100
        })
    
    upcoming_milestone = []
    unlocked_milestone = []
    for reward in milestone_rewards:
        item = {
            'id': reward.id,
            'type': 'milestone',
            'level': reward.target_level,
            'reward_text': reward.reward_text,
            'unlocked_at': reward.unlocked_at,
            'progress': min(100, (current_level / reward.target_level) * 100) if reward.target_level > 0 else 0
        }
        if reward.unlocked_at:
            unlocked_milestone.append(item)
        else:
            upcoming_milestone.append(item)
    
    all_revenue_rewards = []
    for reward in revenue_rewards:
        status = 'locked'
        if reward.claimed_at:
            status = 'claimed'
        elif reward.unlocked_at:
            status = 'unlocked'
        
        all_revenue_rewards.append({
            'id': reward.id,
            'type': 'revenue',
            'target': reward.target_revenue,
            'reward_text': reward.reward_text,
            'reward_icon': reward.reward_icon,
            'unlocked_at': reward.unlocked_at,
            'claimed_at': reward.claimed_at,
            'status': status,
            'progress': min(100, (lifetime_revenue / reward.target_revenue) * 100) if reward.target_revenue > 0 else 0
        })
    
    unlocked_level_rewards = [r for r in unlocked_rewards if r.reward_type == 'level']
    claimed_level_rewards = [r for r in unlocked_rewards if r.reward_type == 'level' and r.claimed_at]
    unclaimed_level_rewards = [r for r in unlocked_rewards if r.reward_type == 'level' and not r.claimed_at]
    
    unlocked_milestone_from_log = [r for r in unlocked_rewards if r.reward_type == 'milestone']
    claimed_milestone_rewards = [r for r in unlocked_rewards if r.reward_type == 'milestone' and r.claimed_at]
    unclaimed_milestone_rewards = [r for r in unlocked_rewards if r.reward_type == 'milestone' and not r.claimed_at]
    
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
    reward = UnlockedReward.query.get_or_404(id)
    if reward.claimed_at:
        flash('This reward has already been claimed.', 'error')
    else:
        reward.claimed_at = datetime.utcnow()
        db.session.commit()
        flash(f'Claimed: {reward.reward_text}! Enjoy your reward!', 'success')
    return redirect(url_for('battlepass.index'))


@battlepass_bp.route('/claim/revenue/<int:id>', methods=['POST'])
def claim_revenue_reward(id):
    reward = RevenueReward.query.get_or_404(id)
    if not reward.unlocked_at:
        flash('This reward has not been unlocked yet.', 'error')
    elif reward.claimed_at:
        flash('This reward has already been claimed.', 'error')
    else:
        reward.claimed_at = datetime.utcnow()
        db.session.commit()
        flash(f'Claimed: {reward.reward_text}! Enjoy your reward!', 'success')
    return redirect(url_for('battlepass.index'))


@battlepass_bp.route('/milestones')
def manage_milestones():
    revenue_rewards = RevenueReward.query.order_by(RevenueReward.target_revenue).all()
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
        
        reward = RevenueReward(
            target_revenue=target_revenue,
            reward_text=reward_text,
            reward_icon=reward_icon,
            is_active=True
        )
        db.session.add(reward)
        db.session.commit()
        flash(f'Revenue milestone "${target_revenue:,.0f}" added!', 'success')
        return redirect(url_for('battlepass.manage_milestones'))
    
    return render_template('battlepass/milestone_form.html',
        action='Add',
        icon_choices=ICON_CHOICES
    )


@battlepass_bp.route('/milestones/<int:id>/edit', methods=['GET', 'POST'])
def edit_milestone(id):
    reward = RevenueReward.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            reward.target_revenue = float(request.form.get('target_revenue', 0))
        except (ValueError, TypeError):
            flash('Please enter a valid revenue amount.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Edit',
                reward=reward,
                icon_choices=ICON_CHOICES
            )
        reward.reward_text = request.form.get('reward_text', '').strip()
        reward.reward_icon = request.form.get('reward_icon', 'gift')
        
        if not reward.reward_text:
            flash('Please enter a reward description.', 'error')
            return render_template('battlepass/milestone_form.html',
                action='Edit',
                reward=reward,
                icon_choices=ICON_CHOICES
            )
        
        db.session.commit()
        flash('Revenue milestone updated!', 'success')
        return redirect(url_for('battlepass.manage_milestones'))
    
    return render_template('battlepass/milestone_form.html',
        action='Edit',
        reward=reward,
        icon_choices=ICON_CHOICES
    )


@battlepass_bp.route('/milestones/<int:id>/delete', methods=['POST'])
def delete_milestone(id):
    reward = RevenueReward.query.get_or_404(id)
    db.session.delete(reward)
    db.session.commit()
    flash('Revenue milestone deleted.', 'info')
    return redirect(url_for('battlepass.manage_milestones'))
