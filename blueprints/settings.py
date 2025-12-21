from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from db_supabase import (UserSettings, ActivityLog, Lead, Client, Task, Note, 
                         FreelancingIncome, OutreachLog, UserStats, get_supabase)
from datetime import date, timedelta
import csv
import io
import zipfile

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
def index():
    settings = UserSettings.get_settings()
    settings.check_pause_expiry()
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/pause/activate', methods=['POST'])
def pause_activate():
    settings = UserSettings.get_settings()
    
    try:
        duration = int(request.form.get('duration', 1))
        if duration < 1 or duration > 14:
            flash('Pause duration must be between 1 and 14 days.', 'error')
            return redirect(url_for('settings.index'))
    except ValueError:
        flash('Invalid duration value.', 'error')
        return redirect(url_for('settings.index'))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('A reason is required to activate pause mode.', 'error')
        return redirect(url_for('settings.index'))
    
    pause_end = date.today() + timedelta(days=duration)
    UserSettings.update_by_id(settings.id, {
        'pause_active': True,
        'pause_start': date.today().isoformat(),
        'pause_end': pause_end.isoformat(),
        'pause_reason': reason
    })
    
    ActivityLog.log_activity('pause_activated', f'Pause Mode activated until {pause_end.strftime("%b %d, %Y")}')
    
    flash(f'Pause mode activated for {duration} days.', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/pause/end', methods=['POST'])
def pause_end():
    settings = UserSettings.get_settings()
    
    stats = UserStats.get_stats()
    if stats and (getattr(stats, 'current_outreach_streak_days', 0) or 0) > 0:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        UserStats.update_by_id(stats.id, {'last_outreach_date': yesterday})
    
    UserSettings.update_by_id(settings.id, {
        'pause_active': False,
        'pause_start': None,
        'pause_end': None,
        'pause_reason': None
    })
    
    ActivityLog.log_activity('pause_ended', 'Pause Mode ended')
    
    flash('Pause mode ended.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/export', methods=['POST'])
def export_all_data():
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        leads_buffer = io.StringIO()
        leads_writer = csv.writer(leads_buffer)
        leads_writer.writerow(['ID', 'Name', 'Business Name', 'Niche', 'Email', 'Phone', 'Source', 'Status', 
                               'Notes', 'Next Action Date', 'Last Contacted', 'Close Reason', 'Created At', 'Updated At', 'Closed At', 'Archived At'])
        for lead in Lead.query_all():
            leads_writer.writerow([
                getattr(lead, 'id', ''), getattr(lead, 'name', ''), getattr(lead, 'business_name', ''), 
                getattr(lead, 'niche', ''), getattr(lead, 'email', ''), getattr(lead, 'phone', ''),
                getattr(lead, 'source', ''), getattr(lead, 'status', ''), getattr(lead, 'notes', ''),
                getattr(lead, 'next_action_date', ''), getattr(lead, 'last_contacted_at', ''),
                getattr(lead, 'close_reason', ''), getattr(lead, 'created_at', ''),
                getattr(lead, 'updated_at', ''), getattr(lead, 'closed_at', ''), getattr(lead, 'archived_at', '')
            ])
        zip_file.writestr('leads.csv', leads_buffer.getvalue())
        
        clients_buffer = io.StringIO()
        clients_writer = csv.writer(clients_buffer)
        clients_writer.writerow(['ID', 'Name', 'Business Name', 'Contact Email', 'Phone', 'Project Type', 
                                 'Start Date', 'Amount Charged', 'Status', 'Hosting Active', 'Monthly Hosting Fee',
                                 'SaaS Active', 'Monthly SaaS Fee', 'Notes', 'Created At', 'Updated At', 'Related Lead ID'])
        for client in Client.query_all():
            clients_writer.writerow([
                getattr(client, 'id', ''), getattr(client, 'name', ''), getattr(client, 'business_name', ''), 
                getattr(client, 'contact_email', ''), getattr(client, 'phone', ''),
                getattr(client, 'project_type', ''), getattr(client, 'start_date', ''),
                float(getattr(client, 'amount_charged', 0) or 0), getattr(client, 'status', ''),
                getattr(client, 'hosting_active', False), float(getattr(client, 'monthly_hosting_fee', 0) or 0),
                getattr(client, 'saas_active', False), float(getattr(client, 'monthly_saas_fee', 0) or 0),
                getattr(client, 'notes', ''), getattr(client, 'created_at', ''),
                getattr(client, 'updated_at', ''), getattr(client, 'related_lead_id', '')
            ])
        zip_file.writestr('clients.csv', clients_buffer.getvalue())
        
        tasks_buffer = io.StringIO()
        tasks_writer = csv.writer(tasks_buffer)
        tasks_writer.writerow(['ID', 'Title', 'Description', 'Status', 'Due Date', 'Lead ID', 'Client ID', 'Created At'])
        for task in Task.query_all():
            tasks_writer.writerow([
                getattr(task, 'id', ''), getattr(task, 'title', ''), getattr(task, 'description', ''), 
                getattr(task, 'status', ''), getattr(task, 'due_date', ''),
                getattr(task, 'related_lead_id', ''), getattr(task, 'related_client_id', ''),
                getattr(task, 'created_at', '')
            ])
        zip_file.writestr('tasks.csv', tasks_buffer.getvalue())
        
        notes_buffer = io.StringIO()
        notes_writer = csv.writer(notes_buffer)
        notes_writer.writerow(['ID', 'Title', 'Content', 'Tags', 'Pinned', 'Created At', 'Updated At'])
        for note in Note.query_all():
            notes_writer.writerow([
                getattr(note, 'id', ''), getattr(note, 'title', ''), getattr(note, 'content', ''), 
                getattr(note, 'tags', ''), getattr(note, 'pinned', False),
                getattr(note, 'created_at', ''), getattr(note, 'updated_at', '')
            ])
        zip_file.writestr('notes.csv', notes_buffer.getvalue())
        
        outreach_buffer = io.StringIO()
        outreach_writer = csv.writer(outreach_buffer)
        outreach_writer.writerow(['ID', 'Lead ID', 'Type', 'Outcome', 'Notes', 'Date', 'Created At'])
        for log in OutreachLog.query_all():
            outreach_writer.writerow([
                getattr(log, 'id', ''), getattr(log, 'lead_id', ''), getattr(log, 'type', ''), 
                getattr(log, 'outcome', ''), getattr(log, 'notes', ''),
                getattr(log, 'date', ''), getattr(log, 'created_at', '')
            ])
        zip_file.writestr('outreach_logs.csv', outreach_buffer.getvalue())
        
        revenue_buffer = io.StringIO()
        revenue_writer = csv.writer(revenue_buffer)
        revenue_writer.writerow(['ID', 'Description', 'Category', 'Amount', 'Date', 'Created At'])
        for job in FreelancingIncome.query_all():
            revenue_writer.writerow([
                getattr(job, 'id', ''), getattr(job, 'description', ''), getattr(job, 'category', ''), 
                float(getattr(job, 'amount', 0) or 0), getattr(job, 'date', ''),
                getattr(job, 'created_at', '')
            ])
        zip_file.writestr('revenue_entries.csv', revenue_buffer.getvalue())
        
        activity_buffer = io.StringIO()
        activity_writer = csv.writer(activity_buffer)
        activity_writer.writerow(['ID', 'Activity Type', 'Description', 'Related ID', 'Related Type', 'Created At'])
        for activity in ActivityLog.query_all():
            activity_writer.writerow([
                getattr(activity, 'id', ''), getattr(activity, 'activity_type', ''), 
                getattr(activity, 'description', ''), getattr(activity, 'related_id', ''), 
                getattr(activity, 'related_type', ''), getattr(activity, 'created_at', '')
            ])
        zip_file.writestr('activity_log.csv', activity_buffer.getvalue())
        
        stats = UserStats.get_stats()
        analytics_buffer = io.StringIO()
        analytics_writer = csv.writer(analytics_buffer)
        analytics_writer.writerow(['Metric', 'Value'])
        analytics_writer.writerow(['Current XP', getattr(stats, 'current_xp', 0) or 0])
        analytics_writer.writerow(['Current Level', getattr(stats, 'current_level', 1) or 1])
        analytics_writer.writerow(['Current Outreach Streak', getattr(stats, 'current_outreach_streak_days', 0) or 0])
        analytics_writer.writerow(['Best Outreach Streak', getattr(stats, 'longest_outreach_streak_days', 0) or 0])
        analytics_writer.writerow(['Last Outreach Date', getattr(stats, 'last_outreach_date', '')])
        analytics_writer.writerow(['Consistency Score', getattr(stats, 'last_consistency_score', 0) or 0])
        
        total_leads = Lead.count()
        total_clients = Client.count()
        total_tasks = Task.count()
        total_notes = Note.count()
        total_outreach = OutreachLog.count()
        
        freelance_income = FreelancingIncome.query_all()
        total_revenue = sum(float(getattr(f, 'amount', 0) or 0) for f in freelance_income)
        
        closed_won_count = Lead.count({'status': 'closed_won'})
        
        analytics_writer.writerow(['Total Leads', total_leads])
        analytics_writer.writerow(['Total Clients', total_clients])
        analytics_writer.writerow(['Total Tasks', total_tasks])
        analytics_writer.writerow(['Total Notes', total_notes])
        analytics_writer.writerow(['Total Outreach Logs', total_outreach])
        analytics_writer.writerow(['Total Revenue', total_revenue])
        analytics_writer.writerow(['Deals Won', closed_won_count])
        analytics_writer.writerow(['Export Date', date.today().isoformat()])
        zip_file.writestr('analytics_summary.csv', analytics_buffer.getvalue())
    
    zip_buffer.seek(0)
    
    ActivityLog.log_activity('data_exported', 'Full data export downloaded')
    
    return Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename=anchoros_export_{date.today().isoformat()}.zip'
        }
    )
