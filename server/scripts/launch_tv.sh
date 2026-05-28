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

BASE="http://localhost:5002/tv/speed-pyramid"
URL="${1:-$BASE/}"
# If the arg is a path (starts with /), join it onto the speed-pyramid
# base — NOT the bare host (the app is mounted at /tv/speed-pyramid/).
# E.g. "/dev/hub" -> http://localhost:5002/tv/speed-pyramid/dev/hub.
if [[ "$URL" == /* ]]; then
  URL="${BASE}${URL}"
fi

PROFILE_DIR="${TMPDIR:-/tmp}/sp-tv-profile"
mkdir -p "$PROFILE_DIR"

echo "Launching Speed Pyramid TV (audio autoplay ENABLED)"
echo "  URL:     $URL"
echo "  profile: $PROFILE_DIR"

case "$(uname -s)" in
  Darwin)
    # --app= makes the window have NO tabs / NO address bar — looks like a
    # dedicated app window, impossible to confuse with regular Chrome
    # browsing. (Previously the launcher opened a normal Chrome window in
    # a separate profile, which looked identical to regular Chrome and
    # was easy to mix up — leading to "no audio" reports when the user
    # was actually testing in their regular Chrome with autoplay blocked.)
    open -na "Google Chrome" --args \
      --autoplay-policy=no-user-gesture-required \
      --user-data-dir="$PROFILE_DIR" \
      --window-size=1600,1000 \
      --window-position=80,80 \
      --app="$URL"
    ;;
  Linux)
    google-chrome \
      --autoplay-policy=no-user-gesture-required \
      --user-data-dir="$PROFILE_DIR" \
      --window-size=1600,1000 \
      --app="$URL" &
    disown
    ;;
  *)
    echo "Unsupported OS: $(uname -s)"; exit 1
    ;;
esac
