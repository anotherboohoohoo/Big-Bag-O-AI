"""
Database handler for firewall rules and connection logs — v0.2
Changes vs v0.1:
- Added 'direction' column to logs (IN / OUT)
- Schema migration: adds column if missing (upgrade-safe)
- get_logs now returns direction
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class FirewallDB:
    def __init__(self, db_path: str = "firewall.db"):
        self.db_path = db_path
        self.init_database()
        self._migrate()

    def init_database(self):
        """Initialize database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                app_path TEXT,
                destination_ip TEXT,
                destination_domain TEXT,
                destination_port INTEGER,
                action TEXT CHECK(action IN ('allow', 'block')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                app_name TEXT NOT NULL,
                app_path TEXT,
                destination_ip TEXT,
                destination_domain TEXT,
                destination_port INTEGER,
                action TEXT CHECK(action IN ('allow', 'block')),
                rule_id INTEGER,
                repeat_count INTEGER DEFAULT 1,
                direction TEXT DEFAULT 'OUT',
                FOREIGN KEY (rule_id) REFERENCES rules(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Defaults
        for key, val in [
            ('default_mode',  'block'),
            ('poll_interval', '2'),
            ('popup_timeout', '30'),
            ('dns_lookup',    'false'),
        ]:
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, val))

        conn.commit()
        conn.close()

    def _migrate(self):
        """Safe schema migration — adds missing columns without breaking existing data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add 'direction' column if missing
        cursor.execute("PRAGMA table_info(logs)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'direction' not in cols:
            cursor.execute(
                "ALTER TABLE logs ADD COLUMN direction TEXT DEFAULT 'OUT'")
            conn.commit()

        conn.close()

    # ── Rules ──────────────────────────────────────────────────────────────

    def add_rule(self, app_name=None, app_path=None,
                 dest_ip=None, dest_domain=None,
                 dest_port=None, action='block', notes='') -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rules
              (app_name, app_path, destination_ip, destination_domain,
               destination_port, action, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (app_name, app_path, dest_ip, dest_domain, dest_port, action, notes))
        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rule_id

    def get_rules(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rules ORDER BY created_at DESC")
        rules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rules

    def delete_rule(self, rule_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
        conn.close()

    def check_rule_match(self, app_name, app_path, dest_ip,
                         dest_domain, dest_port) -> Optional[Tuple[str, int]]:
        """Return (action, rule_id) for best matching rule, or None."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rules")
        rules = cursor.fetchall()
        conn.close()

        best       = None
        best_score = -1

        for rule in rules:
            (rule_id, r_app_name, r_app_path,
             r_dest_ip, r_dest_domain, r_dest_port,
             action, _created, _notes) = rule

            # Each matched criterion adds to specificity score
            score = 0
            if r_app_name  is not None:
                if r_app_name != app_name:
                    continue
                score += 1
            if r_app_path  is not None:
                if r_app_path != app_path:
                    continue
                score += 1
            if r_dest_ip   is not None:
                if r_dest_ip != dest_ip:
                    continue
                score += 2
            if r_dest_domain is not None:
                if r_dest_domain != dest_domain:
                    continue
                score += 2
            if r_dest_port is not None:
                if r_dest_port != dest_port:
                    continue
                score += 3

            if score > best_score:
                best_score = score
                best = (action, rule_id)

        return best

    # ── Logs ───────────────────────────────────────────────────────────────

    def add_log_entry(self, app_name: str, app_path: str = '',
                      dest_ip: str = '', dest_domain: str = '',
                      dest_port: int = 0, action: str = 'block',
                      rule_id: Optional[int] = None,
                      direction: str = 'OUT'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # De-duplicate within 60 s window
        cursor.execute("""
            SELECT id, repeat_count FROM logs
            WHERE app_name = ? AND destination_ip = ? AND destination_port = ?
              AND direction = ?
              AND datetime(timestamp) > datetime('now', '-60 seconds')
            ORDER BY timestamp DESC LIMIT 1
        """, (app_name, dest_ip, dest_port, direction))

        recent = cursor.fetchone()
        if recent:
            log_id, count = recent
            cursor.execute("""
                UPDATE logs SET repeat_count = ?, timestamp = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (count + 1, log_id))
        else:
            cursor.execute("""
                INSERT INTO logs
                  (app_name, app_path, destination_ip, destination_domain,
                   destination_port, action, rule_id, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (app_name, app_path, dest_ip, dest_domain,
                  dest_port, action, rule_id, direction))

        conn.commit()
        conn.close()

    def get_logs(self, limit: int = 2000) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM logs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs

    def clear_logs(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logs")
        conn.commit()
        conn.close()

    # ── Settings ───────────────────────────────────────────────────────────

    def get_setting(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def set_setting(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))
        conn.commit()
        conn.close()

    # ── Export ─────────────────────────────────────────────────────────────

    def export_rules_to_markdown(self, filepath: str):
        rules = self.get_rules()
        with open(filepath, 'w') as f:
            f.write("# WireFall — Rules Export\n\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for rule in rules:
                f.write(f"## Rule #{rule['id']}  —  {rule['action'].upper()}\n\n")
                for field, label in [
                    ('app_name',         'Application'),
                    ('app_path',         'Path'),
                    ('destination_ip',   'Destination IP'),
                    ('destination_domain', 'Domain'),
                    ('destination_port', 'Port'),
                    ('notes',            'Notes'),
                    ('created_at',       'Created'),
                ]:
                    val = rule.get(field)
                    if val:
                        f.write(f"- **{label}**: {val}\n")
                f.write("\n")

    def export_logs_to_markdown(self, filepath: str, limit: int = 2000):
        logs = self.get_logs(limit)
        with open(filepath, 'w') as f:
            f.write("# WireFall — Connection Logs\n\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("| Timestamp | Dir | Application | Destination | Port | Action | Repeats |\n")
            f.write("|-----------|-----|-------------|-------------|------|--------|---------|\n")
            for log in logs:
                f.write(
                    f"| {log['timestamp']} "
                    f"| {log.get('direction','OUT')} "
                    f"| {log['app_name'] or '?'} "
                    f"| {log['destination_ip'] or log['destination_domain'] or '?'} "
                    f"| {log['destination_port'] or '-'} "
                    f"| {log['action']} "
                    f"| {log['repeat_count']} |\n")
