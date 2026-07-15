# Remote Access — Admin Dashboard from Anywhere

## Comparison of Methods

| Method | Cost | Security | Setup Time | Best For |
|---|---|---|---|---|
| **Tailscale** | Free (3 users) | Very high — encrypted tunnel, no open ports | 5 min | **Recommended** for production |
| **Cloudflare Tunnel** | Free | High — DDoS protection, access policies | 15 min | Custom domain, zero-trust access |
| **ngrok** | Free tier (random URL) | Medium — plain TCP tunnel | 2 min | Quick testing only |
| **Port forward + HTTPS** | Free | Low — must add auth, firewall config | 20 min | Not recommended alone |
| **WireGuard VPN** | Free | Very high — enterprise-grade VPN | 30 min | Advanced users, self-hosted |

---

## Method 1: Tailscale (Recommended)

Tailscale creates a secure, encrypted network between your devices. No open ports on the router, no static IP needed.

### How it works

```
Admin's phone       Admin's laptop          Internet
    │                     │                    │
    └─────────────────────┘                    │
            │                            Tailscale DERP
       Tailscale net                   (relay if needed)
            │                                  │
            └──────────────────────────────────┘
                            │
                     Raspberry Pi
                     (tailscale up)
```

### Installation

```bash
# On the Pi
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Follow the URL to authenticate in your browser
# The Pi gets a 100.x.x.x IP address
```

```bash
# On your phone/laptop
# Install from: https://tailscale.com/download
# Sign in to the same account as the Pi
```

### Access the dashboard

Open `http://100.x.x.x:8000/admin` from any device on your Tailscale network.

### Distributing to friends — two models

#### Model A: Your Tailscale account (zero effort for friends)

You create one Tailscale account. Each Pi joins **your** network using a pre-authorized auth key.

```
You (admin) ─── Tailscale ─── Pi #1 (Friend A)
                              ─── Pi #2 (Friend B)
                              ─── Pi #3 (Friend C)
```

- **You** can access all dashboards from one account — monitoring, support, updates
- **Friends** don't need to do anything — the Pi auto-joins on first boot
- Pre-auth key baked into the SD card image
- Tailscale ACLs can restrict what each device can access

**How to generate a pre-auth key:**
1. Log into https://login.tailscale.com
2. Settings → Keys → Generate auth key
3. Set "Reusable" and "Ephemeral" as needed
4. Bake `sudo tailscale up --authkey tskey-xxxx` into the first-boot script

#### Model B: Each friend's own account

Each friend installs Tailscale on their phone, creates a free account, then the Pi joins their network.

- **Friend** can access their own dashboard from anywhere
- **You** can only see their Pi if they share it to you (Tailscale "share device" feature)
- More setup per person, but each friend has full control

---

## Method 2: Multi-Tenant Cloud Platform (Future Feature)

For a centralized system where multiple vendos can be managed through a single website.

### Architecture

```
┌──────────────────────────────┐
│    Cloud Server              │
│    (piso.example.com)        │
│                              │
│  ┌────────────────────────┐  │
│  │  Web Dashboard (React) │  │
│  │  ┌───┐ ┌───┐ ┌───┐   │  │
│  │  │ A │ │ B │ │ C │   │  │
│  │  └───┘ └───┘ └───┘   │  │
│  │  (isolated per user)  │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  API + JWT Auth        │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  PostgreSQL            │  │
│  └────────────────────────┘  │
└──────────────┬───────────────┘
               │ Internet
    ┌──────────┼──────────┐
    │          │          │
┌───▼────┐ ┌───▼────┐ ┌───▼────┐
│ Pi #1  │ │ Pi #2  │ │ Pi #3  │
│ Agent  │ │ Agent  │ │ Agent  │
│ syncs  │ │ syncs  │ │ syncs  │
│ data   │ │ data   │ │ data   │
└────────┘ └────────┘ └────────┘
```

### Key principles

1. **Local-first** — Pi works fully offline. Voucher generation, sessions, local admin all work without internet
2. **Opt-in remote** — Admin enables cloud sync from local settings. No data leaves the Pi unless turned on
3. **Multi-tenant isolation** — Each cloud user sees only their Pi(s). No cross-tenant access
4. **Simple sync** — Pi sends JSON payloads every ~60s. Server stores them. No complex real-time needed

### Components to build

| Component | Description |
|---|---|
| **Cloud backend** | New FastAPI project (`piso-cloud/`) with Postgres, JWT auth, REST API |
| **Cloud frontend** | React/Vue dashboard — log in, list vendos, view stats per vendo |
| **Pi sync agent** | Background task in the Pi app that pushes sessions/revenue to the cloud |
| **Settings UI** | Toggle "Enable remote sync" with API key configuration in the local admin panel |

### What the Pi sends to the cloud

```json
{
  "pi_id": "xxxx-xxxx",
  "api_key": "sk-xxxx",
  "timestamp": "2026-06-09T12:00:00+08:00",
  "stats": {
    "active_sessions": 3,
    "total_vouchers_used": 142,
    "total_revenue": 1420.00
  },
  "recent_sessions": [
    {"mac": "AA:BB:CC:DD:EE:FF", "duration": 60, "price": 10, "time": "..."}
  ],
  "system": {
    "uptime_hours": 240,
    "disk_usage_pct": 45,
    "cpu_temp_c": 62
  }
}
```

### When you're ready to build this

This is a substantial feature — an entire new cloud project plus changes to the Pi app. The recommended order:

1. Register/Login with JWT on the cloud
2. Pi registration (generate API key, link to user account)
3. Pi sync agent (push data every 60s)
4. Cloud dashboard (list vendos, view stats)
5. Optional: remote commands (disconnect session, create voucher from cloud)
