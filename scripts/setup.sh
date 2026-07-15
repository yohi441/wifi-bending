#!/usr/bin/env bash
set -euo pipefail

# Piso WiFi — Multi-Platform Setup Script
# Supports: Raspberry Pi (Pi OS, DietPi) + Orange Pi (Armbian)
# Auto-detects: network manager, WAN interface, WiFi interface

SSID="${SSID:-PisoWiFi}"
PASSPHRASE="${PASSPHRASE:-}"
WIFI_IFACE="${WIFI_IFACE:-}"
WAN_IFACE="${WAN_IFACE:-}"
IP_NET="${IP_NET:-192.168.1}"
GATEWAY="${IP_NET}.1"
DHCP_RANGE_START="${IP_NET}.100"
DHCP_RANGE_END="${IP_NET}.200"
INSTALL_DIR="${INSTALL_DIR:-}"

echo "=== Piso WiFi Multi-Platform Setup ==="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# --- Auto-detect interfaces ---
if [ -z "$WAN_IFACE" ]; then
    if ip link show eth0 &>/dev/null; then
        WAN_IFACE="eth0"
    elif ip link show end0 &>/dev/null; then
        WAN_IFACE="end0"
    else
        echo "ERROR: No WAN interface found. Set WAN_IFACE manually."
        exit 1
    fi
fi

if [ -z "$WIFI_IFACE" ]; then
    if ip link show wlan0 &>/dev/null; then
        WIFI_IFACE="wlan0"
    else
        WIFI_IFACE=$(ls /sys/class/net/ 2>/dev/null | grep -E '^wl' | head -1 || true)
        if [ -z "$WIFI_IFACE" ]; then
            echo "ERROR: No WiFi interface found. Plug in a USB WiFi dongle or set WIFI_IFACE manually."
            exit 1
        fi
    fi
fi

echo "SSID: $SSID"
echo "WiFi Interface: $WIFI_IFACE"
echo "WAN Interface: $WAN_IFACE"
echo "Gateway: $GATEWAY"
echo ""

# --- Install packages ---
echo ""
echo "[1/8] Installing packages..."
apt-get update -qq
apt-get install -y -qq hostapd dnsmasq iptables-persistent netfilter-persistent python3-pip python3-venv

# --- Configure hostapd ---
echo "[2/8] Configuring hostapd..."
cat > /etc/hostapd/hostapd.conf <<HOSTAPD
interface=$WIFI_IFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
HOSTAPD

if [ -n "$PASSPHRASE" ]; then
    cat >> /etc/hostapd/hostapd.conf <<HOSTAPD_SEC
wpa=2
wpa_passphrase=$PASSPHRASE
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
HOSTAPD_SEC
fi

sed -i 's|^#DAEMON_CONF.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd 2>/dev/null || true

# --- Configure dnsmasq ---
echo "[3/8] Configuring dnsmasq..."
cat > /etc/dnsmasq.conf <<DNSMASQ
interface=$WIFI_IFACE
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,255.255.255.0,24h
dhcp-option=3,$GATEWAY
dhcp-option=6,$GATEWAY
server=8.8.8.8
server=8.8.4.4
no-resolv
log-queries
log-dhcp
DNSMASQ

# --- Configure static IP via systemd-networkd ---
echo "[4/8] Configuring static IP for $WIFI_IFACE..."

ip addr flush dev "$WIFI_IFACE" 2>/dev/null || true

cat > /etc/systemd/network/12-piso-wifi.network <<NETWORK
[Match]
Name=$WIFI_IFACE

[Network]
Address=${GATEWAY}/24
IPForward=yes
NETWORK

systemctl enable systemd-networkd 2>/dev/null || true
systemctl restart systemd-networkd 2>/dev/null || true

ip addr add "${GATEWAY}/24" dev "$WIFI_IFACE" 2>/dev/null || true
ip link set "$WIFI_IFACE" up 2>/dev/null || true

# --- Enable IP forwarding ---
echo "[5/8] Enabling IP forwarding..."
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.d/99-piso-wifi.conf
sysctl -p /etc/sysctl.d/99-piso-wifi.conf 2>/dev/null || true

# --- Disable wpa_supplicant and unblock WiFi ---
echo "[6/8] Preparing WiFi interface..."
systemctl stop wpa_supplicant 2>/dev/null || true
systemctl disable wpa_supplicant 2>/dev/null || true
rfkill unblock wifi 2>/dev/null || true
ip link set "$WIFI_IFACE" down 2>/dev/null || true
ip link set "$WIFI_IFACE" up 2>/dev/null || true

# --- Enable services ---
echo "[7/8] Enabling services..."
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd dnsmasq
systemctl restart hostapd dnsmasq 2>/dev/null || true

# --- Install systemd service ---
echo "[8/8] Installing pisowifi.service..."

if [ -z "$INSTALL_DIR" ]; then
    if [ -d "/home/pi/piso_wifi" ]; then
        INSTALL_DIR="/home/pi/piso_wifi"
    elif [ -d "/root/piso_wifi" ]; then
        INSTALL_DIR="/root/piso_wifi"
    elif [ -f "$PWD/backend/main.py" ]; then
        INSTALL_DIR="$PWD"
    else
        INSTALL_DIR="/home/pi/piso_wifi"
    fi
fi

VENV_PYTHON="${INSTALL_DIR}/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$(which python3)"
fi

cat > /etc/systemd/system/pisowifi.service <<SERVICE
[Unit]
Description=Piso WiFi Server
After=network.target hostapd.service dnsmasq.service
Wants=hostapd.service dnsmasq.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_PYTHON} -m backend.main
Restart=on-failure
RestartSec=5
Environment=DEV_MODE=false

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable pisowifi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Interfaces:"
echo "  WAN:  $WAN_IFACE (internet from router)"
echo "  WiFi: $WIFI_IFACE (AP broadcasting '$SSID')"
echo "  Gateway: $GATEWAY"
echo "  DHCP range: $DHCP_RANGE_START - $DHCP_RANGE_END"
echo ""
echo "Reboot to apply changes: sudo reboot"
echo ""
echo "After reboot, the system starts automatically."
echo "To start manually without reboot:"
echo "  sudo systemctl start pisowifi"
echo ""
