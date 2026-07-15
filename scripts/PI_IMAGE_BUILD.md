# Piso WiFi — Custom Raspberry Pi Image

Two approaches to create a ready-to-flash image with piso_wifi pre-installed and auto-configured.

## Approach 1: Raspberry Pi Imager + First-Boot Script

Simpler method. Uses the official Raspberry Pi Imager to flash Lite OS with a preloaded first-boot script that auto-configures everything.

### What it does

1. Raspberry Pi Imager writes Raspberry Pi OS Lite to the SD card
2. The `firstboot.sh` script is placed in `/boot/` and runs on first power-on
3. Script installs hostapd, dnsmasq, python deps, copies piso_wifi files, creates systemd service, enables IP forwarding
4. 60 seconds later the Pi is broadcasting "PisoWiFi" and the portal is live at `192.168.1.1:8000`

### Files needed

- `scripts/pisowifi.service` — systemd unit to auto-start the app
- `scripts/firstboot.sh` — first-boot setup script

### User steps

1. Open Raspberry Pi Imager
2. Choose: Raspberry Pi OS Lite (64-bit)
3. In advanced menu (Ctrl+Shift+X): set hostname = `pisowifi`, enable SSH, set locale = Asia/Manila
4. Add firstboot.sh to run on first boot
5. Flash SD card → insert into Pi → power on
6. After ~1 minute, connect to "PisoWiFi" SSID and open `http://192.168.1.1:8000`

## Approach 2: Custom Image with pi-gen

Fully pre-built `.img` file. Uses [pi-gen](https://github.com/RPi-Distro/pi-gen) to build a custom OS image with piso_wifi baked in.

### What it does

- Builds a complete `.img` file from source
- Includes all packages, files, and configuration
- Output is a ready-to-flash image that can be shared or downloaded

### Steps

1. Fork/clone `github.com/RPi-Distro/pi-gen`
2. Add a custom stage (`stage-pisowifi`) that:
   - Installs hostapd, dnsmasq, iptables-persistent, python3-pip
   - Copies piso_wifi/ backend into the image
   - Creates systemd service for auto-start
   - Configures hostapd (SSID = "PisoWiFi"), dnsmasq, static IP
3. Run `sudo ./build.sh` → produces `pisowifi-lite-xxx.img`

### Build prerequisites

- Ubuntu/Debian Linux machine
- ~8GB free disk space
- Several hours build time (first build)

## Recommendation

Use Approach 1 for now:
- Faster to iterate
- No build machine needed
- Just share the SD card or a disk image created by the Imager's "Save" feature
- Easier to update when the app changes

Switch to Approach 2 if you need to distribute the image publicly or flash many units at once.
