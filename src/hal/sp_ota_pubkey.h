#pragma once
// ---------------------------------------------------------------------------
// Firmware-signing PUBLIC key (ECDSA P-256).
//
// PLACEHOLDER — replace the body below with YOUR key, then reflash pucks ONCE
// over USB so they carry it. Generate it with:
//     cd server && python tools/firmware_keygen.py
// (it prints this exact block, ready to paste).
//
// Until a real key is pasted here, mbedtls_pk_parse_public_key() fails on this
// garbage and the OTA client REFUSES every update (fail-closed) — so an
// un-provisioned puck never installs anything.
// ---------------------------------------------------------------------------
static const char FIRMWARE_PUBKEY_PEM[] =
    "-----BEGIN PUBLIC KEY-----\n"
    "REPLACE_ME_WITH_YOUR_ECDSA_P256_PUBLIC_KEY_FROM_firmware_keygen_py\n"
    "-----END PUBLIC KEY-----\n";
