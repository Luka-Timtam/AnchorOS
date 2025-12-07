# Personal CRM

A single-user personal CRM web application for tracking leads, clients, outreach, and tasks.

## Overview

This is a private, single-user CRM tool built with:
- Python 3 + Flask
- SQLite (via SQLAlchemy)
- Server-rendered HTML templates (Jinja2)
- Tailwind CSS (CDN)
- Chart.js for dashboard visualizations

## Authentication

- Simple single-password login system
- Password stored in `CRM_PASSWORD` environment variable
- 30-day session persistence
- All routes protected except `/login`

## Features

### Dashboard (/)
- Lead counts by status
- New leads this week/month
- Outreach stats (today/week/month)
- New clients this month
- Project revenue this month
- MRR tracking (hosting + SaaS)
- 3-month revenue forecast
- Charts: Outreach per week, Deals closed per week (last 12 weeks)
- Follow-up reminders: Today and Overdue counts (clickable)
- Customizable widgets via settings

### Analytics (/analytics)
- Advanced charts with filters (date range, niche, source, status)
- Monthly project revenue chart (bar, last 12 months)
- MRR growth chart (line, hosting/SaaS/total, last 12 months)
- Outreach volume per week (last 12 weeks)
- Deals closed per week (last 12 weeks)
- Lead pipeline chart (by status)
- 3-month revenue forecast breakdown
- Follow-up reminders: Today and Overdue counts
- Dashboard widget settings page (/analytics/settings)

### Leads (/leads)
- Full CRUD operations
- Filters: status, niche, source, text search, follow-up (today/overdue)
- Quick status update dropdown
- Convert lead to client functionality
- Lead detail page with outreach history
- Website tracking: has_website (yes/no), website_quality (multiple issues: outdated, poor_design, not_mobile_friendly, slow_loading, broken_features)
- Demo site built tracker visible on leads index
- Converted leads shown in separate section at bottom of page
- Auto-redirect to conversion form when status set to "closed_won"
- Next action date for follow-up scheduling

### Clients (/clients)
- Full CRUD operations
- Filters: status, project type, hosting/SaaS active
- Revenue tracking (project + recurring)
- Client detail page with revenue summary

### Outreach (/outreach)
- Log outreach activities (email, call, DM, in-person, other)
- Link to leads (optional)
- Track outcomes (contacted, booked_call, no_response, closed_won, closed_lost, follow_up_set)
- Filters: type, outcome, date range
- Stats: today/week/month counts

### Tasks (/tasks)
- Add tasks with due dates
- Link to leads or clients (optional)
- Status tracking (open, in_progress, done)
- Overdue and Due Today sections highlighted
- Completed tasks shown in separate section at bottom
- Filters: status, due date

### Gamification (/gamification)
- XP system with levels (1-15)
- XP earned from:
  - Outreach log: +5 XP
  - Lead contacted: +4 XP
  - Call booked: +8 XP
  - Proposal sent: +12 XP
  - Deal closed: +30 XP
  - Task completed: +8 XP
  - Daily goal hit: +10 XP
  - Weekly goal hit: +25 XP
  - Monthly revenue goal hit: +50 XP
  - 10-day streak: +20 XP (one-time)
  - 30-day streak: +50 XP (one-time)
- Level thresholds: 0, 150, 400, 800, 1400, 2200, 3200, 4500, 6500, 9000, 12000, 16000, 20000, 25000, 30000
- Outreach streak tracking (current and longest)
- Consistency score (0-100) based on last 7 days
- Achievements system with unlock tracking
- Charts: XP gained this week, consistency breakdown
- Reward System:
  - Level interval rewards (recurring): Rewards earned every X levels (e.g., every 2 levels)
  - Milestone rewards (one-time): Rewards for reaching specific levels (e.g., level 10, 25, 50)
  - Upcoming rewards section shows next rewards to earn
  - Unlocked rewards history
  - Reward settings: Add, toggle, delete level and milestone rewards

### Token System & Reward Shop (/rewards)
- Separate token currency from XP for purchasing rewards
- Token earning:
  - Outreach log: +1 token
  - Lead contacted: +1 token
  - Task completed: +1 token
  - Proposal sent: +2 tokens
  - Daily goal hit: +3 tokens
  - Weekly goal hit: +7 tokens
  - Streak bonuses: +5/+10/+20/+30 tokens (3/7/14/30 days)
  - Daily mission completion: variable tokens
- Reward Shop with customizable items
- Default rewards: lollies (8), coffee (10), gaming time (12), lunch treat (20), car care (50), t-shirt (75)
- Add/edit/toggle/delete rewards
- Transaction history tracking

