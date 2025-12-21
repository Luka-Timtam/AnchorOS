from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import OutreachLog, Lead, ActivityLog, get_supabase
from datetime import datetime, date, timedelta
from blueprints.gamification import add_xp, update_outreach_streak, XP_RULES, TOKEN_RULES, add_tokens, update_mission_progress
from blueprints.boss import update_boss_progress

outreach_bp = Blueprint('outreach', __name__, url_prefix='/outreach')

def parse_date(date_str):
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)

@outreach_bp.route('/')
def index():
    today = date.today()
    week_start = get_week_start(today)
    month_start = get_month_start(today)
    
    client = get_supabase()
    
    today_result = client.table('outreach_logs').select('id', count='exact').eq('date', today.isoformat()).execute()
    outreach_today = today_result.count if today_result.count else len(today_result.data)
    
    week_result = client.table('outreach_logs').select('id', count='exact').gte('date', week_start.isoformat()).execute()
    outreach_week = week_result.count if week_result.count else len(week_result.data)
    
    month_result = client.table('outreach_logs').select('id', count='exact').gte('date', month_start.isoformat()).execute()
    outreach_month = month_result.count if month_result.count else len(month_result.data)
    
    type_filter = request.args.get('type', '')
    outcome_filter = request.args.get('outcome', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = client.table('outreach_logs').select('*')
    
    if type_filter:
        query = query.eq('type', type_filter)
    if outcome_filter:
        query = query.eq('outcome', outcome_filter)
    if date_from:
        query = query.gte('date', date_from)
    if date_to:
        query = query.lte('date', date_to)
    
    result = query.order('date', desc=True).order('created_at', desc=True).execute()
    logs = [OutreachLog._parse_row(row) for row in result.data]
    
    leads = Lead.query_all(order_by='name')
    
    return render_template('outreach/index.html',
        logs=logs,
        leads=leads,
        types=OutreachLog.type_choices(),
        outcomes=OutreachLog.outcome_choices(),
        outreach_today=outreach_today,
        outreach_week=outreach_week,
        outreach_month=outreach_month,
        current_type=type_filter,
        current_outcome=outcome_filter,
        current_date_from=date_from,
        current_date_to=date_to,
        today=today.isoformat()
    )

@outreach_bp.route('/create', methods=['POST'])
def create():
    log_date = parse_date(request.form.get('date')) or date.today()
    lead_id = request.form.get('lead_id')
    lead_id = int(lead_id) if lead_id else None
    
    is_cold_lead_revival = False
    lead_name = 'Unknown'
    
    if lead_id:
        lead = Lead.get_by_id(lead_id)
        if lead:
            lead_name = getattr(lead, 'name', 'Unknown')
            last_contacted = getattr(lead, 'last_contacted_at', None)
            if last_contacted:
                from db_supabase import parse_datetime
                last_dt = parse_datetime(last_contacted)
                if last_dt and last_dt < datetime.utcnow() - timedelta(days=30):
                    is_cold_lead_revival = True
            else:
                is_cold_lead_revival = True
            
            Lead.update_by_id(lead_id, {'last_contacted_at': datetime.utcnow().isoformat()})
    
    log = OutreachLog.insert({
        'date': log_date.isoformat(),
        'type': request.form.get('type', 'email'),
        'lead_id': lead_id,
        'outcome': request.form.get('outcome', 'contacted'),
        'notes': request.form.get('notes')
    })
    
    add_xp(XP_RULES['outreach_log'], 'Outreach logged')
    add_tokens(TOKEN_RULES['outreach_log'], 'Outreach logged')
    update_outreach_streak()
    update_mission_progress('outreach')
    update_boss_progress('outreach')
    
    if is_cold_lead_revival:
        update_boss_progress('revive_leads')
    
    ActivityLog.log_activity('outreach_logged', f'Logged {log.type} outreach for {lead_name}', 
                            lead_id, 'lead' if lead_id else None)
    
    flash('Outreach logged successfully! +5 XP, +1 token', 'success')
    
    return redirect(request.form.get('redirect_url') or url_for('outreach.index'))

@outreach_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    log = OutreachLog.get_by_id(id)
    if not log:
        abort(404)
    OutreachLog.delete_by_id(id)
    flash('Outreach log deleted!', 'success')
    return redirect(url_for('outreach.index'))
