#!/usr/bin/env python3
"""Sign a firmware .bin with the operator's private key, locally.

    python tools/firmware_sign.py firmware.bin --key firmware_private_key.pem

Prints the SHA-256 and the signature (hex). Upload the .bin together with this
signature (the /firmware/upload endpoint's `signature` field). The private key
NEVER leaves your machine — the server only ever sees the public signature.

With --upload <base_url> --version X.Y.Z --token <ADMIN_API_TOKEN> it will also
POST the binary + signature to the running server in one step.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firmware_signing import sha256_hex, sign, verify  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign a firmware binary")
    ap.add_argument("binary", help="path to firmware .bin")
    ap.add_argument("--key", default="firmware_private_key.pem",
                    help="path to the private signing key PEM")
    ap.add_argument("--pubkey", help="optional public key PEM to self-verify")
    ap.add_argument("--upload", help="base URL of the server to publish to")
    ap.add_argument("--version", help="version string (required with --upload)")
    ap.add_argument("--token", help="ADMIN_API_TOKEN (required with --upload)")
    args = ap.parse_args()

    with open(args.binary, "rb") as f:
        data = f.read()
    with open(args.key, "rb") as f:
        private_pem = f.read()

    digest = sha256_hex(data)
    signature = sign(data, private_pem)

    if args.pubkey:
        with open(args.pubkey, "rb") as f:
            if not verify(data, signature, f.read()):
                print("self-verify FAILED — key mismatch?", file=sys.stderr)
                return 1
        print("self-verify: OK")

    print(f"sha256:    {digest}")
    print(f"signature: {signature}")

    if args.upload:
        if not (args.version and args.token):
            print("--upload requires --version and --token", file=sys.stderr)
            return 1
        try:
            import requests
        except ImportError:
            print("`pip install requests` to use --upload", file=sys.stderr)
            return 1
        url = args.upload.rstrip("/") + "/firmware/upload"
        with open(args.binary, "rb") as f:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {args.token}"},
                data={"version": args.version, "signature": signature,
                      "sha256": digest},
                files={"file": (os.path.basename(args.binary), f,
                                "application/octet-stream")},
                timeout=60,
            )
        print(f"upload -> {resp.status_code}: {resp.text[:400]}")
        return 0 if resp.ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
