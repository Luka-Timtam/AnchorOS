-- AnchorOS CRM Database Schema for Supabase/PostgreSQL
-- Converted from SQLite schema

CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    "key" VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    unlocked_at TIMESTAMP
);

CREATE TABLE activity_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    action_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    related_id INTEGER,
    related_object_type VARCHAR(50)
);

CREATE TABLE boss_fights (
    id SERIAL PRIMARY KEY,
    month VARCHAR(7) NOT NULL,
    description TEXT NOT NULL,
    boss_type VARCHAR(50) NOT NULL,
    target_value INTEGER NOT NULL,
    progress_value INTEGER DEFAULT 0,
    reward_tokens INTEGER NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE boss_fight_history (
    id SERIAL PRIMARY KEY,
    boss_fight_id INTEGER NOT NULL REFERENCES boss_fights(id),
    month VARCHAR(7) NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    reward_tokens INTEGER NOT NULL
);

CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    business_name VARCHAR(200),
    niche VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(50),
    source VARCHAR(100),
    status VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_contacted_at TIMESTAMP,
    next_action_date DATE,
    has_website BOOLEAN DEFAULT FALSE,
    website_quality VARCHAR(50),
    demo_site_built BOOLEAN DEFAULT FALSE,
    converted_at TIMESTAMP,
    close_reason VARCHAR(500),
    closed_at TIMESTAMP,
    archived_at TIMESTAMP
);

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    business_name VARCHAR(200),
    contact_email VARCHAR(200),
    phone VARCHAR(50),
    project_type VARCHAR(50),
    start_date DATE,
    amount_charged NUMERIC(10, 2),
    status VARCHAR(50),
    hosting_active BOOLEAN DEFAULT FALSE,
    monthly_hosting_fee NUMERIC(10, 2),
    saas_active BOOLEAN DEFAULT FALSE,
    monthly_saas_fee NUMERIC(10, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    related_lead_id INTEGER REFERENCES leads(id)
);

CREATE TABLE daily_missions (
    id SERIAL PRIMARY KEY,
    mission_date DATE NOT NULL,
    description VARCHAR(200) NOT NULL,
    mission_type VARCHAR(50) NOT NULL,
    target_count INTEGER NOT NULL,
    reward_tokens INTEGER NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    progress_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE focus_sessions (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_minutes INTEGER NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE freelance_jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    amount NUMERIC(10, 2) NOT NULL,
    date_completed DATE,
    client_name VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE goals (
    id SERIAL PRIMARY KEY,
    goal_type VARCHAR(50) NOT NULL,
    period VARCHAR(20) NOT NULL,
    target_value INTEGER,
    is_manual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE level_rewards (
    id SERIAL PRIMARY KEY,
    level_interval INTEGER NOT NULL,
    reward_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE milestone_rewards (
    id SERIAL PRIMARY KEY,
    target_level INTEGER NOT NULL UNIQUE,
    reward_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    unlocked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE monthly_reviews (
    id SERIAL PRIMARY KEY,
    year_month VARCHAR(7) NOT NULL UNIQUE,
    content_json TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL
);

CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    tags VARCHAR(500),
    pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE outreach_logs (
    id SERIAL PRIMARY KEY,
    date DATE,
    type VARCHAR(50),
    lead_id INTEGER REFERENCES leads(id),
    notes TEXT,
    outcome VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE outreach_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(100),
    content TEXT NOT NULL,
    is_favourite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE revenue_rewards (
    id SERIAL PRIMARY KEY,
    target_revenue FLOAT NOT NULL UNIQUE,
    reward_text TEXT NOT NULL,
    reward_icon VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    unlocked_at TIMESTAMP,
    claimed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reward_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    cost INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATE,
    status VARCHAR(50),
    related_lead_id INTEGER REFERENCES leads(id),
    related_client_id INTEGER REFERENCES clients(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE token_transactions (
    id SERIAL PRIMARY KEY,
    amount INTEGER NOT NULL,
    reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE unlocked_rewards (
    id SERIAL PRIMARY KEY,
    reward_type VARCHAR(20) NOT NULL,
    reward_reference_id INTEGER NOT NULL,
    level_achieved INTEGER NOT NULL,
    reward_text TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT NOW(),
    claimed_at TIMESTAMP
);

CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    show_mrr_widget BOOLEAN DEFAULT TRUE,
    show_project_revenue_widget BOOLEAN DEFAULT TRUE,
    show_outreach_widget BOOLEAN DEFAULT TRUE,
    show_deals_widget BOOLEAN DEFAULT TRUE,
    show_consistency_score_widget BOOLEAN DEFAULT TRUE,
    show_forecast_widget BOOLEAN DEFAULT TRUE,
    show_followup_widget BOOLEAN DEFAULT TRUE,
    pause_active BOOLEAN DEFAULT FALSE,
    pause_start DATE,
    pause_end DATE,
    pause_reason TEXT,
    focus_timer_active BOOLEAN DEFAULT FALSE,
    focus_timer_end TIMESTAMP,
    focus_timer_length INTEGER DEFAULT 25,
    dashboard_layout TEXT,
    dashboard_active_widgets TEXT,
    dashboard_order TEXT,
    dashboard_active TEXT
);

CREATE TABLE user_stats (
    id SERIAL PRIMARY KEY,
    current_xp INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    current_outreach_streak_days INTEGER DEFAULT 0,
    longest_outreach_streak_days INTEGER DEFAULT 0,
    last_outreach_date DATE,
    last_consistency_score INTEGER DEFAULT 0,
    last_consistency_calculated_at TIMESTAMP
);

CREATE TABLE user_tokens (
    id SERIAL PRIMARY KEY,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE wins_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    xp_value INTEGER,
    token_value INTEGER
);

CREATE TABLE xp_logs (
    id SERIAL PRIMARY KEY,
    amount INTEGER NOT NULL,
    reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for commonly queried columns
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_next_action_date ON leads(next_action_date);
CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_outreach_logs_date ON outreach_logs(date);
CREATE INDEX idx_activity_log_timestamp ON activity_log(timestamp);
CREATE INDEX idx_daily_missions_date ON daily_missions(mission_date);
