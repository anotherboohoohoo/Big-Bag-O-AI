"""
WireFall GUI - v0.2
Improvements over v0.1:
- Proper date/time formatting in logs
- Drag-and-drop app onto Add Rule dialog (auto-fills name & path)
- Inbound / Outbound colour coding in logs
- Path column visible in Rules tab
- Non-blocking popups (no more freeze)
- Array/range support for IPs and ports in manual rules
- Tabbed main window: Rules | Logs | Preferences
- Connection type badge (IN/OUT) in log rows
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, List
import threading
from datetime import datetime
import os
import subprocess


# ── Colour palette ────────────────────────────────────────────────────────────
DARK_BG     = "#1a1a2e"
PANEL_BG    = "#16213e"
ACCENT      = "#0f3460"
GREEN       = "#00d4aa"
RED         = "#e94560"
AMBER       = "#f5a623"
TEXT_MAIN   = "#e8e8f0"
TEXT_DIM    = "#8888aa"
BORDER      = "#2a2a4a"

ALLOW_FG    = GREEN
BLOCK_FG    = RED
IN_BADGE    = "#5b8dee"   # blue  – inbound
OUT_BADGE   = AMBER       # amber – outbound

FONT_MONO   = ("Menlo", 11)
FONT_HEAD   = ("Helvetica Neue", 10, "bold")
FONT_SMALL  = ("Helvetica Neue", 9)
FONT_TITLE  = ("Helvetica Neue", 13, "bold")


def _apply_dark(widget, bg=DARK_BG, fg=TEXT_MAIN):
    """Recursively set dark background/foreground."""
    try:
        widget.configure(bg=bg, fg=fg)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _apply_dark(child, bg, fg)


# ── Main window ───────────────────────────────────────────────────────────────

class FirewallGUI:
    def __init__(self, db, on_mode_change: Optional[Callable] = None):
        self.db = db
        self.on_mode_change = on_mode_change

        self.window = tk.Tk()
        self.window.title("WireFall  ·  v0.2")
        self.window.geometry("1060x660")
        self.window.configure(bg=DARK_BG)
        self.window.minsize(820, 500)

        # ttk dark style
        self._apply_style()
        self._create_widgets()
        self._load_data()

        # Auto-refresh logs every 5 s
        self._schedule_auto_refresh()

    # ── Style ──────────────────────────────────────────────────────────────

    def _apply_style(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")

        style.configure(".",
            background=DARK_BG, foreground=TEXT_MAIN,
            fieldbackground=PANEL_BG, bordercolor=BORDER,
            troughcolor=PANEL_BG, selectbackground=ACCENT,
            selectforeground=TEXT_MAIN, font=FONT_SMALL)

        style.configure("TFrame", background=DARK_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)

        style.configure("TLabel",
            background=DARK_BG, foreground=TEXT_MAIN, font=FONT_SMALL)
        style.configure("Dim.TLabel",
            background=DARK_BG, foreground=TEXT_DIM, font=FONT_SMALL)
        style.configure("Title.TLabel",
            background=DARK_BG, foreground=TEXT_MAIN, font=FONT_TITLE)

        style.configure("TNotebook",
            background=DARK_BG, tabmargins=[2, 4, 2, 0])
        style.configure("TNotebook.Tab",
            background=PANEL_BG, foreground=TEXT_DIM,
            padding=[14, 6], font=FONT_HEAD)
        style.map("TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", TEXT_MAIN)])

        style.configure("Treeview",
            background=PANEL_BG, foreground=TEXT_MAIN,
            fieldbackground=PANEL_BG, rowheight=24,
            borderwidth=0, font=FONT_SMALL)
        style.configure("Treeview.Heading",
            background=ACCENT, foreground=TEXT_MAIN,
            font=FONT_HEAD, relief="flat")
        style.map("Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", TEXT_MAIN)])

        style.configure("TButton",
            background=ACCENT, foreground=TEXT_MAIN,
            padding=[10, 5], font=FONT_SMALL, relief="flat")
        style.map("TButton",
            background=[("active", GREEN), ("pressed", GREEN)],
            foreground=[("active", DARK_BG)])

        style.configure("Allow.TButton",
            background=GREEN, foreground=DARK_BG, font=FONT_HEAD)
        style.map("Allow.TButton",
            background=[("active", "#00b892")])

        style.configure("Block.TButton",
            background=RED, foreground=TEXT_MAIN, font=FONT_HEAD)
        style.map("Block.TButton",
            background=[("active", "#c03050")])

        style.configure("TRadiobutton",
            background=DARK_BG, foreground=TEXT_MAIN, font=FONT_SMALL)
        style.configure("TCheckbutton",
            background=DARK_BG, foreground=TEXT_MAIN, font=FONT_SMALL)
        style.configure("TEntry",
            fieldbackground=PANEL_BG, foreground=TEXT_MAIN,
            insertcolor=GREEN, bordercolor=BORDER)
        style.configure("TScrollbar",
            background=PANEL_BG, troughcolor=DARK_BG, bordercolor=BORDER)

    # ── Widgets ────────────────────────────────────────────────────────────

    def _create_widgets(self):
        # ── Header bar
        header = ttk.Frame(self.window, style="Panel.TFrame")
        header.pack(fill=tk.X)

        ttk.Label(header, text="🔒  WireFall", style="Title.TLabel",
                  padding=[14, 10]).pack(side=tk.LEFT)

        # Mode pills
        mode_frame = ttk.Frame(header, style="Panel.TFrame")
        mode_frame.pack(side=tk.LEFT, padx=20, pady=8)

        ttk.Label(mode_frame, text="Mode:", style="Dim.TLabel",
                  background=PANEL_BG).pack(side=tk.LEFT, padx=(0, 6))

        self.mode_var = tk.StringVar(
            value=self.db.get_setting('default_mode') or 'block')

        ttk.Radiobutton(
            mode_frame, text="⛔  Block All",
            variable=self.mode_var, value='block',
            command=self._on_mode_change,
            style="TRadiobutton"
        ).pack(side=tk.LEFT, padx=4)

        ttk.Radiobutton(
            mode_frame, text="✅  Allow All (log)",
            variable=self.mode_var, value='allow',
            command=self._on_mode_change,
            style="TRadiobutton"
        ).pack(side=tk.LEFT, padx=4)

        # Export buttons (right side)
        ttk.Button(header, text="Export Logs",
                   command=self._export_logs).pack(side=tk.RIGHT, padx=5, pady=8)
        ttk.Button(header, text="Export Rules",
                   command=self._export_rules).pack(side=tk.RIGHT, padx=5, pady=8)

        # ── Notebook
        nb = ttk.Notebook(self.window)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        self.rules_frame = ttk.Frame(nb)
        nb.add(self.rules_frame, text="  Rules  ")
        self._create_rules_tab()

        self.logs_frame = ttk.Frame(nb)
        nb.add(self.logs_frame, text="  Logs  ")
        self._create_logs_tab()

        self.prefs_frame = ttk.Frame(nb)
        nb.add(self.prefs_frame, text="  Preferences  ")
        self._create_prefs_tab()

        # ── Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self.window, textvariable=self.status_var,
            bg=PANEL_BG, fg=TEXT_DIM, anchor=tk.W,
            font=FONT_SMALL, padx=10, pady=4)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ── Rules tab ──────────────────────────────────────────────────────────

    def _create_rules_tab(self):
        cols = ('ID', 'Action', 'App', 'Path', 'Destination', 'Port', 'Created')

        tree_frame = ttk.Frame(self.rules_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        sb = ttk.Scrollbar(tree_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.rules_tree = ttk.Treeview(
            tree_frame, columns=cols, show='headings',
            yscrollcommand=sb.set, selectmode="browse")

        widths = [40, 70, 140, 220, 160, 60, 140]
        for col, w in zip(cols, widths):
            self.rules_tree.heading(col, text=col)
            self.rules_tree.column(col, width=w, minwidth=30)

        # Colour tags
        self.rules_tree.tag_configure('allow',
            foreground=ALLOW_FG, background=PANEL_BG)
        self.rules_tree.tag_configure('block',
            foreground=BLOCK_FG, background=PANEL_BG)

        self.rules_tree.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.rules_tree.yview)

        btn_frame = ttk.Frame(self.rules_frame)
        btn_frame.pack(fill=tk.X, padx=6, pady=4)

        ttk.Button(btn_frame, text="＋  Add Rule",
                   command=self._add_rule_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="✕  Delete",
                   command=self._delete_rule).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="↺  Refresh",
                   command=self._refresh_rules).pack(side=tk.LEFT, padx=4)

    # ── Logs tab ───────────────────────────────────────────────────────────

    def _create_logs_tab(self):
        cols = ('Time', 'Dir', 'App', 'Destination', 'Port', 'Action', 'Repeats')

        # Filter bar
        filter_frame = ttk.Frame(self.logs_frame)
        filter_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

        ttk.Label(filter_frame, text="Filter app:").pack(side=tk.LEFT, padx=(0, 4))
        self.log_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.log_filter_var, width=20)
        filter_entry.pack(side=tk.LEFT, padx=4)
        self.log_filter_var.trace_add("write", lambda *_: self._refresh_logs())

        ttk.Label(filter_frame, text="Action:").pack(side=tk.LEFT, padx=(12, 4))
        self.log_action_filter = tk.StringVar(value="all")
        for val, lbl in [("all", "All"), ("allow", "Allow"), ("block", "Block")]:
            ttk.Radiobutton(filter_frame, text=lbl,
                            variable=self.log_action_filter, value=val,
                            command=self._refresh_logs).pack(side=tk.LEFT, padx=2)

        tree_frame = ttk.Frame(self.logs_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        sb = ttk.Scrollbar(tree_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.logs_tree = ttk.Treeview(
            tree_frame, columns=cols, show='headings',
            yscrollcommand=sb.set, selectmode="browse")

        widths = [155, 50, 140, 180, 55, 70, 60]
        for col, w in zip(cols, widths):
            self.logs_tree.heading(col, text=col)
            self.logs_tree.column(col, width=w, minwidth=30)

        # Colour tags
        self.logs_tree.tag_configure('allow',
            foreground=ALLOW_FG, background=PANEL_BG)
        self.logs_tree.tag_configure('block',
            foreground=BLOCK_FG, background=PANEL_BG)
        self.logs_tree.tag_configure('inbound',
            foreground=IN_BADGE)
        self.logs_tree.tag_configure('outbound',
            foreground=OUT_BADGE)

        self.logs_tree.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.logs_tree.yview)

        btn_frame = ttk.Frame(self.logs_frame)
        btn_frame.pack(fill=tk.X, padx=6, pady=4)

        ttk.Button(btn_frame, text="↺  Refresh",
                   command=self._refresh_logs).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="🗑  Clear Logs",
                   command=self._clear_logs).pack(side=tk.LEFT, padx=4)

        self.log_count_label = ttk.Label(btn_frame, text="", style="Dim.TLabel")
        self.log_count_label.pack(side=tk.RIGHT, padx=8)

    # ── Preferences tab ────────────────────────────────────────────────────

    def _create_prefs_tab(self):
        pad = {"padx": 20, "pady": 8}

        ttk.Label(self.prefs_frame, text="Preferences",
                  style="Title.TLabel").pack(anchor=tk.W, **pad)

        # Poll interval
        row = ttk.Frame(self.prefs_frame)
        row.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(row, text="Connection poll interval (seconds):").pack(
            side=tk.LEFT, padx=(0, 8))
        self.poll_var = tk.StringVar(
            value=self.db.get_setting('poll_interval') or '2')
        e = ttk.Entry(row, textvariable=self.poll_var, width=6)
        e.pack(side=tk.LEFT)

        # Popup timeout
        row2 = ttk.Frame(self.prefs_frame)
        row2.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(row2, text="Popup auto-block timeout (seconds):").pack(
            side=tk.LEFT, padx=(0, 8))
        self.popup_timeout_var = tk.StringVar(
            value=self.db.get_setting('popup_timeout') or '30')
        ttk.Entry(row2, textvariable=self.popup_timeout_var, width=6).pack(
            side=tk.LEFT)

        # DNS lookups toggle
        self.dns_var = tk.BooleanVar(
            value=(self.db.get_setting('dns_lookup') or 'false') == 'true')
        ttk.Checkbutton(
            self.prefs_frame,
            text="Enable reverse DNS lookups (slower, more info)",
            variable=self.dns_var
        ).pack(anchor=tk.W, padx=20, pady=4)

        # Save
        ttk.Button(self.prefs_frame, text="Save Preferences",
                   command=self._save_prefs).pack(anchor=tk.W, padx=20, pady=12)

        ttk.Separator(self.prefs_frame, orient='horizontal').pack(
            fill=tk.X, padx=20, pady=8)

        # Danger zone
        ttk.Label(self.prefs_frame, text="Danger zone",
                  foreground=RED, background=DARK_BG,
                  font=FONT_HEAD).pack(anchor=tk.W, padx=20)
        ttk.Button(self.prefs_frame, text="🗑  Reset ALL rules & logs",
                   command=self._reset_all).pack(anchor=tk.W, padx=20, pady=6)

    def _save_prefs(self):
        try:
            interval = int(self.poll_var.get())
            timeout  = int(self.popup_timeout_var.get())
            self.db.set_setting('poll_interval', str(interval))
            self.db.set_setting('popup_timeout',  str(timeout))
            self.db.set_setting('dns_lookup', 'true' if self.dns_var.get() else 'false')
            self._set_status("Preferences saved ✓")
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "Poll interval and timeout must be whole numbers.")

    def _reset_all(self):
        if messagebox.askyesno("Are you sure?",
                               "This will delete ALL rules and logs permanently.",
                               icon='warning'):
            self.db.clear_logs()
            for r in self.db.get_rules():
                self.db.delete_rule(r['id'])
            self._refresh_rules()
            self._refresh_logs()
            self._set_status("All rules and logs deleted.")

    # ── Data loading ───────────────────────────────────────────────────────

    def _load_data(self):
        self._refresh_rules()
        self._refresh_logs()

    def _refresh_rules(self):
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        rules = self.db.get_rules()
        for rule in rules:
            app  = rule['app_name'] or 'Any'
            path = rule['app_path'] or ''
            dest = rule['destination_ip'] or rule['destination_domain'] or 'Any'
            port = rule['destination_port'] or 'Any'
            tag  = rule['action']   # 'allow' or 'block'

            # Format timestamp nicely
            created = _fmt_ts(rule['created_at'])

            self.rules_tree.insert('', 'end', tags=(tag,), values=(
                rule['id'], rule['action'].upper(),
                app, path, dest, port, created))

        self._set_status(f"{len(rules)} rules loaded")

    def _refresh_logs(self):
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)

        logs = self.db.get_logs(limit=2000)

        app_filter    = self.log_filter_var.get().lower()
        action_filter = self.log_action_filter.get()

        shown = 0
        for log in logs:
            if app_filter and app_filter not in (log['app_name'] or '').lower():
                continue
            if action_filter != 'all' and log['action'] != action_filter:
                continue

            dest      = log['destination_ip'] or log['destination_domain'] or 'Unknown'
            direction = log.get('direction', 'OUT')
            dir_label = "→ OUT" if direction == 'OUT' else "← IN"
            action    = log['action']
            tag       = action  # 'allow' or 'block'

            ts = _fmt_ts(log['timestamp'])

            self.logs_tree.insert('', 'end', tags=(tag,), values=(
                ts,
                dir_label,
                log['app_name'] or '?',
                dest,
                log['destination_port'] or '-',
                action.upper(),
                log['repeat_count']
            ))
            shown += 1

        self.log_count_label.config(text=f"{shown} entries")
        self._set_status(f"{shown} log entries shown")

    # ── Add Rule dialog ────────────────────────────────────────────────────

    def _add_rule_dialog(self, prefill: dict = None):
        """
        Dialog to add a new rule.
        Supports:
        - Drag-and-drop of an .app bundle → auto-fills name & path
        - Comma-separated IPs  (e.g.  10.0.0.1, 10.0.0.2)
        - Port ranges          (e.g.  8080-8090)
        - Comma-separated ports (e.g. 80, 443, 8080)
        """
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Firewall Rule")
        dialog.geometry("480x500")
        dialog.configure(bg=DARK_BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        pad = {"padx": 16, "pady": 4}

        ttk.Label(dialog, text="Add Rule", style="Title.TLabel").pack(
            anchor=tk.W, padx=16, pady=(14, 6))

        # ── Drag-and-drop target
        dnd_frame = tk.Frame(dialog, bg=ACCENT, bd=0, relief=tk.FLAT,
                             cursor="hand2")
        dnd_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

        dnd_label = tk.Label(
            dnd_frame,
            text="  ⬇  Drag an .app here  —  or browse below  ",
            bg=ACCENT, fg=TEXT_MAIN,
            font=FONT_SMALL, pady=8, cursor="hand2")
        dnd_label.pack(fill=tk.X)

        # Fields
        def make_field(label_text, prefill_val=''):
            ttk.Label(dialog, text=label_text).pack(anchor=tk.W, **pad)
            var = tk.StringVar(value=prefill_val or '')
            e = ttk.Entry(dialog, textvariable=var, width=52)
            e.pack(fill=tk.X, padx=16, pady=(0, 2))
            return var

        pf = prefill or {}
        app_name_var   = make_field("Application Name:",
                                     pf.get('app_name', ''))
        app_path_var   = make_field("Application Path  (or drop .app above):",
                                     pf.get('app_path', ''))

        ttk.Label(dialog,
            text="Destination IP(s)  — comma-separated OK, e.g.  1.2.3.4, 5.6.7.8",
            style="Dim.TLabel"
        ).pack(anchor=tk.W, padx=16, pady=(6, 0))
        dest_ip_var = make_field("", pf.get('dest_ip', ''))

        ttk.Label(dialog,
            text="Port(s)  — single, range (80-90), or comma list (80,443,8080)",
            style="Dim.TLabel"
        ).pack(anchor=tk.W, padx=16, pady=(6, 0))
        port_var = make_field("", pf.get('port', ''))

        dest_domain_var = make_field("Destination Domain  (optional):",
                                      pf.get('dest_domain', ''))

        # ── Browse button for app path
        def browse_app():
            path = filedialog.askopenfilename(
                title="Select application",
                filetypes=[("Applications", "*.app"), ("All files", "*.*")],
                initialdir="/Applications")
            if path:
                _fill_app_fields(path, app_name_var, app_path_var)

        ttk.Button(dialog, text="Browse app…",
                   command=browse_app).pack(anchor=tk.W, padx=16, pady=2)

        # ── Drag and drop via tkinter dnd (macOS path via drag)
        def _on_drop(event):
            raw = event.data if hasattr(event, 'data') else ''
            # tkdnd not always available; fallback handled gracefully
            if raw:
                path = raw.strip().strip('{}')
                _fill_app_fields(path, app_name_var, app_path_var)

        # Try to bind tkdnd if available
        try:
            dialog.tk.call('package', 'require', 'tkdnd')
            dnd_frame.drop_target_register('DND_Files')
            dnd_frame.dnd_bind('<<Drop>>', _on_drop)
            dnd_label.config(text="  ⬇  Drop .app here  —  or browse below  ")
        except Exception:
            dnd_label.config(
                text="  (Use Browse button to select app)  ",
                fg=TEXT_DIM)

        # ── Action selector
        ttk.Label(dialog, text="Action:").pack(anchor=tk.W, **pad)
        action_var = tk.StringVar(value=pf.get('action', 'block'))
        af = ttk.Frame(dialog)
        af.pack(anchor=tk.W, padx=16, pady=2)
        ttk.Radiobutton(af, text="⛔  Block",
                        variable=action_var, value='block').pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(af, text="✅  Allow",
                        variable=action_var, value='allow').pack(side=tk.LEFT, padx=8)

        # ── Buttons
        bf = ttk.Frame(dialog)
        bf.pack(fill=tk.X, padx=16, pady=12)

        def save_rules():
            errors = []
            rules_to_add = []

            app_name = app_name_var.get().strip() or None
            app_path = app_path_var.get().strip() or None
            dest_domain = dest_domain_var.get().strip() or None
            action = action_var.get()

            # Parse IPs
            raw_ips = dest_ip_var.get().strip()
            ips = [x.strip() for x in raw_ips.split(',') if x.strip()] if raw_ips else [None]

            # Parse ports
            raw_ports = port_var.get().strip()
            ports = _parse_ports(raw_ports)
            if ports is None:
                errors.append("Port format invalid. Use: 443  or  80-90  or  80,443,8080")

            if errors:
                messagebox.showerror("Input error", "\n".join(errors))
                return

            # Expand all combinations
            for ip in ips:
                for port in (ports or [None]):
                    rules_to_add.append(dict(
                        app_name=app_name,
                        app_path=app_path,
                        dest_ip=ip,
                        dest_domain=dest_domain,
                        dest_port=port,
                        action=action,
                        notes="Added manually v0.2"
                    ))

            for r in rules_to_add:
                self.db.add_rule(**r)

            n = len(rules_to_add)
            self._set_status(f"Added {n} rule{'s' if n > 1 else ''} ✓")
            dialog.destroy()
            self._refresh_rules()

        ttk.Button(bf, text="Save", command=save_rules).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Cancel",
                   command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    # ── Delete rule ────────────────────────────────────────────────────────

    def _delete_rule(self):
        sel = self.rules_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a rule first.")
            return
        rule_id = self.rules_tree.item(sel[0])['values'][0]
        if messagebox.askyesno("Delete rule", f"Delete rule #{rule_id}?"):
            self.db.delete_rule(rule_id)
            self._refresh_rules()

    # ── Clear logs ─────────────────────────────────────────────────────────

    def _clear_logs(self):
        if messagebox.askyesno("Clear logs", "Delete all log entries?"):
            self.db.clear_logs()
            self._refresh_logs()

    # ── Mode change ────────────────────────────────────────────────────────

    def _on_mode_change(self):
        mode = self.mode_var.get()
        self.db.set_setting('default_mode', mode)
        if self.on_mode_change:
            self.on_mode_change(mode)
        label = "Block All" if mode == 'block' else "Allow All (log only)"
        self._set_status(f"Mode → {label}")

    # ── Export ─────────────────────────────────────────────────────────────

    def _export_rules(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All", "*.*")],
            initialfile=f"wf_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        if fp:
            self.db.export_rules_to_markdown(fp)
            self._set_status(f"Rules exported → {fp}")

    def _export_logs(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All", "*.*")],
            initialfile=f"wf_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        if fp:
            self.db.export_logs_to_markdown(fp)
            self._set_status(f"Logs exported → {fp}")

    # ── Status bar ─────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.status_var.set(f"  {msg}")

    # ── Auto refresh ───────────────────────────────────────────────────────

    def _schedule_auto_refresh(self):
        try:
            interval = int(self.db.get_setting('poll_interval') or 5) * 1000
        except (ValueError, TypeError):
            interval = 5000
        self._refresh_logs()
        self.window.after(interval, self._schedule_auto_refresh)

    # ── Run ────────────────────────────────────────────────────────────────

    def run(self):
        self.window.mainloop()

    def destroy(self):
        self.window.destroy()


# ── Connection Popup (non-blocking) ──────────────────────────────────────────

class ConnectionPopup:
    """
    Non-blocking popup for new connection alerts.
    Uses window.after() scheduling instead of wait_window()
    to avoid freezing the main loop.
    """

    def __init__(self, app_name: str, dest_ip: str, dest_port: int,
                 callback: Callable, dest_domain: str = '',
                 direction: str = 'OUT', app_path: str = '',
                 timeout_seconds: int = 30):

        self.callback = callback
        self._decided = False

        win = tk.Toplevel()
        win.title("Connection Alert  —  WireFall")
        win.geometry("460x280")
        win.configure(bg=DARK_BG)
        win.attributes('-topmost', True)
        win.resizable(False, False)
        self.win = win

        # Direction badge colour
        dir_color = IN_BADGE if direction == 'IN' else OUT_BADGE
        dir_text  = "← INBOUND" if direction == 'IN' else "→ OUTBOUND"

        # Header
        hdr = tk.Frame(win, bg=ACCENT)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="  New Connection Attempt",
                 bg=ACCENT, fg=TEXT_MAIN,
                 font=FONT_TITLE, pady=10).pack(side=tk.LEFT)
        tk.Label(hdr, text=f"  {dir_text}  ",
                 bg=dir_color, fg=DARK_BG,
                 font=FONT_HEAD, pady=10).pack(side=tk.RIGHT)

        # Info
        info = tk.Frame(win, bg=DARK_BG)
        info.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        def row(label, value, highlight=False):
            f = tk.Frame(info, bg=DARK_BG)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f"{label}:", bg=DARK_BG, fg=TEXT_DIM,
                     font=FONT_SMALL, width=14, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(f, text=value, bg=DARK_BG,
                     fg=GREEN if highlight else TEXT_MAIN,
                     font=FONT_MONO).pack(side=tk.LEFT)

        row("Application", app_name, highlight=True)
        if app_path:
            row("Path", _truncate(app_path, 42))
        row("Destination", dest_ip)
        if dest_domain:
            row("Domain", dest_domain)
        row("Port", str(dest_port))

        # Remember checkbox
        self.remember_var = tk.BooleanVar(value=True)  # default ON in v0.2
        tk.Checkbutton(
            win, text="Remember this decision (create rule)",
            variable=self.remember_var,
            bg=DARK_BG, fg=TEXT_DIM,
            activebackground=DARK_BG, activeforeground=TEXT_MAIN,
            selectcolor=ACCENT, font=FONT_SMALL
        ).pack(anchor=tk.W, padx=16, pady=2)

        # Countdown label
        self.countdown_var = tk.StringVar(value=f"Auto-block in {timeout_seconds}s")
        tk.Label(win, textvariable=self.countdown_var,
                 bg=DARK_BG, fg=TEXT_DIM, font=FONT_SMALL).pack()

        # Buttons
        bf = tk.Frame(win, bg=DARK_BG)
        bf.pack(fill=tk.X, padx=16, pady=8)

        allow_btn = tk.Button(
            bf, text="✅  Allow",
            bg=GREEN, fg=DARK_BG, activebackground="#00b892",
            font=FONT_HEAD, relief=tk.FLAT, padx=16, pady=6,
            command=lambda: self._decide('allow'))
        allow_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        block_btn = tk.Button(
            bf, text="⛔  Block",
            bg=RED, fg=TEXT_MAIN, activebackground="#c03050",
            font=FONT_HEAD, relief=tk.FLAT, padx=16, pady=6,
            command=lambda: self._decide('block'))
        block_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Countdown ticker
        self._remaining = timeout_seconds
        self._tick()

    def _tick(self):
        if self._decided:
            return
        if self._remaining <= 0:
            self._decide('block')
            return
        self.countdown_var.set(f"Auto-block in {self._remaining}s")
        self._remaining -= 1
        self.win.after(1000, self._tick)

    def _decide(self, action: str):
        if self._decided:
            return
        self._decided = True
        remember = self.remember_var.get()
        try:
            self.win.destroy()
        except Exception:
            pass
        # Fire callback outside Tk event so it never blocks the UI
        threading.Thread(
            target=self.callback,
            args=(action, remember),
            daemon=True
        ).start()

    def show(self):
        """Non-blocking show — returns immediately."""
        # Do NOT call wait_window(); the popup lives on its own.
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_ts(raw: str) -> str:
    """Format an ISO timestamp to human-friendly local format."""
    if not raw:
        return ''
    try:
        dt = datetime.fromisoformat(str(raw))
        return dt.strftime("%d %b %Y  %H:%M:%S")
    except Exception:
        return str(raw)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else '…' + s[-(n - 1):]


def _fill_app_fields(path: str, name_var: tk.StringVar,
                      path_var: tk.StringVar):
    """Given a file-system path, fill app name and path fields."""
    path = path.strip().strip('{}')
    # Resolve .app bundle name
    basename = os.path.basename(path)
    app_name = basename.replace('.app', '')
    name_var.set(app_name)
    path_var.set(path)


def _parse_ports(raw: str):
    """
    Parse a port expression into a list of ints (or None for 'any').
    Accepts:
        ''          → [None]
        '443'       → [443]
        '80-90'     → [80,81,...,90]
        '80,443'    → [80, 443]
        '80,443,8000-8010' → mixed
    Returns None on parse error.
    """
    if not raw.strip():
        return [None]

    ports = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            bounds = part.split('-')
            if len(bounds) != 2:
                return None
            try:
                lo, hi = int(bounds[0]), int(bounds[1])
            except ValueError:
                return None
            if lo > hi or hi > 65535:
                return None
            ports.extend(range(lo, hi + 1))
        else:
            try:
                ports.append(int(part))
            except ValueError:
                return None

    return ports if ports else [None]
