from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
from models import db, UserSettings, UserStats, UserTokens, FocusSession, ActivityLog, XPLog

focus_bp = Blueprint('focus', __name__, url_prefix='/focus')

@focus_bp.route('/start', methods=['POST'])
def start_timer():
    duration = request.form.get('duration', type=int, default=25)
    if duration not in [25, 30, 45, 60]:
        duration = 25
    
    settings = UserSettings.get_settings()
    
    if settings.focus_timer_active:
        return jsonify({'error': 'Timer already active'}), 400
    
    settings.focus_timer_active = True
    settings.focus_timer_end = datetime.utcnow() + timedelta(minutes=duration)
    settings.focus_timer_length = duration
    
    session = FocusSession(
        start_time=datetime.utcnow(),
        duration_minutes=duration,
        completed=False
    )
    db.session.add(session)
    db.session.commit()
    
    ActivityLog.log_activity('focus_started', f'Started {duration}-minute focus session')
    
    return jsonify({
        'success': True,
        'end_time': settings.focus_timer_end.isoformat(),
        'duration': duration,
        'session_id': session.id
    })

@focus_bp.route('/cancel', methods=['POST'])
def cancel_timer():
    settings = UserSettings.get_settings()
    
    if not settings.focus_timer_active:
        return jsonify({'error': 'No active timer'}), 400
    
    active_session = FocusSession.query.filter_by(completed=False).order_by(FocusSession.id.desc()).first()
    if active_session:
        db.session.delete(active_session)
    
    settings.focus_timer_active = False
    settings.focus_timer_end = None
    settings.focus_timer_length = None
    db.session.commit()
    
    ActivityLog.log_activity('focus_cancelled', 'Cancelled focus session')
    
    return jsonify({'success': True})

@focus_bp.route('/check', methods=['GET'])
def check_timer():
    settings = UserSettings.get_settings()
    
    if not settings.focus_timer_active:
        return jsonify({
            'active': False,
            'remaining_seconds': 0
        })
    
    now = datetime.utcnow()
    if settings.focus_timer_end and now >= settings.focus_timer_end:
        return complete_session_internal(settings)
    
    remaining = (settings.focus_timer_end - now).total_seconds() if settings.focus_timer_end else 0
    
    return jsonify({
        'active': True,
        'remaining_seconds': max(0, int(remaining)),
        'duration': settings.focus_timer_length,
        'end_time': settings.focus_timer_end.isoformat() if settings.focus_timer_end else None
    })

@focus_bp.route('/complete', methods=['POST'])
def complete_timer():
    settings = UserSettings.get_settings()
    
    if not settings.focus_timer_active:
        return jsonify({'error': 'No active timer'}), 400
    
    return complete_session_internal(settings)

def complete_session_internal(settings):
    active_session = FocusSession.query.filter_by(completed=False).order_by(FocusSession.id.desc()).first()
    
    if active_session:
        active_session.completed = True
        active_session.end_time = datetime.utcnow()
    
    duration = settings.focus_timer_length or 25
    
    settings.focus_timer_active = False
    settings.focus_timer_end = None
    settings.focus_timer_length = None
    
    UserTokens.add_tokens(3, f'Focus session completed ({duration} min)')
    
    stats = UserStats.get_stats()
    stats.current_xp += 5
    xp_log = XPLog(amount=5, reason=f'Focus session completed ({duration} min)')
    db.session.add(xp_log)
    
    db.session.commit()
    
    ActivityLog.log_activity('focus_completed', f'Completed {duration}-minute focus session (+3 tokens, +5 XP)')
    
    return jsonify({
        'active': False,
        'completed': True,
        'remaining_seconds': 0,
        'tokens_earned': 3,
        'xp_earned': 5,
        'message': f'Focus session complete! +3 tokens, +5 XP'
    })

@focus_bp.route('/status', methods=['GET'])
def get_status():
    settings = UserSettings.get_settings()
    
    if not settings.focus_timer_active:
        return jsonify({
            'active': False
        })
    
    now = datetime.utcnow()
    if settings.focus_timer_end and now >= settings.focus_timer_end:
        remaining = 0
    else:
        remaining = (settings.focus_timer_end - now).total_seconds() if settings.focus_timer_end else 0
    
    return jsonify({
        'active': True,
        'remaining_seconds': max(0, int(remaining)),
        'duration': settings.focus_timer_length,
        'end_time': settings.focus_timer_end.isoformat() if settings.focus_timer_end else None
    })

@focus_bp.route('/stats', methods=['GET'])
def get_stats():
    total_sessions = FocusSession.get_completed_count()
    total_minutes = FocusSession.get_total_focus_minutes()
    today_sessions = len([s for s in FocusSession.get_today_sessions() if s.completed])
    
    return jsonify({
        'total_sessions': total_sessions,
        'total_minutes': total_minutes,
        'today_sessions': today_sessions
    })
