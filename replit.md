# Personal CRM

## Overview
A private, single-user personal CRM web application designed to manage leads, clients, outreach, and tasks efficiently. It aims to streamline CRM processes, enhance productivity through gamification, and provide insightful analytics for business growth. The application tracks lead progression, client relationships, revenue, and user performance, offering a comprehensive toolkit for individual business development.

## User Preferences
I prefer simple language and clear explanations. I want iterative development, with small, testable changes. Please ask before making any major architectural changes or adding new external dependencies. Do not make changes to the `database.db` file directly. I prefer detailed explanations for complex logic.

## System Architecture
The application is built with Python 3 and Flask, utilizing SQLite via SQLAlchemy for data persistence. Server-rendered HTML templates (Jinja2) are styled with Tailwind CSS (CDN) for a modern, responsive UI. Chart.js is integrated for dynamic dashboard visualizations and comprehensive analytics.

**Key Features:**
*   **Authentication:** Single-password login with session persistence.
*   **Dashboard:** Centralized view of leads, outreach stats, revenue, and follow-up reminders. Features a 15-widget system with direct on-dashboard editing: click "Customize Dashboard" to enter edit mode where widgets can be dragged to reorder, hidden with X buttons, and restored from the hidden widgets bar. Widget layout and visibility are persisted in user settings via AJAX.
*   **Analytics:** Advanced charting and filtering for project revenue, MRR growth, outreach volume, deal pipeline, and win/loss reasons. Includes "Flex Mode" - a full-screen showcase of lifetime power stats with high-impact visuals and confetti animation.
*   **CRM Modules:** Full CRUD for Leads, Clients, Outreach, and Tasks, with detailed tracking and filtering capabilities. Includes lead conversion workflows and comprehensive close reason tracking.
*   **Gamification:** XP system with levels, streaks, achievements, and a reward system (level, milestone, and unlockable rewards). Features a "Wins Log" for tracking significant accomplishments and monthly performance reviews.
*   **Token System & Reward Shop:** In-app currency for purchasing customizable rewards, with a transaction history.
*   **Daily Missions & Boss Fights:** Gamified challenges to encourage consistent engagement and reward completion.
*   **Productivity Tools:** Focus Session Timer (Pomodoro-style), Mini Notebook with tagging and pinning, and customizable Goals for daily, weekly, and monthly targets.
*   **Communication Aids:** Outreach Templates for efficient email, DM, and call script management.
*   **Activity Timeline:** Unified feed of all significant user actions, grouped by day.
*   **Calendar:** Dashboard widget and full-screen modal displaying tasks, follow-ups, and daily missions.
*   **Global Search:** Command palette for quick searching across all application data.
*   **Settings:** Includes "Pause Mode" to temporarily halt gamification elements without affecting core tasks.
*   **Daily Summary Email:** Automated email containing performance summaries and upcoming tasks.

**Project Structure:**
The application follows a modular structure with Flask Blueprints separating concerns for different features (e.g., `auth.py`, `leads.py`, `gamification.py`). Templates are organized hierarchically within the `templates/` directory.

## External Dependencies
*   **Python 3:** Core programming language.
*   **Flask:** Web framework.
*   **SQLAlchemy:** ORM for database interaction.
*   **SQLite:** Default database.
*   **Jinja2:** Templating engine.
*   **Tailwind CSS (CDN):** For styling and UI.
*   **Chart.js:** For data visualization and charts.
*   **SortableJS:** For drag-and-drop widget reordering on the dashboard.
*   **External Scheduler:** (Implied for Daily Summary Email) To trigger the `/internal/run-daily-summary` endpoint.

## Recent Changes
*   **December 8, 2025:** Implemented draggable widget system for the dashboard with SortableJS. Added `dashboard_layout` and `dashboard_active_widgets` JSON fields to UserSettings. Created modular widget template partials in `templates/widgets/`. Added AJAX endpoints for saving layout and visibility changes. Includes "Customize Widgets" modal with toggle switches and drag-to-reorder. Reset to default option available. Flex Mode now focuses on revenue and deals, using line chart for 3-month trend.
*   **December 8, 2025:** Expanded widget system from 10 to 15 widgets (added MRR, Project Revenue, Outreach, Deals, Forecast). Completely refactored dashboard customization from modal-based to in-place edit mode. Implemented direct drag-and-drop widget reordering on the dashboard itself. Added edit mode toggle with show/hide controls (X to hide, + to add back widgets). Removed widget grouping; all widgets now operate independently. Fixed JavaScript bugs including undefined variables and null reference errors. Removed "Dashboard Settings" button from analytics page.