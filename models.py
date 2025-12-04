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


class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    show_mrr_widget = db.Column(db.Boolean, default=True)
    show_project_revenue_widget = db.Column(db.Boolean, default=True)
    show_outreach_widget = db.Column(db.Boolean, default=True)
    show_deals_widget = db.Column(db.Boolean, default=True)
    show_consistency_score_widget = db.Column(db.Boolean, default=True)
    show_forecast_widget = db.Column(db.Boolean, default=True)
    show_followup_widget = db.Column(db.Boolean, default=True)
    
    @staticmethod
    def get_settings():
        settings = UserSettings.query.first()
        if not settings:
            settings = UserSettings()
            db.session.add(settings)
            db.session.commit()
        return settings


class UserStats(db.Model):
    __tablename__ = 'user_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    current_xp = db.Column(db.Integer, default=0)
    current_level = db.Column(db.Integer, default=1)
    current_outreach_streak_days = db.Column(db.Integer, default=0)
    longest_outreach_streak_days = db.Column(db.Integer, default=0)
    last_outreach_date = db.Column(db.Date, nullable=True)
    last_consistency_score = db.Column(db.Integer, default=0)
    last_consistency_calculated_at = db.Column(db.DateTime, nullable=True)
    
    @staticmethod
    def get_stats():
        stats = UserStats.query.first()
        if not stats:
            stats = UserStats()
            db.session.add(stats)
            db.session.commit()
        return stats
    
    def get_level_from_xp(self):
        xp = self.current_xp
        if xp >= 10000: return 10
        if xp >= 7500: return 9
        if xp >= 5000: return 8
        if xp >= 3500: return 7
        if xp >= 2500: return 6
        if xp >= 1500: return 5
        if xp >= 1000: return 4
        if xp >= 500: return 3
        if xp >= 200: return 2
        return 1
    
    def xp_for_next_level(self):
        levels = [0, 200, 500, 1000, 1500, 2500, 3500, 5000, 7500, 10000, float('inf')]
        current = self.get_level_from_xp()
        if current >= 10:
            return None
        return levels[current]


class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unlocked_at = db.Column(db.DateTime, nullable=True)
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'key': 'streak_7', 'name': 'Week Warrior', 'description': 'Maintain a 7-day outreach streak'},
            {'key': 'streak_30', 'name': 'Consistency King', 'description': 'Maintain a 30-day outreach streak'},
            {'key': 'xp_1000', 'name': 'Rising Star', 'description': 'Earn 1,000 XP'},
            {'key': 'xp_5000', 'name': 'Power Player', 'description': 'Earn 5,000 XP'},
            {'key': 'outreach_100', 'name': 'Outreach Machine', 'description': 'Log 100 outreach activities'},
            {'key': 'deals_10', 'name': 'Deal Closer', 'description': 'Close 10 deals'},
        ]
        for item in defaults:
            existing = Achievement.query.filter_by(key=item['key']).first()
            if not existing:
                achievement = Achievement(**item)
                db.session.add(achievement)
        db.session.commit()


class Goal(db.Model):
    __tablename__ = 'goals'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_type = db.Column(db.String(50), nullable=False)
    period = db.Column(db.String(20), nullable=False)
    target_value = db.Column(db.Integer, default=0)
    is_manual = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def goal_types():
        return ['daily_outreach', 'weekly_outreach', 'monthly_revenue', 'monthly_deals']
    
    @staticmethod
    def get_or_create(goal_type, period):
        goal = Goal.query.filter_by(goal_type=goal_type, period=period).first()
        if not goal:
            goal = Goal(goal_type=goal_type, period=period, target_value=0, is_manual=False)
            db.session.add(goal)
            db.session.commit()
        return goal


class XPLog(db.Model):
    __tablename__ = 'xp_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OutreachTemplate(db.Model):
    __tablename__ = 'outreach_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(100), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_favourite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def category_choices():
        return ['email', 'dm', 'call']
    
    @staticmethod
    def subcategory_choices():
        return ['cold_outreach', 'follow_up', 'cold_call_script', 'objection_handling', 'booking_confirmation', 'proposal', 'other']
