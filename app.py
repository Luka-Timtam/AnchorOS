import os
from datetime import timedelta
from flask import Flask, redirect, url_for, session, request
from models import db

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.permanent_session_lifetime = timedelta(days=30)
    
    db.init_app(app)
    
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.leads import leads_bp
    from blueprints.clients import clients_bp
    from blueprints.outreach import outreach_bp
    from blueprints.tasks import tasks_bp
    from blueprints.analytics import analytics_bp
    from blueprints.gamification import gamification_bp
    from blueprints.goals import goals_bp
    from blueprints.outreach_templates import outreach_templates_bp
    from blueprints.internal import internal_bp
    from blueprints.rewards import rewards_bp
    from blueprints.missions import missions_bp
    from blueprints.boss import boss_bp
    from blueprints.settings import settings_bp
    from blueprints.timeline import timeline_bp
    from blueprints.notes import notes_bp
    from blueprints.search import search_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(outreach_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(outreach_templates_bp)
    app.register_blueprint(internal_bp)
    app.register_blueprint(rewards_bp)
    app.register_blueprint(missions_bp)
    app.register_blueprint(boss_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(search_bp)
    
    @app.before_request
    def require_login():
        allowed_routes = ['auth.login', 'static', 'internal.run_daily_summary']
        if request.endpoint and request.endpoint not in allowed_routes:
            if not session.get('authenticated'):
                return redirect(url_for('auth.login'))
    
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
