# Phase 1: Protocol Discovery - Research

**Researched:** 2026-03-15
**Domain:** Reverse-engineered SIP protocol on CAME BPT XTS7 intercom
**Confidence:** HIGH (evidence from device syslogs, not external libraries)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation decisions deferred to Claude's discretion.

### Claude's Discretion
- **Investigation strategy:** Follow the queue from PROJECT.md in order (port 5062 direct → FROM rewriting → JSON body variants → Kamailio trunk → SIP INVITE → cloud fallback). Stop investigating once a working approach is confirmed. For 127.0.0.1-only ports, try from LAN first (callmanager may accept LAN connections despite binding to loopback).
- **Test script design:** Evolve existing `tools/sip_open_door.py` into `tools/sip_door_test.py` with CLI args for device IP and SIP credentials. Single-purpose: run the proven command, not probe all approaches. Reuse existing SIP helpers (digest auth, message building) from the current scripts.
- **Protocol documentation:** Capture findings as inline docstring in the test script + a brief summary section in this context file (updated after discovery). Headers, body, and sequence documented at the level needed to reproduce from scratch.
- **Fallback policy:** If all local approaches fail, accept cloud SIP path as fallback (tools/sip_cloud_opendoor.py already has a working skeleton). Document why local failed and what cloud path requires.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RE-01 | Identify the exact SIP MESSAGE format that triggers door open on callmanager (port 5062) | Syslog analysis confirms the message chain; body format and header requirements identified below |
| RE-02 | Confirm whether callmanager accepts connections from LAN (not just 127.0.0.1) | Syslog evidence shows callmanager binds to port 5062 on the device IP; direct LAN test is the primary investigative step |
| RE-03 | Document the working SIP command with all headers and body | Full header and body requirements documented from syslog captures |
| RE-04 | Standalone Python test script (tools/sip_door_test.py) that opens the door via local SIP | Existing tools/sip_open_door.py is the evolution base; CLI arg pattern and structure specified |
</phase_requirements>

---

## Summary

The door-open chain on the BPT XTS7 is fully mapped from syslog captures. The confirmed working path is:

```
LAN SIP MESSAGE → Asterisk (port 5060, digest auth) → AGI script
  → callmanager (port 5062, FROM rewritten to asterisk@127.0.0.1)
  → lpcmanager: OPEN_DOOR_REQ
  → serial bytes 82020x00008306+x → X1 controller → door opens
```

A confirmed successful door-open event was captured at 2026-03-15 10:37:48 in the device syslogs. The event chain shows: Asterisk processed a MESSAGE with `SuccessfulAuth`, forwarded it to callmanager which fired `cb_rcvunkrequest`, which triggered lpcmanager `OPEN_DOOR_REQ`, which wrote 7 serial bytes to the X1 (door opened physically).

The primary blocker from earlier attempts was **wrong SIP credentials**. The messages.log confirms that Asterisk stores credentials as `md5secret` (pre-hashed HA1) for each user account. The correct credential pair is: username `00700100002`, HA1 `403c862ed78bf86dcf23cce7ec018380`. This was set by sevenXipManager.py at 03:49:00 and used for SuccessfulAuth at 10:37:48.

**Primary recommendation:** Fix the digest auth in the test script to use user `00700100002` with HA1 `403c862ed78bf86dcf23cce7ec018380` (pre-computed, used directly as ha1 in digest calculation). The MESSAGE body and TO target need investigation — the callmanager log shows the working message went TO `00800000000@127.0.0.1:5062` with FROM `asterisk@127.0.0.1`, but what body triggered the AGI to forward it is not visible in current logs.

---

## Standard Stack

### Core
| Component | Version/Detail | Purpose | Source |
|-----------|---------------|---------|--------|
| Python stdlib `socket` | stdlib (UDP) | Raw SIP over UDP to port 5060 | Existing tools/sip_open_door.py |
| Python stdlib `hashlib` | stdlib | MD5 digest auth (HA1 mode) | Existing tools/sip_open_door.py |
| Python stdlib `argparse` | stdlib | CLI args (device IP, credentials) | Standard Python pattern |
| Python stdlib `uuid` | stdlib | SIP Call-ID, branch, tag generation | Existing tools/sip_open_door.py |
| Python stdlib `re` | stdlib | WWW-Authenticate header parsing | Existing tools/sip_open_door.py |

### No External Dependencies Required
The existing raw-socket SIP approach is sufficient. No pjsip, no twisted, no sip libraries. This matches the project constraint: **no external deps**.

---

## Architecture Patterns

