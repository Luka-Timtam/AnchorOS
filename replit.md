# AnchorOS

## Overview
A private, single-user personal CRM web application named "AnchorOS" designed to manage leads, clients, outreach, and tasks efficiently. It aims to streamline CRM processes, enhance productivity through gamification, and provide insightful analytics for business growth. The application tracks lead progression, client relationships, revenue, and user performance, offering a comprehensive toolkit for individual business development.

## User Preferences
I prefer simple language and clear explanations. I want iterative development, with small, testable changes. Please ask before making any major architectural changes or adding new external dependencies. Do not make changes to the `database.db` file directly. I prefer detailed explanations for complex logic.

## System Architecture
The application is built with Python 3 and Flask, utilizing SQLite via SQLAlchemy for data persistence. Server-rendered HTML templates (Jinja2) are styled with Tailwind CSS (CDN) for a modern, responsive UI. Chart.js is integrated for dynamic dashboard visualizations and comprehensive analytics.

**Key Features:**
*   **Authentication:** Single-password login with session persistence.
*   **Dashboard:** Centralized view of leads, outreach stats, revenue, and follow-up reminders. Includes customizable widgets (show/hide, reorder via modal) and deal closure banners.
*   **Analytics:** Advanced charting and filtering for project revenue, MRR growth, outreach volume, deal pipeline, and win/loss reasons. Includes "Flex Mode" - a full-screen showcase of lifetime power stats with high-impact visuals and confetti animation.
*   **CRM Modules:** Full CRUD for Leads, Clients, Outreach, and Tasks, with detailed tracking and filtering capabilities. Includes lead conversion workflows and comprehensive close reason tracking.
*   **Gamification:** XP system with levels, streaks, achievements, and a reward system (level, milestone, and unlockable rewards). Features a "Wins Log" for tracking significant accomplishments and monthly performance reviews.
*   **Token System & Reward Shop:** In-app currency for purchasing customizable rewards, with a transaction history.
*   **Daily Missions & Boss Fights:** Gamified challenges to encourage consistent engagement and reward completion.
*   **Productivity Tools:** Focus Session Timer (Pomodoro-style), Mini Notebook with tagging and pinning, and customizable Goals for daily, weekly, and monthly targets.
*   **Freelancing:** Dedicated section for tracking side income from photography, one-off jobs, consulting, side projects, and cash work. Includes category-based organization, analytics charts (monthly income and category breakdown), and automatic integration with lifetime revenue calculations.
*   **Communication Aids:** Outreach Templates for efficient email, DM, and call script management.
*   **Activity Timeline:** Unified feed of all significant user actions, grouped by day.
*   **Calendar:** Dashboard widget and full-screen modal displaying tasks, follow-ups, and daily missions.
*   **Global Search:** Command palette for quick searching across all application data.
*   **Settings:** Includes "Pause Mode" to temporarily halt gamification elements without affecting core tasks.
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
*   **SQLAlchemy:** ORM for database interaction.
*   **SQLite:** Default database.
*   **Jinja2:** Templating engine.
*   **Tailwind CSS (CDN):** For styling and UI.
*   **Chart.js:** For data visualization and charts.
*   **Swup.js:** For smooth page transitions (native-app-like navigation).
*   **External Scheduler:** (Implied for Daily Summary Email) To trigger the `/internal/run-daily-summary` endpoint.

## Page Transitions (December 2025)
- Swup.js integration for smooth, native-app-like page transitions
- Fade + slide animation (0.3s) on content area only
- Electric Aqua (#31E0F7) radial glow overlay during transitions
- Sidebar stays persistent (not animated)
- Form submissions bypass transitions to prevent issues
- Page scripts reinitialize on content replace via `swup.hooks.on('content:replace')`

## Mobile Optimization (December 2025)
CSS-only responsive design with dedicated `static/mobile.css` file.

**Breakpoints:**
- Desktop: ≥769px (unchanged, all existing styles preserved)
- Mobile: ≤768px (mobile-specific overrides only)

**Key Mobile Features:**
- Hamburger menu for sidebar navigation (slides out as overlay)
- Tables convert to stacked card layouts using `data-label` attributes
- Forms stack vertically with larger touch targets (48px min-height)
- Grid layouts collapse to single column
- Typography scaled for mobile readability
- No horizontal scrolling

**Implementation Rules:**
- All mobile styles in `static/mobile.css` using `@media (max-width: 768px)`
- Desktop CSS never modified - mobile uses overrides only
- No JavaScript-based layout switching
- Tables require `mobile-card-table` class on `<table>` and `data-label="Column Name"` on each `<td>` for card labels
- Action buttons wrapped in `<div class="flex flex-wrap gap-2">` for mobile

**Mobile Utility Classes:**
- `.mobile-hidden` - Hide on mobile only
- `.mobile-only` - Show on mobile only
- `.mobile-full` - Full width on mobile
- `.mobile-stack` - Stack flex items vertically on mobile