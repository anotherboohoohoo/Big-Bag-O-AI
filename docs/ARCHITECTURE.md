# WireFall Architecture

## Overview

WireFall is a network firewall and connection monitoring tool for macOS. It monitors active connections and allows users to create rules to allow or block traffic.

## Module Structure

```
src/
├── main.py              # Application entry point & controller
├── database/
│   ├── __init__.py
│   └── database.py      # SQLite database operations
├── firewall/
│   ├── __init__.py
│   └── connection_monitor.py  # Connection detection & monitoring
└── ui/
    ├── __init__.py
    └── gui.py           # tkinter GUI
```

## Core Components

### FirewallController (main.py)

- Orchestrates all components
- Handles connection callbacks from monitor
- Manages rule matching and decisions
- Shows popups for unknown connections

### ConnectionMonitor (firewall/connection_monitor.py)

- Monitors active network connections using `lsof`
- Detects connection direction (IN/OUT)
- Parses IPv4 and IPv6 addresses
- Runs in a background thread

### FirewallDB (database/database.py)

- Stores firewall rules
- Logs all connection events
- Manages application settings
- Safe schema migrations

### FirewallGUI (ui/gui.py)

- Dark-themed tkinter interface
- Three main tabs: Rules, Logs, Preferences
- Non-blocking connection popups
- Export functionality (Markdown)

## Data Flow

1. **Connection Detected**: `ConnectionMonitor` finds active connection
2. **Rule Check**: `FirewallDB.check_rule_match()` evaluates existing rules
3. **Rule Found**: Action (allow/block) is applied and logged
4. **Rule Not Found**: In block mode, popup is shown to user
5. **User Decision**: Decision is logged and optional rule is created

## Database Schema

### rules table

| Column | Type | Purpose |
|--------|------|----------|
| id | INTEGER | Primary key |
| app_name | TEXT | Application name |
| app_path | TEXT | Full path to binary |
| destination_ip | TEXT | Target IP address |
| destination_domain | TEXT | Target domain name |
| destination_port | INTEGER | Target port |
| action | TEXT | 'allow' or 'block' |
| created_at | TIMESTAMP | Rule creation time |
| notes | TEXT | User notes |

### logs table

| Column | Type | Purpose |
|--------|------|----------|
| id | INTEGER | Primary key |
| timestamp | TIMESTAMP | Event time |
| app_name | TEXT | Application |
| app_path | TEXT | Application path |
| destination_ip | TEXT | Remote IP |
| destination_domain | TEXT | Remote domain |
| destination_port | INTEGER | Remote port |
| action | TEXT | 'allow' or 'block' |
| rule_id | INTEGER | Matched rule ID |
| repeat_count | INTEGER | Duplicate count |
| direction | TEXT | 'IN' or 'OUT' |

## Threading Model

- **Main Thread**: GUI event loop
- **Monitor Thread**: Connection polling (daemon)
- **Popup Thread**: Decision callbacks (daemon)

Thread-safe operations use locks for popup queue management.

## Design Decisions

1. **No External Dependencies**: Uses Python stdlib (tkinter, sqlite3, subprocess)
2. **Non-blocking Popups**: Prevents GUI freeze during decision waiting
3. **Rule Specificity Scoring**: More specific rules take precedence
4. **Safe Migrations**: Database schema changes don't break existing data
5. **Dark Theme**: Easier on the eyes for security monitoring
