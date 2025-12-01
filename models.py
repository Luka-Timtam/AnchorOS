from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_name = db.Column(db.String(200))
    niche = db.Column(db.String(100))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    source = db.Column(db.String(100))
    status = db.Column(db.String(50), default='new')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted_at = db.Column(db.DateTime, nullable=True)
    next_action_date = db.Column(db.Date, nullable=True)
    
    has_website = db.Column(db.Boolean, default=False)
    website_quality = db.Column(db.String(50), nullable=True)
    demo_site_built = db.Column(db.Boolean, default=False)
    converted_at = db.Column(db.DateTime, nullable=True)
    
    outreach_logs = db.relationship('OutreachLog', backref='lead', lazy=True)
    tasks = db.relationship('Task', backref='lead', lazy=True, foreign_keys='Task.related_lead_id')

    @staticmethod
    def status_choices():
        return ['new', 'contacted', 'call_booked', 'follow_up', 'proposal_sent', 'closed_won', 'closed_lost']
    
    @staticmethod
    def website_quality_choices():
        return ['no_website', 'outdated', 'poor_design', 'not_mobile_friendly', 'slow_loading', 'broken_features']


class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_name = db.Column(db.String(200))
    contact_email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    project_type = db.Column(db.String(50), default='website')
    start_date = db.Column(db.Date)
    amount_charged = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(50), default='active')
    hosting_active = db.Column(db.Boolean, default=False)
    monthly_hosting_fee = db.Column(db.Numeric(10, 2), default=0)
    saas_active = db.Column(db.Boolean, default=False)
    monthly_saas_fee = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    related_lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    
    related_lead = db.relationship('Lead', backref='converted_client', foreign_keys=[related_lead_id])
    tasks = db.relationship('Task', backref='client', lazy=True, foreign_keys='Task.related_client_id')

    @staticmethod
    def project_type_choices():
        return ['website', 'hosting_only', 'saas_only', 'bundle']
    
    @staticmethod
    def status_choices():
        return ['active', 'completed', 'paused', 'cancelled']


class OutreachLog(db.Model):
    __tablename__ = 'outreach_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=date.today)
    type = db.Column(db.String(50), default='email')
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    notes = db.Column(db.Text)
    outcome = db.Column(db.String(50), default='contacted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def type_choices():
        return ['email', 'call', 'dm', 'in_person', 'other']
    
    @staticmethod
    def outcome_choices():
        return ['contacted', 'booked_call', 'no_response', 'closed_won', 'closed_lost', 'follow_up_set']


class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='open')
    related_lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    related_client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def status_choices():
        return ['open', 'in_progress', 'done']
