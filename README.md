# Forza UDP Python

A small Python logger for Forza Data Out UDP telemetry.

This first version targets the Forza Horizon packet layout and writes each
session as plain files:

- `telemetry.csv`
- `telemetry.jsonl`
- `run.log`

No dashboard, web server, screen capture, model training, or external Python
packages are included.

## Run

```powershell
python main.py
```

If Windows intercepts `python` with the Microsoft Store alias, run the same
command with your full Python interpreter path or fix Python in `PATH`.

Default settings live at the top of `main.py`:

```python
HOST = "0.0.0.0"
PORT = 9999
OUTPUT_DIR = "data"
QUIET = False
DEBUG = False
```

Each run creates:

```text
data/YYYYMMDD_HHMMSS/
  telemetry.csv
  telemetry.jsonl
  run.log
```

## Forza Setup

In Forza HUD/gameplay options:

1. Enable Data Out.
2. Set the Data Out IP address to this computer's LAN IP.
3. Set the Data Out port to `9999`.

If Forza is running on the same PC, try the machine LAN IP first. Some Forza
titles do not send Data Out traffic to `127.0.0.1`.

## Data

Every output row includes local receive metadata:

- `received_time_ns`
- `received_time_iso`
- `packet_size`

The remaining columns are parsed telemetry values such as:

- `Speed`
- `CurrentEngineRpm`
- `Gear`
- `Accel`
- `Brake`
- `Steer`

The parser returns a plain Python `dict`, so later dataset code can import
`parse_packet` or `parse_horizon_packet` from `packet_format.py`.

## Test

Run the parser tests:

```powershell
python -m unittest
```

## References

- Forza official Data Out field order:
  <https://forums.forza.net/t/forza-motorsport-7-data-out-feature-details/74013>
- Reference project:
  <https://github.com/richstokes/Forza-data-tools>