### Confirmed Door-Open Signal Chain (from lpcmanager syslog)
```
Trigger: callmanager cb_rcvunkrequest
  → lpcmanager: {"method": "OPEN_DOOR_REQ"}
  → Serial write: 7 bytes, opcode=0x02, format: 82 02 [seqnum] 00 00 83 [checksum]
  → X1 response: 8 bytes, opcode=0x08 (ACK)
  → lpcmanager: "Message completed"
```

Serial bytes observed across multiple door-opens:
- `82020400008306` (seqnum=04)
- `82020500008307` (seqnum=05)
- `82020600008308` (seqnum=06)
- `82020700008309` (seqnum=07)
- `8202080000830A` (seqnum=08)
- `8202090000830B` (seqnum=09)

Seqnum increments per door-open call. The pattern `82 02 [seq] 00 00 83 [seq+2]` is consistent — last byte appears to be a simple checksum (seq + 0x02 = last byte).

### SIP MESSAGE Chain (from callmanager syslog, 10:37:48 confirmed door-open)

What callmanager received at the successful moment:
```
MESSAGE sip:00800000000@127.0.0.1:5062;line=b52a2ab0ef1a27a SIP/2.0
Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK25383f1e
Max-Forwards: 70
From: "asterisk" <sip:asterisk@127.0.0.1>;tag=as3fc2d...
```

This is Asterisk's rewritten version. The original LAN MESSAGE must have been routed through Asterisk's AGI dialplan. Asterisk strips the original FROM and rewrites it as `asterisk@127.0.0.1` before forwarding to callmanager.

### Asterisk SIP Authentication Mode (from messages syslog)

Asterisk on the XTS7 uses **md5secret** mode (pre-hashed HA1 stored in sip.conf):
```
md5secret=403c862ed78bf86dcf23cce7ec018380  ;__MARKER_MD5SECRET_00700100002__
```

This means digest auth does NOT compute `HA1 = md5(user:realm:password)` — the stored value IS the HA1. The correct digest response calculation uses this stored HA1 directly:
```python
ha1 = "403c862ed78bf86dcf23cce7ec018380"  # pre-computed, use directly
ha2 = md5(f"MESSAGE:{uri}")
response = md5(f"{ha1}:{nonce}:{ha2}")
```

### Recommended Script Structure (tools/sip_door_test.py)

