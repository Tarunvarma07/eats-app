#!/usr/bin/env python3
"""
EATS Desktop Activity Agent
============================
Sends activity heartbeats to the EATS server every HEARTBEAT_INTERVAL seconds.
Detects idle time via pynput (cross-platform keyboard + mouse monitoring).

Workflow
--------
1. Agent starts.  It asks for (or reads from keyring) a JWT token.
2. Every HEARTBEAT_INTERVAL seconds it checks how long the system has been idle.
3. If idle_seconds < IDLE_THRESHOLD  → status = "active"
   If idle_seconds >= IDLE_THRESHOLD → status = "idle"
4. POSTs to /activity/heartbeat.  Stops if the server returns 409 (no open session).
5. On Ctrl-C or SIGTERM, gracefully stops the heartbeat loop.

Requirements: pynput, requests, keyring  (see requirements.txt)
"""

import time
import signal
import logging
import threading
import sys
import getpass
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from pynput import keyboard, mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# ── Configuration (edit or override via environment variables) ────────────────
import os

SERVER_URL        = os.getenv("EATS_SERVER", "http://127.0.0.1:8000")
HEARTBEAT_INTERVAL= int(os.getenv("EATS_INTERVAL",  "90"))   # seconds
IDLE_THRESHOLD    = int(os.getenv("EATS_IDLE_THRESH","300"))  # 5 minutes

KEYRING_SERVICE  = "EATS_Agent"
KEYRING_USERNAME = "jwt_token"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("eats-agent")

# ── Idle detection ────────────────────────────────────────────────────────────
_last_input_time: float = time.monotonic()
_lock = threading.Lock()


def _record_input(*args):
    """Called by pynput listeners on any keyboard/mouse event."""
    global _last_input_time
    with _lock:
        _last_input_time = time.monotonic()


def get_idle_seconds() -> float:
    """Returns seconds since the last keyboard/mouse event."""
    with _lock:
        return time.monotonic() - _last_input_time


def start_input_listeners():
    """
    Attach pynput listeners for keyboard and mouse.
    Both run in daemon threads so they die when the main thread exits.
    """
    if not PYNPUT_AVAILABLE:
        log.warning(
            "pynput is not installed — idle detection disabled. "
            "All heartbeats will report status='active'."
        )
        return

    try:
        kb = keyboard.Listener(
            on_press=_record_input,
            on_release=_record_input,
            daemon=True,
        )
        ms = mouse.Listener(
            on_move=_record_input,
            on_click=_record_input,
            on_scroll=_record_input,
            daemon=True,
        )
        kb.start()
        ms.start()
        log.info("Input listeners started (keyboard + mouse).")
    except Exception as exc:
        log.warning(f"Could not start input listeners: {exc}")


# ── Token management ──────────────────────────────────────────────────────────
def load_token() -> Optional[str]:
    """Try keyring first, then fall back to manual entry."""
    if KEYRING_AVAILABLE:
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if token:
            log.info("Token loaded from system keychain.")
            return token

    print("\n" + "=" * 50)
    print("  EATS Activity Agent — Authentication")
    print("=" * 50)
    print(f"Server: {SERVER_URL}")
    print()
    print("Paste your JWT token (from the EATS web login page)")
    print("or press Enter to login with email + password:")
    print()

    token = input("JWT token (or blank to login): ").strip()
    if token:
        _save_token(token)
        return token

    # Login with credentials
    email    = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    try:
        resp = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token", "")
        if not token:
            raise ValueError("No token in login response")
        _save_token(token)
        log.info("Login successful.")
        return token
    except requests.HTTPError as exc:
        log.error(f"Login failed: {exc.response.text}")
        return None
    except Exception as exc:
        log.error(f"Login error: {exc}")
        return None


def _save_token(token: str):
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
            log.info("Token saved to system keychain.")
        except Exception:
            pass   # keychain unavailable on this system — run statelessly


def clear_token():
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception:
            pass


# ── Heartbeat ─────────────────────────────────────────────────────────────────
_stop_event = threading.Event()


def send_heartbeat(token: str) -> bool:
    """
    POST /activity/heartbeat.
    Returns False when the agent should stop (401 token expired / 409 no session).
    """
    idle_secs   = int(get_idle_seconds())
    is_idle     = idle_secs >= IDLE_THRESHOLD
    status      = "idle" if is_idle else "active"
    idle_payload= idle_secs if is_idle else None

    payload = {"status": status}
    if idle_payload is not None:
        payload["idle_seconds"] = idle_payload

    try:
        resp = requests.post(
            f"{SERVER_URL}/activity/heartbeat",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if resp.status_code == 200:
            log.info(
                f"♥  Heartbeat sent — {status}"
                + (f" (idle {idle_secs}s)" if is_idle else "")
            )
            return True

        elif resp.status_code == 401:
            log.warning("Token expired or invalid — stopping agent.")
            clear_token()
            return False   # signal to stop

        elif resp.status_code == 409:
            log.info("No active session on server — agent paused. "
                     "Will retry next cycle.")
            return True    # keep running; user might log in again

        else:
            log.warning(f"Unexpected response {resp.status_code}: {resp.text[:200]}")
            return True

    except requests.ConnectionError:
        log.warning(f"Cannot reach server at {SERVER_URL} — will retry.")
        return True
    except requests.Timeout:
        log.warning("Heartbeat request timed out — will retry.")
        return True
    except Exception as exc:
        log.error(f"Heartbeat error: {exc}")
        return True


def heartbeat_loop(token: str):
    """Main loop: send a heartbeat every HEARTBEAT_INTERVAL seconds."""
    log.info(
        f"Heartbeat loop started — interval: {HEARTBEAT_INTERVAL}s, "
        f"idle threshold: {IDLE_THRESHOLD}s"
    )

    while not _stop_event.is_set():
        keep_going = send_heartbeat(token)
        if not keep_going:
            _stop_event.set()
            break

        # Sleep in small increments so Ctrl-C interrupts promptly
        for _ in range(HEARTBEAT_INTERVAL):
            if _stop_event.is_set():
                break
            time.sleep(1)

    log.info("Heartbeat loop stopped.")


# ── Signal handling ───────────────────────────────────────────────────────────
def _handle_signal(signum, frame):
    log.info("Shutdown signal received — stopping agent.")
    _stop_event.set()


signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    log.info("EATS Desktop Activity Agent starting…")
    log.info(f"  Server:    {SERVER_URL}")
    log.info(f"  Interval:  {HEARTBEAT_INTERVAL}s")
    log.info(f"  Idle threshold: {IDLE_THRESHOLD}s ({IDLE_THRESHOLD//60}m)")

    # 1. Start input listeners (background daemon threads)
    start_input_listeners()

    # 2. Acquire token
    token = load_token()
    if not token:
        log.error("Could not obtain a valid token. Exiting.")
        sys.exit(1)

    # 3. Run heartbeat loop
    heartbeat_loop(token)

    log.info("EATS agent exited cleanly.")


if __name__ == "__main__":
    main()
