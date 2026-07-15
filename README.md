# Piso WiFi

A self-hosted, coin-operated-style WiFi voucher system for Raspberry Pi. Users enter a voucher code to get timed internet access — no physical coin acceptor needed. Built with FastAPI + SQLite + iptables.

## Features

- **Captive Portal** — Unauthenticated users are redirected to a login page; authenticated users get internet
- **Voucher System** — Generate codes with configurable duration and price
- **Session Management** — Tracks active sessions with automatic expiry
- **Admin Dashboard** — Create vouchers, monitor active sessions, view revenue, force-disconnect users
- **Background Scheduler** — Automatically disconnects expired sessions every 15 seconds
- **Firewall Integration** — Uses iptables MAC allowlisting to grant/revoke access per device

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| **Backend** | FastAPI (Python) | Async-native, auto OpenAPI docs, Pydantic validation, lightweight on Pi |
| **Database** | SQLite | Zero-config, fast enough for single-Pi deployment |
| **ORM** | SQLAlchemy 2.0 | Reliable, well-documented, async-compatible |
| **Templates** | Jinja2 | Server-rendered HTML (no JS framework needed for portal) |
| **WiFi AP** | hostapd | Standard Linux tool for AP mode, proven on Raspberry Pi |
| **DHCP/DNS** | dnsmasq | Single binary, lightweight, handles both DHCP and DNS |
| **Firewall** | iptables | Kernel-level packet filtering, MAC-based allowlisting |

## Hardware Requirements

### Minimum (learning / light use)

| Component | Model | Est. Cost (PHP) |
|---|---|---|
| Raspberry Pi | Pi 3 Model B+ (1.4GHz, 1GB RAM) | ₱1,500–2,000 |
| microSD | 16GB Class 10 | ₱250–300 |
| Power | 5V/2.5A adapter | ₱200–300 |
| Case | Basic acrylic | ₱150–250 |
| **Total** | | **~₱2,500–3,500** |

### Recommended (production)

| Component | Model | Est. Cost (PHP) |
|---|---|---|
| Raspberry Pi | Pi 4 Model B (2GB or 4GB) | ₱2,500–3,500 |
| microSD | 32GB A2 High Endurance (Samsung Pro Endurance) | ₱500–700 |
| Power | Official 5V/3A USB-C | ₱500–600 |
| Case | Heatsink case with fan | ₱400–500 |
| **Total** | | **~₱4,000–5,500** |

**Network layout:**
- `eth0` — WAN (internet from modem/router)
- `wlan0` — WiFi AP (broadcasts the Piso WiFi SSID)

> Pi 4 is preferred over Pi 5: better thermal stability in enclosed vendo cabinets, proven hostapd compatibility.

## Architecture

```
┌────────────────────────────────────────────┐
│              Raspberry Pi                   │
│                                              │
│  ┌──────────┐      ┌──────────────────┐     │
│  │  hostapd  │─────▶│  WiFi AP (SSID)  │     │
│  │ (AP mode) │      │   wlan0          │     │
│  └──────────┘      └──────────────────┘     │
│                                              │
│  ┌──────────┐      ┌──────────────────┐     │
│  │ dnsmasq   │─────▶│  DHCP + DNS      │     │
│  │           │      │  192.168.1.0/24  │     │
│  └──────────┘      └──────────────────┘     │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │          iptables                     │    │
│  │  PISO_WIFI chain:                    │    │
│  │    ├─ ACCEPT (authenticated MACs)    │────▶ eth0 → Internet
│  │    └─ DROP (unauth → redirect :8000) │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │         FastAPI Server (:8000)        │    │
│  │  ├─ GET /portal    — captive portal  │    │
│  │  ├─ POST /redeem   — voucher auth    │    │
│  │  ├─ GET /status    — session check   │    │
│  │  ├─ GET /admin/*   — admin dashboard │    │
│  │  └─ Scheduler      — expiry every 15s│    │
│  └──────────────┬───────────────────────┘    │
│                 │                             │
│  ┌──────────────▼───────────────────────┐    │
│  │           SQLite Database            │    │
│  │  ├─ vouchers (code, duration, used) │    │
│  │  └─ sessions (MAC, IP, time)        │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

## Client Workflow

```
1. CONNECT       User connects to the Piso WiFi SSID on their phone/laptop

