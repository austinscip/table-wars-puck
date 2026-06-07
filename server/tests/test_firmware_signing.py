"""Firmware-signing tests — the authenticity backbone for OTA.

A puck must install ONLY firmware the operator signed. These prove the
ECDSA P-256 / SHA-256 sign+verify round-trips, rejects tampering and the wrong
key, and that the upload endpoint enforces a valid signature when a public key
is configured. The firmware-side verification (mbedTLS on the ESP32) is the
matching half and needs a hardware smoke test — see docs/firmware-ota.md.
"""
from __future__ import annotations

import importlib
import io
import os

import pytest

pytest.importorskip("cryptography")  # firmware signing needs the crypto lib

import firmware_signing as fs


def test_sign_verify_roundtrip():
    priv, pub = fs.generate_keypair()
    data = b"\x00\x01firmware-image\xff" * 1000
    sig = fs.sign(data, priv)
    assert fs.verify(data, sig, pub) is True


def test_verify_rejects_tampered_image():
    priv, pub = fs.generate_keypair()
    data = b"good image" * 100
    sig = fs.sign(data, priv)
    tampered = data + b"x"
    assert fs.verify(tampered, sig, pub) is False


def test_verify_rejects_wrong_key():
    priv1, _ = fs.generate_keypair()
    _, pub2 = fs.generate_keypair()  # a DIFFERENT key's public half
    data = b"image"
    sig = fs.sign(data, priv1)
    assert fs.verify(data, sig, pub2) is False, "signature must not verify under another key"


def test_verify_is_fail_closed_on_garbage():
    _, pub = fs.generate_keypair()
    assert fs.verify(b"x", "not-hex", pub) is False
    assert fs.verify(b"x", "", pub) is False


def test_fingerprint_is_stable_and_key_specific():
    _, pub1 = fs.generate_keypair()
    _, pub2 = fs.generate_keypair()
    assert fs.public_key_fingerprint(pub1) == fs.public_key_fingerprint(pub1)
    assert fs.public_key_fingerprint(pub1) != fs.public_key_fingerprint(pub2)


# --- upload endpoint enforcement (real Flask app) -------------------------

def _client(tmp_path, monkeypatch, pubkey_path=None):
    monkeypatch.setenv("ADMIN_API_TOKEN", "admintok")
    if pubkey_path:
        monkeypatch.setenv("FIRMWARE_PUBLIC_KEY_PATH", str(pubkey_path))
    else:
        monkeypatch.delenv("FIRMWARE_PUBLIC_KEY_PATH", raising=False)
    import firmware_routes
    importlib.reload(firmware_routes)
    # Point the firmware dir at a temp location so the test doesn't write repo.
    monkeypatch.setattr(firmware_routes, "FIRMWARE_DIR", str(tmp_path))
    monkeypatch.setattr(firmware_routes, "FIRMWARE_MANIFEST",
                        str(tmp_path / "manifest.json"))
    from flask import Flask
    app = Flask(__name__)
    firmware_routes.init_firmware_routes(app)
    return app.test_client()


def test_upload_rejects_bad_signature_when_pubkey_configured(tmp_path, monkeypatch):
    priv, pub = fs.generate_keypair()
    pub_path = tmp_path / "pub.pem"
    pub_path.write_bytes(pub)
    client = _client(tmp_path, monkeypatch, pubkey_path=pub_path)

    data = b"firmware-v2-image" * 100
    # Sign with a DIFFERENT key -> must be rejected at publish.
    wrong_priv, _ = fs.generate_keypair()
    bad_sig = fs.sign(data, wrong_priv)
    resp = client.post("/firmware/upload",
                       headers={"Authorization": "Bearer admintok"},
                       data={"version": "2.0.0", "signature": bad_sig,
                             "file": (io.BytesIO(data), "fw.bin")},
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"verify" in resp.data

    # The correct signature is accepted and stored.
    good_sig = fs.sign(data, priv)
    resp = client.post("/firmware/upload",
                       headers={"Authorization": "Bearer admintok"},
                       data={"version": "2.0.0", "signature": good_sig,
                             "file": (io.BytesIO(data), "fw.bin")},
                       content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["signed"] is True
    assert body["sha256"] == fs.sha256_hex(data)


def test_upload_requires_signature_when_pubkey_configured(tmp_path, monkeypatch):
    _, pub = fs.generate_keypair()
    pub_path = tmp_path / "pub.pem"
    pub_path.write_bytes(pub)
    client = _client(tmp_path, monkeypatch, pubkey_path=pub_path)
    resp = client.post("/firmware/upload",
                       headers={"Authorization": "Bearer admintok"},
                       data={"version": "2.0.0",
                             "file": (io.BytesIO(b"img"), "fw.bin")},
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"signature required" in resp.data
