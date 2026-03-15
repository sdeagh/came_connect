# Roadmap: BPT XTS7 Door Open

## Overview

Two phases: first prove the local SIP protocol works by sending the correct command directly to the XTS7, then wire that working command into Home Assistant as a configurable button entity. Phase 1 is pure investigation and validation — nothing ships until the door actually opens. Phase 2 turns the proven technique into a published HA integration.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Protocol Discovery** - Find and prove the exact local SIP command that opens the door
- [ ] **Phase 2: HA Integration** - Build the button entity, config flow, and publish the working integration

## Phase Details

### Phase 1: Protocol Discovery
**Goal**: A standalone Python script reliably opens the door via local SIP, with the exact protocol documented
**Depends on**: Nothing (first phase)
**Requirements**: RE-01, RE-02, RE-03, RE-04
**Success Criteria** (what must be TRUE):
  1. Running tools/sip_door_test.py from a LAN machine physically opens the door
  2. The script requires no hardcoded device-specific values — device IP and SIP credentials are passed as arguments
  3. RE-03 documentation captures every header, body, and sequence needed to reproduce the result
  4. The investigation queue (callmanager port 5062, FROM rewriting, JSON body variants) is exhausted and the winning approach is identified
**Plans:** 2 plans
Plans:
- [ ] 01-01-PLAN.md — Build investigation script with all 6 SIP approaches and correct HA1 credentials
- [ ] 01-02-PLAN.md — Run approaches against device, identify winner, document protocol

### Phase 2: HA Integration
**Goal**: Users can press a button in Home Assistant to open the door, with the BPT device fully configurable via the config flow
**Depends on**: Phase 1
**Requirements**: DOOR-01, DOOR-02, DOOR-03, CONF-01, CONF-02, CONF-03, INTG-01, INTG-02, INTG-03
**Success Criteria** (what must be TRUE):
  1. Pressing the button entity in HA causes the door to physically open
  2. The button entity shows success or failure state after each press (no silent failures)
  3. A fresh install on a different BPT XTS7 owner's HA can configure device IP and SIP credentials via config flow without editing code
  4. The integration has no new external Python dependencies beyond what came_connect already uses
  5. The button platform is wired into the existing came_connect integration structure (button.py, manifest, const)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Protocol Discovery | 0/2 | Planning complete | - |
| 2. HA Integration | 0/? | Not started | - |
