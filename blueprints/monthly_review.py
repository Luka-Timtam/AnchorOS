from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db_supabase import (MonthlyReview, XPLog, TokenTransaction, OutreachLog, Lead, 
                         DailyMission, BossBattle, UserStats, WinsLog, ActivityLog, Client, get_supabase)
from datetime import datetime, date, timedelta
from collections import Counter

monthly_review_bp = Blueprint('monthly_review', __name__)


def get_month_date_range(year_month):
    year, month = map(int, year_month.split('-'))
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return first_day, last_day


def generate_review_content(year_month):
    first_day, last_day = get_month_date_range(year_month)
    first_datetime = f'{first_day.isoformat()}T00:00:00'
    last_datetime = f'{last_day.isoformat()}T23:59:59'
    
    client = get_supabase()
    
    xp_result = client.table('xp_logs').select('amount').gte('created_at', first_datetime).lte('created_at', last_datetime).execute()
    total_xp = sum(row.get('amount', 0) or 0 for row in xp_result.data)
    
    token_result = client.table('token_transactions').select('amount').gt('amount', 0).gte('created_at', first_datetime).lte('created_at', last_datetime).execute()
    token_gains = sum(row.get('amount', 0) or 0 for row in token_result.data)
    
    outreach_result = client.table('outreach_logs').select('id, date, outcome', count='exact').gte('date', first_day.isoformat()).lte('date', last_day.isoformat()).execute()
    total_outreach = len(outreach_result.data)
    
    outreach_calls_booked = sum(1 for row in outreach_result.data if row.get('outcome') == 'booked_call')
    calls_booked = outreach_calls_booked
    
    proposals_result = client.table('activity_log').select('id', count='exact').eq('activity_type', 'proposal_sent').execute()
    proposals_sent = len(proposals_result.data)
    
    leads_result = client.table('leads').select('*').execute()
    leads_data = leads_result.data
    
    deals_won = 0
    deals_lost = 0
    win_reasons = []
    loss_reasons = []
    
    for lead in leads_data:
        closed_at = lead.get('closed_at', '')
        status = lead.get('status', '')
        if closed_at and first_datetime <= closed_at <= last_datetime:
            if status == 'closed_won':
                deals_won += 1
                if lead.get('close_reason'):
                    win_reasons.extend([r.strip() for r in lead['close_reason'].split(',') if r.strip()])
            elif status == 'closed_lost':
                deals_lost += 1
                if lead.get('close_reason'):
                    loss_reasons.extend([r.strip() for r in lead['close_reason'].split(',') if r.strip()])
    
    clients_result = client.table('clients').select('*').execute()
    clients_data = clients_result.data
    
    new_clients = [c for c in clients_data if first_datetime <= c.get('created_at', '') <= last_datetime]
    new_client_count = len(new_clients)
    project_revenue = sum(float(c.get('amount_charged', 0) or 0) for c in new_clients)
    
    active_clients_count = sum(1 for c in clients_data if c.get('status') == 'active' and c.get('created_at', '') <= last_datetime)
    
    hosting_clients = [c for c in clients_data if c.get('hosting_active') and c.get('created_at', '') <= last_datetime]
    monthly_hosting_revenue = sum(float(c.get('monthly_hosting_fee', 0) or 0) for c in hosting_clients)
    
    saas_clients = [c for c in clients_data if c.get('saas_active') and c.get('created_at', '') <= last_datetime]
    monthly_saas_revenue = sum(float(c.get('monthly_saas_fee', 0) or 0) for c in saas_clients)
    
    mrr = monthly_hosting_revenue + monthly_saas_revenue
    total_revenue = project_revenue + mrr
    
    avg_deal_value = project_revenue / new_client_count if new_client_count > 0 else 0
    
    stats = UserStats.get_stats()
    streak_current = getattr(stats, 'current_outreach_streak_days', 0) or 0
    streak_longest = getattr(stats, 'longest_outreach_streak_days', 0) or 0
    
    outreach_by_day = {}
    for row in outreach_result.data:
        d = row.get('date', '')
        if d:
            outreach_by_day[d] = outreach_by_day.get(d, 0) + 1
    
    if outreach_by_day:
        sorted_days = sorted(outreach_by_day.items(), key=lambda x: x[1], reverse=True)
        most_active_day = sorted_days[0][0]
        most_active_count = sorted_days[0][1]
        least_active_day = sorted_days[-1][0]
        least_active_count = sorted_days[-1][1]
        try:
            most_active_day = date.fromisoformat(most_active_day).strftime('%A, %b %d')
            least_active_day = date.fromisoformat(least_active_day).strftime('%A, %b %d')
        except:
            pass
    else:
        most_active_day = 'N/A'
        most_active_count = 0
        least_active_day = 'N/A'
        least_active_count = 0
    
    missions_result = client.table('daily_missions').select('id', count='exact').eq('is_completed', True).gte('mission_date', first_day.isoformat()).lte('mission_date', last_day.isoformat()).execute()
    missions_completed = len(missions_result.data)
    
    boss_result = client.table('boss_battles').select('*').eq('month_start', f'{year_month}-01').execute()
    boss_result_data = None
    if boss_result.data:
        boss = boss_result.data[0]
        boss_result_data = {
            'boss_name': boss.get('boss_name', ''),
            'is_defeated': boss.get('is_defeated', False),
            'current_outreach': boss.get('current_outreach', 0),
            'target_outreach': boss.get('target_outreach', 0),
            'reward_tokens': boss.get('reward_tokens', 0)
        }
    
    win_reason_counts = Counter(win_reasons).most_common(5)
    loss_reason_counts = Counter(loss_reasons).most_common(5)
    
    wins_result = client.table('wins_log').select('*').order('id', desc=True).limit(10).execute()
    wins_list = [{
        'title': w.get('title', ''),
        'description': w.get('description', ''),
        'xp': w.get('xp_value', 0),
        'tokens': w.get('token_value', 0)
    } for w in wins_result.data]
    
    num_days = (last_day - first_day).days + 1
    days_with_outreach = len(outreach_by_day)
    consistency_score = int((days_with_outreach / num_days) * 100) if num_days > 0 else 0
    
    content = {
        'year_month': year_month,
        'total_xp': total_xp,
        'total_tokens': int(token_gains),
        'outreach_volume': total_outreach,
        'calls_booked': calls_booked,
        'proposals_sent': proposals_sent,
        'deals_won': deals_won,
        'deals_lost': deals_lost,
        'new_clients': new_client_count,
        'project_revenue': round(project_revenue, 2),
        'mrr': round(mrr, 2),
        'total_revenue': round(total_revenue, 2),
        'avg_deal_value': round(avg_deal_value, 2),
        'active_clients': active_clients_count,
        'streak_current': streak_current,
        'streak_longest': streak_longest,
        'consistency_score': consistency_score,
        'missions_completed': missions_completed,
        'boss_result': boss_result_data,
        'most_active_day': most_active_day,
        'most_active_count': most_active_count,
        'least_active_day': least_active_day,
        'least_active_count': least_active_count,
        'top_win_reasons': win_reason_counts,
        'top_loss_reasons': loss_reason_counts,
        'highlights': wins_list
    }
    
    return content


