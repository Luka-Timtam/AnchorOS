-- AnchorOS CRM Database Schema
-- Exported from: /home/runner/workspace/instance/database.db

CREATE TABLE achievements (
	id INTEGER NOT NULL, 
	"key" VARCHAR(100) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	unlocked_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE ("key")
);

CREATE TABLE activity_log (
	id INTEGER NOT NULL, 
	timestamp DATETIME, 
	action_type VARCHAR(50) NOT NULL, 
	description TEXT NOT NULL, 
	related_id INTEGER, 
	related_object_type VARCHAR(50), 
	PRIMARY KEY (id)
);

CREATE TABLE boss_fight_history (
	id INTEGER NOT NULL, 
	boss_fight_id INTEGER NOT NULL, 
	month VARCHAR(7) NOT NULL, 
	completed_at DATETIME NOT NULL, 
	reward_tokens INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(boss_fight_id) REFERENCES boss_fights (id)
);

CREATE TABLE boss_fights (
	id INTEGER NOT NULL, 
	month VARCHAR(7) NOT NULL, 
	description TEXT NOT NULL, 
	boss_type VARCHAR(50) NOT NULL, 
	target_value INTEGER NOT NULL, 
	progress_value INTEGER, 
	reward_tokens INTEGER NOT NULL, 
	is_completed BOOLEAN, 
	completed_at DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE clients (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	business_name VARCHAR(200), 
	contact_email VARCHAR(200), 
	phone VARCHAR(50), 
	project_type VARCHAR(50), 
	start_date DATE, 
	amount_charged NUMERIC(10, 2), 
	status VARCHAR(50), 
	hosting_active BOOLEAN, 
	monthly_hosting_fee NUMERIC(10, 2), 
	saas_active BOOLEAN, 
	monthly_saas_fee NUMERIC(10, 2), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	related_lead_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(related_lead_id) REFERENCES leads (id)
);

CREATE TABLE daily_missions (
	id INTEGER NOT NULL, 
	mission_date DATE NOT NULL, 
	description VARCHAR(200) NOT NULL, 
	mission_type VARCHAR(50) NOT NULL, 
	target_count INTEGER NOT NULL, 
	reward_tokens INTEGER NOT NULL, 
	is_completed BOOLEAN, 
	progress_count INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE focus_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, start_time DATETIME NOT NULL, end_time DATETIME, duration_minutes INTEGER NOT NULL, completed BOOLEAN DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE freelance_jobs (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	category VARCHAR(50), 
	amount NUMERIC(10, 2) NOT NULL, 
	date_completed DATE, 
	client_name VARCHAR(200), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE goals (
	id INTEGER NOT NULL, 
	goal_type VARCHAR(50) NOT NULL, 
	period VARCHAR(20) NOT NULL, 
	target_value INTEGER, 
	is_manual BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE leads (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	business_name VARCHAR(200), 
	niche VARCHAR(100), 
	email VARCHAR(200), 
	phone VARCHAR(50), 
	source VARCHAR(100), 
	status VARCHAR(50), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	last_contacted_at DATETIME, 
	next_action_date DATE, has_website BOOLEAN DEFAULT 0, website_quality VARCHAR(50), demo_site_built BOOLEAN DEFAULT 0, converted_at DATETIME, close_reason VARCHAR(500), closed_at DATETIME, archived_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE level_rewards (
	id INTEGER NOT NULL, 
	level_interval INTEGER NOT NULL, 
	reward_text TEXT NOT NULL, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE milestone_rewards (
	id INTEGER NOT NULL, 
	target_level INTEGER NOT NULL, 
	reward_text TEXT NOT NULL, 
	is_active BOOLEAN, 
	unlocked_at DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (target_level)
);

CREATE TABLE monthly_reviews (
	id INTEGER NOT NULL, 
	year_month VARCHAR(7) NOT NULL, 
	content_json TEXT NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (year_month)
);

CREATE TABLE notes (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT NOT NULL, 
	tags VARCHAR(500), 
	pinned BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE outreach_logs (
	id INTEGER NOT NULL, 
	date DATE, 
	type VARCHAR(50), 
	lead_id INTEGER, 
	notes TEXT, 
	outcome VARCHAR(50), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id)
);

CREATE TABLE outreach_templates (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	subcategory VARCHAR(100), 
	content TEXT NOT NULL, 
	is_favourite BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE revenue_rewards (
	id INTEGER NOT NULL, 
	target_revenue FLOAT NOT NULL, 
	reward_text TEXT NOT NULL, 
	reward_icon VARCHAR(50), 
	is_active BOOLEAN, 
	unlocked_at DATETIME, 
	claimed_at DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (target_revenue)
);

CREATE TABLE reward_items (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	cost INTEGER NOT NULL, 
	description TEXT, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE tasks (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	due_date DATE, 
	status VARCHAR(50), 
	related_lead_id INTEGER, 
	related_client_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(related_lead_id) REFERENCES leads (id), 
	FOREIGN KEY(related_client_id) REFERENCES clients (id)
);

CREATE TABLE token_transactions (
	id INTEGER NOT NULL, 
	amount INTEGER NOT NULL, 
	reason VARCHAR(200), 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE unlocked_rewards (
	id INTEGER NOT NULL, 
	reward_type VARCHAR(20) NOT NULL, 
	reward_reference_id INTEGER NOT NULL, 
	level_achieved INTEGER NOT NULL, 
	reward_text TEXT NOT NULL, 
	unlocked_at DATETIME, claimed_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE user_settings (
	id INTEGER NOT NULL, 
	show_mrr_widget BOOLEAN, 
	show_project_revenue_widget BOOLEAN, 
	show_outreach_widget BOOLEAN, 
	show_deals_widget BOOLEAN, 
	show_consistency_score_widget BOOLEAN, 
	show_forecast_widget BOOLEAN, 
	show_followup_widget BOOLEAN, pause_active BOOLEAN DEFAULT 0, pause_start DATE, pause_end DATE, pause_reason TEXT, focus_timer_active BOOLEAN DEFAULT 0, focus_timer_end DATETIME, focus_timer_length INTEGER DEFAULT 25, dashboard_layout TEXT, dashboard_active_widgets TEXT, dashboard_order TEXT, dashboard_active TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE user_stats (
	id INTEGER NOT NULL, 
	current_xp INTEGER, 
	current_level INTEGER, 
	current_outreach_streak_days INTEGER, 
	longest_outreach_streak_days INTEGER, 
	last_outreach_date DATE, 
	last_consistency_score INTEGER, 
	last_consistency_calculated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE user_tokens (
	id INTEGER NOT NULL, 
	total_tokens INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE wins_log (
	id INTEGER NOT NULL, 
	timestamp DATETIME NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	xp_value INTEGER, 
	token_value INTEGER, 
	PRIMARY KEY (id)
);

CREATE TABLE xp_logs (
	id INTEGER NOT NULL, 
	amount INTEGER NOT NULL, 
	reason VARCHAR(200), 
	created_at DATETIME, 
	PRIMARY KEY (id)
);