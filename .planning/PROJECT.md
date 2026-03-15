# BPT XTS7 Door Open — HA Integration

## What This Is

A Home Assistant button entity that opens the door via a CAME BPT XTS7 WiFi intercom. Extends the existing `came_connect` custom integration with a new `button` platform that sends the correct SIP/serial command to the X1 controller. Built for publication to other BPT XTS7 owners.

## Core Value

Press a button in Home Assistant and the door physically opens — reliably, every time.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Reverse engineer the exact SIP MESSAGE format that triggers door open via the local XTS7
- [ ] Implement `button.py` platform with `CameBptDoorButton` entity
- [ ] Config flow: add BPT device options (SIP credentials, device IP)
- [ ] Works for other BPT XTS7 owners (not hardcoded to one device)
- [ ] No new external dependencies (pure Python SIP, like existing integration)

### Out of Scope

- Cloud SIP path (via 104.239.174.100:5061) — adds cloud dependency, local is more reliable
- Multi-device BPT support — one intercom per integration instance for now
- Aux relay control (Aux 1-10 from entry panel) — separate feature, different command
- Video/live view from XTS7 — different protocol entirely
- Local HTTP API door open — exhaustively probed, doesn't exist

## Context

### Reverse Engineering Status

The API is reverse-engineered from network inspection of the XTS7 (192.168.1.88, firmware v6.0.0, serial 0x4c004e12) connected to an X1 CAME BPT controller.

**Confirmed door open chain (from syslogs):**
```
CAME Access app → SIP/TLS → cloud proxy (104.239.174.100:5061)
  → Kamailio (127.0.0.1:5061) → Asterisk (127.0.0.1:5060)
  → AGI script → callmanager (127.0.0.1:5062): processes MESSAGE via cb_rcvunkrequest
  → lpcmanager: {"method": "OPEN_DOOR_REQ"}
  → serial bytes (82020400008306) → X1 → door opens
```

**What works:**
- SIP auth solved: user `00700100002`, HA1 `403c862ed78bf86dcf23cce7ec018380`
- MESSAGE to Asterisk (port 5060) gets `202 Accepted` — but Asterisk doesn't route it to callmanager
- Fresh syslog capture confirmed: Asterisk forwards MESSAGE to callmanager on port 5062 with FROM rewritten to `asterisk@127.0.0.1`

**Current blocker:**
Our local SIP MESSAGE reaches Asterisk but doesn't trigger the AGI/dialplan chain. Asterisk only runs the door-open dialplan for messages arriving from the cloud SIP trunk.

**Primary lead (untested):**
Send MESSAGE directly to callmanager on port 5062, bypassing Asterisk entirely. Callmanager processes messages from `127.0.0.1:5060` via `cb_rcvunkrequest` callback — may also accept from LAN.

**Investigation queue:**
1. Try MESSAGE directly to port 5062 (callmanager)
2. Try FROM as entry panel address (`00e00000`)
3. Try JSON body `{"method":"OPEN_DOOR_IND",...}` with `text/plain` content-type
4. Try sending to Kamailio trunk user (`00401200000`)
5. Try SIP INVITE instead of MESSAGE
6. Fall back to cloud SIP path if local fails

### Device Details

| Field | Value |
|-------|-------|
| Device | CAME BPT XTS7 WiFi v6.0.0, HW 1.0 |
| Local IP | 192.168.1.88 |
| Serial | 0x4c004e12 |
| MAC | 9C:53:CD:01:21:6A |
| CameConnect domain | 2B8EED6C49FCD387.xip.cameconnect.net |
| Cloud device ID | 190285 |
| SiteId | 132023 |
| Plant type | X1 |

### SIP Users

| Username | BptL3Addr | Role |
|----------|-----------|------|
| 00700100000 | 00e70000 | Mobile App 1 |
| 00700100001 | 00e70001 | Mobile App 2 |
| 00700100002 | 00e70002 | Mobile App 3 (test account) |
| 00700100003 | 00e70003 | Mobile App 4 |
| 00401200000 | 00dc0000 | XTS receiver (Kamailio trunk) |
| 00800000000 | 00e00000 | Entry panel |

### Open Ports

- 22: SSH (inaccessible)
- 80: BPT web admin (session auth)
- 5060: Asterisk SIP (UDP)
- 5061: Kamailio SIP (internal only, 127.0.0.1)
- 5062: callmanager SIP (internal only, 127.0.0.1)

## Constraints

- **No external deps**: Pure Python only — no `pjsip`, no `twisted`. Raw socket SIP like existing integration.
- **LAN access required**: Local SIP path needs device on same network.
- **Reverse-engineered API**: Protocol may change with firmware updates. Document everything.
- **Single device**: One BPT intercom per integration instance (matches existing gate limitation).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local SIP over cloud | No cloud dependency, faster, more reliable | — Pending |
| Button entity (not switch) | Momentary action — press to open, no on/off state | — Pending |
| Pure Python SIP | No new deps, matches integration style | — Pending |
| Use mobile app SIP account | Reuse existing credentials, no special provisioning | — Pending |

---
*Last updated: 2026-03-15 after initialization*
