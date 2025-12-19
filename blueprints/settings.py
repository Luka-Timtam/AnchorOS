from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from models import db, UserSettings, ActivityLog, Lead, Client, Task, Note, FreelanceJob, OutreachLog, UserStats
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
    
    settings.pause_active = True
    settings.pause_start = date.today()
    settings.pause_end = date.today() + timedelta(days=duration)
    settings.pause_reason = reason
    db.session.commit()
    
    ActivityLog.log_activity('pause_activated', f'Pause Mode activated until {settings.pause_end.strftime("%b %d, %Y")}')
    
    flash(f'Pause mode activated for {duration} days.', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/pause/end', methods=['POST'])
def pause_end():
    from models import UserStats
    settings = UserSettings.get_settings()
    
    stats = UserStats.query.first()
    if stats and stats.current_outreach_streak_days > 0:
        stats.last_outreach_date = date.today() - timedelta(days=1)
    
    settings.pause_active = False
    settings.pause_start = None
    settings.pause_end = None
    settings.pause_reason = None
    db.session.commit()
    
    ActivityLog.log_activity('pause_ended', 'Pause Mode ended')
    
    flash('Pause mode ended.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/export', methods=['POST'])
def export_all_data():
    """Export all core data as a ZIP file containing CSV files."""
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        leads_buffer = io.StringIO()
        leads_writer = csv.writer(leads_buffer)
        leads_writer.writerow(['ID', 'Name', 'Business Name', 'Niche', 'Email', 'Phone', 'Source', 'Status', 
                               'Notes', 'Next Action Date', 'Last Contacted', 'Close Reason', 'Created At', 'Updated At', 'Closed At', 'Archived At'])
        for lead in Lead.query.all():
            leads_writer.writerow([
                lead.id, lead.name, lead.business_name, lead.niche, lead.email, lead.phone,
                lead.source, lead.status, lead.notes,
                lead.next_action_date.isoformat() if lead.next_action_date else '',
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else '',
                lead.close_reason or '',
                lead.created_at.isoformat() if lead.created_at else '',
                lead.updated_at.isoformat() if lead.updated_at else '',
                lead.closed_at.isoformat() if lead.closed_at else '',
                lead.archived_at.isoformat() if lead.archived_at else ''
            ])
        zip_file.writestr('leads.csv', leads_buffer.getvalue())
        
        clients_buffer = io.StringIO()
        clients_writer = csv.writer(clients_buffer)
        clients_writer.writerow(['ID', 'Name', 'Business Name', 'Contact Email', 'Phone', 'Project Type', 
                                 'Start Date', 'Amount Charged', 'Status', 'Hosting Active', 'Monthly Hosting Fee',
                                 'SaaS Active', 'Monthly SaaS Fee', 'Notes', 'Created At', 'Updated At', 'Related Lead ID'])
        for client in Client.query.all():
            clients_writer.writerow([
                client.id, client.name, client.business_name, client.contact_email, client.phone,
                client.project_type, client.start_date.isoformat() if client.start_date else '',
                float(client.amount_charged) if client.amount_charged else 0, client.status,
                client.hosting_active, float(client.monthly_hosting_fee) if client.monthly_hosting_fee else 0,
                client.saas_active, float(client.monthly_saas_fee) if client.monthly_saas_fee else 0,
                client.notes, client.created_at.isoformat() if client.created_at else '',
                client.updated_at.isoformat() if client.updated_at else '', client.related_lead_id
            ])
        zip_file.writestr('clients.csv', clients_buffer.getvalue())
        
        tasks_buffer = io.StringIO()
        tasks_writer = csv.writer(tasks_buffer)
        tasks_writer.writerow(['ID', 'Title', 'Description', 'Status', 'Priority', 'Due Date', 
                               'Lead ID', 'Client ID', 'Created At', 'Updated At', 'Completed At'])
        for task in Task.query.all():
            tasks_writer.writerow([
                task.id, task.title, task.description, task.status, task.priority,
                task.due_date.isoformat() if task.due_date else '',
                task.lead_id, task.client_id,
                task.created_at.isoformat() if task.created_at else '',
                task.updated_at.isoformat() if task.updated_at else '',
                task.completed_at.isoformat() if task.completed_at else ''
            ])
        zip_file.writestr('tasks.csv', tasks_buffer.getvalue())
        
        notes_buffer = io.StringIO()
        notes_writer = csv.writer(notes_buffer)
        notes_writer.writerow(['ID', 'Title', 'Content', 'Tags', 'Pinned', 'Created At', 'Updated At'])
        for note in Note.query.all():
            notes_writer.writerow([
                note.id, note.title, note.content, note.tags, note.pinned,
                note.created_at.isoformat() if note.created_at else '',
                note.updated_at.isoformat() if note.updated_at else ''
            ])
        zip_file.writestr('notes.csv', notes_buffer.getvalue())
        
        outreach_buffer = io.StringIO()
        outreach_writer = csv.writer(outreach_buffer)
        outreach_writer.writerow(['ID', 'Lead ID', 'Type', 'Outcome', 'Notes', 'Date', 'Created At'])
        for log in OutreachLog.query.all():
            outreach_writer.writerow([
                log.id, log.lead_id, log.type, log.outcome, log.notes,
                log.date.isoformat() if log.date else '',
                log.created_at.isoformat() if log.created_at else ''
            ])
        zip_file.writestr('outreach_logs.csv', outreach_buffer.getvalue())
        
        revenue_buffer = io.StringIO()
        revenue_writer = csv.writer(revenue_buffer)
        revenue_writer.writerow(['ID', 'Title', 'Description', 'Category', 'Amount', 'Date Completed', 
                                 'Client Name', 'Notes', 'Created At', 'Updated At'])
        for job in FreelanceJob.query.all():
            revenue_writer.writerow([
                job.id, job.title, job.description, job.category, float(job.amount) if job.amount else 0,
                job.date_completed.isoformat() if job.date_completed else '',
                job.client_name, job.notes,
                job.created_at.isoformat() if job.created_at else '',
                job.updated_at.isoformat() if job.updated_at else ''
            ])
        zip_file.writestr('revenue_entries.csv', revenue_buffer.getvalue())
        
        activity_buffer = io.StringIO()
        activity_writer = csv.writer(activity_buffer)
        activity_writer.writerow(['ID', 'Action Type', 'Description', 'Related ID', 'Related Object Type', 'Timestamp'])
        for activity in ActivityLog.query.all():
            activity_writer.writerow([
                activity.id, activity.action_type, activity.description,
                activity.related_id or '', activity.related_object_type or '',
                activity.timestamp.isoformat() if activity.timestamp else ''
            ])
        zip_file.writestr('activity_log.csv', activity_buffer.getvalue())
        
        stats = UserStats.get_stats()
        analytics_buffer = io.StringIO()
        analytics_writer = csv.writer(analytics_buffer)
        analytics_writer.writerow(['Metric', 'Value'])
        analytics_writer.writerow(['Current XP', stats.current_xp if stats.current_xp else 0])
        analytics_writer.writerow(['Current Level', stats.current_level if stats.current_level else 1])
        analytics_writer.writerow(['Current Outreach Streak', stats.current_outreach_streak_days if stats.current_outreach_streak_days else 0])
        analytics_writer.writerow(['Best Outreach Streak', stats.longest_outreach_streak_days if stats.longest_outreach_streak_days else 0])
        analytics_writer.writerow(['Last Outreach Date', stats.last_outreach_date.isoformat() if stats.last_outreach_date else ''])
        analytics_writer.writerow(['Consistency Score', stats.last_consistency_score if stats.last_consistency_score else 0])
        
        # Calculate totals from related records
        total_leads = Lead.query.count()
        total_clients = Client.query.count()
        total_tasks = Task.query.count()
        total_notes = Note.query.count()
        total_outreach = OutreachLog.query.count()
        total_revenue = float(FreelanceJob.get_total_income())
        closed_won_count = Lead.query.filter_by(status='closed_won').count()
        
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
