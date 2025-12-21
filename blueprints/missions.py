from flask import Blueprint, render_template
from db_supabase import DailyMission, UserTokens, get_supabase
from datetime import date, timedelta

missions_bp = Blueprint('missions', __name__, url_prefix='/missions')


@missions_bp.route('/')
def index():
    today = date.today()
    
    mission = DailyMission.get_today_mission()
    if not mission:
        mission = DailyMission.create_today_mission()
    
    target = getattr(mission, 'target_count', 0) or 0
    progress = getattr(mission, 'progress_count', 0) or 0
    is_completed = getattr(mission, 'is_completed', False)
    mission_date = getattr(mission, 'mission_date', today.isoformat())
    
    if isinstance(mission_date, str):
        mission_date_obj = date.fromisoformat(mission_date.split('T')[0])
    else:
        mission_date_obj = mission_date
    
    if not is_completed and progress >= target and target > 0:
        reward_tokens = getattr(mission, 'reward_tokens', 0) or 0
        DailyMission.update_by_id(mission.id, {'is_completed': True})
        UserTokens.add_tokens(reward_tokens, f'Mission completed')
        is_completed = True
    
    progress_pct = 0
    if target > 0:
        progress_pct = min(100, int((progress / target) * 100))
    
    if is_completed:
        status = 'Completed'
    elif mission_date_obj < today:
        status = 'Expired'
    else:
        status = 'In Progress'
    
    week_ago = today - timedelta(days=7)
    client = get_supabase()
    result = client.table('daily_missions').select('*').gte('mission_date', week_ago.isoformat()).lt('mission_date', today.isoformat()).order('mission_date', desc=True).execute()
    past_missions = [DailyMission._parse_row(row) for row in result.data]
    
    token_balance = UserTokens.get_balance()
    
    return render_template('missions/index.html',
        mission=mission,
        progress_pct=progress_pct,
        status=status,
        past_missions=past_missions,
        token_balance=token_balance
    )
