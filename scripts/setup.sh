#!/usr/bin/env bash
set -euo pipefail

# Piso WiFi — Raspberry Pi Setup Script
# Configures hostapd, dnsmasq, and iptables for captive portal

SSID="${SSID:-PisoWiFi}"
PASSPHRASE="${PASSPHRASE:-}"
WIFI_IFACE="${WIFI_IFACE:-wlan0}"
WAN_IFACE="${WAN_IFACE:-eth0}"
IP_NET="${IP_NET:-192.168.1}"
GATEWAY="${IP_NET}.1"
DHCP_RANGE_START="${IP_NET}.100"
DHCP_RANGE_END="${IP_NET}.200"

echo "=== Piso WiFi Setup ==="
echo "SSID: $SSID"
echo "WiFi Interface: $WIFI_IFACE"
echo "WAN Interface: $WAN_IFACE"
echo "Gateway: $GATEWAY"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

echo ""
echo "[1/6] Installing packages..."
apt-get update -qq
apt-get install -y -qq hostapd dnsmasq iptables-persistent netfilter-persistent python3-pip

echo "[2/6] Configuring hostapd..."
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

sed -i 's|^#DAEMON_CONF.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "[3/6] Configuring dnsmasq..."
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

echo "[4/6] Configuring static IP for $WIFI_IFACE..."
cat > /etc/dhcpcd.conf <<DHCPCD
interface $WIFI_IFACE
static ip_address=${GATEWAY}/24
nohook wpa_supplicant
DHCPCD

echo "[5/6] Enabling IP forwarding..."
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-piso-wifi.conf
sysctl -p /etc/sysctl.d/99-piso-wifi.conf

echo "[6/6] Enabling services..."
systemctl unmask hostapd
systemctl enable hostapd dnsmasq
systemctl restart dhcpcd

echo ""
echo "=== Setup complete! ==="
echo "Reboot to apply changes: sudo reboot"
echo ""
echo "After reboot, run the Piso WiFi server:"
echo "  cd /path/to/piso_wifi"
echo "  pip install -r requirements.txt"
echo "  python -m backend.main"
