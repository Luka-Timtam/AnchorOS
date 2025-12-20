# AnchorOS CRM

A private, single-user personal CRM and sales management system with integrated gamification features. Built to streamline lead tracking, client management, outreach, and productivity while making the sales process engaging and rewarding.

## Features

### Core CRM
- **Lead Management** - Full CRUD operations with status tracking, conversion workflows, and close reason tracking
- **Client Management** - Track active clients, project types, hosting/SaaS fees, and monthly recurring revenue
- **Outreach Tracking** - Log calls, emails, DMs with outcomes and follow-up scheduling
- **Task Management** - Create, assign, and complete tasks with due dates and priority levels

### Gamification System
- **XP & Levels** - Earn experience points for completing actions, level up to unlock rewards
- **Token System** - In-app currency for purchasing customizable rewards in the Reward Shop
- **Daily Missions** - Gamified challenges to encourage consistent engagement
- **Boss Fights** - Special challenges with bonus rewards
- **Achievements** - Unlock milestones for various accomplishments
- **Streaks** - Track consecutive days of outreach activity
- **Wins Log** - Record and celebrate significant accomplishments

### Productivity Tools
- **Focus Timer** - Pomodoro-style timer for deep work sessions
- **Notes** - Mini notebook with tagging, pinning, and quick capture
- **Goals** - Set and track daily, weekly, and monthly targets
- **Outreach Templates** - Pre-built templates for emails, DMs, and call scripts
- **Calendar** - View tasks, follow-ups, and missions in calendar format

### Analytics & Reporting
- **Dashboard** - Centralized view of leads, revenue, outreach stats, and reminders
- **Analytics** - Charts for revenue, MRR growth, outreach volume, deal pipeline, and win/loss analysis
- **Flex Mode** - Full-screen showcase of lifetime stats with animations
- **Monthly Review** - Performance summaries and insights
- **Activity Timeline** - Unified feed of all user actions grouped by day

### Additional Features
- **Freelancing Tracker** - Track side income from photography, consulting, and other work
- **Mobile Interface** - Responsive mobile version with full feature parity
- **Global Search** - Command palette for quick searching across all data
- **Data Export** - Download all CRM data as CSV files in a ZIP archive
- **Pause Mode** - Temporarily halt gamification without affecting core tasks
- **PWA Support** - Install as an app on iOS/Android home screens

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite with SQLAlchemy ORM
- **Frontend:** Jinja2 templates, Tailwind CSS
- **Charts:** Chart.js
- **Transitions:** Swup.js for smooth page navigation

## Project Structure

```
├── app.py                 # Application factory and configuration
├── models.py              # SQLAlchemy database models
├── blueprints/            # Flask blueprints (modular routes)
│   ├── analytics.py       # Analytics and reporting
│   ├── auth.py            # Authentication
│   ├── battlepass.py      # Battle pass system
│   ├── boss.py            # Boss fight challenges
│   ├── calendar.py        # Calendar views
│   ├── clients.py         # Client management
│   ├── dashboard.py       # Main dashboard
│   ├── focus.py           # Focus timer
│   ├── freelancing.py     # Freelance income tracking
│   ├── gamification.py    # XP, levels, rewards system
│   ├── goals.py           # Goal setting and tracking
│   ├── leads.py           # Lead management
│   ├── missions.py        # Daily missions
│   ├── mobile.py          # Mobile interface
│   ├── monthly_review.py  # Monthly performance reviews
│   ├── notes.py           # Note-taking
│   ├── outreach.py        # Outreach logging
│   ├── outreach_templates.py # Template management
│   ├── rewards.py         # Reward shop
│   ├── search.py          # Global search
│   ├── settings.py        # User settings
│   ├── tasks.py           # Task management
│   └── timeline.py        # Activity timeline
├── templates/             # Jinja2 HTML templates
│   ├── mobile/            # Mobile-specific templates
│   └── ...                # Desktop templates
├── static/                # Static assets (CSS, JS, images)
└── instance/              # SQLite database file
```

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Luka-Timtam/AnchorOS.git
cd AnchorOS
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or using pyproject.toml
pip install .
```

3. Set environment variables:
```bash
export SESSION_SECRET="your-secret-key"
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Deployment

### Production (Gunicorn)
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --workers 4 app:app
```

### Replit
The app is configured for Replit deployment with autoscale support. Use the built-in deployment tools.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION_SECRET` | Secret key for session encryption | `dev-secret-key` |

## API Endpoints

- `GET /health` - Health check endpoint for load balancers
- `GET /internal/run-daily-summary` - Trigger daily summary email (for scheduled tasks)

## License

Private project - All rights reserved.

## Author

Built with passion for sales productivity and gamification.
