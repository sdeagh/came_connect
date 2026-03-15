#!/usr/bin/env python3
"""
BPT XTS7 Door-Open Investigation Script
========================================

Tests all 6 investigation approaches for opening the door via local SIP.
Run with --approach 1 through 6 (or "all") to try each method in turn.

DEVICE
------
  BPT XTS7 intercom, IP 192.168.1.88
  Asterisk on port 5060 (UDP)
  callmanager on port 5062 (internal only, likely 127.0.0.1 bound)
  Kamailio on port 5060 (shared via dispatcher)

CONFIRMED DOOR-OPEN CHAIN (from syslog captures)
-------------------------------------------------
  LAN SIP MESSAGE → Asterisk (port 5060, digest auth)
    → AGI script (fastagi.agi)
    → callmanager (port 5062, FROM rewritten to asterisk@127.0.0.1)
    → lpcmanager: OPEN_DOOR_REQ
    → Serial write: 7 bytes  82 02 [seqnum] 00 00 83 [seqnum+2]
    → X1 controller → door physically opens

SYSLOG EVIDENCE
---------------
  2026-03-15 10:37:48 — confirmed successful door-open event in lpcmanager syslog.
  callmanager received:  MESSAGE sip:00800000000@127.0.0.1:5062 SIP/2.0
  messages.syslog shows: SuccessfulAuth for user 00700100002 at 10:37:48

SIP CREDENTIALS (from messages.syslog 03:49:00 sevenXipManager.py)
-------------------------------------------------------------------
  username:   00700100002
  md5secret:  403c862ed78bf86dcf23cce7ec018380  (pre-computed HA1; NOT cleartext password)
  realm:      (provided by Asterisk in WWW-Authenticate challenge)

  CRITICAL: Asterisk on XTS7 uses md5secret mode (pre-hashed HA1).
  Digest response = md5(HA1 + ":" + nonce + ":" + md5("MESSAGE:" + uri))
  Do NOT compute HA1 from username:realm:password — use the stored HA1 directly.

INVESTIGATION QUEUE (priority order)
-------------------------------------
  1. MESSAGE to Asterisk port 5060, TO=00e00000, body=OPEN_DOOR_IND, text/plain
     Question: Does HA1-correct auth + correct TO trigger AGI door-open?

  2. MESSAGE to Asterisk port 5060, TO=00800000000, body=OPEN_DOOR_IND, text/plain
     Question: Does FROM user (TO target) affect dialplan routing?

  3. MESSAGE to Asterisk port 5060, TO=00e00000 and TO=00800000000,
     body=JSON OPEN_DOOR_IND, content-type=application/json
     Question: Does JSON body/content-type affect AGI trigger?

  4. MESSAGE to Asterisk port 5060, TO=00401200000 (Kamailio trunk),
     body=OPEN_DOOR_IND, text/plain
     Question: Does Kamailio trunk user trigger a different dialplan path?

  5. Direct MESSAGE to callmanager port 5062, TO=00800000000, no auth (UDP + TCP)
     Question: Does callmanager accept LAN connections at all?

  6. Cloud SIP path (fallback) — requires TLS + OAuth2.
     Refer to tools/sip_cloud_opendoor.py.

KNOWN PITFALLS
--------------
  - Wrong auth mode: earlier scripts computed HA1 from empty password — WRONG.
    Fix: use the stored md5secret (HA1) directly.
  - Asterisk trunk filter: 202 Accepted does not guarantee AGI ran.
    Verify by checking lpcmanager for OPEN_DOOR_REQ after each attempt.
  - callmanager port 5062: likely bound to 127.0.0.1 only (will refuse from LAN).
  - Branch reuse: always use a fresh branch for the authenticated retry (already handled).
  - Wrong body: if text/plain fails, try JSON OPEN_DOOR_IND (approach 3).

USAGE
-----
  python3 tools/sip_door_test.py                         # all approaches
  python3 tools/sip_door_test.py --approach 1            # approach 1 only
  python3 tools/sip_door_test.py --approach all          # all approaches
  python3 tools/sip_door_test.py --device-ip 192.168.1.88 --approach 1
  python3 tools/sip_door_test.py --ha1 403c862ed78bf86dcf23cce7ec018380 --approach 1

After running, check device syslogs for OPEN_DOOR_REQ in lpcmanager to confirm
the door-open signal reached the hardware (independent of whether door physically opens).
"""

