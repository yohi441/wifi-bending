#!/usr/bin/env python3
"""
Piso WiFi Coin Simulator

Simulates coin insert pulses to the captive portal API.
Usage:
    python scripts/coin-simulator.py --amount 5
    python scripts/coin-simulator.py --amount 5 --base-url http://192.168.1.1:8000
"""

import argparse
import sys
import time
import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000"


def post_json(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def main():
    parser = argparse.ArgumentParser(description="Simulate coin insert pulses")
    parser.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Amount in pesos to insert (e.g. 5, 10, 20)",
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL of the Piso WiFi portal (default: {BASE_URL})",
    )
    parser.add_argument(
        "--pulse-value",
        type=float,
        default=1.0,
        help="Value of each simulated pulse in pesos (default: 1.0)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between simulated pulses (default: 0.5)",
    )
    args = parser.parse_args()

    if args.amount <= 0:
        print("Error: amount must be positive")
        sys.exit(1)
    if args.pulse_value <= 0:
        print("Error: pulse-value must be positive")
        sys.exit(1)

    base = args.base_url.rstrip("/")
    pulses = int(args.amount / args.pulse_value)

    print(f"Simulating {args.amount} peso(s) via {pulses} pulse(s) of ₱{args.pulse_value} each")
    print(f"Portal: {base}/portal")
    print(f"Interval: {args.interval}s")
    print()

    # Check initial status
    try:
        status = get_json(f"{base}/coin-status")
        print(f"Before: amount=₱{status['amount']}, safe={status['safe']}")
    except Exception as e:
        print(f"Warning: could not fetch initial status: {e}")

    total_sent = 0.0
    for i in range(pulses):
        remaining = pulses - i
        sys.stdout.write(
            f"\rPulse {i+1}/{pulses} (₱{args.pulse_value}) — total: ₱{total_sent + args.pulse_value:.1f}    "
        )
        sys.stdout.flush()

        try:
            post_json(f"{base}/coin-pulse", {"amount": args.pulse_value})
            total_sent += args.pulse_value
        except urllib.error.HTTPError as e:
            print(f"\nHTTP error: {e.code} {e.reason}")
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"\nConnection error: {e.reason}")
            print(f"Make sure the server is running at {base}")
            sys.exit(1)

        if i < pulses - 1:
            time.sleep(args.interval)

    print()
    print()

    # Check final status
    try:
        status = get_json(f"{base}/coin-status")
        print(f"After:  amount=₱{status['amount']}, minutes={status['minutes']}, safe={status['safe']}")
        print(f"Button enabled: {status['button_enabled']}")
        print(f"Auto-grant seconds remaining: {status['auto_grant_seconds']}")
        print()
        print(f"Now open {base}/portal and click Connect")
    except Exception as e:
        print(f"Warning: could not fetch final status: {e}")


if __name__ == "__main__":
    main()
