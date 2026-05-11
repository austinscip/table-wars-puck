# How to demo Speed Pyramid v1

This is the owner-action checklist. Three paths depending on how real
you want the demo. Each step is concrete.

## Path A — Click-through on the laptop (fastest)

You did this already. The fix landed:

1. `cd ~/table-wars-puck/server/static/games/speed-pyramid && npm run build`
2. `cd ~/table-wars-puck/server && DATABASE_URL= python app.py`
3. Open `http://localhost:5001/tv/speed-pyramid` in a browser.
4. Click **"Demo mode — no puck"**.

**Audio should now play** (the demo button now primes the AudioContext on
that click — browser autoplay policies were blocking it before).

If you still hear nothing: check the laptop's system volume, then
DevTools console for `AudioContext` errors. Tab must stay focused.

## Path B — Play on the actual TV, no puck (real screen, demo input)

Your laptop's LAN IP is **192.168.1.67**. Flask binds to 0.0.0.0 already.

1. Make sure laptop + TV are on the **same WiFi**.
2. On the laptop, run the same two commands as Path A
   (`npm run build` and `python app.py`).
3. On the TV's built-in browser (most smart TVs have one — Samsung's is
   the Tizen browser, LG's is the webOS browser, Sony/Roku/Hisense all
   ship one), open:

   ```
   http://192.168.1.67:5001/tv/speed-pyramid
   ```

   If the TV's remote can't type easily, use the TV's keyboard shortcut
   to recent URLs, or cast a tab from the laptop's Chrome.
4. Click **"Demo mode — no puck"** with the TV remote / mouse.

If the LAN IP changes after a router restart, find the new one:
`ipconfig getifaddr en0`. Update the URL on the TV accordingly. (Or
give the laptop a static DHCP lease in your router so it sticks.)

## Path C — Real puck, real TV, full demo

This is the actual product. Requires editing the firmware build to
include WiFi creds + your LAN IP, then flashing the puck over USB.

### One-shot config + flash

I wrote a script that prompts you for everything and rewrites
`platformio.ini` in place:

```
cd ~/table-wars-puck
bin/configure-puck.sh --upload
```

It will ask for:
- WiFi SSID (your home WiFi or the bar's WiFi — must match the TV's network)
- WiFi password
- Server URL (default `http://192.168.1.67:5001` — auto-detected from your en0)
- Puck ID (default 1)

Then it builds and uploads to whichever ESP32 is plugged into USB.

After flashing:
- `pio device monitor --baud 115200` to watch the serial logs.
- The puck connects to WiFi. Serial prints its IP if successful.
- Hold the puck button 1s — it enters pair mode.
- Tilt the puck up/down to dial each of the 6 digits the TV displays.
  Tap to advance.
- After the 6th tap, the puck POSTs `/api/pair/confirm`; both ends light up
  the PAIRED state and the TV begins the 3-2-1 countdown.
- Play 7 questions. Tilt the puck up/right/down/left to aim at A/B/C/D;
  tap to lock. LED ring shows the tilt quadrant in blue + a depleting
  timer ring in pink.

If the puck can't reach the server: it's almost always (a) WiFi creds
typo, (b) wrong server IP, or (c) firewall blocking port 5001. Re-run
`bin/configure-puck.sh --upload`.

## Common gotchas

- **No audio.** Browser blocked AudioContext. Click the demo button or
  any UI element to grant the gesture, then audio kicks in for the rest
  of the match. Hard-refresh (Cmd+Shift+R) after rebuilding the bundle.
- **Blank white screen.** Vite asset path mismatch. Rebuild + hard-refresh.
- **`/api/sp/load-question` returns 409.** Match already complete on
  that session_code. Hit `/api/sp/reset/<code>` or pair a new session.
- **Puck connects but never appears.** Check serial output. WiFi STA
  takes 1-3s to associate; if it times out after 15s you'll see a
  "WiFi: NOT CONNECTED" line. Verify SSID/PASS by joining from a phone.
- **Production deploy still missing the Node build step.** Don't ship to
  Railway yet — `Dockerfile` needs `npm install && npm run build` before
  it copies `server/static/games/speed-pyramid/dist/` into the image.
  Tracked in `server/static/games/speed-pyramid/README.md`.

## What "DONE" really means

When this checklist runs clean — laptop → real TV → real puck → audible
audio → full 7-round match → scoreboard count-up — Speed Pyramid v1 is
demoable to a bar owner. Everything code-side is in. The remaining work
is hardware integration and visual side-by-side review against an HQ
Trivia north-star frame (see `docs/north-star/README.md`).
