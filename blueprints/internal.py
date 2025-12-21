import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session
from db_supabase import get_supabase

internal_bp = Blueprint('internal', __name__, url_prefix='/internal')

def get_summary_data():
    client = get_supabase()
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    followups_result = client.table('leads').select('id', count='exact').eq('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")').execute()
    followups_today = followups_result.count if followups_result.count else len(followups_result.data)
    
    overdue_result = client.table('leads').select('id', count='exact').lt('next_action_date', today.isoformat()).filter('status', 'not.in', '("closed_won","closed_lost")').execute()
    overdue_followups = overdue_result.count if overdue_result.count else len(overdue_result.data)
    
    tasks_result = client.table('tasks').select('id', count='exact').eq('due_date', today.isoformat()).neq('status', 'done').execute()
    tasks_today = tasks_result.count if tasks_result.count else len(tasks_result.data)
    
    outreach_result = client.table('outreach_logs').select('id', count='exact').eq('date', yesterday.isoformat()).execute()
    outreach_yesterday = outreach_result.count if outreach_result.count else len(outreach_result.data)
    
    goals_result = client.table('goals').select('target_value').eq('goal_type', 'daily_outreach').eq('period', 'daily').execute()
    daily_goal_value = goals_result.data[0]['target_value'] if goals_result.data else 5
    
    stats_result = client.table('user_stats').select('*').execute()
    stats = stats_result.data[0] if stats_result.data else {}
    
    new_leads_result = client.table('leads').select('id', count='exact').gte('created_at', f'{yesterday.isoformat()}T00:00:00').lt('created_at', f'{today.isoformat()}T00:00:00').execute()
    new_leads_yesterday = new_leads_result.count if new_leads_result.count else len(new_leads_result.data)
    
    hosting_result = client.table('clients').select('monthly_hosting_fee').eq('hosting_active', True).execute()
    hosting_mrr = sum(float(c.get('monthly_hosting_fee') or 0) for c in hosting_result.data)
    
    saas_result = client.table('clients').select('monthly_saas_fee').eq('saas_active', True).execute()
    saas_mrr = sum(float(c.get('monthly_saas_fee') or 0) for c in saas_result.data)
    
    total_mrr = hosting_mrr + saas_mrr
    
    return {
        'followups_today': followups_today,
        'overdue_followups': overdue_followups,
        'tasks_today': tasks_today,
        'outreach_yesterday': outreach_yesterday,
        'daily_goal': daily_goal_value,
        'streak': stats.get('current_outreach_streak_days', 0),
        'xp': stats.get('current_xp', 0),
        'level': stats.get('current_level', 1),
        'consistency': stats.get('last_consistency_score', 0),
        'new_leads_yesterday': new_leads_yesterday,
        'hosting_mrr': hosting_mrr,
        'saas_mrr': saas_mrr,
        'total_mrr': total_mrr
    }


def get_weekly_data():
    client = get_supabase()
    today = date.today()
    last_week_start = today - timedelta(days=today.weekday() + 7)
    last_week_end = last_week_start + timedelta(days=6)
    
    outreach_result = client.table('outreach_logs').select('id', count='exact').gte('date', last_week_start.isoformat()).lte('date', last_week_end.isoformat()).execute()
    outreach_last_week = outreach_result.count if outreach_result.count else len(outreach_result.data)
    
    weekly_goal_result = client.table('goals').select('target_value').eq('goal_type', 'weekly_outreach').eq('period', 'weekly').execute()
    weekly_goal_value = weekly_goal_result.data[0]['target_value'] if weekly_goal_result.data else 25
    
    deals_result = client.table('leads').select('id', count='exact').eq('status', 'closed_won').gte('converted_at', f'{last_week_start.isoformat()}T00:00:00').lte('converted_at', f'{last_week_end.isoformat()}T23:59:59').execute()
    deals_last_week = deals_result.count if deals_result.count else len(deals_result.data)
    
    month_start = today.replace(day=1)
    revenue_result = client.table('clients').select('amount_charged').gte('start_date', month_start.isoformat()).execute()
    revenue_this_month = sum(float(c.get('amount_charged') or 0) for c in revenue_result.data)
    
    mrr_result = client.table('clients').select('monthly_hosting_fee,monthly_saas_fee').or_('hosting_active.eq.true,saas_active.eq.true').execute()
    current_mrr = sum(float(c.get('monthly_hosting_fee') or 0) + float(c.get('monthly_saas_fee') or 0) for c in mrr_result.data)
    
    return {
        'outreach_last_week': outreach_last_week,
        'weekly_goal': weekly_goal_value,
        'deals_last_week': deals_last_week,
        'revenue_this_month': float(revenue_this_month),
        'current_mrr': current_mrr
    }


