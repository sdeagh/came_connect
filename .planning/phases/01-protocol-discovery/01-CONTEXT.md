# Phase 1: Protocol Discovery - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Find and prove the exact local SIP command that opens the door via the BPT XTS7. Deliver a standalone Python script that reliably opens the door from LAN, with the protocol fully documented. No HA integration — that's Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All areas — user deferred to Claude's judgement:

- **Investigation strategy:** Follow the queue from PROJECT.md in order (port 5062 direct → FROM rewriting → JSON body variants → Kamailio trunk → SIP INVITE → cloud fallback). Stop investigating once a working approach is confirmed. For 127.0.0.1-only ports, try from LAN first (callmanager may accept LAN connections despite binding to loopback).
- **Test script design:** Evolve existing `tools/sip_open_door.py` into `tools/sip_door_test.py` with CLI args for device IP and SIP credentials. Single-purpose: run the proven command, not probe all approaches. Reuse existing SIP helpers (digest auth, message building) from the current scripts.
- **Protocol documentation:** Capture findings as inline docstring in the test script + a brief summary section in this context file (updated after discovery). Headers, body, and sequence documented at the level needed to reproduce from scratch.
- **Fallback policy:** If all local approaches fail, accept cloud SIP path as fallback (tools/sip_cloud_opendoor.py already has a working skeleton). Document why local failed and what cloud path requires.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/sip_open_door.py`: Local SIP MESSAGE with digest auth, body candidates, multiple TO targets. Raw UDP socket approach.
- `tools/sip_cloud_opendoor.py`: Cloud SIP path with OAuth2 PKCE + TLS + REGISTER + MESSAGE. Full digest auth flow over TLS.
- Both scripts share: MD5 digest helpers, SIP message builders, challenge parsing.

### Established Patterns
- Raw socket SIP (no pjsip/twisted) — matches integration constraint
- Digest auth challenge-response flow already implemented
- OPEN_DOOR_IND JSON body format known from syslog analysis

### Integration Points
- Investigation queue defined in PROJECT.md (6 approaches)
- Device details, SIP users, and credentials documented in PROJECT.md
- Syslog captures in `systemlogs/` for reference (callmanager, asterisklog, lpcmanager)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-protocol-discovery*
*Context gathered: 2026-03-15*
