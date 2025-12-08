from flask import Blueprint, render_template, request, jsonify
from models import db, Lead, Client, OutreachLog, UserSettings, UserStats, UserTokens, DailyMission, BossFight, ActivityLog
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
from decimal import Decimal
from blueprints.gamification import calculate_consistency_score
import json

dashboard_bp = Blueprint('dashboard', __name__)

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)

@dashboard_bp.route('/')
def index():
    today = date.today()
    week_start = get_week_start(today)
    month_start = get_month_start(today)
    
    lead_counts = db.session.query(
        Lead.status, func.count(Lead.id)
    ).group_by(Lead.status).all()
    lead_counts_dict = {status: count for status, count in lead_counts}
    
    new_leads_week = Lead.query.filter(
        func.date(Lead.created_at) >= week_start
    ).count()
    
    new_leads_month = Lead.query.filter(
        func.date(Lead.created_at) >= month_start
    ).count()
    
    outreach_today = OutreachLog.query.filter(
        OutreachLog.date == today
    ).count()
    
    outreach_week = OutreachLog.query.filter(
        OutreachLog.date >= week_start
    ).count()
    
    outreach_month = OutreachLog.query.filter(
        OutreachLog.date >= month_start
    ).count()
    
    new_clients_month = Client.query.filter(
        Client.start_date >= month_start
    ).count()
    
    project_revenue_month = db.session.query(
        func.coalesce(func.sum(Client.amount_charged), 0)
    ).filter(
        Client.start_date >= month_start
    ).scalar() or Decimal('0')
    
    hosting_mrr = db.session.query(
        func.coalesce(func.sum(Client.monthly_hosting_fee), 0)
    ).filter(Client.hosting_active == True).scalar() or Decimal('0')
    
    saas_mrr = db.session.query(
        func.coalesce(func.sum(Client.monthly_saas_fee), 0)
    ).filter(Client.saas_active == True).scalar() or Decimal('0')
    
    total_mrr = hosting_mrr + saas_mrr
    
    last_3_months_revenue = []
    for i in range(1, 4):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        m_end = (m_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        rev = db.session.query(
            func.coalesce(func.sum(Client.amount_charged), 0)
        ).filter(
            and_(Client.start_date >= m_start, Client.start_date <= m_end)
        ).scalar() or Decimal('0')
        last_3_months_revenue.append(float(rev))
    
    avg_project_revenue = sum(last_3_months_revenue) / 3 if last_3_months_revenue else 0
    forecast_monthly = float(total_mrr) + avg_project_revenue
    forecast_3_months = forecast_monthly * 3
    
    outreach_weekly_data = []
    deals_weekly_data = []
    week_labels = []
    
    for i in range(11, -1, -1):
        w_start = get_week_start(today) - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        
        week_labels.append(w_start.strftime('%b %d'))
        
        outreach_count = OutreachLog.query.filter(
            and_(OutreachLog.date >= w_start, OutreachLog.date <= w_end)
        ).count()
        outreach_weekly_data.append(outreach_count)
        
        deals_count = Lead.query.filter(
            and_(
                Lead.status == 'closed_won',
                func.date(Lead.updated_at) >= w_start,
                func.date(Lead.updated_at) <= w_end
            )
        ).count()
        deals_weekly_data.append(deals_count)
    
    settings = UserSettings.get_settings()
    
    user_stats = UserStats.get_stats()
    consistency = calculate_consistency_score()
    
    followup_today = Lead.query.filter(
        Lead.next_action_date == today,
        Lead.status.notin_(['closed_won', 'closed_lost']),
        Lead.converted_at.is_(None)
    ).count()
    
    followup_overdue = Lead.query.filter(
        Lead.next_action_date < today,
        Lead.status.notin_(['closed_won', 'closed_lost']),
        Lead.converted_at.is_(None)
    ).count()
    
    monthly_revenue_data = []
    monthly_mrr_data = []
    month_labels = []
    
    for i in range(11, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
        month_labels.append(m_start.strftime('%b %Y'))
        
        month_revenue = db.session.query(
            func.coalesce(func.sum(Client.amount_charged), 0)
        ).filter(
            and_(Client.start_date >= m_start, Client.start_date <= m_end)
        ).scalar() or Decimal('0')
        monthly_revenue_data.append(float(month_revenue))
        
        hosting_at_month = db.session.query(
            func.coalesce(func.sum(Client.monthly_hosting_fee), 0)
        ).filter(
            Client.hosting_active == True,
            Client.start_date <= m_end
        ).scalar() or Decimal('0')
        
        saas_at_month = db.session.query(
            func.coalesce(func.sum(Client.monthly_saas_fee), 0)
        ).filter(
            Client.saas_active == True,
            Client.start_date <= m_end
        ).scalar() or Decimal('0')
        
        monthly_mrr_data.append(float(hosting_at_month + saas_at_month))
    
    token_balance = UserTokens.get_balance()
    
    daily_mission = DailyMission.get_today_mission()
    mission_progress_pct = 0
    if daily_mission.target_count > 0:
        mission_progress_pct = min(100, int((daily_mission.progress_count / daily_mission.target_count) * 100))
    
    current_boss = BossFight.get_current_boss()
    boss_progress_pct = 0
    if current_boss and current_boss.target_value > 0:
        boss_progress_pct = min(100, int((current_boss.progress_value / current_boss.target_value) * 100))
    
    pause_active = settings.is_paused()
    pause_end = settings.pause_end
    
    recent_activities = ActivityLog.get_recent(5)
    
    deals_closed_today = Lead.query.filter(
        Lead.closed_at.isnot(None),
        func.date(Lead.closed_at) == today,
        Lead.status.in_(['closed_won', 'closed_lost'])
    ).all()
    
    ordered_widgets = settings.get_ordered_active_widgets()
    active_widgets = settings.get_active_widgets()
    widget_definitions = UserSettings.WIDGET_DEFINITIONS
    
    return render_template('dashboard.html',
        settings=settings,
        user_stats=user_stats,
        consistency_score=consistency['score'],
        followup_today=followup_today,
        followup_overdue=followup_overdue,
        lead_counts=lead_counts_dict,
        lead_statuses=Lead.status_choices(),
        new_leads_week=new_leads_week,
        new_leads_month=new_leads_month,
        outreach_today=outreach_today,
        outreach_week=outreach_week,
        outreach_month=outreach_month,
        new_clients_month=new_clients_month,
        project_revenue_month=float(project_revenue_month),
        hosting_mrr=float(hosting_mrr),
        saas_mrr=float(saas_mrr),
        total_mrr=float(total_mrr),
        forecast_monthly=forecast_monthly,
        forecast_3_months=forecast_3_months,
        week_labels=week_labels,
        outreach_weekly_data=outreach_weekly_data,
        deals_weekly_data=deals_weekly_data,
        month_labels=month_labels,
        monthly_revenue_data=monthly_revenue_data,
        monthly_mrr_data=monthly_mrr_data,
        token_balance=token_balance,
        daily_mission=daily_mission,
        mission_progress_pct=mission_progress_pct,
        current_boss=current_boss,
        boss_progress_pct=boss_progress_pct,
        pause_active=pause_active,
        pause_end=pause_end,
        recent_activities=recent_activities,
        deals_closed_today=deals_closed_today,
        ordered_widgets=ordered_widgets,
        active_widgets=active_widgets,
        widget_definitions=widget_definitions
    )


@dashboard_bp.route('/widgets/save-layout', methods=['POST'])
def save_widget_layout():
    try:
        data = request.get_json()
        order = data.get('order', [])
        
        if not isinstance(order, list):
            return jsonify({'success': False, 'error': 'Invalid order format'}), 400
        
        valid_widgets = list(UserSettings.WIDGET_DEFINITIONS.keys())
        order = [w for w in order if w in valid_widgets]
        
        settings = UserSettings.get_settings()
        settings.set_dashboard_layout(order)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/widgets/save-active', methods=['POST'])
def save_active_widgets():
    try:
        data = request.get_json()
        active = data.get('active', {})
        
        if not isinstance(active, dict):
            return jsonify({'success': False, 'error': 'Invalid format'}), 400
        
        valid_widgets = list(UserSettings.WIDGET_DEFINITIONS.keys())
        active = {k: bool(v) for k, v in active.items() if k in valid_widgets}
        
        settings = UserSettings.get_settings()
        settings.set_active_widgets(active)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/widgets/reset-layout', methods=['POST'])
def reset_widget_layout():
    try:
        settings = UserSettings.get_settings()
        settings.dashboard_layout = None
        settings.dashboard_active_widgets = None
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/widgets/get-config')
def get_widget_config():
    settings = UserSettings.get_settings()
    return jsonify({
        'order': settings.get_dashboard_layout(),
        'active': settings.get_active_widgets(),
        'definitions': UserSettings.WIDGET_DEFINITIONS
    })
