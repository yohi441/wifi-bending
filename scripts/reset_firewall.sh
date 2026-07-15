#!/usr/bin/env bash
set -euo pipefail

# Reset all Piso WiFi iptables rules

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Auto-detect WAN interface
WAN_IFACE="${WAN_IFACE:-}"
if [ -z "$WAN_IFACE" ]; then
    if ip link show eth0 &>/dev/null; then
        WAN_IFACE="eth0"
    elif ip link show end0 &>/dev/null; then
        WAN_IFACE="end0"
    else
        WAN_IFACE="eth0"
    fi
fi

WIFI_IFACE="${WIFI_IFACE:-wlan0}"

echo "Resetting Piso WiFi firewall rules..."
echo "  WAN: $WAN_IFACE, WiFi: $WIFI_IFACE"

# Flush PISO_WIFI chain
iptables -F PISO_WIFI 2>/dev/null || true
iptables -X PISO_WIFI 2>/dev/null || true

# Remove FORWARD rules
iptables -D FORWARD -i "$WIFI_IFACE" -o "$WAN_IFACE" -j PISO_WIFI 2>/dev/null || true
iptables -D FORWARD -i "$WAN_IFACE" -o "$WIFI_IFACE" -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true

# Remove NAT rules
iptables -t nat -D PREROUTING -i "$WIFI_IFACE" -p tcp --dport 80 -j REDIRECT --to-port 8000 2>/dev/null || true
iptables -t nat -D PREROUTING -i "$WIFI_IFACE" -p tcp --dport 443 -j REDIRECT --to-port 8000 2>/dev/null || true
iptables -t nat -D POSTROUTING -o "$WAN_IFACE" -j MASQUERADE 2>/dev/null || true

echo "All Piso WiFi rules flushed. All clients disconnected."
