# Development Workflow

## Local Development (on your laptop)

The app runs on any machine with Python 3.9+. Dev mode skips iptables calls and generates synthetic MAC addresses.

```bash
cd piso_wifi
source venv/bin/activate
rm -f piso_wifi.db   # fresh database
python -m backend.main
```

Then open:
- http://localhost:8000/portal — captive portal
- http://localhost:8000/admin — admin dashboard
- http://localhost:8000/docs — auto-generated API docs (Swagger UI)

### Dev mode behavior

| Feature | In production (Pi) | In dev mode (laptop) |
|---|---|---|
| **MAC detection** | Reads `/proc/net/arp` | Synthetic MAC: `DE:VI:CE:{IP}` |
| **iptables grant** | Adds ACCEPT rule | Logs to console only |
| **iptables revoke** | Removes ACCEPT rule | Logs to console only |
| **Captive redirect** | iptables NAT redirect | Manual navigation to `/portal` |

Dev mode is enabled by default. Set `DEV_MODE=false` in the environment to disable it:

```bash
DEV_MODE=false python -m backend.main
```

---

## Syncing Code to the Raspberry Pi

### Option 1: rsync (fastest)

Create `scripts/sync-to-pi.sh`:

```bash
#!/usr/bin/env bash
PI_HOST="${1:-pi@192.168.1.100}"

rsync -avz --exclude venv --exclude __pycache__ --exclude '*.db' \
  --exclude '.git' \
  ~/Desktop/piso_wifi/ "$PI_HOST:/home/pi/piso_wifi/"

echo "Synced to $PI_HOST"
```

Make it executable and run:

```bash
chmod +x scripts/sync-to-pi.sh
./scripts/sync-to-pi.sh
```

### Option 2: Git

```bash
# On laptop
cd ~/Desktop/piso_wifi
git init
git add .
git commit -m "initial"

# Add remote (GitHub, GitLab, or your own server)
git remote add origin git@github.com:yourname/piso-wifi.git
git push -u origin main

# On Pi
ssh pi@192.168.1.100
git clone git@github.com:yourname/piso-wifi.git
cd piso-wifi
git pull  # to update later
```

### Option 3: VS Code Remote SSH (best for active development)

1. Install the **Remote - SSH** extension in VS Code
2. Press `F1` → "Remote-SSH: Connect to Host"
3. Enter: `ssh pi@192.168.1.100`
4. Open folder: `/home/pi/piso_wifi`
5. Edit files on your laptop — they save directly to the Pi
6. VS Code terminal runs on the Pi — restart the server directly

---

## Auto-Reload (Zero-Downtime Restarts)

Run uvicorn with `--reload` to auto-restart when Python files change:

```bash
# On the Pi
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Now every time you sync files (rsync, git pull), uvicorn detects the changes and restarts automatically.

---

## Development Cycle (End-to-End)

```
1. Edit code on laptop (VS Code)
2. Run: ./scripts/sync-to-pi.sh    (< 1 second)
3. uvicorn on Pi auto-reloads      (zero manual restart)
4. Test on phone browser           (instant)
```

Total time from code change to testing on phone: **~2 seconds**.

---

## Debugging Tips

### View real-time logs

```bash
ssh pi@192.168.1.100
source ~/piso_wifi/venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Check if the app is running

```bash
curl -s http://localhost:8000/portal | head -5
```

### Manually test voucher redemption

```bash
# Create a voucher
curl -X POST http://localhost:8000/admin/vouchers/create \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 10, "price_pesos": 5, "count": 1}'

# Redeem it (replace CODE with actual code)
curl -X POST http://localhost:8000/redeem \
  -H "Content-Type: application/json" \
  -d '{"code": "ZH7TSG75"}'
```

### Check sessions and vouchers

```bash
# Check active sessions
sqlite3 piso_wifi.db "SELECT * FROM sessions WHERE is_active=1;"

# Check voucher stats
sqlite3 piso_wifi.db "SELECT COUNT(*), SUM(is_used) FROM vouchers;"
```