import argparse
import hashlib
import json
import re
import socket
import subprocess
import uuid

# ── Default credentials & targets ─────────────────────────────────────────────

DEFAULT_DEVICE_IP = "192.168.1.88"
DEFAULT_SIP_USER  = "00700100002"
DEFAULT_HA1       = "403c862ed78bf86dcf23cce7ec018380"
DEFAULT_TO_USER   = "00e00000"

# JSON body srcaddr for user 00700100002 (Mobile App 3 BptL3Addr)
SRC_ADDR          = "00e70002"


# ── Core helpers ──────────────────────────────────────────────────────────────

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def make_digest_response(ha1: str, nonce: str, method: str, uri: str) -> str:
    """
    Compute SIP digest response when Asterisk uses md5secret (pre-hashed HA1).
    ha1 is used directly — do NOT recompute it from username:realm:password.
    """
    ha2 = md5(f"{method}:{uri}")
    return md5(f"{ha1}:{nonce}:{ha2}")


def parse_www_authenticate(header: str):
    """Extract realm and nonce from WWW-Authenticate or Proxy-Authenticate header."""
    realm = re.search(r'realm="([^"]+)"', header)
    nonce = re.search(r'nonce="([^"]+)"', header)
    return (realm.group(1) if realm else ""), (nonce.group(1) if nonce else "")


def get_local_ip(device_ip: str) -> str:
    """Auto-detect local IP address used to reach device_ip."""
    try:
        return subprocess.check_output(
            f"ip route get {device_ip} | awk '{{print $7; exit}}'", shell=True
        ).decode().strip()
    except Exception:
        # Fallback: connect a UDP socket and read local address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((device_ip, 80))
            return s.getsockname()[0]
        finally:
            s.close()


# ── SIP message builder ────────────────────────────────────────────────────────

def build_message(device_ip: str, local_ip: str, local_port: int,
                  sip_user: str, to_user: str, body: str, content_type: str,
                  cseq: int, call_id: str, tag: str, branch: str,
                  auth_header: str = "") -> bytes:
    """Build a SIP MESSAGE request."""
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


# ── Challenge-response send ────────────────────────────────────────────────────

def send_message_with_auth(sock: socket.socket, device_ip: str, device_port: int,
                           local_ip: str, local_port: int, sip_user: str, ha1: str,
                           to_user: str, body: str, content_type: str = "text/plain"):
    """
    Send a SIP MESSAGE with digest auth challenge-response.
    Returns (full_response_str, first_line_str).
    Uses a fresh call-id and tag but the same socket (caller must set timeout).
    """
    call_id   = f"{uuid.uuid4().hex}@{local_ip}"
    tag       = uuid.uuid4().hex[:8]
    branch1   = f"z9hG4bK{uuid.uuid4().hex[:8]}"
    uri       = f"sip:{to_user}@{device_ip}"

    # Step 1: send without auth
    msg1 = build_message(device_ip, local_ip, local_port, sip_user, to_user,
                         body, content_type, 1, call_id, tag, branch1)
    sock.sendto(msg1, (device_ip, device_port))
    try:
        data, _ = sock.recvfrom(4096)
        resp1 = data.decode(errors="replace")
    except socket.timeout:
        return None, "(no response — timeout)"

    first_line = resp1.split("\r\n")[0]

    # Not a challenge — return immediately
    if "401" not in first_line and "407" not in first_line:
        return resp1, first_line

    # Step 2: parse challenge
    www_auth = ""
    for line in resp1.split("\r\n"):
        if line.lower().startswith("www-authenticate:") or line.lower().startswith("proxy-authenticate:"):
            www_auth = line
            break

    if not www_auth:
        return resp1, f"{first_line} (no auth challenge in response)"

    realm, nonce = parse_www_authenticate(www_auth)
    response     = make_digest_response(ha1, nonce, "MESSAGE", uri)
    auth_header  = (
        f'Authorization: Digest username="{sip_user}", realm="{realm}", '
        f'nonce="{nonce}", uri="{uri}", response="{response}", algorithm=MD5'
    )

    # Step 3: re-send with auth (new branch, same Call-ID)
    branch2 = f"z9hG4bK{uuid.uuid4().hex[:8]}"
    msg2 = build_message(device_ip, local_ip, local_port, sip_user, to_user,
                         body, content_type, 2, call_id, tag, branch2, auth_header)
    sock.sendto(msg2, (device_ip, device_port))
    try:
        data, _ = sock.recvfrom(4096)
        resp2 = data.decode(errors="replace")
    except socket.timeout:
        return None, f"(auth sent to realm={realm!r}, no response — timeout)"

    return resp2, resp2.split("\r\n")[0]


