"""
WireFall GUI - v0.2
(Full GUI implementation - see original gui.py for complete code)
This is a placeholder. Use the full gui.py from the original repository.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, List
import threading
from datetime import datetime
import os
import subprocess


DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT = "#0f3460"
GREEN = "#00d4aa"
RED = "#e94560"
AMBER = "#f5a623"
TEXT_MAIN = "#e8e8f0"
TEXT_DIM = "#8888aa"
BORDER = "#2a2a4a"

ALLOW_FG = GREEN
BLOCK_FG = RED
IN_BADGE = "#5b8dee"
OUT_BADGE = AMBER

FONT_MONO = ("Menlo", 11)
FONT_HEAD = ("Helvetica Neue", 10, "bold")
FONT_SMALL = ("Helvetica Neue", 9)
FONT_TITLE = ("Helvetica Neue", 13, "bold")


def _apply_dark(widget, bg=DARK_BG, fg=TEXT_MAIN):
    """Recursively set dark background/foreground."""
    try:
        widget.configure(bg=bg, fg=fg)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _apply_dark(child, bg, fg)


class FirewallGUI:
    def __init__(self, db, on_mode_change: Optional[Callable] = None):
        self.db = db
        self.on_mode_change = on_mode_change

        self.window = tk.Tk()
        self.window.title("WireFall  ·  v0.2")
        self.window.geometry("1060x660")
        self.window.configure(bg=DARK_BG)
        self.window.minsize(820, 500)

        self._apply_style()
        self._create_widgets()
        self._load_data()
        self._schedule_auto_refresh()

    def _apply_style(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure(".", background=DARK_BG, foreground=TEXT_MAIN,
                      fieldbackground=PANEL_BG, bordercolor=BORDER,
                      troughcolor=PANEL_BG, selectbackground=ACCENT,
                      selectforeground=TEXT_MAIN, font=FONT_SMALL)

    def _create_widgets(self):
        header = ttk.Frame(self.window)
        header.pack(fill=tk.X)
        ttk.Label(header, text="🔒  WireFall", font=FONT_TITLE).pack(side=tk.LEFT, padx=14, pady=10)

    def _load_data(self):
        pass

    def _refresh_rules(self):
        pass

    def _refresh_logs(self):
        pass

    def _schedule_auto_refresh(self):
        self.window.after(5000, self._schedule_auto_refresh)

    def _set_status(self, msg: str):
        pass

    def run(self):
        self.window.mainloop()

    def destroy(self):
        self.window.destroy()


class ConnectionPopup:
    """Non-blocking popup for new connection alerts."""
    def __init__(self, app_name: str, dest_ip: str, dest_port: int,
                 callback: Callable, dest_domain: str = '',
                 direction: str = 'OUT', app_path: str = '',
                 timeout_seconds: int = 30):
        self.callback = callback
        self._decided = False

    def show(self):
        pass
