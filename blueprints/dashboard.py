from flask import Blueprint, render_template, request, jsonify
from db_supabase import (Lead, Client, OutreachLog, UserSettings, UserStats, UserTokens, 
                         DailyMission, BossBattle, ActivityLog, RevenueReward, get_supabase)
from datetime import datetime, date, timedelta
from decimal import Decimal
from blueprints.gamification import calculate_consistency_score
from blueprints.monthly_review import auto_generate_monthly_review_if_needed, get_newly_generated_review
from cache import cache, CACHE_KEY_DASHBOARD_CHARTS, CACHE_KEY_MRR
import timezone as tz
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)


def get_cached_client_stats(clients):
    cached_value, hit = cache.get(CACHE_KEY_MRR)
    if hit:
        logger.debug("[Dashboard] Using cached MRR/client stats")
        return cached_value
    
    today = date.today()
    month_start = get_month_start(today)
    
    new_clients_month = 0
    project_revenue_month = Decimal('0')
    hosting_mrr = Decimal('0')
    saas_mrr = Decimal('0')
    
    for c in clients:
        start_date = getattr(c, 'start_date', '')
        if isinstance(start_date, str) and start_date >= month_start.isoformat():
            new_clients_month += 1
            project_revenue_month += Decimal(str(getattr(c, 'amount_charged', 0) or 0))
        
        if getattr(c, 'hosting_active', False):
            hosting_mrr += Decimal(str(getattr(c, 'monthly_hosting_fee', 0) or 0))
        if getattr(c, 'saas_active', False):
            saas_mrr += Decimal(str(getattr(c, 'monthly_saas_fee', 0) or 0))
    
    last_3_months_revenue = []
    for i in range(1, 4):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        m_end = (m_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        rev = Decimal('0')
        for c in clients:
            start_date = getattr(c, 'start_date', '')
            if isinstance(start_date, str):
                if m_start.isoformat() <= start_date <= m_end.isoformat():
                    rev += Decimal(str(getattr(c, 'amount_charged', 0) or 0))
        last_3_months_revenue.append(float(rev))
    
    avg_project_revenue = sum(last_3_months_revenue) / 3 if last_3_months_revenue else 0
    total_mrr = hosting_mrr + saas_mrr
    forecast_monthly = float(total_mrr) + avg_project_revenue
    forecast_3_months = forecast_monthly * 3
    
    result = {
        'new_clients_month': new_clients_month,
        'project_revenue_month': float(project_revenue_month),
        'hosting_mrr': float(hosting_mrr),
        'saas_mrr': float(saas_mrr),
        'total_mrr': float(total_mrr),
        'forecast_monthly': forecast_monthly,
        'forecast_3_months': forecast_3_months
    }
    
    cache.set(CACHE_KEY_MRR, result, ttl=45)
    logger.debug("[Dashboard] Cached MRR/client stats")
    return result


def get_cached_chart_data(clients):
    cached_value, hit = cache.get(CACHE_KEY_DASHBOARD_CHARTS)
    if hit:
        logger.debug("[Dashboard] Using cached chart data")
        return cached_value
    
    today = date.today()
    
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
        
        month_revenue = Decimal('0')
        hosting_at_month = Decimal('0')
        saas_at_month = Decimal('0')
        
        for c in clients:
            start_date = getattr(c, 'start_date', '')
            if isinstance(start_date, str):
                if m_start.isoformat() <= start_date <= m_end.isoformat():
                    month_revenue += Decimal(str(getattr(c, 'amount_charged', 0) or 0))
                if start_date <= m_end.isoformat():
                    if getattr(c, 'hosting_active', False):
                        hosting_at_month += Decimal(str(getattr(c, 'monthly_hosting_fee', 0) or 0))
                    if getattr(c, 'saas_active', False):
                        saas_at_month += Decimal(str(getattr(c, 'monthly_saas_fee', 0) or 0))
        
        monthly_revenue_data.append(float(month_revenue))
        monthly_mrr_data.append(float(hosting_at_month + saas_at_month))
    
    result = {
        'month_labels': month_labels,
        'monthly_revenue_data': monthly_revenue_data,
        'monthly_mrr_data': monthly_mrr_data
    }
    
    cache.set(CACHE_KEY_DASHBOARD_CHARTS, result, ttl=60)
    logger.debug("[Dashboard] Cached chart data")
    return result

@dashboard_bp.route('/')
def index():
    today = date.today()
    week_start = get_week_start(today)
    month_start = get_month_start(today)
    
    supabase_client = get_supabase()
    
    leads = Lead.query_all()
    lead_counts_dict = {}
    for lead in leads:
        status = getattr(lead, 'status', 'new')
        lead_counts_dict[status] = lead_counts_dict.get(status, 0) + 1
    
    new_leads_week = 0
    new_leads_month = 0
    for lead in leads:
        created = getattr(lead, 'created_at', '')
        if isinstance(created, str):
            created_date = created.split('T')[0]
            if created_date >= week_start.isoformat():
                new_leads_week += 1
            if created_date >= month_start.isoformat():
                new_leads_month += 1
    
    outreach_today_result = supabase_client.table('outreach_logs').select('id', count='exact').eq('date', today.isoformat()).execute()
    outreach_today = outreach_today_result.count if outreach_today_result.count else len(outreach_today_result.data)
    
    outreach_week_result = supabase_client.table('outreach_logs').select('id', count='exact').gte('date', week_start.isoformat()).execute()
    outreach_week = outreach_week_result.count if outreach_week_result.count else len(outreach_week_result.data)
    
    outreach_month_result = supabase_client.table('outreach_logs').select('id', count='exact').gte('date', month_start.isoformat()).execute()
    outreach_month = outreach_month_result.count if outreach_month_result.count else len(outreach_month_result.data)
    
    twelve_weeks_ago = get_week_start(today) - timedelta(weeks=11)
    outreach_result = supabase_client.table('outreach_logs').select('date').gte('date', twelve_weeks_ago.isoformat()).execute()
    
    clients = Client.query_all()
    
    client_stats = get_cached_client_stats(clients)
    new_clients_month = client_stats['new_clients_month']
    project_revenue_month = client_stats['project_revenue_month']
    hosting_mrr = client_stats['hosting_mrr']
    saas_mrr = client_stats['saas_mrr']
    total_mrr = client_stats['total_mrr']
    forecast_monthly = client_stats['forecast_monthly']
    forecast_3_months = client_stats['forecast_3_months']
    
    outreach_weekly_data = []
    deals_weekly_data = []
    week_labels = []
    
    for i in range(11, -1, -1):
        w_start = get_week_start(today) - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        
        week_labels.append(w_start.strftime('%b %d'))
        
        outreach_count = sum(1 for o in outreach_result.data 
                            if w_start.isoformat() <= o.get('date', '') <= w_end.isoformat())
        outreach_weekly_data.append(outreach_count)
        
        deals_count = 0
        for lead in leads:
            if getattr(lead, 'status', '') == 'closed_won':
                updated = getattr(lead, 'updated_at', '')
                if isinstance(updated, str):
                    updated_date = updated.split('T')[0]
                    if w_start.isoformat() <= updated_date <= w_end.isoformat():
                        deals_count += 1
        deals_weekly_data.append(deals_count)
    
    settings = UserSettings.get_settings()
    
    user_stats = UserStats.get_stats()
    consistency = calculate_consistency_score()
    
    followup_today = 0
    followup_overdue = 0
    for lead in leads:
        next_action = getattr(lead, 'next_action_date', None)
        status = getattr(lead, 'status', '')
        converted = getattr(lead, 'converted_at', None)
        if next_action and status not in ['closed_won', 'closed_lost'] and not converted:
            if isinstance(next_action, str):
                next_action = next_action.split('T')[0]
            if next_action == today.isoformat():
                followup_today += 1
            elif next_action < today.isoformat():
                followup_overdue += 1
    
    chart_data = get_cached_chart_data(clients)
    month_labels = chart_data['month_labels']
    monthly_revenue_data = chart_data['monthly_revenue_data']
    monthly_mrr_data = chart_data['monthly_mrr_data']
    
    token_balance = UserTokens.get_balance()
    
    daily_mission = DailyMission.get_today_mission()
    if not daily_mission:
        daily_mission = DailyMission.create_today_mission()
    
    mission_progress_pct = 0
    if daily_mission:
        target = getattr(daily_mission, 'target_count', 0) or 0
        progress = getattr(daily_mission, 'progress_count', 0) or 0
        if target > 0:
            mission_progress_pct = min(100, int((progress / target) * 100))
    
    current_boss = BossBattle.get_current_battle()
    if not current_boss:
        current_boss = BossBattle.create_current_battle()
    
    boss_progress_pct = 0
    if current_boss:
        target = getattr(current_boss, 'target_value', 0) or 0
        progress = getattr(current_boss, 'progress_value', 0) or 0
        if target > 0:
            boss_progress_pct = min(100, int((progress / target) * 100))
    
    pause_active = settings.is_paused()
    pause_end = getattr(settings, 'pause_end', None)
    
    recent_activities = ActivityLog.query_all(order_by='timestamp', order_desc=True, limit=5)
    
    deals_closed_today = []
    for lead in leads:
        closed_at = getattr(lead, 'closed_at', None)
        status = getattr(lead, 'status', '')
        if closed_at and status in ['closed_won', 'closed_lost']:
            if isinstance(closed_at, str):
                closed_date = closed_at.split('T')[0]
                if closed_date == today.isoformat():
                    deals_closed_today.append(lead)
    
    widget_order = settings.get_dashboard_order()
    widget_active = settings.get_dashboard_active()
    widget_names = UserSettings.DEFAULT_WIDGET_NAMES
    
    seven_days_ago = (tz.now() - timedelta(days=7)).isoformat()
    revenue_rewards = RevenueReward.query_all()
    revenue_notifications = []
    for r in revenue_rewards:
        unlocked = getattr(r, 'unlocked_at', None)
        claimed = getattr(r, 'claimed_at', None)
        if unlocked and not claimed:
            if isinstance(unlocked, str) and unlocked >= seven_days_ago:
                revenue_notifications.append(r)
    revenue_notifications.sort(key=lambda x: getattr(x, 'target_revenue', 0))
    
    auto_generate_monthly_review_if_needed()
    new_monthly_review = get_newly_generated_review()
    
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
        widget_order=widget_order,
        widget_active=widget_active,
        widget_names=widget_names,
        revenue_notifications=revenue_notifications,
        new_monthly_review=new_monthly_review
    )


@dashboard_bp.route('/widget-settings', methods=['POST'])
def save_widget_settings():
    data = request.get_json()
    settings = UserSettings.get_settings()
    
    if 'order' in data:
        settings.set_dashboard_order(data['order'])
    if 'active' in data:
        settings.set_dashboard_active(data['active'])
    
    settings.save()
    return jsonify({'success': True})
