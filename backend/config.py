import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = f"sqlite:///{BASE_DIR}/piso_wifi.db"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

WIFI_IFACE = os.getenv("WIFI_IFACE", "wlan0")
WAN_IFACE = os.getenv("WAN_IFACE", "eth0")
GATEWAY_IP = os.getenv("GATEWAY_IP", "192.168.1.1")
SUBNET = os.getenv("SUBNET", "192.168.1.0/24")

VOUCHER_CODE_LENGTH = 8
VOUCHER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SESSION_CHECK_INTERVAL = 15

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"

COIN_MINUTES_PER_PESO = 6
COIN_AUTO_GRANT_TIMEOUT = 10
COIN_MINIMUM_AMOUNT = 1
COIN_POLL_INTERVAL = 2
COIN_GPIO_PIN = int(os.getenv("COIN_GPIO_PIN", "17"))

DEFAULT_COIN_SETTINGS = {
    "coin_minutes_per_peso": str(COIN_MINUTES_PER_PESO),
    "coin_auto_grant_timeout": str(COIN_AUTO_GRANT_TIMEOUT),
    "coin_minimum_amount": str(COIN_MINIMUM_AMOUNT),
}
