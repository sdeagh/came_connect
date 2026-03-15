---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: blocked
stopped_at: Paused after writing Android handoff; next best resume point is controlled Android capture restart or gadget-based instrumentation
last_updated: "2026-03-15T23:14:18.098Z"
last_activity: 2026-03-15 — Wrote pause handoff after confirming Android app opens door as 00700100001/00e70001 and direct cloud repro still fails
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 2
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Press a button in Home Assistant and the door physically opens — reliably, every time.
**Current focus:** Phase 1 — Protocol Discovery (blocked)

## Current Position

Phase: 1 of 2 (Protocol Discovery)
Plan: 2 of 2 executed in current phase
Status: Blocked after investigation sweep
Last activity: 2026-03-15 — Wrote pause handoff after confirming Android app opens door as 00700100001/00e70001 and direct cloud repro still fails

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
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
| Phase 01-protocol-discovery P01-P02 | 2 | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Local SIP over cloud: No cloud dependency, faster, more reliable (blocked by device-side SIP policy)
- Button entity (not switch): Momentary action, no on/off state needed
- Pure Python SIP: No new deps, matches integration style
- [Phase 01-protocol-discovery]: HA1-mode digest auth: use md5secret directly (Asterisk pre-hashed HA1, not cleartext password)
- [Phase 01-protocol-discovery]: Local sweep completed on 2026-03-15 — 403 on plain-text MESSAGE, 415 on JSON MESSAGE, and 5062 unreachable from LAN
- [Phase 01-protocol-discovery]: Cloud fallback still needs the real SIP secret or auth shape — current SIP REGISTER attempts return 401
- [Phase 01-protocol-discovery]: Browser-confirmed local UI shows internal receiver SIP account `00401200000` with blank password field, while CameConnect remains connected via `xip01.cameconnect.net`
- [Phase 01-protocol-discovery]: Changing `00700100000` to password `test` updated local `md5secret` and uploaded to `xip01.cameconnect.net`, but the direct cloud SIP probe still returned `401`
- [Phase 01-protocol-discovery]: Fresh official app opens at `14:50` used `srcaddr=00e70000` and triggered the working local Asterisk -> callmanager -> lpcmanager door-open chain
- [Phase 01-protocol-discovery]: Android emulator app opens at `22:17:37` used `srcaddr=00e70001` / `00700100001` and triggered the same working local chain
- [Phase 01-protocol-discovery]: Direct cloud probing of `00700100001` still fails with `xipregister -> 403` and SIP `REGISTER -> 401`, even with the locally rotated `md5secret` and Android FCM token

### Pending Todos

None yet.

### Blockers/Concerns

- Primary blocker: Asterisk returns `403 Forbidden` for the plain-text LAN door-open MESSAGE and `415 Unsupported Media Type` for the JSON variants
- Secondary blocker: `callmanager` on port `5062` is not reachable from LAN (UDP timeout, TCP refused)
- Cloud blocker: the CameConnect cloud currently exposes SIP user `00700100000`, but SIP REGISTER still returns `401 Unauthorized` even after rotating that account to known password `test`
- Identity split: the local SIP page exposes the internal receiver account `00401200000`; mobile SIP user `00700100002` exists locally but is rejected by cloud `xipregister`
- Model blocker: the official apps' working path likely involves additional auth material or signaling beyond the current standalone `REGISTER + MESSAGE` script, because both `00700100000` and `00700100001` fail direct repro

## Session Continuity

Last session: 2026-03-15T23:14:18.098Z
Stopped at: Paused after writing Android handoff; next best resume point is controlled Android capture restart or gadget-based instrumentation
Resume file: .planning/phases/01-protocol-discovery/.continue-here.md