2. DHCP          dnsmasq assigns an IP (e.g. 192.168.1.100)

3. BROWSE        User opens any website (e.g. google.com)

4. REDIRECT      iptables catches port 80 → redirects to FastAPI on :8000

5. DETECTION     FastAPI reads client IP from request, looks up MAC via ARP table,
                 checks for an active session:
                 ├─ YES → return 204 (device thinks internet works)
                 └─ NO  → return 302 redirect to /portal

6. PORTAL        User sees the Piso WiFi login page with a voucher input field

7. ENTER CODE    User types the 8-character code (displayed as XXXX-XXXX)

8. REDEEM        JavaScript sends POST /redeem with the code.
                 Server validates:
                 ├─ Valid? → iptables ACCEPT rule added for MAC,
                 │           session created, voucher marked used,
                 │           success page with countdown timer shown
                 └─ Invalid? → error message displayed

9. INTERNET      User's traffic passes through iptables FORWARD → eth0 → internet

10. EXPIRY       Background scheduler (every 15s) finds sessions where
                 end_time ≤ now, removes iptables rule, sets session inactive.
                 User's next request returns to the portal.
```

## Admin Workflow

```
1. DASHBOARD     Open http://[pi-ip]:8000/admin
                 Shows: total vouchers, used/unused counts, revenue, active sessions

2. CREATE        Click "Create Vouchers" → set duration (min), price (PHP), quantity
                 → system generates unique codes (e.g. ZH7TSG75)
                 → codes displayed on screen, stored in database

3. MANAGE        Browse /admin/vouchers — table of all vouchers with status
                 Deactivate individual vouchers to prevent future use

4. MONITOR       Browse /admin/sessions — two sections:
                 Active Sessions: currently connected users with expiry times
                 Recent Sessions: historical log of all past connections

5. DISCONNECT    Click "Disconnect" on any active session →
                 iptables rule removed, session ended, user loses internet immediately
```

## Installation

### Development (local PC testing)

```bash
cd piso_wifi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m backend.main
```

Open http://localhost:8000 for the captive portal and http://localhost:8000/admin for the admin dashboard.

> Note: iptables firewall commands will fail on a regular PC. The web UI, voucher system, and session management work without it.

### Raspberry Pi (production)

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit) to microSD

# 2. Boot the Pi, connect via SSH, then run:
cd piso_wifi
sudo bash scripts/setup.sh

# 3. Reboot
sudo reboot

# 4. After reboot:
cd piso_wifi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo python -m backend.main
```

### Configuration

Edit `backend/config.py` to customize:

| Setting | Default | Description |
|---|---|---|
| `WIFI_IFACE` | `wlan0` | WiFi interface for AP |
| `WAN_IFACE` | `eth0` | WAN interface for internet |
| `GATEWAY_IP` | `192.168.1.1` | Gateway IP for clients |
| `SUBNET` | `192.168.1.0/24` | Client subnet |
| `HOST` | `0.0.0.0` | FastAPI bind address |
| `PORT` | `8000` | FastAPI port |
| `VOUCHER_CODE_LENGTH` | `8` | Characters per voucher code |
| `SESSION_CHECK_INTERVAL` | `15` | Seconds between expiry checks |

## API Endpoints

### Captive Portal

| Method | Path | Description |
|---|---|---|
| `GET` | `/portal` | Serves the captive portal login page |
| `POST` | `/redeem` | Redeems a voucher code (body: `{"code": "..."}`) |
| `GET` | `/status` | Checks if the requesting client is authenticated |
| `GET` | `/generate_204` | Captive portal detection (returns 204 if authenticated) |
| `GET` | `/` | Redirects to /portal |