### Daily Missions (/missions)
- One random mission generated per day
- Mission types: outreach count, contact leads, complete tasks, message old leads
- Progress tracking with visual progress bar
- Token rewards upon completion (4-8 tokens)
- Past 7 days mission history
- Auto-reset at midnight

### Boss Fight Mode (/boss)
- Monthly boss challenges with big token rewards (50-150 tokens)
- Boss types: close deals, send outreaches, revive cold leads, send proposals
- Auto-generated at start of each month
- Progress tracking with visual progress bar
- "Boss Defeated!" notification when completed
- Past bosses history with completion status
- Dashboard integration with boss battle card

### Settings (/settings)
- Full settings page with Pause Mode feature
- Pause Mode (1-14 days duration, requires reason):
  - Freezes: outreach streak, consistency score, daily goals, daily missions
  - Does NOT freeze: tasks (still become overdue), boss fights
  - Dashboard banner when pause is active
- Theme Settings (coming soon)
- Sound Settings (coming soon)
- Notifications (coming soon)

### Goals (/goals)
- Set daily/weekly/monthly targets
- Goal types: daily outreach, weekly outreach, monthly revenue, monthly deals
- Auto-generated recommended goals based on historical data
- Manual override with "Keep manual" option
- Reset to recommended functionality

### Outreach Templates (/outreach-templates)
- Full CRUD for email, DM, and call script templates
- Categories: email, dm, call
- Subcategories: cold_outreach, follow_up, cold_call_script, objection_handling, booking_confirmation, proposal, other
- Filters by category, subcategory, and text search
- Copy to clipboard functionality
- Favourite toggle for quick access
- Templates sorted by favourite status and last updated

### Daily Summary Email
- Automated endpoint: GET /internal/run-daily-summary
- Sends Mon-Fri at scheduled time (via external scheduler)
- Includes: follow-ups due, overdue, tasks due, outreach stats, streak/XP/level, MRR snapshot
- Monday emails include weekly summary: outreach count, deals closed, revenue
- Requires CRM_EMAIL env var for recipient
- Optional INTERNAL_API_TOKEN for automated access

## Project Structure

```
├── app.py                 # Main Flask application
├── models.py              # SQLAlchemy database models
├── blueprints/
│   ├── auth.py              # Authentication routes
│   ├── dashboard.py         # Dashboard with stats
│   ├── leads.py             # Lead management
│   ├── clients.py           # Client management
│   ├── outreach.py          # Outreach logging
│   ├── tasks.py             # Task management
│   ├── analytics.py         # Analytics and settings
│   ├── gamification.py      # XP, streaks, achievements
│   ├── goals.py             # Goal setting and tracking
│   ├── outreach_templates.py # Email/DM/Call templates
│   └── internal.py          # Internal API endpoints
├── templates/
│   ├── base.html         # Base template with nav
│   ├── login.html        # Login page
│   ├── dashboard.html    # Dashboard view
│   ├── leads/            # Lead templates
│   ├── clients/          # Client templates
│   ├── outreach/         # Outreach templates
│   ├── tasks/            # Task templates
│   ├── analytics/           # Analytics templates
│   ├── gamification/        # Gamification templates
│   ├── goals/               # Goals templates
│   └── outreach_templates/  # Template management pages
└── database.db              # SQLite database (auto-created)
```

## Environment Variables

- `CRM_PASSWORD`: Required password for login
- `SESSION_SECRET`: Flask session secret key

## Running the Application

```bash
python app.py
```

The application runs on port 5000.

## Database

SQLite database with 17 tables:
- leads: Lead tracking with status pipeline
- clients: Client info with project and recurring revenue
- outreach_logs: Outreach activity logging
- tasks: Task management with due dates
- user_settings: Dashboard widget visibility preferences
- user_stats: XP, level, streak tracking (single row)
- achievements: Achievement definitions and unlock status
- goals: Goal targets (daily outreach, weekly outreach, monthly revenue, monthly deals)
- xp_logs: XP gain history for tracking
- outreach_templates: Email, DM, and call script templates
- level_rewards: Recurring rewards at level intervals (e.g., every 2 levels)
- milestone_rewards: One-time rewards at specific levels (e.g., level 10, 25)
- unlocked_rewards: History of all earned rewards
- user_tokens: Token balance tracking (single row)
- token_transactions: Log of all token gains and spends
- reward_items: Shop items that can be purchased with tokens
- daily_missions: Daily mission tracking with progress
- boss_fights: Monthly boss challenges
- boss_fight_history: Record of defeated bosses

Tables are auto-created on first run.
