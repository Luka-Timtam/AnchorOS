# AnchorOS

## Overview
A private, single-user personal CRM web application named "AnchorOS" designed to manage leads, clients, outreach, and tasks efficiently. It aims to streamline CRM processes, enhance productivity through gamification, and provide insightful analytics for business growth. The application tracks lead progression, client relationships, revenue, and user performance, offering a comprehensive toolkit for individual business development.

## User Preferences
I prefer simple language and clear explanations. I want iterative development, with small, testable changes. Please ask before making any major architectural changes or adding new external dependencies. Do not make changes to the `database.db` file directly. I prefer detailed explanations for complex logic.

## System Architecture
The application is built with Python 3 and Flask, utilizing **Supabase** (PostgreSQL) via REST API for data persistence. Server-rendered HTML templates (Jinja2) are styled with Tailwind CSS (CDN) for a modern, responsive UI. Chart.js is integrated for dynamic dashboard visualizations and comprehensive analytics.

**Database Migration (December 2025):**
- Migrated from SQLAlchemy/SQLite to Supabase REST API
- All database operations use `db_supabase.py` module with `SupabaseModel` base class
- Environment variables: `SUPABASE_URL` and `SUPABASE_ANON_KEY` required
- Legacy `models.py` retained for reference but not used in production

**Key Features:**
*   **Authentication:** Single-password login with session persistence.
*   **Dashboard:** Centralized view of leads, outreach stats, revenue, and follow-up reminders. Includes customizable widgets (show/hide, reorder via modal) and deal closure banners.
*   **Analytics:** Advanced charting and filtering for project revenue, MRR growth, outreach volume, deal pipeline, and win/loss reasons. Includes "Flex Mode" - a full-screen showcase of lifetime power stats with high-impact visuals and confetti animation.
*   **CRM Modules:** Full CRUD for Leads, Clients, Outreach, and Tasks, with detailed tracking and filtering capabilities. Includes lead conversion workflows and comprehensive close reason tracking.
*   **Gamification:** XP system with levels, streaks, achievements, and a reward system (level, milestone, and unlockable rewards). Features a "Wins Log" for tracking significant accomplishments and monthly performance reviews.
*   **Token System & Reward Shop:** In-app currency for purchasing customizable rewards, with a transaction history. Full CRUD: create new rewards, edit existing rewards (name, cost, description), toggle active/inactive, delete, and view transaction history.
*   **Daily Missions & Boss Fights:** Gamified challenges to encourage consistent engagement and reward completion.
*   **Productivity Tools:** Focus Session Timer (Pomodoro-style), Mini Notebook with tagging and pinning, and customizable Goals for daily, weekly, and monthly targets.
*   **Freelancing:** Dedicated section for tracking side income from photography, one-off jobs, consulting, side projects, and cash work. Includes category-based organization, analytics charts (monthly income and category breakdown), and automatic integration with lifetime revenue calculations.
*   **Communication Aids:** Outreach Templates for efficient email, DM, and call script management.
*   **Activity Timeline:** Unified feed of all significant user actions, grouped by day.
*   **Calendar:** Dashboard widget and full-screen modal displaying tasks, follow-ups, and daily missions.
*   **Global Search:** Command palette for quick searching across all application data.
*   **Settings:** Includes "Pause Mode" to temporarily halt gamification elements without affecting core tasks. Features "Data & Safety" section for full data export.
*   **Data Export:** Download all CRM data as a ZIP file containing CSV exports (leads, clients, tasks, notes, outreach logs, revenue entries, activity log, analytics summary).
*   **Confirmation Dialogs:** All destructive actions (delete buttons) require explicit confirmation via modal dialog to prevent accidental data loss.
*   **Daily Summary Email:** Automated email containing performance summaries and upcoming tasks.

**Project Structure:**
The application follows a modular structure with Flask Blueprints separating concerns for different features (e.g., `auth.py`, `leads.py`, `gamification.py`). Templates are organized hierarchically within the `templates/` directory.

## Design System (December 2025)
Dark glassmorphic design with modern aesthetics:

