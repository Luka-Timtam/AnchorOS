from flask import Blueprint, render_template
from models import db, DailyMission, UserTokens
from datetime import date, timedelta

missions_bp = Blueprint('missions', __name__, url_prefix='/missions')


@missions_bp.route('/')
def index():
    today = date.today()
    
    mission = DailyMission.get_today_mission()
    
    mission.check_completion()
    
    progress_pct = 0
    if mission.target_count > 0:
        progress_pct = min(100, int((mission.progress_count / mission.target_count) * 100))
    
    if mission.is_completed:
        status = 'Completed'
    elif mission.mission_date < today:
        status = 'Expired'
    else:
        status = 'In Progress'
    
    week_ago = today - timedelta(days=7)
    past_missions = DailyMission.query.filter(
        DailyMission.mission_date >= week_ago,
        DailyMission.mission_date < today
    ).order_by(DailyMission.mission_date.desc()).all()
    
    token_balance = UserTokens.get_balance()
    
    return render_template('missions/index.html',
        mission=mission,
        progress_pct=progress_pct,
        status=status,
        past_missions=past_missions,
        token_balance=token_balance
    )
