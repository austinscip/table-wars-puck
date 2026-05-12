#!/usr/bin/env bash
# Configure the puck1_speed_pyramid PlatformIO env with real WiFi
# credentials and the server URL, then build + (optionally) upload.
#
# Usage:
#   bin/configure-puck.sh           # interactive prompts, build only
#   bin/configure-puck.sh --upload  # interactive prompts, build + flash
#
# Re-writes platformio.ini in place, scoped to the puck1_speed_pyramid
# [env:] section only. Other envs are not touched.

set -euo pipefail

cd "$(dirname "$0")/.."
PIO_INI="platformio.ini"

if [ ! -f "$PIO_INI" ]; then
  echo "error: $PIO_INI not found (run this from the repo root or via bin/configure-puck.sh)" >&2
  exit 1
fi

# Pull current LAN IP for the default server URL prompt.
default_ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 192.168.1.100)"
default_url="http://${default_ip}:5001"

echo "============================================"
echo " Speed Pyramid v1 puck configuration"
echo "============================================"
echo
read -r -p "WiFi SSID (the bar's WiFi): " ssid
read -r -s -p "WiFi password: " pass
echo
read -r -p "Server URL [${default_url}]: " server
server="${server:-$default_url}"
read -r -p "Puck ID [1]: " puck_id
puck_id="${puck_id:-1}"
read -r -p "Hardware revision (a/b) [b]: " rev
rev="${rev:-b}"
rev="$(echo "$rev" | tr '[:upper:]' '[:lower:]')"

# Escape any double-quotes the user typed.
esc() { printf '%s' "$1" | sed 's/"/\\"/g'; }
ssid_esc="$(esc "$ssid")"
pass_esc="$(esc "$pass")"
server_esc="$(esc "$server")"

# Use a Python helper for the in-place rewrite — bash sed is fragile
# across BSD/GNU and we want to scope the edit to the right [env:] block.
python3 - "$PIO_INI" "$puck_id" "$ssid_esc" "$pass_esc" "$server_esc" "$rev" <<'PY'
import sys, re
path, puck_id, ssid, pwd, url, rev = sys.argv[1:]
with open(path) as f:
    src = f.read()

# Find the [env:puck1_speed_pyramid] section and replace its build_flags.
section_re = re.compile(
    r"(\[env:puck1_speed_pyramid\][\s\S]*?build_flags\s*=)([\s\S]*?)(?=\n\[|\Z)",
    re.MULTILINE,
)

rev_line = "\n    -D PUCK_REV_B" if rev.startswith("b") else ""
new_flags = (
    f"\n    -D PUCK_ID={puck_id}"
    f"{rev_line}"
    f"\n    -D SPEED_PYRAMID_SERVER_URL=\\\"{url}\\\""
    f"\n    -D SPEED_PYRAMID_WIFI_SSID=\\\"{ssid}\\\""
    f"\n    -D SPEED_PYRAMID_WIFI_PASS=\\\"{pwd}\\\"\n"
)

m = section_re.search(src)
if not m:
    sys.stderr.write("could not find [env:puck1_speed_pyramid] build_flags block\n")
    sys.exit(2)

src = src[:m.start(2)] + new_flags + src[m.end(2):]
with open(path, "w") as f:
    f.write(src)
print(f"updated {path}: PUCK_ID={puck_id}, rev={rev}, server={url}, ssid={ssid}")
PY

echo
echo "Now building firmware..."
if ! command -v pio >/dev/null 2>&1; then
  echo "error: pio (PlatformIO) not on PATH. Install with: pip install platformio" >&2
  exit 1
fi
pio run -e puck1_speed_pyramid

if [ "${1:-}" = "--upload" ]; then
  echo
  echo "Uploading to ESP32 over USB. Make sure the puck is plugged in."
  pio run -e puck1_speed_pyramid -t upload
  echo
  echo "Done. Run \`pio device monitor --baud 115200\` to watch serial output."
else
  echo
  echo "Build done. To flash an ESP32 plugged in via USB:"
  echo "  bin/configure-puck.sh --upload    (or rerun pio run -e puck1_speed_pyramid -t upload)"
fi
