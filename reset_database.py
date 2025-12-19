"""
Database reset script for AnchorOS deployment.
Clears all data EXCEPT revenue_rewards (battlepass) table.
"""
from app import app
from models import db

TABLES_TO_CLEAR = [
    'leads',
    'clients', 
    'outreach_logs',
    'tasks',
    'user_settings',
    'user_stats',
    'achievements',
    'goals',
    'xp_logs',
    'outreach_templates',
    'level_rewards',
    'milestone_rewards',
    'unlocked_rewards',
    'user_tokens',
    'token_transactions',
    'reward_items',
    'daily_missions',
    'boss_fights',
    'boss_fight_history',
    'activity_logs',
    'notes',
    'focus_sessions',
    'wins_logs',
    'monthly_reviews',
    'freelance_jobs',
]

def reset_database():
    with app.app_context():
        print("Starting database reset...")
        print("Preserving: revenue_rewards (battlepass)")
        print("-" * 40)
        
        for table in TABLES_TO_CLEAR:
            try:
                result = db.session.execute(db.text(f"DELETE FROM {table}"))
                count = result.rowcount
                print(f"Cleared {table}: {count} rows deleted")
            except Exception as e:
                print(f"Skipping {table}: {e}")
        
        db.session.commit()
        print("-" * 40)
        print("Database reset complete!")
        
        bp_count = db.session.execute(db.text("SELECT COUNT(*) FROM revenue_rewards")).scalar()
        print(f"Battlepass items preserved: {bp_count}")

if __name__ == "__main__":
    reset_database()
