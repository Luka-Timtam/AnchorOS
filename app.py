import os
import logging
from datetime import timedelta
from flask import Flask, redirect, url_for, session, request
import timezone as tz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    app.permanent_session_lifetime = timedelta(days=30)
    
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
    from blueprints.calendar import calendar_bp
    from blueprints.focus import focus_bp
    from blueprints.monthly_review import monthly_review_bp
    from blueprints.battlepass import battlepass_bp
    from blueprints.freelancing import freelancing_bp
    from blueprints.mobile import mobile_bp
    
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
    app.register_blueprint(calendar_bp)
    app.register_blueprint(focus_bp)
    app.register_blueprint(monthly_review_bp)
    app.register_blueprint(battlepass_bp)
    app.register_blueprint(freelancing_bp)
    app.register_blueprint(mobile_bp)
    
    def is_mobile_device():
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    @app.route('/health')
    def health_check():
        return 'OK', 200
    
    @app.before_request
    def require_login():
        allowed_routes = ['auth.login', 'static', 'internal.run_daily_summary', 'health_check']
        if request.endpoint and request.endpoint not in allowed_routes:
            if not session.get('authenticated'):
                return redirect(url_for('auth.login'))
    
    @app.before_request
    def mobile_redirect():
        if not session.get('authenticated'):
            return
        
        if request.args.get('desktop') == '1':
            session['force_desktop'] = True
        
        if request.args.get('mobile') == '1':
            session.pop('force_desktop', None)
            if not request.endpoint or not request.endpoint.startswith('mobile.'):
                return redirect(url_for('mobile.index'))
        
        if session.get('force_desktop'):
            return
        
        if request.endpoint and request.endpoint.startswith('mobile.'):
            return
        
        if request.endpoint in ['auth.login', 'auth.logout', 'static', 'internal.run_daily_summary', 
                               'focus.status', 'calendar.mini', 'search.search']:
            return
        
        if is_mobile_device() and request.endpoint == 'dashboard.index':
            return redirect(url_for('mobile.index'))
    
    with app.app_context():
        from db_supabase import check_connection, is_client_initialized
        logger.info("[App] Initializing Supabase client on app startup...")
        if not check_connection():
            logger.warning("[App] Could not connect to Supabase. Please check SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        else:
            logger.info("[App] Supabase connection successful!")
            logger.info(f"[App] Supabase client initialized: {is_client_initialized()}")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