**Brand Colors:**
- Electric Aqua (#31E0F7) - Primary accent, buttons, links
- Porcelain (#FFFDF7) - High emphasis text
- Graphite (#2E2F37) - Base background
- Cinnabar (#EB564E) - Warnings, errors, boss fights

**UI Components:**
- `.glass` / `.glass-card` - Frosted glass panels with backdrop blur and white/10 borders
- `.glass-sidebar` - Fixed left sidebar with glassmorphic styling (260px expanded, 80px collapsed)
- `.sidebar-item` - Navigation items with active states (aqua left border + background)
- `.btn-primary` - Aqua gradient buttons with glow
- `.input-glass` / `.select-glass` - Styled form inputs
- `.pill-aqua` / `.pill-success` / `.pill-warning` - Status indicators
- `.progress-bar-aqua` / `.progress-bar-cinnabar` - Progress bars

**Sidebar Navigation (December 2025):**
- Vertical left-side auto-collapsing sidebar replacing horizontal top nav
- 80px width collapsed, 260px when hovered (no toggle button)
- Hover-to-expand: sidebar expands when mouse enters, collapses when mouse leaves
- Mobile: hamburger menu slides out sidebar overlay
- Contains: Logo, Search button, all nav items, Focus Timer, Settings, Logout

**Typography:**
- Inter font family from Google Fonts
- Text hierarchy: `.text-high` (porcelain), `.text-medium` (gray-400), `.text-low` (gray-500)

## External Dependencies
*   **Python 3:** Core programming language.
*   **Flask:** Web framework.
*   **Supabase:** PostgreSQL database via REST API (replaced SQLAlchemy/SQLite).
*   **Jinja2:** Templating engine.
*   **Tailwind CSS (CDN):** For styling and UI.
*   **Chart.js:** For data visualization and charts.
*   **Swup.js:** For smooth page transitions (native-app-like navigation).
*   **External Scheduler:** (Implied for Daily Summary Email) To trigger the `/internal/run-daily-summary` endpoint.

## Supabase Schema Notes
Key table name mappings (some differ from legacy models):
- `boss_fights` - Uses `month` (YYYY-MM format), `target_value`, `progress_value`, `is_completed`
- `activity_log` - Uses `timestamp`, `action_type`, `related_object_type`
- `outreach_logs` - Plural form
- `freelance_jobs` - Income tracking table

**Query Filter Syntax:**
- NOT IN: `.filter('status', 'not.in', '("closed_won","closed_lost")')`
- IS NOT NULL: `.filter('column', 'not.is', 'null')`
- IS NULL: `.is_('column', 'null')`

**Performance Optimizations (December 2025):**
- Count queries: Use `count='exact'` for totals (e.g., lead/client counts)
- Column-specific selects: Use ONLY for sum/aggregate calculations (e.g., freelance amounts, MRR)
- Full fetches: Always use `select('*')` for queries returning objects to templates
- Query limits: Apply limits (20-50) to list queries to prevent over-fetching
- Query-level filtering: Apply status filters at database level instead of Python

**In-Memory Caching (December 2025):**
- Module: `cache.py` provides simple in-memory caching with TTL (30-60 seconds)
- Cached data: Dashboard MRR/client stats, chart data, lifetime revenue
- Invalidation: Automatic cache clear on client/freelance create/edit/delete
- Functions: `invalidate_client_cache()`, `invalidate_freelance_cache()`, `invalidate_revenue_cache()`
- Logging: Debug-level cache hit/miss logging for troubleshooting
- Dashboard widgets: Staggered fade-in animation (`.widget-animate` class)
- Skeleton CSS: Available via `.skeleton`, `.skeleton-text`, `.skeleton-number` classes

## Page Transitions (December 2025)
- Swup.js integration for smooth, native-app-like page transitions
- Fade + slide animation (0.3s) on content area only
- Electric Aqua (#31E0F7) radial glow overlay during transitions
- Sidebar stays persistent (not animated)
- Form submissions bypass transitions to prevent issues
- Page scripts reinitialize on content replace via `swup.hooks.on('content:replace')`

## Mobile Companion Mode (December 2025)
Separate mobile companion interface at `/mobile/` with its own routing, templates, and navigation.

**Core Principle:**
- Desktop remains completely unchanged
- Mobile is a stripped-down companion tool, not a responsive version
- Auto-redirects mobile devices (detected via User-Agent) to `/mobile/`
- Desktop users can access mobile view at `/mobile/` for testing

**Mobile Companion Features:**
- Leads & Clients: View list, see details, add new, log outreach
- Tasks: View today/overdue/all, mark complete, add tasks
- Calendar: View upcoming tasks and follow-ups
- Notes: View, add quick notes
- Freelancing: View income totals, log new income
- Quick Outreach: Fast outreach logging from home screen
- Basic Stats: Outreach today, streak, lead count, pending tasks

**Navigation:**
- Fixed bottom navigation bar with 6 tabs: Home, Leads, Tasks, Calendar, Income, Notes
- Touch-friendly (48px minimum tap targets)
- No hover interactions, tap-first design

**Excluded from Mobile:**
- Full dashboards and analytics graphs
- Deep settings/configuration pages
- Gamification configuration
- Desktop-style tables
- Complex multi-step workflows

**Technical Implementation:**
- Blueprint: `blueprints/mobile.py` with `/mobile/` prefix
- Templates: `templates/mobile/` directory with `base.html` and page templates
- Mobile detection in `app.py` before_request handler
- Session flag `force_desktop` can override auto-redirect
- URL parameter `?desktop=1` bypasses mobile redirect