# Deployment — Networking & WiFi Coverage

## Network Setup

The Raspberry Pi needs **two network connections** in production:

- `eth0` — WAN (connected to the router/modem for internet)
- `wlan0` — WiFi AP (broadcasts the Piso WiFi SSID for customers)

```
Internet ── Router (modem) ──LAN cable── Pi (eth0)
                                            │
                                        wlan0 (AP mode)
                                            │
                                    SSID: "PisoWiFi"
                                    Customers connect here
```

### Why Ethernet is required

The Pi's WiFi chip can only operate in **one mode at a time**:
- **AP mode** (broadcasting its own SSID) — this is what we need for the captive portal
- **Client mode** (connecting to another WiFi network) — not used here

If the Pi connects to the internet via WiFi (client mode), it can't simultaneously broadcast its own AP on the same chip. Most USB WiFi adapters have the same limitation.

**Ethernet is not optional for production** — it's the Pi's WAN uplink.

---

## Direct Laptop Testing (No Router)

If you're testing away from a router, connect your laptop directly to the Pi via Ethernet and share your laptop's internet:

```
Laptop ──LAN cable── Pi (eth0)
    │                    │
    │               wlan0 (AP)
    │                    │
  Internet            Phone
  (WiFi/data)      (connects to
                    "PisoWiFi")
```

### On macOS (Internet Sharing)
1. System Settings → Sharing → Internet Sharing
2. Share from: Wi-Fi → To devices using: Ethernet
3. Enable

### On Linux
```bash
# Share internet from wlan0 (laptop's WiFi) to eth0 (connected to Pi)
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo sysctl net.ipv4.ip_forward=1
# Set up DHCP on eth0 side (dnsmasq or similar)
```

### On Windows
1. Settings → Network & Internet → Mobile Hotspot
2. Share my internet connection from: Wi-Fi
3. Choose Ethernet as the sharing method

---

## WiFi Coverage Options

The Pi's built-in WiFi may not be enough depending on the venue size.

### Option 1: Pi built-in WiFi (free, limited range)

| Item | Details |
|---|---|
| **Cost** | Free (already on the Pi) |
| **Range** | ~10–15m through walls |
| **Max clients** | ~15 before performance drops |
| **Best for** | Small sari-sari stores, single vendo |
| **Setup** | Default, no extra hardware needed |

### Option 2: USB WiFi adapter (better range)

| Item | Details |
|---|---|
| **Cost** | ₱400–1,200 |
| **Recommended** | Alfa AWUS036ACH (RTL8812AU chipset) |
| **Range** | ~30–50m with external antenna |
| **Max clients** | ~25 |
| **Note** | Pi USB is USB 2.0 — theoretical max ~300 Mbps, still fine for piso WiFi |
| **Setup** | Plug in, install driver if needed, set as AP interface |

### Option 3: Dedicated AP router (best for production)

```
Internet ── Router (modem) ── Pi (eth0)
                                 │
                            AP Router (Access Point mode)
                              │
                          Customers connect here
```

| Item | Details |
|---|---|
| **Cost** | ₱800–2,000 (any used TP-Link, Tenda, Linksys) |
| **Range** | Depends on router — 50–100m typical |
| **Max clients** | 30–50 |
| **Best for** | Large stores, multiple vendos, reliable coverage |
| **Setup** | Put router in **Access Point mode**, disable its DHCP, connect LAN-to-LAN |

#### How to configure the AP router

1. Connect laptop to the AP router via Ethernet
2. Disable DHCP on the AP router (the Pi's dnsmasq handles DHCP)
3. Set the AP router's IP to something unused (e.g. 192.168.1.2)
4. Connect the AP router to the Pi: **LAN port → Pi's LAN port** (not WAN)
5. The Pi's dnsmasq will assign IPs to clients connecting through the AP

No code changes needed — the Pi's iptables rules work the same regardless of which device broadcasts the WiFi.

### Recommendation

| Use case | What to use |
|---|---|
| Testing / small store | Option 1 (built-in WiFi) |
| Medium store | Option 2 (USB adapter) |
| Production / large venue | **Option 3 (dedicated AP router)** — most reliable |
