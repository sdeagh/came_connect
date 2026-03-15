---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 01-01-PLAN.md
last_updated: "2026-03-15T11:11:15.261Z"
last_activity: 2026-03-15 — Roadmap created
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Press a button in Home Assistant and the door physically opens — reliably, every time.
**Current focus:** Phase 1 — Protocol Discovery

## Current Position

Phase: 1 of 2 (Protocol Discovery)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-15 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-protocol-discovery P01 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Local SIP over cloud: No cloud dependency, faster, more reliable (outcome pending)
- Button entity (not switch): Momentary action, no on/off state needed
- Pure Python SIP: No new deps, matches integration style
- [Phase 01-protocol-discovery]: HA1-mode digest auth: use md5secret directly (Asterisk pre-hashed HA1, not cleartext password)
- [Phase 01-protocol-discovery]: Fresh socket per approach in sip_door_test.py — avoids port reuse and inter-approach state leakage

### Pending Todos

None yet.

### Blockers/Concerns

- Primary blocker: Local SIP MESSAGE reaches Asterisk (202 Accepted) but Asterisk does not route it to callmanager — cloud SIP trunk filter suspected
- Primary lead: Try MESSAGE directly to callmanager port 5062, bypassing Asterisk
- Unknown: Whether callmanager accepts connections from LAN (vs 127.0.0.1 only)

## Session Continuity

Last session: 2026-03-15T11:11:15.258Z
Stopped at: Completed 01-01-PLAN.md
Resume file: None
