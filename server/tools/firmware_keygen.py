#!/usr/bin/env python3
"""Generate the operator's firmware-signing keypair — run ONCE.

    python tools/firmware_keygen.py [--out-dir .]

Writes:
  - firmware_private_key.pem   <- YOUR SECRET. Keep it on your laptop, never
                                  commit it, never put it on the server.
  - firmware_public_key.pem    <- safe to share; embedded in the firmware.

Also prints a paste-ready C header (FIRMWARE_PUBKEY_PEM) for the firmware.

If you lose the private key you can't sign new firmware (you'd reflash pucks
with a new embedded public key over USB). If it LEAKS, anyone can push firmware
to your pucks — rotate it (new keypair + reflash) immediately.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firmware_signing import (  # noqa: E402
    generate_keypair,
    public_key_fingerprint,
    public_pem_to_c_header,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate firmware-signing keypair")
    ap.add_argument("--out-dir", default=".", help="where to write the .pem files")
    args = ap.parse_args()

    priv_path = os.path.join(args.out_dir, "firmware_private_key.pem")
    pub_path = os.path.join(args.out_dir, "firmware_public_key.pem")
    if os.path.exists(priv_path):
        print(f"refusing to overwrite existing {priv_path}", file=sys.stderr)
        return 1

    private_pem, public_pem = generate_keypair()
    # Private key: owner-only permissions.
    fd = os.open(priv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(private_pem)
    with open(pub_path, "wb") as f:
        f.write(public_pem)

    print(f"wrote {priv_path}  (SECRET — keep off the server, never commit)")
    print(f"wrote {pub_path}")
    print(f"public key fingerprint: {public_key_fingerprint(public_pem)}")
    print("\n--- paste into the firmware (src/hal/sp_ota_pubkey.h) ---\n")
    print(public_pem_to_c_header(public_pem))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
