from flask import Blueprint, render_template
from db_supabase import DailyMission, UserTokens, get_supabase
from datetime import date, timedelta
import timezone as tz

missions_bp = Blueprint('missions', __name__, url_prefix='/missions')


@missions_bp.route('/')
def index():
    today = tz.today()
    is_weekend = today.weekday() >= 5  # Saturday=5, Sunday=6
    
    mission = DailyMission.get_today_mission()
    if not mission and not is_weekend:
        mission = DailyMission.create_today_mission()
    
    # Handle weekend case where there's no mission
    if is_weekend or mission is None:
        token_balance = UserTokens.get_balance()
        
        # Still get past missions for display
        week_ago = today - timedelta(days=7)
        client = get_supabase()
        result = client.table('daily_missions').select('*').gte('mission_date', week_ago.isoformat()).lte('mission_date', today.isoformat()).order('mission_date', desc=True).execute()
        past_missions = []
        if result.data:
            for row in result.data:
                m = DailyMission._parse_row(row)
                mission_date_val = getattr(m, 'mission_date', None)
                if mission_date_val:
                    if isinstance(mission_date_val, str):
                        m.mission_date = date.fromisoformat(mission_date_val.split('T')[0])
                past_missions.append(m)
        
        return render_template('missions/index.html',
            mission=None,
            progress_pct=0,
            status='Weekend',
            past_missions=past_missions,
            token_balance=token_balance,
            is_weekend=True
        )
    
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
    result = client.table('daily_missions').select('*').gte('mission_date', week_ago.isoformat()).lte('mission_date', today.isoformat()).order('mission_date', desc=True).execute()
    past_missions = []
    if result.data:
        for row in result.data:
            mission = DailyMission._parse_row(row)
            # Convert mission_date string to date object for template formatting
            mission_date = getattr(mission, 'mission_date', None)
            if mission_date:
                if isinstance(mission_date, str):
                    mission.mission_date = date.fromisoformat(mission_date.split('T')[0])
                elif hasattr(mission_date, 'date'):
                    # If it's a datetime object, extract the date
                    mission.mission_date = mission_date.date()
            past_missions.append(mission)
    
    token_balance = UserTokens.get_balance()
    
    return render_template('missions/index.html',
        mission=mission,
        progress_pct=progress_pct,
        status=status,
        past_missions=past_missions,
        token_balance=token_balance,
        is_weekend=False
    )
