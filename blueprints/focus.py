from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
from db_supabase import UserSettings, UserStats, UserTokens, FocusSession, ActivityLog, XPLog, get_supabase
import timezone as tz

focus_bp = Blueprint('focus', __name__, url_prefix='/focus')

@focus_bp.route('/start', methods=['POST'])
def start_timer():
    duration = request.form.get('duration', type=int, default=25)
    if duration not in [25, 30, 45, 60]:
        duration = 25
    
    settings = UserSettings.get_settings()
    
    if getattr(settings, 'focus_timer_active', False):
        return jsonify({'error': 'Timer already active'}), 400
    
    end_time = tz.now() + timedelta(minutes=duration)
    
    UserSettings.update_by_id(settings.id, {
        'focus_timer_active': True,
        'focus_timer_end': end_time.isoformat(),
        'focus_timer_length': duration
    })
    
    session = FocusSession.insert({
        'start_time': tz.now_iso(),
        'duration_minutes': duration,
        'completed': False
    })
    
    ActivityLog.log_activity('focus_started', f'Started {duration}-minute focus session')
    
    return jsonify({
        'success': True,
        'end_time': end_time.isoformat(),
        'duration': duration,
        'session_id': session.id
    })

@focus_bp.route('/cancel', methods=['POST'])
def cancel_timer():
    settings = UserSettings.get_settings()
    
    if not getattr(settings, 'focus_timer_active', False):
        return jsonify({'error': 'No active timer'}), 400
    
    client = get_supabase()
    result = client.table('focus_sessions').select('*').eq('completed', False).order('id', desc=True).limit(1).execute()
    if result.data:
        FocusSession.delete_by_id(result.data[0]['id'])
    
    UserSettings.update_by_id(settings.id, {
        'focus_timer_active': False,
        'focus_timer_end': None,
        'focus_timer_length': None
    })
    
    ActivityLog.log_activity('focus_cancelled', 'Cancelled focus session')
    
    return jsonify({'success': True})

@focus_bp.route('/check', methods=['GET'])
def check_timer():
    settings = UserSettings.get_settings()
    
    if not getattr(settings, 'focus_timer_active', False):
        return jsonify({
            'active': False,
            'remaining_seconds': 0
        })
    
    now = tz.now()
    focus_end = getattr(settings, 'focus_timer_end', None)
    
    if focus_end:
        if isinstance(focus_end, str):
            try:
                focus_end = datetime.fromisoformat(focus_end.replace('Z', '+00:00').replace('+00:00', ''))
            except:
                focus_end = None
    
    if focus_end and now >= focus_end:
        return complete_session_internal(settings)
    
    remaining = (focus_end - now).total_seconds() if focus_end else 0
    
    return jsonify({
        'active': True,
        'remaining_seconds': max(0, int(remaining)),
        'duration': getattr(settings, 'focus_timer_length', 25),
        'end_time': getattr(settings, 'focus_timer_end', None)
    })

@focus_bp.route('/complete', methods=['POST'])
def complete_timer():
    settings = UserSettings.get_settings()
    
    if not getattr(settings, 'focus_timer_active', False):
        return jsonify({'error': 'No active timer'}), 400
    
    return complete_session_internal(settings)

def complete_session_internal(settings):
    client = get_supabase()
    result = client.table('focus_sessions').select('*').eq('completed', False).order('id', desc=True).limit(1).execute()
    
    if result.data:
        session = result.data[0]
        FocusSession.update_by_id(session['id'], {
            'completed': True,
            'end_time': tz.now_iso()
        })
    
    duration = getattr(settings, 'focus_timer_length', 25) or 25
    
    UserSettings.update_by_id(settings.id, {
        'focus_timer_active': False,
        'focus_timer_end': None,
        'focus_timer_length': None
    })
    
    UserTokens.add_tokens(3, f'Focus session completed ({duration} min)')
    
    stats = UserStats.get_stats()
    new_xp = (getattr(stats, 'current_xp', 0) or 0) + 5
    UserStats.update_by_id(stats.id, {'current_xp': new_xp})
    XPLog.insert({'amount': 5, 'reason': f'Focus session completed ({duration} min)'})
    
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
    
    if not getattr(settings, 'focus_timer_active', False):
        return jsonify({
            'active': False
        })
    
    now = tz.now()
    focus_end = getattr(settings, 'focus_timer_end', None)
    
    if focus_end:
        if isinstance(focus_end, str):
            focus_end = tz.parse_datetime_to_local(focus_end)
    
    if focus_end and now >= focus_end:
        remaining = 0
    else:
        remaining = (focus_end - now).total_seconds() if focus_end else 0
    
    return jsonify({
        'active': True,
        'remaining_seconds': max(0, int(remaining)),
        'duration': getattr(settings, 'focus_timer_length', 25),
        'end_time': getattr(settings, 'focus_timer_end', None)
    })

@focus_bp.route('/stats', methods=['GET'])
def get_stats():
    total_sessions = FocusSession.count({'completed': True})
    
    sessions = FocusSession.query_filter({'completed': True})
    total_minutes = sum(getattr(s, 'duration_minutes', 0) or 0 for s in sessions)
    
    today = tz.today().isoformat()
    client = get_supabase()
    result = client.table('focus_sessions').select('*').gte('start_time', f'{today}T00:00:00').eq('completed', True).execute()
    today_sessions = len(result.data)
    
    return jsonify({
        'total_sessions': total_sessions,
        'total_minutes': total_minutes,
        'today_sessions': today_sessions
    })