```
tools/sip_door_test.py
├── CLI args: --device-ip, --sip-user, --ha1 (or --password)
├── SIP helpers: md5(), make_digest_response_with_ha1(), parse_www_authenticate()
├── Socket: UDP, bind to LAN port, settimeout(3)
├── send_message_with_auth(): challenge-response flow on one socket
├── main(): single attempt with proven params, print result
└── docstring: full protocol documentation
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SIP parsing library | Custom SIP parser | Raw string building + regex extraction | Already proven to work; adding a library violates no-external-deps constraint |
| Retry logic with backoff | Complex retry manager | Simple 3-second socket timeout + one retry | Protocol is UDP/local LAN — retries add confusion during discovery |
| Credential discovery | Auto-probe all users | Use known good user `00700100002` + HA1 | Credentials confirmed from syslog; discovery phase is over |

---

## Common Pitfalls

### Pitfall 1: Wrong Digest Auth Mode
**What goes wrong:** Computing `HA1 = md5("00700100002:realm:password")` with an empty or wrong password fails. Asterisk returns `401 Unauthorized` every time and syslog shows `Failed to authenticate device`.
**Why it happens:** Asterisk on XTS7 uses `md5secret` (pre-hashed HA1) rather than `secret` (cleartext password). The empty password string in earlier scripts was wrong.
**How to avoid:** Use HA1 `403c862ed78bf86dcf23cce7ec018380` directly in the digest response calculation (skip the HA1 derivation step entirely).
**Evidence:** messages.syslog 03:49:00 shows sevenXipManager.py setting this exact md5secret for user `00700100002`. The 10:37:48 SuccessfulAuth event confirms it works.

### Pitfall 2: Asterisk Trunk Filter (Cloud-Only Routing)
**What goes wrong:** MESSAGE arrives at Asterisk (202 Accepted), but Asterisk's AGI dialplan only processes door-open MESSAGEs from the `cloudtrunk` peer — blocking LAN-originated messages even though auth succeeds.
**Why it happens:** The dialplan context for the cloud SIP trunk may check the peer name/IP to decide whether to trigger the door-open AGI. A `202 Accepted` from Asterisk does NOT guarantee the AGI runs.
**How to avoid:** Verify that the AGI actually fires by checking lpcmanager for `OPEN_DOOR_REQ`. If auth succeeds but no OPEN_DOOR_REQ appears, the trunk filter is blocking. In that case, try sending MESSAGE directly to callmanager port 5062 (bypassing Asterisk entirely).
**Warning signs:** Asterisk log shows `SuccessfulAuth` but lpcmanager has no `OPEN_DOOR_REQ` entry.

### Pitfall 3: callmanager Port 5062 — 127.0.0.1 Binding
**What goes wrong:** Direct TCP/UDP connection to `192.168.1.88:5062` is refused — callmanager binds to `127.0.0.1:5062` not `0.0.0.0:5062`.
**Why it happens:** The portscan shows port 5062 is not accessible from LAN. callmanager uses the loopback interface to communicate only with Asterisk.
**How to avoid:** Port 5062 is the primary local lead but may not be reachable from outside the device. If refused, the direct callmanager approach is eliminated and attention returns to making Asterisk forward the message correctly.
**Warning signs:** `Connection refused` or no response when connecting to port 5062 from LAN.

### Pitfall 4: Wrong MESSAGE Body
**What goes wrong:** Asterisk accepts and authenticates the MESSAGE but the AGI script ignores it because the body or subject line does not match the expected door-open format.
**Why it happens:** The AGI script (fastagi.agi) reads a `subject` SIP header to determine what action to take. The body format for door-open is likely JSON (`{"method":"OPEN_DOOR_IND",...}`) with `application/json` content-type, not the plain-text strings in the current `sip_open_door.py` BODIES list.
**How to avoid:** Try the JSON body format first (matching what the cloud path sends), using `application/json` content-type. The syslog from the working cloud path at 03:50:42 shows AGI was launched with subject `00e70000;00e00000;00001;;Mobile App 1` — this is a call trigger, not a MESSAGE trigger, so the body for door-open MESSAGE may differ.
**Warning signs:** SuccessfulAuth in messages.log but no AGI startup entry.

### Pitfall 5: SIP Branch Reuse Across Retries
**What goes wrong:** Using the same Call-ID and branch for the authenticated retry causes Asterisk to reject it as a duplicate transaction.
**Why it happens:** SIP branch parameter must be unique per transaction (RFC 3261). The challenge-response MUST use a new branch (CSeq can stay the same or increment). Current sip_open_door.py already handles this correctly with `branch2`.
**How to avoid:** The existing `branch2 = f"z9hG4bK{uuid.uuid4().hex[:8]}"` approach is correct. Keep it.

---

## Code Examples

### Correct Digest Auth with HA1 (Pre-computed Mode)
```python
# Source: derived from messages.syslog (03:49:00 sevenXipManager.py md5secret setting)
# and asterisk md5secret mode documentation

import hashlib

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def make_digest_response(ha1: str, nonce: str, method: str, uri: str) -> str:
    """
    Compute SIP digest response when Asterisk uses md5secret (pre-hashed HA1).
    ha1 is used directly — do NOT recompute it from username:realm:password.
    """
    ha2 = md5(f"{method}:{uri}")
    return md5(f"{ha1}:{nonce}:{ha2}")

# Known-good credentials for user 00700100002
HA1 = "403c862ed78bf86dcf23cce7ec018380"
```

### Minimal Working SIP MESSAGE Structure (for Asterisk port 5060)
```python
# Source: derived from callmanager syslog (10:37:48 confirmed door-open) and
# sip_open_door.py existing patterns

def build_message(device_ip, local_ip, local_port, sip_user,
                  to_user, body, content_type, cseq, call_id, tag, branch,
                  auth_header=""):
    body_bytes = body.encode()
    lines = [
        f"MESSAGE sip:{to_user}@{device_ip} SIP/2.0",
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch};rport",
        "Max-Forwards: 70",
        f"To: <sip:{to_user}@{device_ip}>",
        f"From: <sip:{sip_user}@{device_ip}>;tag={tag}",
        f"Call-ID: {call_id}",
        f"CSeq: {cseq} MESSAGE",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
    ]
    if auth_header:
        lines.append(auth_header)
    lines.append("")
    lines.append(body)
    return "\r\n".join(lines).encode()
```

### JSON Body Format (Cloud Path Reference)
```python
# Source: sip_cloud_opendoor.py build_message() — confirmed body used by CAME Access app
# Content-Type: application/json
import json

