from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Lead, Client, OutreachLog, UserSettings
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
