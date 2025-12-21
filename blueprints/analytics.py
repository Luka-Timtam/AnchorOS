from flask import Blueprint, render_template, request, redirect, url_for, flash
from db_supabase import get_supabase, UserSettings
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

def status_choices():
    return ['new', 'contacted', 'qualified', 'proposal_sent', 'negotiating', 'closed_won', 'closed_lost']

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)

@analytics_bp.route('/')
def index():
    client = get_supabase()
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
    
    niches_result = client.table('leads').select('niche').filter('niche', 'not.is', 'null').neq('niche', '').execute()
    niches = list(set([n['niche'] for n in niches_result.data if n.get('niche')]))
    
    sources_result = client.table('leads').select('source').filter('source', 'not.is', 'null').neq('source', '').execute()
    sources = list(set([s['source'] for s in sources_result.data if s.get('source')]))
    
    followup_today_result = client.table('leads').select('id', count='exact').eq('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")').is_('converted_at', 'null').execute()
    followup_today = followup_today_result.count if followup_today_result.count else len(followup_today_result.data)
    
    followup_overdue_result = client.table('leads').select('id', count='exact').lt('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")').is_('converted_at', 'null').execute()
    followup_overdue = followup_overdue_result.count if followup_overdue_result.count else len(followup_overdue_result.data)
    
    monthly_revenue_data = []
    month_labels = []
    
    for i in range(11, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
        month_labels.append(m_start.strftime('%b %Y'))
        
        revenue_result = client.table('clients').select('amount_charged').gte('start_date', m_start.isoformat()).lte('start_date', m_end.isoformat()).execute()
        month_revenue = sum(float(r.get('amount_charged') or 0) for r in revenue_result.data)
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
        
        hosting_result = client.table('clients').select('monthly_hosting_fee').eq('hosting_active', True).lte('start_date', m_end.isoformat()).execute()
        hosting_at_month = sum(float(r.get('monthly_hosting_fee') or 0) for r in hosting_result.data)
        
        saas_result = client.table('clients').select('monthly_saas_fee').eq('saas_active', True).lte('start_date', m_end.isoformat()).execute()
        saas_at_month = sum(float(r.get('monthly_saas_fee') or 0) for r in saas_result.data)
        
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
        
        outreach_result = client.table('outreach_logs').select('id', count='exact').gte('date', w_start.isoformat()).lte('date', w_end.isoformat()).execute()
        outreach_weekly_data.append(outreach_result.count if outreach_result.count else len(outreach_result.data))
        
        deals_query = client.table('leads').select('id', count='exact').eq('status', 'closed_won').gte('updated_at', f'{w_start.isoformat()}T00:00:00').lte('updated_at', f'{w_end.isoformat()}T23:59:59')
        if niche_filter:
            deals_query = deals_query.eq('niche', niche_filter)
        if source_filter:
            deals_query = deals_query.eq('source', source_filter)
        deals_result = deals_query.execute()
        deals_weekly_data.append(deals_result.count if deals_result.count else len(deals_result.data))
    
    lead_pipeline = {}
    for status in status_choices():
        query = client.table('leads').select('id', count='exact').eq('status', status).is_('converted_at', 'null')
        if niche_filter:
            query = query.eq('niche', niche_filter)
        if source_filter:
            query = query.eq('source', source_filter)
        result = query.execute()
        lead_pipeline[status] = result.count if result.count else len(result.data)
    
    win_reasons_count = {}
    won_leads_result = client.table('leads').select('close_reason').eq('status', 'closed_won').filter('close_reason', 'not.is', 'null').neq('close_reason', '').execute()
    for lead in won_leads_result.data:
        close_reason = lead.get('close_reason', '')
        if close_reason:
            for reason in close_reason.split(','):
                reason = reason.strip()
                reason_key = reason.split(':')[0].strip() if reason.startswith('Other:') else reason
                win_reasons_count[reason_key] = win_reasons_count.get(reason_key, 0) + 1
    
    loss_reasons_count = {}
    lost_leads_result = client.table('leads').select('close_reason').eq('status', 'closed_lost').filter('close_reason', 'not.is', 'null').neq('close_reason', '').execute()
    for lead in lost_leads_result.data:
        close_reason = lead.get('close_reason', '')
        if close_reason:
            for reason in close_reason.split(','):
                reason = reason.strip()
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
        'pipelineLabels': [s.replace('_', ' ').title() for s in status_choices()],
        'pipelineData': [lead_pipeline.get(s, 0) for s in status_choices()],
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
        statuses=status_choices(),
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
    client = get_supabase()
    user_settings = UserSettings.get_settings()
    
    if request.method == 'POST':
        update_data = {
            'show_mrr_widget': 'show_mrr_widget' in request.form,
            'show_project_revenue_widget': 'show_project_revenue_widget' in request.form,
            'show_outreach_widget': 'show_outreach_widget' in request.form,
            'show_deals_widget': 'show_deals_widget' in request.form,
            'show_consistency_score_widget': 'show_consistency_score_widget' in request.form,
            'show_forecast_widget': 'show_forecast_widget' in request.form,
            'show_followup_widget': 'show_followup_widget' in request.form
        }
        
        settings_result = client.table('user_settings').select('id').execute()
        if settings_result.data:
            client.table('user_settings').update(update_data).eq('id', settings_result.data[0]['id']).execute()
        else:
            client.table('user_settings').insert(update_data).execute()
        
        flash('Dashboard settings saved!', 'success')
        return redirect(url_for('analytics.settings'))
    
    return render_template('analytics/settings.html', settings=user_settings)


@analytics_bp.route('/flex')
def flex():
    client = get_supabase()
    today = date.today()
    
    total_revenue_result = client.table('clients').select('amount_charged').execute()
    total_revenue = sum(float(r.get('amount_charged') or 0) for r in total_revenue_result.data)
    
    month_start = today.replace(day=1)
    current_month_result = client.table('clients').select('amount_charged').gte('start_date', month_start.isoformat()).lte('start_date', today.isoformat()).execute()
    current_month_revenue = sum(float(r.get('amount_charged') or 0) for r in current_month_result.data)
    
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
        
        month_result = client.table('clients').select('amount_charged').gte('start_date', m_start.isoformat()).lte('start_date', m_end.isoformat()).execute()
        month_rev = sum(float(r.get('amount_charged') or 0) for r in month_result.data)
        
        last_3_months.append({
            'label': m_start.strftime('%b %Y'),
            'amount': float(month_rev)
        })
    
    won_result = client.table('leads').select('id', count='exact').eq('status', 'closed_won').execute()
    total_deals_won = won_result.count if won_result.count else len(won_result.data)
    
    lost_result = client.table('leads').select('id', count='exact').eq('status', 'closed_lost').execute()
    total_deals_lost = lost_result.count if lost_result.count else len(lost_result.data)
    
    total_closed = total_deals_won + total_deals_lost
    win_rate = int((total_deals_won / total_closed * 100)) if total_closed > 0 else 0
    
    stats_result = client.table('user_stats').select('*').execute()
    stats = stats_result.data[0] if stats_result.data else {}
    highest_streak = stats.get('longest_outreach_streak_days', 0)
    current_streak = stats.get('current_outreach_streak_days', 0)
    
    xp_result = client.table('xp_log').select('amount').execute()
    total_xp = sum(r.get('amount', 0) for r in xp_result.data)
    
    outreach_result = client.table('outreach_logs').select('id', count='exact').execute()
    total_outreach = outreach_result.count if outreach_result.count else len(outreach_result.data)
    
    this_month_outreach_result = client.table('outreach_logs').select('id', count='exact').gte('date', month_start.isoformat()).lte('date', today.isoformat()).execute()
    this_month_outreach = this_month_outreach_result.count if this_month_outreach_result.count else len(this_month_outreach_result.data)
    
    largest_deal_result = client.table('clients').select('amount_charged').order('amount_charged', desc=True).limit(1).execute()
    largest_deal = float(largest_deal_result.data[0].get('amount_charged', 0)) if largest_deal_result.data else 0
    
    monthly_revenues = []
    for i in range(24):
        m_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
        
        month_result = client.table('clients').select('amount_charged').gte('start_date', m_start.isoformat()).lte('start_date', m_end.isoformat()).execute()
        month_rev = sum(float(r.get('amount_charged') or 0) for r in month_result.data)
        
        if float(month_rev) > 0:
            monthly_revenues.append({
                'month': m_start.strftime('%B %Y'),
                'amount': float(month_rev)
            })
    
    highest_month = max(monthly_revenues, key=lambda x: x['amount']) if monthly_revenues else None
    
    fastest_deal_days = None
    won_leads_result = client.table('leads').select('id,closed_at').eq('status', 'closed_won').filter('closed_at', 'not.is', 'null').execute()
    
    for lead in won_leads_result.data:
        lead_id = lead.get('id')
        closed_at_str = lead.get('closed_at')
        if closed_at_str:
            try:
                closed_at = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                first_outreach_result = client.table('outreach_logs').select('date').eq('lead_id', lead_id).order('date').limit(1).execute()
                if first_outreach_result.data:
                    first_date_str = first_outreach_result.data[0].get('date')
                    if first_date_str:
                        first_date = datetime.strptime(first_date_str, '%Y-%m-%d').date()
                        days = (closed_at.date() - first_date).days
                        if days >= 0:
                            if fastest_deal_days is None or days < fastest_deal_days:
                                fastest_deal_days = days
            except (ValueError, TypeError):
                pass
    
    leads_revived_result = client.table('activity_log').select('id', count='exact').eq('action_type', 'lead_revived').execute()
    leads_revived = leads_revived_result.count if leads_revived_result.count else len(leads_revived_result.data)
    
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
