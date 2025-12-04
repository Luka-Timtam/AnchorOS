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
- XP system with levels (1-10)
- XP earned from: outreach (+5), lead status changes (+3/7/10), deals closed (+20), tasks completed (+8)
- Outreach streak tracking (current and longest)
- Consistency score (0-100) based on last 7 days
- Achievements system with unlock tracking
- Charts: XP gained this week, consistency breakdown

### Goals (/goals)
- Set daily/weekly/monthly targets
- Goal types: daily outreach, weekly outreach, monthly revenue, monthly deals
- Auto-generated recommended goals based on historical data
- Manual override with "Keep manual" option
- Reset to recommended functionality

## Project Structure

```
├── app.py                 # Main Flask application
├── models.py              # SQLAlchemy database models
├── blueprints/
│   ├── auth.py           # Authentication routes
│   ├── dashboard.py      # Dashboard with stats
│   ├── leads.py          # Lead management
│   ├── clients.py        # Client management
│   ├── outreach.py       # Outreach logging
│   ├── tasks.py          # Task management
│   ├── analytics.py      # Analytics and settings
│   ├── gamification.py   # XP, streaks, achievements
│   └── goals.py          # Goal setting and tracking
├── templates/
│   ├── base.html         # Base template with nav
│   ├── login.html        # Login page
│   ├── dashboard.html    # Dashboard view
│   ├── leads/            # Lead templates
│   ├── clients/          # Client templates
│   ├── outreach/         # Outreach templates
│   ├── tasks/            # Task templates
│   ├── analytics/        # Analytics templates
│   ├── gamification/     # Gamification templates
│   └── goals/            # Goals templates
└── database.db           # SQLite database (auto-created)
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

SQLite database with 9 tables:
- leads: Lead tracking with status pipeline
- clients: Client info with project and recurring revenue
- outreach_logs: Outreach activity logging
- tasks: Task management with due dates
- user_settings: Dashboard widget visibility preferences
- user_stats: XP, level, streak tracking (single row)
- achievements: Achievement definitions and unlock status
- goals: Goal targets (daily outreach, weekly outreach, monthly revenue, monthly deals)
- xp_logs: XP gain history for tracking

Tables are auto-created on first run.
