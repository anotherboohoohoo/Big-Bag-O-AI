# 🌈 NETWORK NERDATHRON 3000™
### "Keep on Truckin'... But Ask Permission First!"

The grooviest, most psychedelic network firewall monitor in the known universe.

---

## 📦 Installation (one-time)

```bash
pip install PyQt6 psutil
```

Or if you use pip3:
```bash
pip3 install PyQt6 psutil
```

---

## 🚀 Running

**Monitoring-only mode** (no root needed):
```bash
python3 nerdathron3000.py
```

**Full mode** — monitoring + connection termination (recommended):
```bash
sudo python3 nerdathron3000.py
```

---

## 🎨 What You Get

| Panel | What it does |
|-------|-------------|
| ⚡ **Live Connections** | Real-time table of all active network connections |
| 🚨 **Alert Dialog** | Pop-up whenever an *unknown* process connects — you decide! |
| 📋 **Rules** | All your allow/deny rules, deletable, refreshable |
| 📓 **Log** | Full scrollable history of every connection attempt, filterable |
| 📊 **Stats** | Top processes, top IPs, top ports, recent denies |

---

## 🔒 How the Alert System Works

When a **new connection** is detected and **no matching rule exists**:

1. A **flashing pop-up dialog** appears (stays on top!)
2. You see: process name, remote IP, port, protocol, direction, timestamp
3. You choose: **ALLOW** ✅ or **DENY** 🚫
4. You pick a **scope**: this IP only / this IP+port / any IP
5. You pick a **duration**: once / 1 hour / 24 hours / 1 week / forever
6. The rule is saved and applied to all future matching connections

Known connections (already have a rule) are handled **silently** in the background.

---

## 📁 Data Location

All data is stored in:
```
~/.nerdathron3000/traffic.db
```

This is a standard SQLite database — you can open it with any SQLite browser.

---

## ⚠️ Limitations (vs. Little Snitch)

| Feature | Nerdathron 3000 | Little Snitch |
|---------|----------------|---------------|
| Monitor connections | ✅ | ✅ |
| Alert for new connections | ✅ | ✅ |
| Create allow/deny rules | ✅ | ✅ |
| Full traffic log | ✅ | ✅ |
| **Block BEFORE connection** | ⚠️ Needs kernel ext | ✅ |
| Terminate denied process | ✅ (with sudo) | ✅ |

True pre-connection blocking requires a kernel extension (like Little Snitch uses).
Nerdathron 3000 catches connections as they're established and can terminate the process.

---

## 🎸 Frank Zappa would be proud.
