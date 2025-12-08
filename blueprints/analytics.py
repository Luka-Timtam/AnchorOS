from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import (db, Lead, Client, OutreachLog, UserSettings, UserStats, 
                    XPLog, TokenTransaction, DailyMission, BossFight, ActivityLog)
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
from decimal import Decimal
import json

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)

@analytics_bp.route('/')
def index():
    today = date.today()
    settings = UserSettings.get_settings()
    
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    niche_filter = request.args.get('niche', '')
    source_filter = request.args.get('source', '')
    status_filter = request.args.get('status', '')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=90)
    else:
        start_date = today - timedelta(days=90)
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
    
    niches = db.session.query(Lead.niche).filter(Lead.niche.isnot(None), Lead.niche != '').distinct().all()
    niches = [n[0] for n in niches]
    
    sources = db.session.query(Lead.source).filter(Lead.source.isnot(None), Lead.source != '').distinct().all()
    sources = [s[0] for s in sources]
    
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
    
    hosting_mrr_data = []
    saas_mrr_data = []
    total_mrr_data = []
    
    for i in range(11, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
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
        
        hosting_mrr_data.append(float(hosting_at_month))
        saas_mrr_data.append(float(saas_at_month))
        total_mrr_data.append(float(hosting_at_month + saas_at_month))
    
    outreach_weekly_data = []
    deals_weekly_data = []
    week_labels = []
    
    for i in range(11, -1, -1):
        w_start = get_week_start(today) - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        
        week_labels.append(w_start.strftime('%b %d'))
        
        outreach_query = OutreachLog.query.filter(
            and_(OutreachLog.date >= w_start, OutreachLog.date <= w_end)
        )
        if niche_filter or source_filter:
            outreach_query = outreach_query.join(Lead, OutreachLog.lead_id == Lead.id, isouter=True)
            if niche_filter:
                outreach_query = outreach_query.filter(Lead.niche == niche_filter)
            if source_filter:
                outreach_query = outreach_query.filter(Lead.source == source_filter)
        outreach_weekly_data.append(outreach_query.count())
        
        deals_query = Lead.query.filter(
            and_(
                Lead.status == 'closed_won',
                func.date(Lead.updated_at) >= w_start,
                func.date(Lead.updated_at) <= w_end
            )
        )
        if niche_filter:
            deals_query = deals_query.filter(Lead.niche == niche_filter)
        if source_filter:
            deals_query = deals_query.filter(Lead.source == source_filter)
        deals_weekly_data.append(deals_query.count())
    
    lead_pipeline = {}
    for status in Lead.status_choices():
        query = Lead.query.filter(Lead.status == status, Lead.converted_at.is_(None))
        if niche_filter:
            query = query.filter(Lead.niche == niche_filter)
        if source_filter:
            query = query.filter(Lead.source == source_filter)
        if status_filter:
            query = query.filter(Lead.status == status_filter)
        lead_pipeline[status] = query.count()
    
    win_reasons_count = {}
    won_leads = Lead.query.filter(
        Lead.status == 'closed_won',
        Lead.close_reason.isnot(None),
        Lead.close_reason != ''
    ).all()
    for lead in won_leads:
        for reason in lead.get_close_reasons_list():
            reason_key = reason.split(':')[0].strip() if reason.startswith('Other:') else reason
            win_reasons_count[reason_key] = win_reasons_count.get(reason_key, 0) + 1
    
    loss_reasons_count = {}
    lost_leads = Lead.query.filter(
        Lead.status == 'closed_lost',
        Lead.close_reason.isnot(None),
        Lead.close_reason != ''
    ).all()
    for lead in lost_leads:
        for reason in lead.get_close_reasons_list():
            reason_key = reason.split(':')[0].strip() if reason.startswith('Other:') else reason
            loss_reasons_count[reason_key] = loss_reasons_count.get(reason_key, 0) + 1
    
    win_reasons_sorted = sorted(win_reasons_count.items(), key=lambda x: x[1], reverse=True)
    loss_reasons_sorted = sorted(loss_reasons_count.items(), key=lambda x: x[1], reverse=True)
    
    current_mrr = total_mrr_data[-1] if total_mrr_data else 0
    last_3_months_revenue = monthly_revenue_data[-3:] if len(monthly_revenue_data) >= 3 else monthly_revenue_data
    avg_project_revenue = sum(last_3_months_revenue) / len(last_3_months_revenue) if last_3_months_revenue else 0
    forecast_monthly = current_mrr + avg_project_revenue
    forecast_3_months = forecast_monthly * 3
    
    chart_data = {
        'monthLabels': month_labels,
        'monthlyRevenue': monthly_revenue_data,
        'hostingMrr': hosting_mrr_data,
        'saasMrr': saas_mrr_data,
        'totalMrr': total_mrr_data,
        'weekLabels': week_labels,
        'outreachWeekly': outreach_weekly_data,
        'dealsWeekly': deals_weekly_data,
        'leadPipeline': lead_pipeline,
        'pipelineLabels': [s.replace('_', ' ').title() for s in Lead.status_choices()],
        'pipelineData': [lead_pipeline.get(s, 0) for s in Lead.status_choices()],
        'winReasonLabels': [r[0] for r in win_reasons_sorted[:8]],
        'winReasonData': [r[1] for r in win_reasons_sorted[:8]],
        'lossReasonLabels': [r[0] for r in loss_reasons_sorted[:8]],
        'lossReasonData': [r[1] for r in loss_reasons_sorted[:8]]
    }
    
    return render_template('analytics/index.html',
        chart_data=json.dumps(chart_data),
        settings=settings,
        niches=niches,
        sources=sources,
        statuses=Lead.status_choices(),
        current_niche=niche_filter,
        current_source=source_filter,
        current_status=status_filter,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        forecast_monthly=forecast_monthly,
        forecast_3_months=forecast_3_months,
        current_mrr=current_mrr,
        avg_project_revenue=avg_project_revenue,
        followup_today=followup_today,
        followup_overdue=followup_overdue
    )


@analytics_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    user_settings = UserSettings.get_settings()
    
    if request.method == 'POST':
        user_settings.show_mrr_widget = 'show_mrr_widget' in request.form
        user_settings.show_project_revenue_widget = 'show_project_revenue_widget' in request.form
        user_settings.show_outreach_widget = 'show_outreach_widget' in request.form
        user_settings.show_deals_widget = 'show_deals_widget' in request.form
        user_settings.show_consistency_score_widget = 'show_consistency_score_widget' in request.form
        user_settings.show_forecast_widget = 'show_forecast_widget' in request.form
        user_settings.show_followup_widget = 'show_followup_widget' in request.form
        
        db.session.commit()
        flash('Dashboard settings saved!', 'success')
        return redirect(url_for('analytics.settings'))
    
    return render_template('analytics/settings.html', settings=user_settings)


@analytics_bp.route('/flex')
def flex():
    today = date.today()
    
    total_revenue = db.session.query(
        func.coalesce(func.sum(Client.amount_charged), 0)
    ).scalar() or Decimal('0')
    total_revenue = float(total_revenue)
    
    month_start = today.replace(day=1)
    current_month_revenue = db.session.query(
        func.coalesce(func.sum(Client.amount_charged), 0)
    ).filter(
        Client.start_date >= month_start,
        Client.start_date <= today
    ).scalar() or Decimal('0')
    current_month_revenue = float(current_month_revenue)
    
    last_3_months = []
    for i in range(2, -1, -1):
        if i == 0:
            m_start = today.replace(day=1)
            m_end = today
        else:
            m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
        month_rev = db.session.query(
            func.coalesce(func.sum(Client.amount_charged), 0)
        ).filter(
            and_(Client.start_date >= m_start, Client.start_date <= m_end)
        ).scalar() or Decimal('0')
        
        last_3_months.append({
            'label': m_start.strftime('%b %Y'),
            'amount': float(month_rev)
        })
    
    total_deals_won = Lead.query.filter(Lead.status == 'closed_won').count()
    total_deals_lost = Lead.query.filter(Lead.status == 'closed_lost').count()
    total_closed = total_deals_won + total_deals_lost
    win_rate = int((total_deals_won / total_closed * 100)) if total_closed > 0 else 0
    
    stats = UserStats.get_stats()
    highest_streak = stats.longest_outreach_streak_days if stats else 0
    current_streak = stats.current_outreach_streak_days if stats else 0
    
    total_xp = db.session.query(func.coalesce(func.sum(XPLog.amount), 0)).scalar() or 0
    
    total_outreach = OutreachLog.query.count()
    
    this_month_outreach = OutreachLog.query.filter(
        OutreachLog.date >= month_start,
        OutreachLog.date <= today
    ).count()
    
    largest_deal = db.session.query(
        func.max(Client.amount_charged)
    ).scalar() or Decimal('0')
    largest_deal = float(largest_deal)
    
    monthly_revenues = []
    for i in range(24):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
        month_rev = db.session.query(
            func.coalesce(func.sum(Client.amount_charged), 0)
        ).filter(
            and_(Client.start_date >= m_start, Client.start_date <= m_end)
        ).scalar() or Decimal('0')
        
        if float(month_rev) > 0:
            monthly_revenues.append({
                'month': m_start.strftime('%B %Y'),
                'amount': float(month_rev)
            })
    
    highest_month = max(monthly_revenues, key=lambda x: x['amount']) if monthly_revenues else None
    
    fastest_deal_days = None
    won_leads = Lead.query.filter(
        Lead.status == 'closed_won',
        Lead.closed_at.isnot(None)
    ).all()
    
    for lead in won_leads:
        first_outreach = OutreachLog.query.filter(
            OutreachLog.lead_id == lead.id
        ).order_by(OutreachLog.date.asc()).first()
        
        if first_outreach and lead.closed_at:
            days = (lead.closed_at.date() - first_outreach.date).days
            if days >= 0:
                if fastest_deal_days is None or days < fastest_deal_days:
                    fastest_deal_days = days
    
    leads_revived = ActivityLog.query.filter(
        ActivityLog.action_type == 'lead_revived'
    ).count()
    
    avg_deal_value = total_revenue / total_deals_won if total_deals_won > 0 else 0
    
    if total_revenue >= 100000:
        revenue_badge = {'title': 'Six-Figure Slayer', 'class': 'from-red-500 to-orange-500'}
    elif total_revenue >= 50000:
        revenue_badge = {'title': 'Half-a-Stack King', 'class': 'from-purple-500 to-pink-500'}
    elif total_revenue >= 10000:
        revenue_badge = {'title': '5-Figure Hunter', 'class': 'from-blue-500 to-cyan-500'}
    else:
        revenue_badge = None
    
    chart_data = {
        'labels': [m['label'] for m in last_3_months],
        'data': [m['amount'] for m in last_3_months]
    }
    
    return render_template('analytics/flex.html',
        total_revenue=total_revenue,
        current_month_revenue=current_month_revenue,
        current_month_name=today.strftime('%B'),
        total_deals_won=total_deals_won,
        win_rate=win_rate,
        highest_streak=highest_streak,
        current_streak=current_streak,
        total_xp=total_xp,
        highest_month=highest_month,
        fastest_deal_days=fastest_deal_days,
        largest_deal=largest_deal,
        avg_deal_value=avg_deal_value,
        leads_revived=leads_revived,
        total_outreach=total_outreach,
        this_month_outreach=this_month_outreach,
        revenue_badge=revenue_badge,
        chart_data=json.dumps(chart_data)
    )
