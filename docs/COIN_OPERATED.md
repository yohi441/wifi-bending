# Coin-Operated Piso WiFi — Hardware Guide

## Overview

The current app is software-only: users redeem a printed voucher code. To make it coin-operated, you need a **coin acceptor** that detects inserted coins and triggers voucher generation automatically.

## Coin Acceptor Hardware Options

| Hardware | Price (PHP) | Connection | How it works |
|---|---|---|---|
| **CH-926 Coin Acceptor** | ₱500–800 | 3 wires to GPIO | Sends a pulse per coin, coin type detected by pulse width |
| **Pulse-type coin acceptor** | ₱800–1,500 | GPIO or USB | Different pulse counts = different coin values |
| **Bill acceptor** | ₱2,000–5,000 | Serial (RS232) or USB | Accepts paper bills, sends denomination via serial data |
| **MDB adapter (e.g. MDB2UART)** | ₱1,500–3,000 | USB to UART | Professional vending standard, needed for complex setups |

### Recommended: CH-926 Coin Acceptor

The CH-926 is the most common choice for DIY Piso WiFi because it's cheap, simple, and well-documented.

**Connection (3 wires):**

| CH-926 wire | Pi GPIO |
|---|---|
| Red (VCC) | 5V pin |
| Black (GND) | GND pin |
| Yellow (Signal) | GPIO 17 (or any GPIO) |

**Coin programming:** The CH-926 has a learning mode — you insert coins and it remembers how long each pulse lasts for each denomination.

## How It Would Work

```
               CH-926 Coin Acceptor
                       │
              Pulse signal (GPIO 17)
                       ▼
          ┌─────────────────────┐
          │  coin_acceptor.py   │
          │  (background daemon)│
          │                     │
          │  Reads GPIO pulses  │
          │  Counts total amount│
          │  Checks price table  │
          └────────┬────────────┘
                   │
        Amount sufficient? (e.g. ₱10)
                   │ YES
                   ▼
          ┌─────────────────────┐
          │  Auto-generate      │
          │  voucher via API    │
          └────────┬────────────┘
                   │
                   ▼
          Customer gets internet
          Show remaining time
          on OLED display
```

### Software changes needed (later)

| File | What it does |
|---|---|
| `backend/coin_acceptor.py` | GPIO listener, coin pulse counter, amount tracking |
| `backend/templates/admin/coin_settings.html` | Configure prices per coin type, duration per amount |
| `backend/admin_api.py` | Add coin acceptor settings routes |

**Pseudo-code for the coin acceptor:**

```python
# backend/coin_acceptor.py (future)
import RPi.GPIO as GPIO
import requests

COIN_PIN = 17
PRICES = {10: 60, 20: 120, 50: 360}  # amount -> minutes

amount = 0

def on_coin_pulse(channel):
    global amount
    amount += 1  # or detect coin value from pulse width

    for price, minutes in sorted(PRICES.items()):
        if amount >= price:
            # Generate voucher and grant access
            r = requests.post("http://localhost:8000/admin/vouchers/create",
                            json={"duration_minutes": minutes, "price_pesos": price, "count": 1})
            voucher_code = r.json()["vouchers"][0]["code"]
            # Also auto-redeem for the current device
            amount = 0
            break

GPIO.setmode(GPIO.BCM)
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(COIN_PIN, GPIO.FALLING, callback=on_coin_pulse)
```

## Optional: OLED Display

A small OLED screen on the vendo machine shows the customer how much they've inserted and how much time they'll get.

| Hardware | Price (PHP) | Connection |
|---|---|---|
| SSD1306 OLED 128x64 (I2C) | ₱150–250 | I2C (SDA/SCL to GPIO 2/3) |
| SSD1306 OLED 128x32 (I2C) | ₱100–200 | Same |

**Displays:**
- "Insert ₱10 for 60 min"
- "Inserted: ₱5 / ₱10"
- "Connected — 45:32 remaining"

**Python library:** `pip install luma.oled`

## Bill of Materials (Full Coin-Op Vendo)

| Item | Est. Cost (PHP) |
|---|---|
| Raspberry Pi 4 (2GB) | ₱2,500–3,500 |
| CH-926 Coin Acceptor | ₱500–800 |
| SSD1306 OLED Display | ₱150–250 |
| Power supply (5V/3A) | ₱500–600 |
| microSD 32GB | ₱500–700 |
| Case with coin slot hole | ₱300–500 |
| **Total** | **~₱4,500–6,500** |

This is about the price of a commercial Piso WiFi unit, but you own the software and can customize everything.
