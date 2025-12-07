from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, UserSettings, ActivityLog
from datetime import date, timedelta

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
def index():
    settings = UserSettings.get_settings()
    settings.check_pause_expiry()
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/pause/activate', methods=['POST'])
def pause_activate():
    settings = UserSettings.get_settings()
    
    try:
        duration = int(request.form.get('duration', 1))
        if duration < 1 or duration > 14:
            flash('Pause duration must be between 1 and 14 days.', 'error')
            return redirect(url_for('settings.index'))
    except ValueError:
        flash('Invalid duration value.', 'error')
        return redirect(url_for('settings.index'))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('A reason is required to activate pause mode.', 'error')
        return redirect(url_for('settings.index'))
    
    settings.pause_active = True
    settings.pause_start = date.today()
    settings.pause_end = date.today() + timedelta(days=duration)
    settings.pause_reason = reason
    db.session.commit()
    
    ActivityLog.log_activity('pause_activated', f'Pause Mode activated until {settings.pause_end.strftime("%b %d, %Y")}')
    
    flash(f'Pause mode activated for {duration} days.', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/pause/end', methods=['POST'])
def pause_end():
    from models import UserStats
    settings = UserSettings.get_settings()
    
    stats = UserStats.query.first()
    if stats and stats.current_outreach_streak_days > 0:
        stats.last_outreach_date = date.today() - timedelta(days=1)
    
    settings.pause_active = False
    settings.pause_start = None
    settings.pause_end = None
    settings.pause_reason = None
    db.session.commit()
    
    ActivityLog.log_activity('pause_ended', 'Pause Mode ended')
    
    flash('Pause mode ended.', 'success')
    return redirect(url_for('settings.index'))
