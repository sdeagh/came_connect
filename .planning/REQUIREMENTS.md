# Requirements: BPT XTS7 Door Open

**Defined:** 2026-03-15
**Core Value:** Press a button in Home Assistant and the door physically opens — reliably, every time.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Reverse Engineering

- [ ] **RE-01**: Identify the exact SIP MESSAGE format that triggers door open on callmanager (port 5062)
- [ ] **RE-02**: Confirm whether callmanager accepts connections from LAN (not just 127.0.0.1)
- [ ] **RE-03**: Document the working SIP command with all headers and body
- [ ] **RE-04**: Standalone Python test script (tools/sip_door_test.py) that opens the door via local SIP, confirming the protocol works independently of HA

### Door Open

- [ ] **DOOR-01**: User can press a button entity in HA and the door physically opens
- [ ] **DOOR-02**: Button sends local SIP MESSAGE to XTS7 on LAN
- [ ] **DOOR-03**: Button provides feedback (success/failure) via HA entity state

### Configuration

- [ ] **CONF-01**: User can configure BPT device IP via config flow
- [ ] **CONF-02**: User can configure SIP credentials (username + password/HA1) via config flow
- [ ] **CONF-03**: Integration auto-discovers SIP account details from cloud API device list

### Integration

- [ ] **INTG-01**: button.py platform added to existing came_connect integration
- [ ] **INTG-02**: No new external Python dependencies
- [ ] **INTG-03**: Works for other BPT XTS7 owners (configurable, not hardcoded)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Aux Control

- **AUX-01**: User can trigger Aux relays (Aux 1-10) from HA
- **AUX-02**: Aux entities auto-discovered from cloud API device list

### Resilience

- **RES-01**: Cloud SIP fallback path when local SIP fails
- **RES-02**: Multi-device BPT support (multiple intercoms)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video/live view from XTS7 | Different protocol (RTP/RTSP), separate integration scope |
| Local HTTP API door open | Exhaustively probed — endpoint doesn't exist |
| SSH access to XTS7 | Locked down, default passwords don't work |
| Mobile push notifications | Handled by CAME Access app, not HA's domain |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RE-01 | — | Pending |
| RE-02 | — | Pending |
| RE-03 | — | Pending |
| RE-04 | — | Pending |
| DOOR-01 | — | Pending |
| DOOR-02 | — | Pending |
| DOOR-03 | — | Pending |
| CONF-01 | — | Pending |
| CONF-02 | — | Pending |
| CONF-03 | — | Pending |
| INTG-01 | — | Pending |
| INTG-02 | — | Pending |
| INTG-03 | — | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after initial definition*