def auto_generate_monthly_review_if_needed():
    today = date.today()
    
    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)
    
    last_day_of_month = next_month_first - timedelta(days=1)
    
    if today == last_day_of_month:
        year_month = today.strftime('%Y-%m')
        existing_review = MonthlyReview.get_first({'year_month': year_month})
        
        if not existing_review:
            try:
                content = generate_review_content(year_month)
                MonthlyReview.save_review(year_month, content)
                return year_month
            except Exception:
                pass
    
    return None


def get_newly_generated_review():
    today = date.today()
    
    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)
    
    last_day_of_month = next_month_first - timedelta(days=1)
    
    if today == last_day_of_month:
        year_month = today.strftime('%Y-%m')
        review = MonthlyReview.get_first({'year_month': year_month})
        if review:
            generated_at = getattr(review, 'generated_at', '')
            if isinstance(generated_at, str) and generated_at.startswith(today.isoformat()):
                return {
                    'year_month': year_month,
                    'label': datetime.strptime(year_month, '%Y-%m').strftime('%B %Y')
                }
    
    return None


@monthly_review_bp.route('/monthly-review')
def index():
    auto_generate_monthly_review_if_needed()
    
    reviews = MonthlyReview.query_all(order_by='year_month', order_desc=True)
    existing_months = {getattr(r, 'year_month', '') for r in reviews}
    
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    years = list(range(current_year, current_year - 3, -1))
    months = [
        {'value': 1, 'label': 'January'},
        {'value': 2, 'label': 'February'},
        {'value': 3, 'label': 'March'},
        {'value': 4, 'label': 'April'},
        {'value': 5, 'label': 'May'},
        {'value': 6, 'label': 'June'},
        {'value': 7, 'label': 'July'},
        {'value': 8, 'label': 'August'},
        {'value': 9, 'label': 'September'},
        {'value': 10, 'label': 'October'},
        {'value': 11, 'label': 'November'},
        {'value': 12, 'label': 'December'},
    ]
    
    reviews_with_content = []
    for review in reviews:
        year_month = getattr(review, 'year_month', '')
        reviews_with_content.append({
            'id': getattr(review, 'id', 0),
            'year_month': year_month,
            'label': datetime.strptime(year_month, '%Y-%m').strftime('%B %Y') if year_month else '',
            'generated_at': getattr(review, 'generated_at', ''),
            'content': review.get_content()
        })
    
    return render_template('monthly_review/index.html',
                         reviews=reviews_with_content,
                         years=years,
                         months=months,
                         current_year=current_year,
                         current_month=current_month,
                         existing_months=list(existing_months))


