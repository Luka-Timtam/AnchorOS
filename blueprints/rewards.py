from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import UserTokens, TokenTransaction, RewardItem
from datetime import datetime

rewards_bp = Blueprint('rewards', __name__, url_prefix='/rewards')


@rewards_bp.route('/')
def index():
    RewardItem.seed_defaults()
    
    token_balance = UserTokens.get_balance()
    rewards = RewardItem.query_filter({'is_active': True}, order_by='cost')
    
    recent_transactions = TokenTransaction.query_all(order_by='created_at', order_desc=True, limit=20)
    
    redeemed = [t for t in recent_transactions if (getattr(t, 'amount', 0) or 0) < 0]
    
    return render_template('rewards/index.html',
        token_balance=token_balance,
        rewards=rewards,
        recent_transactions=recent_transactions,
        redeemed=redeemed
    )


@rewards_bp.route('/redeem/<int:id>', methods=['POST'])
def redeem(id):
    reward = RewardItem.get_by_id(id)
    if not reward:
        abort(404)
    
    if not getattr(reward, 'is_active', True):
        flash('This reward is no longer available.', 'error')
        return redirect(url_for('rewards.index'))
    
    token_balance = UserTokens.get_balance()
    cost = getattr(reward, 'cost', 0) or 0
    
    if token_balance < cost:
        flash(f'Not enough tokens. You need {cost} but have {token_balance}.', 'error')
        return redirect(url_for('rewards.index'))
    
    success = UserTokens.spend_tokens(cost, f"Redeemed: {getattr(reward, 'name', 'Reward')}")
    
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
    
    RewardItem.insert({
        'name': name,
        'cost': cost,
        'description': description,
        'is_active': True
    })
    
    flash(f'Reward "{name}" added!', 'success')
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/<int:id>/toggle', methods=['POST'])
def toggle_reward(id):
    reward = RewardItem.get_by_id(id)
    if not reward:
        abort(404)
    is_active = not getattr(reward, 'is_active', True)
    RewardItem.update_by_id(id, {'is_active': is_active})
    
    status = "enabled" if is_active else "disabled"
    flash(f'Reward "{reward.name}" {status}.', 'success')
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/<int:id>/edit', methods=['POST'])
def edit_reward(id):
    reward = RewardItem.get_by_id(id)
    if not reward:
        abort(404)
    
    name = request.form.get('name', '').strip()
    cost = request.form.get('cost', type=int)
    description = request.form.get('description', '').strip()
    
    if not name or not cost or cost <= 0:
        flash('Please provide a valid name and cost.', 'error')
        return redirect(url_for('rewards.index'))
    
    RewardItem.update_by_id(id, {
        'name': name,
        'cost': cost,
        'description': description
    })
    
    flash(f'Reward "{name}" updated!', 'success')
    return redirect(url_for('rewards.index'))


@rewards_bp.route('/<int:id>/delete', methods=['POST'])
def delete_reward(id):
    reward = RewardItem.get_by_id(id)
    if not reward:
        abort(404)
    RewardItem.delete_by_id(id)
    
    flash('Reward deleted.', 'success')
    return redirect(url_for('rewards.index'))
