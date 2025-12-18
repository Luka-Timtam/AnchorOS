from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import (db, MonthlyReview, XPLog, TokenTransaction, OutreachLog, Lead, 
                    DailyMission, BossFight, UserStats, WinsLog, ActivityLog, Client)
from datetime import datetime, date, timedelta
from sqlalchemy import func
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
    first_datetime = datetime.combine(first_day, datetime.min.time())
    last_datetime = datetime.combine(last_day, datetime.max.time())
    
    total_xp = db.session.query(func.sum(XPLog.amount)).filter(
        XPLog.created_at >= first_datetime,
        XPLog.created_at <= last_datetime
    ).scalar() or 0
    
    token_gains = db.session.query(func.sum(TokenTransaction.amount)).filter(
        TokenTransaction.amount > 0,
        TokenTransaction.created_at >= first_datetime,
        TokenTransaction.created_at <= last_datetime
    ).scalar() or 0
    
    total_outreach = OutreachLog.query.filter(
        OutreachLog.date >= first_day,
        OutreachLog.date <= last_day
    ).count()
    
    calls_booked = ActivityLog.query.filter(
        ActivityLog.action_type == 'call_booked',
        ActivityLog.timestamp >= first_datetime,
        ActivityLog.timestamp <= last_datetime
    ).count()
    
    outreach_calls_booked = OutreachLog.query.filter(
        OutreachLog.outcome == 'booked_call',
        OutreachLog.date >= first_day,
        OutreachLog.date <= last_day
    ).count()
    
    calls_booked = max(calls_booked, outreach_calls_booked)
    
    proposals_sent = ActivityLog.query.filter(
        ActivityLog.action_type == 'proposal_sent',
        ActivityLog.timestamp >= first_datetime,
        ActivityLog.timestamp <= last_datetime
    ).count()
    
    deals_won = Lead.query.filter(
        Lead.status == 'closed_won',
        Lead.closed_at >= first_datetime,
        Lead.closed_at <= last_datetime
    ).count()
    
    deals_lost = Lead.query.filter(
        Lead.status == 'closed_lost',
        Lead.closed_at >= first_datetime,
        Lead.closed_at <= last_datetime
    ).count()
    
    new_clients = Client.query.filter(
        Client.created_at >= first_datetime,
        Client.created_at <= last_datetime
    ).all()
    
    new_client_count = len(new_clients)
    project_revenue = sum(float(c.amount_charged or 0) for c in new_clients)
    
    active_clients_count = Client.query.filter(
        Client.status == 'active',
        Client.created_at <= last_datetime
    ).count()
    
    hosting_clients = Client.query.filter(
        Client.hosting_active == True,
        Client.created_at <= last_datetime
    ).all()
    monthly_hosting_revenue = sum(float(c.monthly_hosting_fee or 0) for c in hosting_clients)
    
    saas_clients = Client.query.filter(
        Client.saas_active == True,
        Client.created_at <= last_datetime
    ).all()
    monthly_saas_revenue = sum(float(c.monthly_saas_fee or 0) for c in saas_clients)
    
    mrr = monthly_hosting_revenue + monthly_saas_revenue
    total_revenue = project_revenue + mrr
    
    avg_deal_value = project_revenue / new_client_count if new_client_count > 0 else 0
    
    stats = UserStats.get_stats()
    streak_current = stats.current_outreach_streak_days if stats else 0
    streak_longest = stats.longest_outreach_streak_days if stats else 0
    
    outreach_by_day = db.session.query(
        OutreachLog.date, func.count(OutreachLog.id)
    ).filter(
        OutreachLog.date >= first_day,
        OutreachLog.date <= last_day
    ).group_by(OutreachLog.date).all()
    
    if outreach_by_day:
        sorted_days = sorted(outreach_by_day, key=lambda x: x[1], reverse=True)
        most_active_day = sorted_days[0][0].strftime('%A, %b %d') if sorted_days else 'N/A'
        most_active_count = sorted_days[0][1] if sorted_days else 0
        least_active_day = sorted_days[-1][0].strftime('%A, %b %d') if sorted_days else 'N/A'
        least_active_count = sorted_days[-1][1] if sorted_days else 0
    else:
        most_active_day = 'N/A'
        most_active_count = 0
        least_active_day = 'N/A'
        least_active_count = 0
    
    missions_completed = DailyMission.query.filter(
        DailyMission.is_completed == True,
        DailyMission.mission_date >= first_day,
        DailyMission.mission_date <= last_day
    ).count()
    
    boss = BossFight.query.filter(
        BossFight.month == year_month
    ).first()
    
    if boss:
        boss_result = {
            'description': boss.description,
            'is_completed': boss.is_completed,
            'progress': boss.progress_value,
            'target': boss.target_value,
            'reward_tokens': boss.reward_tokens
        }
    else:
        boss_result = None
    
    won_leads = Lead.query.filter(
        Lead.status == 'closed_won',
        Lead.closed_at >= first_datetime,
        Lead.closed_at <= last_datetime,
        Lead.close_reason.isnot(None)
    ).all()
    
    win_reasons = []
    for lead in won_leads:
        reasons = lead.get_close_reasons_list()
        win_reasons.extend(reasons)
    
    win_reason_counts = Counter(win_reasons).most_common(5)
    
    lost_leads = Lead.query.filter(
        Lead.status == 'closed_lost',
        Lead.closed_at >= first_datetime,
        Lead.closed_at <= last_datetime,
        Lead.close_reason.isnot(None)
    ).all()
    
    loss_reasons = []
    for lead in lost_leads:
        reasons = lead.get_close_reasons_list()
        loss_reasons.extend(reasons)
    
    loss_reason_counts = Counter(loss_reasons).most_common(5)
    
    wins = WinsLog.query.filter(
        WinsLog.timestamp >= first_datetime,
        WinsLog.timestamp <= last_datetime
    ).order_by(WinsLog.timestamp.desc()).limit(10).all()
    
    wins_list = [{'title': w.title, 'description': w.description, 
                  'xp': w.xp_value, 'tokens': w.token_value} for w in wins]
    
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
        'boss_result': boss_result,
        'most_active_day': most_active_day,
        'most_active_count': most_active_count,
        'least_active_day': least_active_day,
        'least_active_count': least_active_count,
        'top_win_reasons': win_reason_counts,
        'top_loss_reasons': loss_reason_counts,
        'highlights': wins_list
    }
    
    return content


@monthly_review_bp.route('/monthly-review')
def index():
    reviews = MonthlyReview.get_all_reviews()
    existing_months = {r.year_month for r in reviews}
    
    today = date.today()
    available_months = []
    
    for i in range(24):
        year = today.year
        month = today.month - i
        
        while month <= 0:
            month += 12
            year -= 1
        
        month_date = date(year, month, 1)
        year_month = month_date.strftime('%Y-%m')
        
        if year_month not in existing_months:
            available_months.append({
                'value': year_month,
                'label': month_date.strftime('%B %Y')
            })
    
    reviews_with_content = []
    for review in reviews:
        reviews_with_content.append({
            'id': review.id,
            'year_month': review.year_month,
            'label': datetime.strptime(review.year_month, '%Y-%m').strftime('%B %Y'),
            'generated_at': review.generated_at,
            'content': review.get_content()
        })
    
    return render_template('monthly_review/index.html',
                         reviews=reviews_with_content,
                         available_months=available_months)


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
    review = MonthlyReview.get_review(year_month)
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
    review = MonthlyReview.get_review(year_month)
    if review:
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted.', 'success')
    return redirect(url_for('monthly_review.index'))
