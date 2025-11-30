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

### Leads (/leads)
- Full CRUD operations
- Filters: status, niche, source, text search
- Quick status update dropdown
- Convert lead to client functionality
- Lead detail page with outreach history

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
- Filters: status, due date

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
│   └── tasks.py          # Task management
├── templates/
│   ├── base.html         # Base template with nav
│   ├── login.html        # Login page
│   ├── dashboard.html    # Dashboard view
│   ├── leads/            # Lead templates
│   ├── clients/          # Client templates
│   ├── outreach/         # Outreach templates
│   └── tasks/            # Task templates
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

SQLite database with 4 tables:
- leads: Lead tracking with status pipeline
- clients: Client info with project and recurring revenue
- outreach_logs: Outreach activity logging
- tasks: Task management with due dates

Tables are auto-created on first run.
