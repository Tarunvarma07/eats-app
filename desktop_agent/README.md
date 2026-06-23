# EATS Desktop Activity Agent

A lightweight background agent that sends activity heartbeats to the EATS server while an employee is clocked in.

## How it works

```
Employee logs in (web) → opens terminal → runs agent.py → agent sends heartbeat every 90s → admin sees live activity %
```

1. Agent detects keyboard/mouse events via **pynput** (cross-platform).
2. Every **90 seconds** it checks: *"Has there been input in the last 5 minutes?"*
   - YES → `status = "active"`  
   - NO  → `status = "idle"`, includes `idle_seconds`
3. POSTs to `POST /activity/heartbeat` using the employee's JWT.
4. Server rejects with **409** if no open session (employee not clocked in).
5. On **401** (token expired), agent clears the saved token and stops.

---

## Setup

```bash
cd desktop_agent

# Create a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running

```bash
python agent.py
```

On first run, the agent will ask you to:
- **Paste your JWT** (copy from browser DevTools → Application → Local Storage), OR  
- **Enter email + password** to log in directly

The token is stored securely in the **OS keychain** (Windows Credential Manager / macOS Keychain Access) for subsequent runs.

---

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `EATS_SERVER` | `http://127.0.0.1:8000` | EATS backend URL |
| `EATS_INTERVAL` | `90` | Heartbeat interval in seconds |
| `EATS_IDLE_THRESH` | `300` | Seconds without input = idle (5 min) |

```bash
# Example — production server
EATS_SERVER=https://eats.yourcompany.com python agent.py
```

---

## Platform notes

| OS | Idle detection | Token storage |
|---|---|---|
| **Windows** | ✅ Win32 API via pynput | ✅ Windows Credential Manager |
| **macOS** | ✅ Requires Accessibility permission* | ✅ macOS Keychain Access |
| **Linux** | ✅ Xlib (`apt install python3-xlib`) | ✅ Secret Service (GNOME Keyring) |

\* macOS: Go to **System Preferences → Security & Privacy → Privacy → Accessibility** and add your terminal app.

---

## Security notes

- The JWT is stored in the **OS keychain**, not a plaintext file.
- `user_id` is **never** sent in the request body — derived from the JWT server-side.
- The agent has **write-only** access to heartbeats. It cannot read any activity data.
- Heartbeats are silently dropped (409) if the employee is not clocked in.

---

## Office / WFH detection

Office vs Remote classification happens **automatically at login** based on the employee's IP address. The agent itself does not do any location detection — it only reports activity (active/idle).

If the auto-detection is wrong (e.g. you're in the office on a VPN), the employee can correct it from the web dashboard **Settings** page.

---

## Privacy boundary

The agent only tracks:
- ✅ Whether there was **any** keyboard/mouse input in the last interval (binary active/idle)
- ✅ Seconds of idle time

The agent does **NOT** track:
- ❌ Which keys were pressed
- ❌ What apps were open
- ❌ Screenshots or screen recording
- ❌ Browser URLs
- ❌ GPS or precise location
