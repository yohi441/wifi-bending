#!/usr/bin/env bash
set -euo pipefail

# Flush all Piso WiFi firewall rules

echo "Resetting Piso WiFi firewall rules..."

# Remove from FORWARD chain
iptables -D FORWARD -i wlan0 -o eth0 -j PISO_WIFI 2>/dev/null || true
iptables -D FORWARD -i eth0 -o wlan0 -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true

# Flush and delete PISO_WIFI chain
iptables -F PISO_WIFI 2>/dev/null || true
iptables -X PISO_WIFI 2>/dev/null || true

# Remove NAT redirects
iptables -t nat -D PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8000 2>/dev/null || true
iptables -t nat -D PREROUTING -i wlan0 -p tcp --dport 443 -j REDIRECT --to-port 8000 2>/dev/null || true

echo "Firewall rules reset. All clients disconnected."
