# Directory Structure

**Analysis Date:** 2026-03-15

## Top-Level Layout

```
came_connect/
├── custom_components/came_connect/   # HA integration (production code)
│   ├── __init__.py                   # Integration setup, coordinator, lifecycle
│   ├── api.py                        # OAuth2 client + WebSocket client
│   ├── hub.py                        # In-memory state snapshot (CameEventHub)
│   ├── config_flow.py                # Config + options flow
│   ├── const.py                      # Constants, phase codes, URLs, platform list
│   ├── cover.py                      # Gate cover entity (open/close/stop)
│   ├── sensor.py                     # Phase, position, last seen, error sensors
│   ├── binary_sensor.py              # Moving state, hub online binary sensors
│   ├── manifest.json                 # HA integration manifest
│   └── translations/en.json          # UI strings for config/options flow
├── tools/                            # Standalone investigation/debug scripts
│   ├── sip_open_door.py              # Local SIP MESSAGE door open test
│   ├── sip_cloud_opendoor.py         # Cloud SIP path door open test
│   ├── probe_local_api.py            # BPT XTS7 web admin API probe
│   ├── probe_cloud_api.py            # CAME cloud REST API probe
│   ├── probe_http.py                 # HTTP endpoint probe
│   ├── portscan.py                   # Network port scanner
│   └── try_ami.py                    # Asterisk AMI probe
├── docs/                             # Research documentation
│   ├── logs/                         # Captured network traffic
│   │   ├── mitm.txt                  # MITM proxy captures
│   │   └── wireshark-opendoor-x2.txt # Wireshark SIP captures
│   └── tasks/
│       └── bpt-xts7-integration.md   # BPT door integration task notes
├── systemlogs/                       # BPT XTS7 device syslogs (downloaded)
│   ├── asterisklog                   # Asterisk SIP server logs
│   ├── callmanager                   # Door open command processor logs
│   ├── callmanager.0                 # Rotated callmanager logs
│   ├── lpcmanager                    # Serial bus manager logs
│   ├── messages                      # System messages (sip.conf updates)
│   ├── ui                            # Web UI logs
│   ├── ui.0                          # Rotated UI logs
│   └── xipweb                        # XIP cloud connection logs
├── CLAUDE.md                         # AI coding assistant instructions
├── CHANGELOG.md                      # Release changelog
├── README.md                         # Project documentation
└── .gitignore
```

## Key Locations

### Integration Code (`custom_components/came_connect/`)

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `__init__.py` | Entry point, coordinator setup | `async_setup_entry()`, `async_unload_entry()` |
| `api.py` | All network communication | `CameConnectClient`, `CameWebsocketClient` |
| `hub.py` | State management | `CameEventHub` |
| `config_flow.py` | UI setup flow | `CameConnectConfigFlow`, `CameConnectOptionsFlow` |
| `const.py` | Shared constants | `DOMAIN`, `PHASE_*`, `DEFAULT_WS_URL` |
| `cover.py` | Gate entity | `CameConnectCover` |
| `sensor.py` | Sensor entities | `CameConnectPhaseSensor`, `CameConnectPositionSensor`, etc. |
| `binary_sensor.py` | Binary sensors | `CameConnectMovingSensor`, `CameConnectOnlineSensor` |

### Investigation Tools (`tools/`)

Standalone Python scripts for reverse-engineering the BPT XTS7 door intercom. Not part of the HA integration — used for manual testing and protocol discovery.

### Device Logs (`systemlogs/`)

Logs downloaded from the BPT XTS7 device at `192.168.1.88`. Used to understand the SIP → callmanager → lpcmanager → serial door-open chain.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `binary_sensor.py` |
| Classes | `PascalCase` with `CameConnect` prefix | `CameConnectCover` |
| Constants | `UPPER_SNAKE_CASE` | `PHASE_OPEN`, `DEFAULT_WS_URL` |
| Entity attrs | `_attr_` prefix (HA pattern) | `_attr_name`, `_attr_icon` |
| Private methods | Leading underscore | `_raw()`, `_open_door()` |
| HA platforms | Lowercase module name | `cover`, `sensor`, `binary_sensor` |

## Where to Add New Code

| Adding... | Location |
|-----------|----------|
| New entity platform (e.g., button) | New file `custom_components/came_connect/button.py`, add to `PLATFORMS` in `const.py` |
| New API endpoint | `api.py` → add method to `CameConnectClient` |
| New constant | `const.py` |
| New config option | `config_flow.py` → `CameConnectOptionsFlow` |
| New investigation script | `tools/` directory |
| New translations | `translations/en.json` |

---

*Structure analysis: 2026-03-15*
