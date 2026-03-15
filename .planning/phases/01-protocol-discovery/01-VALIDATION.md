---
phase: 1
slug: protocol-discovery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — no test framework in project (per CLAUDE.md) |
| **Config file** | none |
| **Quick run command** | `python tools/sip_door_test.py --device-ip 192.168.1.88 --sip-user 00700100002 --ha1 403c862ed78bf86dcf23cce7ec018380` |
| **Full suite command** | `python tools/sip_door_test.py --device-ip 192.168.1.88 --sip-user 00700100002 --ha1 403c862ed78bf86dcf23cce7ec018380` (same — single script) |
| **Estimated runtime** | ~10 seconds (network + physical door check) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (manual — requires physical observation)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green (door physically opens)
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | RE-01 | manual + physical | `python tools/sip_door_test.py` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | RE-02 | manual probe | `python tools/sip_door_test.py` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | RE-03 | doc review | read docstring in sip_door_test.py | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | RE-04 | manual | `python tools/sip_door_test.py --device-ip X --sip-user Y --ha1 Z` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/sip_door_test.py` — the main deliverable (does not exist yet, evolves from sip_open_door.py)

*Wave 0 creates the script; subsequent tasks refine and validate it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Door physically opens | RE-01 | Physical hardware interaction — cannot be automated | Run script from LAN machine, observe door opening |
| callmanager LAN acceptance | RE-02 | Network probe against live device | Script logs connection result (accepted/rejected) |
| Protocol documentation complete | RE-03 | Documentation quality is subjective | Review docstring in sip_door_test.py for completeness |
| CLI args work (no hardcoded values) | RE-04 | Requires running with different args | Run with `--device-ip X --sip-user Y --ha1 Z` and verify it uses those values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