@monthly_review_bp.route('/monthly-review/generate', methods=['POST'])
def generate():
    year_month = request.form.get('year_month')
    
    if not year_month:
        flash('Please select a month to generate a review.', 'error')
        return redirect(url_for('monthly_review.index'))
    
    try:
        content = generate_review_content(year_month)
        MonthlyReview.save_review(year_month, content)
        flash(f'Review for {datetime.strptime(year_month, "%Y-%m").strftime("%B %Y")} generated successfully!', 'success')
    except Exception as e:
        flash(f'Error generating review: {str(e)}', 'error')
    
    return redirect(url_for('monthly_review.index'))


@monthly_review_bp.route('/monthly-review/<year_month>')
def view(year_month):
    review = MonthlyReview.get_first({'year_month': year_month})
    if not review:
        flash('Review not found.', 'error')
        return redirect(url_for('monthly_review.index'))
    
    content = review.get_content()
    label = datetime.strptime(year_month, '%Y-%m').strftime('%B %Y')
    
    return render_template('monthly_review/view.html',
                         review=review,
                         content=content,
                         label=label)


@monthly_review_bp.route('/monthly-review/<year_month>/regenerate', methods=['POST'])
def regenerate(year_month):
    try:
        content = generate_review_content(year_month)
        MonthlyReview.save_review(year_month, content)
        flash(f'Review regenerated successfully!', 'success')
    except Exception as e:
        flash(f'Error regenerating review: {str(e)}', 'error')
    
    return redirect(url_for('monthly_review.view', year_month=year_month))


@monthly_review_bp.route('/monthly-review/<year_month>/delete', methods=['POST'])
def delete(year_month):
    review = MonthlyReview.get_first({'year_month': year_month})
    if review:
        MonthlyReview.delete_by_id(review.id)
        flash('Review deleted.', 'success')
    return redirect(url_for('monthly_review.index'))