# ── Print helpers ──────────────────────────────────────────────────────────────

def print_approach_header(n: int, description: str, target: str, body: str,
                          content_type: str, auth: str):
    print(f"\n{'='*60}")
    print(f"=== Approach {n}: {description} ===")
    print(f"Target:       {target}")
    print(f"Body:         {body[:80]!r}{'...' if len(body) > 80 else ''}")
    print(f"Content-Type: {content_type}")
    print(f"Auth:         {auth}")


def print_result(result_line: str, full_response: str = None):
    print(f"Result:       {result_line}")
    if full_response and full_response.strip() and result_line not in ("(no response — timeout)",):
        # Print first 400 chars of non-trivial responses
        preview = full_response.strip()[:400]
        if "\r\n" in preview or "\n" in preview:
            print("Response:")
            for line in preview.replace("\r\n", "\n").split("\n")[:8]:
                print(f"  {line}")
    print("-" * 60)


# ── Individual approach runners ────────────────────────────────────────────────

def run_approach_1(device_ip: str, sip_user: str, ha1: str, to_user: str,
                   local_ip: str, port: int = 5060):
    """
    Approach 1: MESSAGE to Asterisk port 5060, TO=00e00000,
    body=OPEN_DOOR_IND (text/plain), digest auth with HA1.
    Tests: does correct auth + canonical TO user trigger AGI and open door?
    """
    body         = "OPEN_DOOR_IND"
    content_type = "text/plain"
    target       = f"sip:{to_user}@{device_ip}:{port}"

    print_approach_header(1, "MESSAGE → Asterisk :5060, TO=00e00000, plain text",
                          target, body, content_type,
                          f"Digest user={sip_user} HA1={ha1[:12]}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(3)
    local_port = sock.getsockname()[1]
    try:
        full, first = send_message_with_auth(
            sock, device_ip, port, local_ip, local_port,
            sip_user, ha1, to_user, body, content_type,
        )
        print_result(first, full)
    finally:
        sock.close()


def run_approach_2(device_ip: str, sip_user: str, ha1: str,
                   local_ip: str, port: int = 5060):
    """
    Approach 2: MESSAGE to Asterisk port 5060, TO=00800000000,
    body=OPEN_DOOR_IND (text/plain), digest auth with HA1.
    Tests: does the TO user (entry panel SettingId 3) affect dialplan routing?
    """
    to_user      = "00800000000"
    body         = "OPEN_DOOR_IND"
    content_type = "text/plain"
    target       = f"sip:{to_user}@{device_ip}:{port}"

    print_approach_header(2, "MESSAGE → Asterisk :5060, TO=00800000000, plain text",
                          target, body, content_type,
                          f"Digest user={sip_user} HA1={ha1[:12]}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(3)
    local_port = sock.getsockname()[1]
    try:
        full, first = send_message_with_auth(
            sock, device_ip, port, local_ip, local_port,
            sip_user, ha1, to_user, body, content_type,
        )
        print_result(first, full)
    finally:
        sock.close()


def run_approach_3(device_ip: str, sip_user: str, ha1: str,
                   local_ip: str, port: int = 5060):
    """
    Approach 3: MESSAGE to Asterisk port 5060, JSON body with application/json.
    Tests both TO=00e00000 and TO=00800000000.
    Tests: does content-type or body format matter for AGI trigger?
    """
    content_type = "application/json"

    for to_user in ("00e00000", "00800000000"):
        body = json.dumps({
            "method":  "OPEN_DOOR_IND",
            "from":    f"<sip:{sip_user}@{device_ip}>",
            "callid":  0,
            "srcaddr": SRC_ADDR,
            "dstaddr": "00e00000",
        }, separators=(",", ":"))
        target = f"sip:{to_user}@{device_ip}:{port}"

        print_approach_header(3, f"MESSAGE → Asterisk :5060, TO={to_user}, JSON body",
                              target, body, content_type,
                              f"Digest user={sip_user} HA1={ha1[:12]}...")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", 0))
        sock.settimeout(3)
        local_port = sock.getsockname()[1]
        try:
            full, first = send_message_with_auth(
                sock, device_ip, port, local_ip, local_port,
                sip_user, ha1, to_user, body, content_type,
            )
            print_result(first, full)
        finally:
            sock.close()


def run_approach_4(device_ip: str, sip_user: str, ha1: str,
                   local_ip: str, port: int = 5060):
    """
    Approach 4: MESSAGE to Asterisk port 5060, TO=00401200000 (Kamailio trunk user),
    body=OPEN_DOOR_IND (text/plain), digest auth with HA1.
    Tests: does addressing the Kamailio trunk user trigger a different dialplan context?
    """
    to_user      = "00401200000"
    body         = "OPEN_DOOR_IND"
    content_type = "text/plain"
    target       = f"sip:{to_user}@{device_ip}:{port}"

    print_approach_header(4, "MESSAGE → Asterisk :5060, TO=00401200000 (Kamailio trunk), plain text",
                          target, body, content_type,
                          f"Digest user={sip_user} HA1={ha1[:12]}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(3)
    local_port = sock.getsockname()[1]
    try:
        full, first = send_message_with_auth(
            sock, device_ip, port, local_ip, local_port,
            sip_user, ha1, to_user, body, content_type,
        )
        print_result(first, full)
    finally:
        sock.close()


def run_approach_5(device_ip: str, local_ip: str, port: int = 5062):
    """
    Approach 5: Direct MESSAGE to callmanager port 5062, TO=00800000000, no auth.
    Tries both UDP and TCP. callmanager is the component that directly triggers
    the door-open (sends OPEN_DOOR_REQ to lpcmanager).
    Tests: does callmanager accept LAN connections (vs 127.0.0.1 only)?
    """
    to_user      = "00800000000"
    body         = "OPEN_DOOR_IND"
    content_type = "text/plain"
    target       = f"sip:{to_user}@{device_ip}:{port}"

    print_approach_header(5, f"Direct MESSAGE → callmanager :{port} (no auth)",
                          target, body, content_type, "None (internal protocol)")

    call_id = f"{uuid.uuid4().hex}@{local_ip}"
    tag     = uuid.uuid4().hex[:8]
    branch  = f"z9hG4bK{uuid.uuid4().hex[:8]}"

    # UDP attempt
    print("  [UDP]")
    try:
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.bind(("", 0))
        sock_udp.settimeout(3)
        local_port = sock_udp.getsockname()[1]
        msg = build_message(device_ip, local_ip, local_port, "00700100002", to_user,
                            body, content_type, 1, call_id, tag, branch)
        sock_udp.sendto(msg, (device_ip, port))
        try:
            data, _ = sock_udp.recvfrom(4096)
            udp_resp = data.decode(errors="replace")
            udp_first = udp_resp.split("\r\n")[0]
        except socket.timeout:
            udp_first = "(no response — timeout)"
            udp_resp  = None
        print(f"  UDP Result: {udp_first}")
        if udp_resp and udp_first not in ("(no response — timeout)",):
            for line in udp_resp.strip()[:300].replace("\r\n", "\n").split("\n")[:5]:
                print(f"    {line}")
    except OSError as e:
        udp_first = f"(socket error: {e})"
        print(f"  UDP Result: {udp_first}")
    finally:
        sock_udp.close()

    # TCP attempt
    print("  [TCP]")
    branch_tcp = f"z9hG4bK{uuid.uuid4().hex[:8]}"
    msg_tcp = build_message(device_ip, local_ip, 0, "00700100002", to_user,
                            body, content_type, 1, call_id, tag, branch_tcp)
    # Replace UDP with TCP in Via
    msg_tcp_str = msg_tcp.decode().replace("SIP/2.0/UDP", "SIP/2.0/TCP")
    try:
        sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_tcp.settimeout(3)
        sock_tcp.connect((device_ip, port))
        sock_tcp.sendall(msg_tcp_str.encode())
        try:
            data = sock_tcp.recv(4096)
            tcp_resp  = data.decode(errors="replace")
            tcp_first = tcp_resp.split("\r\n")[0]
        except socket.timeout:
            tcp_first = "(connected but no response — timeout)"
            tcp_resp  = None
        print(f"  TCP Result: {tcp_first}")
        if tcp_resp and tcp_first not in ("(connected but no response — timeout)",):
            for line in tcp_resp.strip()[:300].replace("\r\n", "\n").split("\n")[:5]:
                print(f"    {line}")
    except ConnectionRefusedError:
        print(f"  TCP Result: (connection refused — port {port} is likely 127.0.0.1-only)")
    except socket.timeout:
        print(f"  TCP Result: (connection timed out — port {port} may be firewalled)")
    except OSError as e:
        print(f"  TCP Result: (socket error: {e})")
    finally:
        try:
            sock_tcp.close()
        except Exception:
            pass

    print("-" * 60)


def run_approach_6():
    """
    Approach 6: Cloud SIP path.
    Requires TLS, OAuth2 PKCE, SIP REGISTER, and MESSAGE over TLS to cloud proxy.
    This is not implemented here — use tools/sip_cloud_opendoor.py instead.
    """
    print(f"\n{'='*60}")
    print("=== Approach 6: Cloud SIP (not implemented in this script) ===")
    print(
        "Approach 6 (cloud SIP) requires TLS and OAuth2. "
        "Use tools/sip_cloud_opendoor.py instead."
    )
    print("-" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="BPT XTS7 door-open investigation script — tests all 6 approaches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "After running, check device syslogs for OPEN_DOOR_REQ in lpcmanager\n"
            "to confirm the door-open signal reached the hardware.\n\n"
            "Example:\n"
            "  python3 tools/sip_door_test.py --approach 1\n"
            "  python3 tools/sip_door_test.py --approach all\n"
            "  python3 tools/sip_door_test.py --device-ip 192.168.1.88 --approach 5\n"
        ),
    )
    p.add_argument("--device-ip", default=DEFAULT_DEVICE_IP,
                   help=f"XTS7 device IP (default: {DEFAULT_DEVICE_IP})")
    p.add_argument("--sip-user", default=DEFAULT_SIP_USER,
                   help=f"SIP username (default: {DEFAULT_SIP_USER})")
    p.add_argument("--ha1", default=DEFAULT_HA1,
                   help=f"Pre-computed HA1 / md5secret (default: known-good from syslog)")
    p.add_argument("--to-user", default=DEFAULT_TO_USER,
                   help=f"TO SIP user for approaches 1 and 3a (default: {DEFAULT_TO_USER})")
    p.add_argument("--approach", default="all",
                   choices=["1", "2", "3", "4", "5", "6", "all"],
                   help="Which investigation approach to run (default: all)")
    p.add_argument("--port", type=int, default=None,
                   help="Override target port (default: 5060 for approaches 1-4, 5062 for 5)")
    return p.parse_args()


def main():
    args   = parse_args()
    device = args.device_ip
    user   = args.sip_user
    ha1    = args.ha1
    to_u   = args.to_user

    local_ip = get_local_ip(device)
    print(f"Local IP detected: {local_ip}")
    print(f"Device IP:         {device}")
    print(f"SIP user:          {user}")
    print(f"HA1:               {ha1[:12]}...")
    print(f"TO user (A1/A3):   {to_u}")

    approaches = (
        ["1", "2", "3", "4", "5", "6"] if args.approach == "all"
        else [args.approach]
    )

    for a in approaches:
        if a == "1":
            p = args.port if args.port is not None else 5060
            run_approach_1(device, user, ha1, to_u, local_ip, port=p)
        elif a == "2":
            p = args.port if args.port is not None else 5060
            run_approach_2(device, user, ha1, local_ip, port=p)
        elif a == "3":
            p = args.port if args.port is not None else 5060
            run_approach_3(device, user, ha1, local_ip, port=p)
        elif a == "4":
            p = args.port if args.port is not None else 5060
            run_approach_4(device, user, ha1, local_ip, port=p)
        elif a == "5":
            p = args.port if args.port is not None else 5062
            run_approach_5(device, local_ip, port=p)
        elif a == "6":
            run_approach_6()

    print("\nDone. Check device syslogs (lpcmanager) for OPEN_DOOR_REQ to confirm hardware trigger.")


if __name__ == "__main__":
    main()
