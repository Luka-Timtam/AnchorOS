from flask import Blueprint, render_template, flash
from db_supabase import BossBattle, ActivityLog, WinsLog, UserTokens, get_supabase
from datetime import date

boss_bp = Blueprint('boss', __name__)


def get_current_month():
    return date.today().strftime('%Y-%m')


@boss_bp.route('/boss')
def index():
    current_boss = BossBattle.get_current_battle()
    if not current_boss:
        current_boss = BossBattle.create_current_battle()
    
    progress_percent = 0
    if current_boss:
        target = getattr(current_boss, 'target_value', 0) or 0
        progress = getattr(current_boss, 'progress_value', 0) or 0
        if target > 0:
            progress_percent = min(100, int((progress / target) * 100))
    
    current_month = get_current_month()
    client = get_supabase()
    result = client.table('boss_fights').select('*').neq('month', current_month).order('month', desc=True).limit(12).execute()
    past_bosses = [BossBattle._parse_row(row) for row in result.data]
    
    return render_template('boss/index.html',
                         current_boss=current_boss,
                         progress_percent=progress_percent,
                         past_bosses=past_bosses)


def update_boss_progress(boss_type, increment=1):
    current_boss = BossBattle.get_current_battle()
    
    if not current_boss:
        return False
    
    current_boss_type = getattr(current_boss, 'boss_type', '')
    if current_boss_type != boss_type:
        return False
    
    is_completed = getattr(current_boss, 'is_completed', False)
    if is_completed:
        return False
    
    progress_value = (getattr(current_boss, 'progress_value', 0) or 0) + increment
    target_value = getattr(current_boss, 'target_value', 0) or 0
    
    is_now_completed = progress_value >= target_value and target_value > 0
    
    update_data = {'progress_value': progress_value}
    if is_now_completed:
        update_data['is_completed'] = True
    
    BossBattle.update_by_id(current_boss.id, update_data)
    
    if is_now_completed:
        reward_tokens = getattr(current_boss, 'reward_tokens', 0) or 0
        description = getattr(current_boss, 'description', 'Monthly Boss')
        
        UserTokens.add_tokens(reward_tokens, f'Boss completed: {description}')
        
        flash(f'Boss Defeated! +{reward_tokens} tokens!', 'success')
        ActivityLog.log_activity('boss_defeated', f'Boss defeated: {description}', current_boss.id, 'boss')
        WinsLog.insert({
            'title': 'Boss Defeated!',
            'description': f'Defeated the monthly boss: {description}',
            'xp_value': 0,
            'token_value': reward_tokens
        })
        return True
    
    return False
