# Setup Guide for WireFall

## System Requirements

- **OS**: macOS (currently tested on macOS 12+)
- **Python**: 3.8 or later
- **Permissions**: Root/sudo access required for firewall operations

## Installation

### From Source

```bash
git clone https://github.com/anotherboohoohoo/Big-Bag-O-AI.git
cd Big-Bag-O-AI
pip install -r requirements.txt
```

## Running WireFall

```bash
sudo python3 -m src.main
```

Or if installed as a package:

```bash
sudo wirefall
```

## Database

WireFall uses SQLite for storing rules and logs. The database file is created automatically:

- **Location**: `firewall.db` (in the working directory)
- **Specify custom path**: `python3 -m src.main --db /path/to/custom.db`

## Configuration

Configuration is stored in the database `settings` table:

| Key | Default | Description |
|-----|---------|-------------|
| `default_mode` | `block` | Default mode: 'block' or 'allow' |
| `poll_interval` | `2` | Connection poll interval in seconds |
| `popup_timeout` | `30` | Auto-block timeout in seconds |
| `dns_lookup` | `false` | Enable reverse DNS lookups |

These can be modified through the Preferences tab in the GUI.

## Troubleshooting

### Permission Denied

WireFall requires root privileges for packet filtering:

```bash
sudo python3 -m src.main
```

### GUI Won't Start

Ensure tkinter is installed (usually included with Python):

```bash
python3 -m tkinter  # Test if tkinter works
```

### Connection Monitor Not Working

- Ensure `lsof` is available: `which lsof`
- Run with sudo for full monitoring capabilities

## Uninstallation

```bash
rm -rf firewall.db  # Delete database (optional)
```
