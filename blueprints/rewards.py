from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, UserTokens, TokenTransaction, RewardItem
from datetime import datetime

rewards_bp = Blueprint('rewards', __name__, url_prefix='/rewards')


@rewards_bp.route('/')
def index():
    RewardItem.seed_defaults()
    
    token_balance = UserTokens.get_balance()
    rewards = RewardItem.query.filter_by(is_active=True).order_by(RewardItem.cost).all()
    
    recent_transactions = TokenTransaction.query.order_by(
        TokenTransaction.created_at.desc()
    ).limit(20).all()
    
    redeemed = [t for t in recent_transactions if t.amount < 0]
    
    return render_template('rewards/index.html',
        token_balance=token_balance,
        rewards=rewards,
        recent_transactions=recent_transactions,
        redeemed=redeemed
    )


@rewards_bp.route('/redeem/<int:id>', methods=['POST'])
def redeem(id):
    reward = RewardItem.query.get_or_404(id)
    
    if not reward.is_active:
        flash('This reward is no longer available.', 'error')
        return redirect(url_for('rewards.index'))
    
    token_balance = UserTokens.get_balance()
    
    if token_balance < reward.cost:
        flash(f'Not enough tokens. You need {reward.cost} but have {token_balance}.', 'error')
        return redirect(url_for('rewards.index'))
    
    success = UserTokens.spend_tokens(reward.cost, f"Redeemed: {reward.name}")
    
    if success:
        flash(f'Congratulations! You redeemed "{reward.name}"!', 'success')
    else:
        flash('Failed to redeem reward. Please try again.', 'error')
    
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/add', methods=['POST'])
def add_reward():
    name = request.form.get('name', '').strip()
    cost = request.form.get('cost', type=int)
    description = request.form.get('description', '').strip()
    
    if not name or not cost or cost <= 0:
        flash('Please provide a valid name and cost.', 'error')
        return redirect(url_for('rewards.index'))
    
    reward = RewardItem(
        name=name,
        cost=cost,
        description=description
    )
    db.session.add(reward)
    db.session.commit()
    
    flash(f'Reward "{name}" added!', 'success')
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/<int:id>/toggle', methods=['POST'])
def toggle_reward(id):
    reward = RewardItem.query.get_or_404(id)
    reward.is_active = not reward.is_active
    db.session.commit()
    
    status = "enabled" if reward.is_active else "disabled"
    flash(f'Reward "{reward.name}" {status}.', 'success')
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/<int:id>/delete', methods=['POST'])
def delete_reward(id):
    reward = RewardItem.query.get_or_404(id)
    db.session.delete(reward)
    db.session.commit()
    
    flash('Reward deleted.', 'success')
    return redirect(url_for('rewards.index'))
