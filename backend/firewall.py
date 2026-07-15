import logging
import subprocess
from pathlib import Path

from backend.config import DEV_MODE, GATEWAY_IP, SUBNET, WAN_IFACE, WIFI_IFACE

logger = logging.getLogger(__name__)

PISO_CHAIN = "PISO_WIFI"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    logger.debug("Running iptables: %s", " ".join(cmd))
    return subprocess.run(
        ["sudo"] + cmd,
        check=check,
        capture_output=True,
        text=True,
    )


def _is_chain_available() -> bool:
    result = subprocess.run(
        ["sudo", "iptables", "-L", PISO_CHAIN],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def setup_captive_portal() -> None:
    if DEV_MODE:
        logger.info("DEV_MODE: skipping iptables setup")
        return
    if _is_chain_available():
        logger.info("PISO_WIFI chain already exists, skipping setup")
        return

    _run(["iptables", "-N", PISO_CHAIN])

    _run([
        "iptables", "-A", "FORWARD",
        "-i", WIFI_IFACE, "-o", WAN_IFACE,
        "-j", PISO_CHAIN,
    ])

    _run(["iptables", "-A", PISO_CHAIN, "-j", "DROP"])

    _run([
        "iptables", "-t", "nat", "-A", "PREROUTING",
        "-i", WIFI_IFACE,
        "-p", "tcp", "--dport", "80",
        "-j", "REDIRECT", "--to-port", "8000",
    ])

    _run([
        "iptables", "-t", "nat", "-A", "PREROUTING",
        "-i", WIFI_IFACE,
        "-p", "tcp", "--dport", "443",
        "-j", "REDIRECT", "--to-port", "8000",
    ])

    _run([
        "iptables", "-A", "FORWARD",
        "-i", WAN_IFACE, "-o", WIFI_IFACE,
        "-m", "state", "--state", "ESTABLISHED,RELATED",
        "-j", "ACCEPT",
    ])

    logger.info("Captive portal iptables rules installed")


def grant_access(mac_address: str) -> None:
    if DEV_MODE:
        logger.info("DEV_MODE: would grant access to %s", mac_address)
        return
    _run([
        "iptables", "-I", PISO_CHAIN, "1",
        "-m", "mac", "--mac-source", mac_address,
        "-j", "ACCEPT",
    ])
    logger.info("Granted access to %s", mac_address)


def revoke_access(mac_address: str) -> None:
    if DEV_MODE:
        logger.info("DEV_MODE: would revoke access for %s", mac_address)
        return
    try:
        _run([
            "iptables", "-D", PISO_CHAIN,
            "-m", "mac", "--mac-source", mac_address,
            "-j", "ACCEPT",
        ])
        logger.info("Revoked access for %s", mac_address)
    except subprocess.CalledProcessError:
        logger.warning("Rule not found for %s (already removed)", mac_address)


def flush_all() -> None:
    if DEV_MODE:
        logger.info("DEV_MODE: skipping iptables flush")
        return
    try:
        _run(["iptables", "-F", PISO_CHAIN])
        _run(["iptables", "-X", PISO_CHAIN])
        _run([
            "iptables", "-t", "nat", "-D", "PREROUTING",
            "-i", WIFI_IFACE,
            "-p", "tcp", "--dport", "80",
            "-j", "REDIRECT", "--to-port", "8000",
        ], check=False)
        _run([
            "iptables", "-t", "nat", "-D", "PREROUTING",
            "-i", WIFI_IFACE,
            "-p", "tcp", "--dport", "443",
            "-j", "REDIRECT", "--to-port", "8000",
        ], check=False)
        _run([
            "iptables", "-D", "FORWARD",
            "-i", WIFI_IFACE, "-o", WAN_IFACE,
            "-j", PISO_CHAIN,
        ], check=False)
        _run([
            "iptables", "-D", "FORWARD",
            "-i", WAN_IFACE, "-o", WIFI_IFACE,
            "-m", "state", "--state", "ESTABLISHED,RELATED",
            "-j", "ACCEPT",
        ], check=False)
        logger.info("All PISO_WIFI rules flushed")
    except subprocess.CalledProcessError as e:
        logger.error("Failed to flush rules: %s", e)


def _synthetic_mac(ip_address: str) -> str:
    ip_parts = ip_address.replace(".", "_")
    return f"DE:VI:CE:{ip_parts}"


def get_mac_from_ip(ip_address: str) -> str | None:
    if DEV_MODE:
        mac = _synthetic_mac(ip_address)
        logger.info("DEV_MODE: using synthetic MAC %s for IP %s", mac, ip_address)
        return mac
    arp_path = Path("/proc/net/arp")
    if not arp_path.exists():
        logger.error("/proc/net/arp not found")
        return None
    for line in arp_path.read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[0] == ip_address:
            mac = parts[3]
            if mac and mac != "00:00:00:00:00:00":
                return mac.upper()
    return None
