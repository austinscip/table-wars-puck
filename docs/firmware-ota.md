# Firmware OTA — signed over-the-air updates

Goal: push a firmware fix from your laptop and have the pucks update themselves
over Wi-Fi — no driving to the bar, no USB cables. The pilot model ("OTA fixes
from my laptop") depends on this.

The danger of OTA is the flip side: a bad or **forged** update could brick every
puck in the field, or let someone on the bar Wi-Fi take them over. So the design
is **authenticity-first**: a puck installs ONLY firmware *you* signed, and keeps
a known-good copy to roll back to.

## Security model

- **ECDSA P-256 / SHA-256** signatures (the scheme the ESP32's built-in mbedTLS
  verifies most cleanly). This replaces the old **MD5**, which only proved a
  file wasn't corrupted — not that it came from you — and is broken anyway.
- **You generate a keypair once.** The **private key stays on your laptop** and
  never touches the server. The **public key is baked into the firmware.**
- **You sign each build locally**, then upload the binary + signature. The
  server stores/serves them; if you configure the public key on the server it
  also verifies at upload so a wrong/missing signature is caught immediately.
- **The puck verifies** the signature against its embedded public key before
  installing, and **refuses** anything it can't verify.

## Status

| Piece | State |
|---|---|
| Signing core (`server/firmware_signing.py`) — ECDSA P-256 sign/verify/hash | ✅ done + host-tested (`tests/test_firmware_signing.py`) |
| Keygen + sign CLIs (`server/tools/firmware_keygen.py`, `firmware_sign.py`) | ✅ done |
| Server distribution (`firmware_routes.py`) — SHA-256 + signature in manifest, publish-time verify, `/firmware/version` surfaces it | ✅ done + tested |
| **Firmware OTA client** — check / download / **mbedTLS-verify** / install via `Update.h` with **A/B-partition rollback** | 🔜 next chunk — **compile-only; MUST pass a hardware smoke test before any field use** (untested on-device crypto is dangerous) |

## How to use (once the firmware client lands)

```bash
# 1. ONE TIME — generate your keypair (keep the private .pem safe).
cd server && python tools/firmware_keygen.py
#    -> paste the printed FIRMWARE_PUBKEY_PEM into src/hal/sp_ota_pubkey.h,
#       reflash pucks ONCE over USB so they carry your public key.

# 2. Build firmware, then sign + publish from your laptop:
python tools/firmware_sign.py .pio/build/puck1_speed_pyramid/firmware.bin \
    --key firmware_private_key.pem \
    --upload https://your-server --version 1.3.0 --token "$ADMIN_API_TOKEN"
```

Optionally set `FIRMWARE_PUBLIC_KEY_PATH` on the server so it rejects any upload
whose signature doesn't verify (catches a wrong key before the fleet sees it).

## Key custody

- **Lose the private key** → you can't sign new firmware; you'd reflash pucks
  over USB with a new embedded public key.
- **Leak the private key** → anyone can push firmware to your pucks. Rotate
  immediately: new keypair, re-embed the public key, reflash.
- `firmware_private_key.pem` and `server/firmware_versions/` are git-ignored.

## Hardware-test gate (before trusting OTA in the field)

The firmware verification + A/B rollback must be smoke-tested on a real puck:
1. flash a signed v_n over USB (with the public key embedded),
2. publish a signed v_n+1, confirm the puck updates itself over Wi-Fi,
3. publish a **deliberately corrupted / wrong-key** image, confirm the puck
   **refuses** it and stays on v_n+1,
4. publish an image that boots-loops, confirm the puck **auto-rolls back** to
   the last good partition.
Only after all four passes should OTA drive a real venue.
