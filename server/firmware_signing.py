"""
Firmware signing — authenticity for OTA updates.

The existing OTA server (firmware_routes.py) used MD5, which proves a file
wasn't *corrupted* but NOT that it came from the operator — and MD5 is
cryptographically broken. A puck on bar Wi-Fi has no way to tell a real update
from one a prankster (or a malicious AP) pushed. That's fleet-takeover risk.

This module adds real authenticity with **ECDSA P-256 over SHA-256** — the
scheme the ESP32's built-in mbedTLS verifies most cleanly:

- The operator generates a keypair ONCE (`tools/firmware_keygen.py`). The
  PRIVATE key stays on their laptop and never touches the server. The PUBLIC
  key is baked into the firmware.
- Before publishing, the operator signs the `.bin` locally
  (`tools/firmware_sign.py`) and uploads the binary + signature.
- The puck (firmware, later chunk) verifies the signature against its embedded
  public key before installing, and refuses anything it can't verify.

Pure functions here so the tools + tests share one implementation.
"""
from __future__ import annotations

import hashlib


def _crypto():
    """Import cryptography lazily so a minimal deploy that never touches
    firmware OTA doesn't need the dependency — only the actual sign/verify
    paths require it."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.exceptions import InvalidSignature
    return hashes, serialization, ec, InvalidSignature


def generate_keypair() -> tuple[bytes, bytes]:
    """Return (private_pem, public_pem) for a fresh ECDSA P-256 keypair.
    The private PEM is the operator's secret (keep off the server / in git);
    the public PEM is embedded in the firmware."""
    _hashes, serialization, ec, _inv = _crypto()
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def sha256_hex(data: bytes) -> str:
    """Integrity hash of a firmware image (replaces the broken MD5)."""
    return hashlib.sha256(data).hexdigest()


def sign(data: bytes, private_pem: bytes) -> str:
    """Sign `data` with the operator's private key. Returns the DER signature
    as hex (mbedTLS `mbedtls_pk_verify` consumes DER directly)."""
    hashes, serialization, ec, _inv = _crypto()
    key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("signing key must be an ECDSA P-256 private key")
    signature = key.sign(data, ec.ECDSA(hashes.SHA256()))
    return signature.hex()


def verify(data: bytes, signature_hex: str, public_pem: bytes) -> bool:
    """True iff `signature_hex` is a valid signature of `data` by the private
    key matching `public_pem`. Never raises on a bad signature — returns False
    (fail-closed at the caller)."""
    try:
        hashes, serialization, ec, InvalidSignature = _crypto()
        key = serialization.load_pem_public_key(public_pem)
        if not isinstance(key, ec.EllipticCurvePublicKey):
            return False
        key.verify(bytes.fromhex(signature_hex), data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:  # noqa: BLE001 — fail closed on ANY error incl. missing dep
        return False


def public_key_fingerprint(public_pem: bytes) -> str:
    """Short, stable id for a public key (first 16 hex of SHA-256 of the PEM).
    Lets the manifest + firmware confirm they're talking about the same key
    without shipping the whole key in every response."""
    return hashlib.sha256(public_pem).hexdigest()[:16]


def public_pem_to_c_header(public_pem: bytes) -> str:
    """Render the public key as a paste-ready C string for the firmware
    (`tools/firmware_keygen.py` prints this)."""
    body = public_pem.decode("ascii").replace("\n", "\\n")
    return (
        "// Operator firmware-signing public key (ECDSA P-256). The puck\n"
        "// verifies every OTA image against this before installing.\n"
        f'static const char FIRMWARE_PUBKEY_PEM[] = "{body}";\n'
    )