### Admin

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin` | Admin dashboard with stats |
| `GET` | `/admin/vouchers` | Voucher list with pagination |
| `GET` | `/admin/vouchers/create` | Voucher creation form |
| `POST` | `/admin/vouchers/create` | Creates vouchers |
| `POST` | `/admin/vouchers/{id}/deactivate` | Deactivates a voucher |
| `GET` | `/admin/sessions` | Session list with pagination |
| `POST` | `/admin/sessions/{id}/disconnect` | Force-disconnects a session |

## Database Schema

### `vouchers` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment ID |
| `code` | TEXT (unique) | 8-char voucher code |
| `duration_minutes` | INTEGER | Minutes of internet access |
| `price_pesos` | REAL | Price in Philippine pesos |
| `is_used` | BOOLEAN | Whether the voucher has been redeemed |
| `is_active` | BOOLEAN | Whether the voucher is active |
| `created_at` | DATETIME | When the voucher was generated |
| `used_at` | DATETIME (nullable) | When the voucher was redeemed |

### `sessions` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment ID |
| `voucher_code` | TEXT (nullable) | Code used to authenticate |
| `mac_address` | TEXT | Client MAC address (indexed) |
| `ip_address` | TEXT | Client IP address |
| `start_time` | DATETIME | Session start time |
| `end_time` | DATETIME | Session expiry time |
| `duration_minutes` | INTEGER | Duration in minutes |
| `is_active` | BOOLEAN | Whether session is currently active |
| `data_used_bytes` | INTEGER | Data usage (reserved for Phase 2) |

## Project Structure

```
piso_wifi/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry, mounts routers, starts scheduler
│   ├── config.py            # Settings (interfaces, ports, voucher format)
│   ├── database.py          # SQLAlchemy engine, session factory, init_db()
│   ├── models.py            # ORM models: Voucher, Session
│   ├── schemas.py           # Pydantic schemas for request/response validation
│   ├── voucher.py           # Generate, validate, redeem, deactivate vouchers
│   ├── session_manager.py   # Create, end, lookup sessions; remaining time
│   ├── firewall.py          # iptables: setup, grant, revoke, flush, MAC lookup
│   ├── scheduler.py         # Background loop: expire stale sessions
│   ├── captive_portal.py    # Routes: /portal, /redeem, /status, /generate_204
│   ├── admin_api.py         # Routes: /admin (dashboard, vouchers, sessions)
│   ├── templates/
│   │   ├── portal.html      # Captive portal login page (voucher input)
│   │   ├── success.html     # Connected page (countdown timer)
│   │   └── admin/
│   │       ├── base.html        # Admin layout with sidebar
│   │       ├── dashboard.html   # Stats overview
│   │       ├── vouchers.html    # Voucher table + management
│   │       ├── create_voucher.html  # Voucher generation form
│   │       └── sessions.html    # Active + recent sessions
│   └── static/
├── scripts/
│   ├── setup.sh             # Automated Pi setup (hostapd, dnsmasq, iptables)
│   └── reset_firewall.sh    # Flush all Piso WiFi iptables rules
├── venv/
├── requirements.txt         # Python dependencies
└── README.md
```

## Scripts

### `scripts/setup.sh`
Automates Raspberry Pi configuration:
- Installs hostapd, dnsmasq, iptables-persistent, python3-pip
- Configures hostapd with configurable SSID and optional WPA2 passphrase
- Sets up dnsmasq for DHCP (192.168.1.100–200 range) and DNS (Google DNS)
- Assigns static IP to the WiFi interface
- Enables IP forwarding

Usage:
```bash
SSID="MyPisoWiFi" sudo bash scripts/setup.sh
```

### `scripts/reset_firewall.sh`
Removes all Piso WiFi iptables rules and chains, disconnecting all clients.

See [ROADMAP.md](ROADMAP.md) for planned features.