def build_daily_email(data, include_weekly=False, weekly_data=None):
    today = date.today()
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #4F46E5; margin-bottom: 20px;">Daily CRM Summary - {today.strftime('%A, %B %d')}</h1>
        
        <div style="background: #FEF3C7; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0; color: #92400E;">Follow-ups & Tasks</h2>
            <p style="margin: 5px 0;"><strong>Follow-ups due today:</strong> {data['followups_today']}</p>
            <p style="margin: 5px 0;"><strong>Overdue follow-ups:</strong> {data['overdue_followups']}</p>
            <p style="margin: 5px 0;"><strong>Tasks due today:</strong> {data['tasks_today']}</p>
        </div>
        
        <div style="background: #DBEAFE; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0; color: #1E40AF;">Outreach</h2>
            <p style="margin: 5px 0;"><strong>Outreach yesterday:</strong> {data['outreach_yesterday']} / {data['daily_goal']} goal</p>
            <p style="margin: 5px 0;"><strong>New leads yesterday:</strong> {data['new_leads_yesterday']}</p>
        </div>
        
        <div style="background: #D1FAE5; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0; color: #065F46;">Gamification</h2>
            <p style="margin: 5px 0;"><strong>Current streak:</strong> {data['streak']} days</p>
            <p style="margin: 5px 0;"><strong>XP / Level:</strong> {data['xp']} XP (Level {data['level']})</p>
            <p style="margin: 5px 0;"><strong>Consistency score:</strong> {data['consistency']}%</p>
        </div>
        
        <div style="background: #E0E7FF; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0; color: #3730A3;">MRR Snapshot</h2>
            <p style="margin: 5px 0;"><strong>Hosting MRR:</strong> ${data['hosting_mrr']:.2f}</p>
            <p style="margin: 5px 0;"><strong>SaaS MRR:</strong> ${data['saas_mrr']:.2f}</p>
            <p style="margin: 5px 0;"><strong>Total MRR:</strong> ${data['total_mrr']:.2f}</p>
        </div>
    """
    
    if include_weekly and weekly_data:
        html += f"""
        <div style="background: #FEE2E2; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0; color: #991B1B;">Weekly Summary</h2>
            <p style="margin: 5px 0;"><strong>Outreach last week:</strong> {weekly_data['outreach_last_week']} / {weekly_data['weekly_goal']} goal</p>
            <p style="margin: 5px 0;"><strong>Deals closed last week:</strong> {weekly_data['deals_last_week']}</p>
            <p style="margin: 5px 0;"><strong>Revenue this month:</strong> ${weekly_data['revenue_this_month']:.2f}</p>
        </div>
        """
    
    html += """
        <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
            This is an automated summary from your Personal CRM.
        </p>
    </body>
    </html>
    """
    
    return html


def send_email(subject, html_content, to_email):
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    from_email = os.environ.get('SMTP_FROM', smtp_user)
    
    if not smtp_user or not smtp_password:
        return False, "SMTP credentials not configured"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)


@internal_bp.route('/run-daily-summary')
def run_daily_summary():
    auth_token = os.environ.get('INTERNAL_API_TOKEN', '')
    provided_token = request.args.get('token', '')
    
    if not session.get('authenticated') and (not auth_token or provided_token != auth_token):
        return jsonify({'error': 'Unauthorized'}), 401
    
    today = date.today()
    day_of_week = today.weekday()
    
    if day_of_week >= 5:
        return jsonify({
            'status': 'skipped',
            'reason': 'Weekend - no email sent',
            'day': today.strftime('%A')
        })
    
    crm_email = os.environ.get('CRM_EMAIL', '')
    if not crm_email:
        return jsonify({
            'status': 'error',
            'reason': 'CRM_EMAIL environment variable not set'
        })
    
    data = get_summary_data()
    include_weekly = (day_of_week == 0)
    weekly_data = get_weekly_data() if include_weekly else None
    
    subject = f"CRM Daily Summary - {today.strftime('%b %d')}"
    if include_weekly:
        subject = f"CRM Weekly + Daily Summary - {today.strftime('%b %d')}"
    
    html_content = build_daily_email(data, include_weekly, weekly_data)
    
    success, message = send_email(subject, html_content, crm_email)
    
    if success:
        return jsonify({
            'status': 'sent',
            'to': crm_email,
            'includes_weekly': include_weekly,
            'day': today.strftime('%A')
        })
    else:
        return jsonify({
            'status': 'error',
            'reason': message
        })