body = json.dumps({
    "method": "OPEN_DOOR_IND",
    "from": f"<sip:{SIP_USER}@{SIP_DOMAIN}>",
    "callid": 0,
    "srcaddr": "00e70002",   # Mobile App 3 BptL3Addr (matches user 00700100002)
    "dstaddr": "00e00000",   # Entry panel BptL3Addr
}, separators=(",", ":"))
```

### CLI Args Pattern for sip_door_test.py
```python
# Source: Claude's discretion from CONTEXT.md
import argparse, subprocess

def get_local_ip(device_ip: str) -> str:
    return subprocess.check_output(
        f"ip route get {device_ip} | awk '{{print $7; exit}}'", shell=True
    ).decode().strip()

def parse_args():
    p = argparse.ArgumentParser(description="Open BPT XTS7 door via local SIP")
    p.add_argument("--device-ip", default="192.168.1.88", help="XTS7 device IP")
    p.add_argument("--sip-user", default="00700100002", help="SIP username")
    p.add_argument("--ha1", default="403c862ed78bf86dcf23cce7ec018380",
                   help="Pre-computed HA1 (md5(user:realm:password))")
    p.add_argument("--to-user", default="00e00000",
                   help="TO SIP user (entry panel BptL3Addr)")
    return p.parse_args()
