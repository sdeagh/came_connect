---
phase: 01-protocol-discovery
plan: 01
subsystem: tools
tags: [sip, udp, socket, digest-auth, ha1, md5secret, asterisk]

# Dependency graph
requires: []
provides:
  - "tools/sip_door_test.py: CLI investigation script covering all 6 door-open approaches"
  - "HA1-mode SIP digest auth pattern (md5secret, not cleartext password)"
  - "Documented door-open signal chain and syslog evidence"
affects:
  - 01-protocol-discovery

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Raw UDP socket SIP (no pjsip/sip libraries) — matches no-external-deps constraint"
    - "HA1-mode digest auth: make_digest_response(ha1, nonce, method, uri) skips HA1 derivation"
    - "Fresh UDP socket per approach (port 0, OS-assigned) — avoids port reuse confusion"

key-files:
  created:
    - tools/sip_door_test.py
  modified: []

key-decisions:
  - "Use HA1 (md5secret) directly in digest auth — Asterisk on XTS7 stores pre-hashed HA1, not cleartext password"
  - "Fresh socket per approach — avoids inter-approach state leakage during investigation"
  - "Approach 6 redirects to sip_cloud_opendoor.py — TLS+OAuth2 out of scope for this script"
  - "Docstring is the primary protocol documentation — captures full door-open chain + syslog evidence inline"

patterns-established:
  - "make_digest_response(ha1, nonce, method, uri): HA1-first signature signals md5secret mode"
  - "Approach runner functions: one function per approach, isolated socket, print_approach_header + print_result"

requirements-completed: [RE-01, RE-02]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 1 Plan 1: Protocol Discovery Investigation Script Summary

**SIP door-open investigation script with 6 approaches and correct HA1-mode digest auth (md5secret, user 00700100002)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T11:08:20Z
- **Completed:** 2026-03-15T11:10:26Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `tools/sip_door_test.py` (554 lines) covering all 6 investigation approaches
- Fixed the critical auth bug from earlier scripts: now uses HA1 directly (md5secret mode) instead of computing HA1 from empty password
- Approach 5 tests both UDP and TCP to callmanager port 5062 with clear connection-refused/timeout logging
- Full docstring documents the confirmed door-open chain, syslog evidence from 10:37:48 event, known credentials, and all pitfalls

## Task Commits

Each task was committed atomically:

1. **Task 1: Create sip_door_test.py with all 6 investigation approaches** - `9749bbe` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tools/sip_door_test.py` - CLI investigation script: 6 approaches, HA1 digest auth, argparse CLI, full protocol docstring

## Decisions Made
- HA1-mode digest auth: `make_digest_response(ha1, nonce, method, uri)` — skips HA1 derivation step entirely. Asterisk on XTS7 stores `md5secret` (pre-hashed HA1), so computing `md5(user:realm:password)` with any password is always wrong.
- Fresh socket per approach: each approach creates a new UDP socket bound to port 0 (OS-assigned). Avoids port conflicts between approaches and keeps state completely isolated.
- Approach 6 is a stub redirect: cloud SIP requires TLS + OAuth2 PKCE, already implemented in `sip_cloud_opendoor.py`. No value duplicating it here.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Script is a standalone investigation tool.

## Next Phase Readiness
- `tools/sip_door_test.py` is ready to run against the device
- User should run `--approach 1` first (most likely to succeed with correct HA1)
- After each approach, check device lpcmanager syslog for `OPEN_DOOR_REQ` to confirm hardware trigger independent of door physically opening
- If all local approaches fail, Approach 6 (sip_cloud_opendoor.py) is the fallback

## Self-Check

Performed after writing.

---
*Phase: 01-protocol-discovery*
*Completed: 2026-03-15*
