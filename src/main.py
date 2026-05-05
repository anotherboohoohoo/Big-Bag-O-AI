"""
WireFall — Main Firewall Controller  v0.2
Entry point for the application.
"""
import sys
import os
import threading
from pathlib import Path

from database import FirewallDB
from pf_controller import PacketFilterController
from connection_monitor import ConnectionMonitor
from ui.gui import FirewallGUI, ConnectionPopup


class FirewallController:
    def __init__(self, db_path: str = "firewall.db"):
        self.db = FirewallDB(db_path)
        self.pf = PacketFilterController()
        self.monitor = ConnectionMonitor(callback=self._on_new_connection)
        self.gui = None

        self.pending_popups: set = set()
        self.popup_lock = threading.Lock()

        print("WireFall v0.2 — controller initialised")

    def start(self):
        print("Starting WireFall…")

        if os.geteuid() != 0:
            print("⚠  Not running as root — some monitoring features limited.")
            print("   Run with:  sudo python3 main.py")

        try:
            interval = int(self.db.get_setting('poll_interval') or 2)
            self.monitor.poll_interval = interval
        except (ValueError, TypeError):
            pass

        self.monitor.start()

        self.gui = FirewallGUI(self.db, on_mode_change=self._on_mode_change)
        print("GUI running…")
        self.gui.run()

        self.stop()

    def stop(self):
        print("Stopping WireFall…")
        self.monitor.stop()
        print("Stopped.")

    def _on_new_connection(self, app_name: str, app_path: str,
                           dest_ip: str, dest_domain: str,
                           dest_port: int, direction: str = 'OUT'):
        mode = self.db.get_setting('default_mode') or 'block'
        rule_match = self.db.check_rule_match(
            app_name, app_path, dest_ip, dest_domain, dest_port)

        if rule_match:
            action, rule_id = rule_match
            self.db.add_log_entry(
                app_name=app_name, app_path=app_path,
                dest_ip=dest_ip, dest_domain=dest_domain,
                dest_port=dest_port, action=action,
                rule_id=rule_id, direction=direction)
            if action == 'block':
                self._block_connection(dest_ip, dest_port)
            print(f"{action.upper()} [{direction}]: {app_name} → {dest_ip}:{dest_port}")

        elif mode == 'block':
            self._show_popup(app_name, app_path, dest_ip,
                             dest_domain, dest_port, direction)
        else:
            self.db.add_log_entry(
                app_name=app_name, app_path=app_path,
                dest_ip=dest_ip, dest_domain=dest_domain,
                dest_port=dest_port, action='allow',
                direction=direction)
            print(f"ALLOW (log) [{direction}]: {app_name} → {dest_ip}:{dest_port}")

    def _show_popup(self, app_name, app_path, dest_ip,
                    dest_domain, dest_port, direction):
        key = (app_name, dest_ip, dest_port, direction)
        with self.popup_lock:
            if key in self.pending_popups:
                return
            self.pending_popups.add(key)

        try:
            timeout = int(self.db.get_setting('popup_timeout') or 30)
        except (ValueError, TypeError):
            timeout = 30

        def on_decision(action: str, remember: bool):
            try:
                rule_id = None
                if remember:
                    rule_id = self.db.add_rule(
                        app_name=app_name, app_path=app_path,
                        dest_ip=dest_ip, dest_domain=dest_domain,
                        dest_port=dest_port, action=action,
                        notes="Created from popup")
                    if self.gui and hasattr(self.gui, '_refresh_rules'):
                        self.gui.window.after(0, self.gui._refresh_rules)

                self.db.add_log_entry(
                    app_name=app_name, app_path=app_path,
                    dest_ip=dest_ip, dest_domain=dest_domain,
                    dest_port=dest_port, action=action,
                    rule_id=rule_id, direction=direction)

                if action == 'block':
                    self._block_connection(dest_ip, dest_port)

                print(f"{action.upper()} [{direction}]: {app_name} → {dest_ip}:{dest_port}")

            finally:
                with self.popup_lock:
                    self.pending_popups.discard(key)

        try:
            popup = ConnectionPopup(
                app_name=app_name,
                dest_ip=dest_ip,
                dest_port=dest_port,
                callback=on_decision,
                dest_domain=dest_domain,
                direction=direction,
                app_path=app_path,
                timeout_seconds=timeout)
            popup.show()
        except Exception as e:
            print(f"Popup error: {e}")
            on_decision('block', False)

    def _block_connection(self, dest_ip: str, dest_port: int):
        try:
            self.pf.block_connection(dest_ip, dest_port)
        except Exception as e:
            print(f"pf block error: {e}")

    def _on_mode_change(self, new_mode: str):
        print(f"Mode → {new_mode}")


def main():
    import argparse
    p = argparse.ArgumentParser(
        description='WireFall — network monitor & firewall v0.2')
    p.add_argument('--db', default='firewall.db', help='Database path')
    args = p.parse_args()

    controller = FirewallController(db_path=args.db)
    try:
        controller.start()
    except KeyboardInterrupt:
        print("\nShutting down…")
        controller.stop()
    except Exception as e:
        print(f"Fatal: {e}")
        import traceback
        traceback.print_exc()
        controller.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
