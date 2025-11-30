from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, OutreachLog, Lead
from datetime import datetime, date, timedelta
from sqlalchemy import and_

outreach_bp = Blueprint('outreach', __name__, url_prefix='/outreach')

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_month_start(d):
    return d.replace(day=1)

@outreach_bp.route('/')
def index():
    today = date.today()
    week_start = get_week_start(today)
    month_start = get_month_start(today)
    
    outreach_today = OutreachLog.query.filter(OutreachLog.date == today).count()
    outreach_week = OutreachLog.query.filter(OutreachLog.date >= week_start).count()
    outreach_month = OutreachLog.query.filter(OutreachLog.date >= month_start).count()
    
    type_filter = request.args.get('type', '')
    outcome_filter = request.args.get('outcome', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = OutreachLog.query
    
    if type_filter:
        query = query.filter(OutreachLog.type == type_filter)
    if outcome_filter:
        query = query.filter(OutreachLog.outcome == outcome_filter)
    if date_from:
        query = query.filter(OutreachLog.date >= date_from)
    if date_to:
        query = query.filter(OutreachLog.date <= date_to)
    
    logs = query.order_by(OutreachLog.date.desc(), OutreachLog.created_at.desc()).all()
    leads = Lead.query.order_by(Lead.name).all()
    
    return render_template('outreach/index.html',
        logs=logs,
        leads=leads,
        types=OutreachLog.type_choices(),
        outcomes=OutreachLog.outcome_choices(),
        outreach_today=outreach_today,
        outreach_week=outreach_week,
        outreach_month=outreach_month,
        current_type=type_filter,
        current_outcome=outcome_filter,
        current_date_from=date_from,
        current_date_to=date_to,
        today=today.isoformat()
    )

@outreach_bp.route('/create', methods=['POST'])
def create():
    log = OutreachLog(
        date=request.form.get('date') or date.today(),
        type=request.form.get('type', 'email'),
        lead_id=request.form.get('lead_id') or None,
        outcome=request.form.get('outcome', 'contacted'),
        notes=request.form.get('notes')
    )
    
    if log.lead_id:
        lead = Lead.query.get(log.lead_id)
        if lead:
            lead.last_contacted_at = datetime.utcnow()
            db.session.add(lead)
    
    db.session.add(log)
    db.session.commit()
    flash('Outreach logged successfully!', 'success')
    
    return redirect(request.form.get('redirect_url') or url_for('outreach.index'))

@outreach_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    log = OutreachLog.query.get_or_404(id)
    db.session.delete(log)
    db.session.commit()
    flash('Outreach log deleted!', 'success')
    return redirect(url_for('outreach.index'))
