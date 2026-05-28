#!/usr/bin/env bash
# Launch the Speed Pyramid TV in Chrome with audio autoplay ENABLED.
#
# Web code cannot disable Chrome's "click to unlock audio" policy from
# inside the page — only a command-line flag can. This is also how the
# headless Playwright gates run, and how a real bar/kiosk TV deploys.
#
# The --user-data-dir is required: Chrome ignores command-line flags if
# another Chrome instance is already running (it just opens a new window
# in that instance and drops the flag). A separate profile dir forces a
# fresh Chrome process with the flag honored.
#
# Usage:
#   ./scripts/launch_tv.sh            # opens the TV title at :5002
#   ./scripts/launch_tv.sh /dev/hub   # opens the Hub instead
#   ./scripts/launch_tv.sh https://... # any url
#
# Save as a Desktop alias / "Start TV" shortcut for one-click launch.

set -e

URL="${1:-http://localhost:5002/tv/speed-pyramid/}"
# If the arg is a path (starts with /), join it to the default host.
if [[ "$URL" == /* ]]; then
  URL="http://localhost:5002${URL}"
fi

PROFILE_DIR="${TMPDIR:-/tmp}/sp-tv-profile"
mkdir -p "$PROFILE_DIR"

echo "Launching Speed Pyramid TV (audio autoplay ENABLED)"
echo "  URL:     $URL"
echo "  profile: $PROFILE_DIR"

case "$(uname -s)" in
  Darwin)
    open -na "Google Chrome" --args \
      --autoplay-policy=no-user-gesture-required \
      --user-data-dir="$PROFILE_DIR" \
      --new-window \
      "$URL"
    ;;
  Linux)
    google-chrome \
      --autoplay-policy=no-user-gesture-required \
      --user-data-dir="$PROFILE_DIR" \
      --new-window \
      "$URL" &
    disown
    ;;
  *)
    echo "Unsupported OS: $(uname -s)"; exit 1
    ;;
esac
