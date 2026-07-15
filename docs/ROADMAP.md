# Roadmap

## Phase 1 (Complete)
- [x] Captive portal with voucher redemption
- [x] Voucher generation and management
- [x] Session tracking with automatic expiry
- [x] iptables-based access control
- [x] Admin dashboard with stats
- [x] Raspberry Pi setup script

## Phase 2 (Planned)
- [ ] Bandwidth control per user (tc rate limiting)
- [ ] Revenue reports (daily/weekly/monthly)
- [ ] Data usage tracking
- [ ] Online payment integration (GCash, PayMaya)
- [ ] Voucher printing / PDF export

## Phase 3 (Planned)
- [ ] Custom branding (SSID, logo, theme)
- [ ] MAC cooldown / anti-abuse
- [ ] Backup & restore
- [ ] Remote admin via management interface (Tailscale)

## Coin-Operated Hardware (Planned)
- [ ] Coin acceptor integration (CH-926 / pulse-type)
- [ ] OLED display support (SSD1306)
- [ ] Auto-voucher generation on coin insert
- [ ] Admin settings for coin pricing tiers

## Multi-Tenant Cloud Platform (Planned)
- [ ] Cloud backend API (FastAPI + PostgreSQL + JWT auth)
- [ ] User registration and login
- [ ] Pi registration with API key generation
- [ ] Pi sync agent (push sessions/revenue to cloud every 60s)
- [ ] Cloud web dashboard (list vendos, view stats, revenue reports)
- [ ] Tenant isolation — each user sees only their Pi(s)
- [ ] Optional: remote commands (disconnect, create voucher from cloud)

## Deployment & Distribution (Planned)
- [ ] First-boot auto-setup script (`scripts/firstboot.sh`)
- [ ] systemd service for auto-start on boot (`scripts/pisowifi.service`)
- [ ] Build helper for Raspberry Pi Imager (`scripts/build-imager-image.sh`)
- [ ] Custom pi-gen stage for fully pre-built `.img` distribution
