from flask import Blueprint, render_template
from models import db, BossFight, BossFightHistory, ActivityLog, WinsLog

boss_bp = Blueprint('boss', __name__)


@boss_bp.route('/boss')
def index():
    current_boss = BossFight.get_current_boss()
    
    progress_percent = 0
    if current_boss and current_boss.target_value > 0:
        progress_percent = min(100, int((current_boss.progress_value / current_boss.target_value) * 100))
    
    past_bosses = BossFight.query.filter(
        BossFight.month != BossFight.get_current_month()
    ).order_by(BossFight.month.desc()).limit(12).all()
    
    return render_template('boss/index.html',
                         current_boss=current_boss,
                         progress_percent=progress_percent,
                         past_bosses=past_bosses)


def update_boss_progress(boss_type, increment=1):
    current_boss = BossFight.get_current_boss()
    
    if current_boss and current_boss.boss_type == boss_type and not current_boss.is_completed:
        current_boss.progress_value += increment
        db.session.commit()
        
        if current_boss.check_completion():
            from flask import flash
            flash(f'Boss Defeated! +{current_boss.reward_tokens} tokens!', 'success')
            ActivityLog.log_activity('boss_defeated', f'Boss defeated: {current_boss.description}', current_boss.id, 'boss')
            WinsLog.log_win(
                title='Boss Defeated!',
                description=f'Defeated the monthly boss: {current_boss.description}',
                xp_value=0,
                token_value=current_boss.reward_tokens
            )
            return True
    return False