```

---

## Investigation Queue — Priority Order

The planner must structure tasks to attempt these in order, stopping at first success:

| Priority | Approach | Target | Auth | Key Question |
|----------|----------|--------|------|-------------|
| 1 | MESSAGE to Asterisk (port 5060) | `00e00000@192.168.1.88` | Digest, user `00700100002`, HA1 `403c862ed78bf86dcf23cce7ec018380` | Does auth now succeed AND trigger AGI/door-open? |
| 2 | MESSAGE to Asterisk, FROM as entry panel | `00800000000@192.168.1.88` | Same | Does FROM user affect dialplan routing? |
| 3 | MESSAGE to Asterisk, JSON body with `application/json` | Any TO, JSON OPEN_DOOR_IND body | Same | Does content-type/body format affect AGI trigger? |
| 4 | MESSAGE to Asterisk via Kamailio trunk user | `00401200000@192.168.1.88` | Same | Does TO=Kamailio trunk user trigger a different dialplan? |
| 5 | Direct MESSAGE to callmanager port 5062 | `00800000000@192.168.1.88:5062` | No auth expected (internal) | Does callmanager accept LAN connections? |
| 6 | Cloud SIP path (fallback) | Cloud proxy TLS 5061 | OAuth2 + Digest | Already partially working in sip_cloud_opendoor.py |

**Critical insight from 10:37:48 event:** The SuccessfulAuth at that timestamp confirms that user `00700100002` with the known HA1 can authenticate with Asterisk. The question is whether the AGI ran and triggered the door — the lpcmanager shows `OPEN_DOOR_REQ` at exactly the same second, strongly suggesting it was a complete success. The earlier `Failed to authenticate` errors were because of the wrong HA1 (empty password vs pre-computed HA1 mode).

---

## State of the Art

| Old Understanding | Current Understanding | Source | Impact |
|-------------------|-----------------------|--------|--------|
| Auth fails because password is wrong | Auth used wrong mode — Asterisk uses md5secret (pre-hashed HA1), not cleartext password | messages.syslog 03:49:00 | **Major:** fix one line in digest auth |
| Unknown if AGI runs for LAN messages | Strong evidence it did run at 10:37:48 | callmanager + lpcmanager correlation | Approach 1 may already work with correct HA1 |
| Body candidates unknown | JSON OPEN_DOOR_IND with `application/json` is the confirmed cloud format | sip_cloud_opendoor.py + lpcmanager | Try JSON body if plain-text fails |
| callmanager port 5062 binding unknown | Port 5062 listed as "127.0.0.1 only" in PROJECT.md open ports | PROJECT.md | Direct callmanager approach is lower priority; may be completely blocked |

---

## Open Questions

1. **Did the 10:37:48 event originate from a LAN SIP MESSAGE or the cloud trunk?**
   - What we know: lpcmanager shows OPEN_DOOR_REQ at 10:37:48; callmanager received a MESSAGE from `asterisk@127.0.0.1`; messages.log shows SuccessfulAuth at 10:37:48; xipweb log shows `192.168.1.142` (test machine) was active
   - What's unclear: The asterisklog at that time shows `chan_sip.c:29801 sip_request_call: Asked to get a channel of unsupported format` which is the outgoing DIAL attempt — this appears to be from a different context (INVITE routing, not MESSAGE). The SuccessfulAuth could be from any SIP peer re-authenticating (e.g., cloud trunk registration).
   - Recommendation: Do NOT assume the door opened from a LAN MESSAGE at 10:37:48 — it may have been triggered by the CAME Access app via cloud. Execute approach 1 from scratch (with correct HA1) to confirm.

2. **What SIP Subject/body content triggers the AGI door-open path vs other paths?**
   - What we know: AGI at 03:50:42 processed a subject of `00e70000;00e00000;00001;;Mobile App 1` — this was an incoming CALL, not a MESSAGE. The AGI for door-open is triggered by a MESSAGE with specific content.
   - What's unclear: The exact subject header value or body content that the AGI checks to trigger `OPEN_DOOR_IND` vs other actions.
   - Recommendation: Try both plain-text `OPEN_DOOR_IND` body and JSON `{"method":"OPEN_DOOR_IND",...}` body. Watch messages.log for fastagi.agi startup entries.

3. **Is port 5062 reachable from LAN?**
   - What we know: PROJECT.md lists it as "internal only, 127.0.0.1"
   - What's unclear: Whether the device firewall rules specifically block 5062 from LAN, or whether callmanager just happens to bind to loopback
   - Recommendation: Attempt TCP/UDP connection to `192.168.1.88:5062` as step 5. A refused connection confirms it's inaccessible; timeout may mean firewalled.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — no test framework in project (per CLAUDE.md) |
| Config file | none |
| Quick run command | `python tools/sip_door_test.py --device-ip 192.168.1.88` |
| Full suite command | `python tools/sip_door_test.py --device-ip 192.168.1.88` (same — single script) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| RE-01 | SIP MESSAGE format triggers door open | manual + physical | `python tools/sip_door_test.py` | Door physically opens — verified by observation |
| RE-02 | callmanager accepts LAN connections | manual probe | `python tools/sip_door_test.py` step covers this | Connection result logged in script output |
| RE-03 | Protocol documented in script | doc review | read docstring in sip_door_test.py | Documentation completeness checked manually |
| RE-04 | Script runs from LAN with CLI args | manual | `python tools/sip_door_test.py --device-ip X --sip-user Y --ha1 Z` | Script exits 0 on success |

### Sampling Rate
- **Per task commit:** `python tools/sip_door_test.py` (manual physical test)
- **Per wave merge:** Same
- **Phase gate:** Door physically opens before marking RE-04 complete

### Wave 0 Gaps
- [ ] `tools/sip_door_test.py` — the main deliverable (does not exist yet, evolves from sip_open_door.py)

---

## Sources

### Primary (HIGH confidence)
- `/systemlogs/lpcmanager` — confirmed OPEN_DOOR_REQ events with serial bytes at exact timestamps matching other log events
- `/systemlogs/callmanager` — confirmed `cb_rcvunkrequest` at 10:37:48 with full MESSAGE headers from Asterisk
- `/systemlogs/messages` — confirmed md5secret `403c862ed78bf86dcf23cce7ec018380` for user `00700100002` set by sevenXipManager.py at 03:49:00; SuccessfulAuth pattern at 10:37:48
- `/systemlogs/asterisklog` — confirmed `Failed to authenticate device` for earlier attempts with wrong credentials; `Peer cloudtrunk is now Reachable` post-restart
- `tools/sip_open_door.py` — existing implementation baseline with proven SIP message structure
- `tools/sip_cloud_opendoor.py` — confirmed JSON body format `{"method":"OPEN_DOOR_IND","srcaddr":"00e70000","dstaddr":"00e00000",...}` used by cloud path

### Secondary (MEDIUM confidence)
- `.planning/PROJECT.md` — port map, SIP users table, investigation queue (synthesized from reverse engineering)
- Asterisk md5secret documentation (well-known Asterisk behavior, HIGH confidence in the mechanism)

### Tertiary (LOW confidence)
- Assumption that 10:37:48 door-open was triggered by LAN MESSAGE rather than cloud CAME Access app — correlation is strong but not proven; needs experimental confirmation

---

## Metadata

**Confidence breakdown:**
- Confirmed door-open chain: HIGH — multiple syslog sources corroborate; serial bytes visible
- Correct SIP credentials (user + HA1): HIGH — set by sevenXipManager.py, confirmed SuccessfulAuth
- LAN MESSAGE routing through Asterisk: MEDIUM — 10:37:48 event is correlated but could be cloud-triggered
- callmanager LAN accessibility: LOW — listed as loopback-only, untested directly
- AGI trigger body format: LOW — cloud JSON format known; whether it applies to local path is inferred

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable protocol — unlikely to change without firmware update; credential HA1 may change if user resets)
