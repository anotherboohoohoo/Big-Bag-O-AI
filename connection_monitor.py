"""
Connection Monitor — v0.2
Changes vs v0.1:
- Detects inbound (LISTEN / ESTABLISHED incoming) vs outbound connections
- Passes 'direction' (IN / OUT) to callback
- Slightly smarter lsof parsing to handle IPv6 better
"""
import time
import threading
import subprocess
import re
from typing import Callable, Set, Optional


class ConnectionMonitor:
    def __init__(self, callback: Callable):
        """
        callback signature:
            callback(app_name, app_path, dest_ip, dest_domain,
                     dest_port, direction)
        direction: 'IN' or 'OUT'
        """
        self.callback       = callback
        self.running        = False
        self.monitor_thread = None
        self.seen_connections: Set[tuple] = set()
        self.poll_interval  = 2  # seconds; overridable from prefs

    def start(self):
        if self.running:
            return
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Connection monitor started")

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Connection monitor stopped")

    def _monitor_loop(self):
        while self.running:
            try:
                for conn in self._get_active_connections():
                    sig = (
                        conn['app_name'],
                        conn['destination_ip'],
                        conn['destination_port'],
                        conn['direction'],
                    )
                    if sig not in self.seen_connections:
                        self.seen_connections.add(sig)
                        self.callback(
                            app_name   = conn['app_name'],
                            app_path   = conn.get('app_path', ''),
                            dest_ip    = conn['destination_ip'],
                            dest_domain= conn.get('destination_domain', ''),
                            dest_port  = conn['destination_port'],
                            direction  = conn['direction'],
                        )

                # Avoid unbounded growth
                if len(self.seen_connections) > 10_000:
                    self.seen_connections.clear()

            except Exception as e:
                print(f"Monitor loop error: {e}")

            time.sleep(self.poll_interval)

    def _get_active_connections(self) -> list:
        try:
            result = subprocess.run(
                ['lsof', '-i', '-n', '-P'],
                capture_output=True, text=True,
                check=False, timeout=5)
        except subprocess.TimeoutExpired:
            print("lsof timed out")
            return []
        except Exception as e:
            print(f"lsof error: {e}")
            return []

        connections = []
        lines = result.stdout.splitlines()[1:]   # skip header

        for line in lines:
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue

            command  = parts[0]
            pid      = parts[1]
            conn_str = parts[8]

            direction = self._detect_direction(conn_str)
            if direction is None:
                continue   # LISTEN / UDP / other → skip

            remote = self._parse_remote(conn_str)
            if remote is None:
                continue

            remote_ip, remote_port = remote
            app_path = self._get_app_path(pid) or ''

            connections.append({
                'app_name':          command,
                'app_path':          app_path,
                'pid':               pid,
                'destination_ip':    remote_ip,
                'destination_domain':'',
                'destination_port':  remote_port,
                'direction':         direction,
            })

        return connections

    # ── Helpers ──────────────────────────────────────────────────────────

    def _detect_direction(self, conn_str: str) -> Optional[str]:
        """
        Returns 'OUT', 'IN', or None (skip).

        lsof NAME column examples:
          192.168.1.1:12345->93.184.216.34:443 (ESTABLISHED)   → OUT
          192.168.1.1:22<-10.0.0.5:51234  (ESTABLISHED)        → IN (rare lsof fmt)
          *:8080 (LISTEN)                                        → skip
        """
        if '->' not in conn_str:
            return None
        status = ''
        if '(' in conn_str:
            status = conn_str[conn_str.rfind('('):].upper()
        if 'LISTEN' in status:
            return None
        if 'ESTABLISHED' in status or 'SYN_SENT' in status or 'SYN_RECV' in status:
            # lsof always shows local->remote for ESTABLISHED on macOS.
            # We distinguish by comparing local port vs remote port heuristic:
            # remote port well-known (< 1024 or 443/80) → outbound
            # local port well-known → inbound
            try:
                addr_part = conn_str.split()[0]
                local_str, remote_str = addr_part.split('->', 1)
                local_port  = int(local_str.rsplit(':', 1)[-1])
                remote_port = int(remote_str.rsplit(':', 1)[-1])
                if remote_port < 1024 or remote_port in (80, 443, 8080, 8443):
                    return 'OUT'
                if local_port < 1024:
                    return 'IN'
                # Ephemeral local port → outbound
                return 'OUT' if local_port > remote_port else 'IN'
            except Exception:
                return 'OUT'
        return None

    def _parse_remote(self, conn_str: str) -> Optional[tuple]:
        """Extract (remote_ip, remote_port) from lsof NAME field."""
        try:
            addr_part = conn_str.split()[0]   # strip status like (ESTABLISHED)
            _, remote = addr_part.split('->', 1)
            if remote.startswith('['):
                # IPv6: [addr]:port
                m = re.match(r'\[([^\]]+)\]:(\d+)', remote)
                if m:
                    return m.group(1), int(m.group(2))
            else:
                ip, port = remote.rsplit(':', 1)
                return ip, int(port)
        except Exception:
            pass
        return None

    def _get_app_path(self, pid: str) -> Optional[str]:
        try:
            r = subprocess.run(
                ['ps', '-p', pid, '-o', 'comm='],
                capture_output=True, text=True,
                check=False, timeout=2)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None
