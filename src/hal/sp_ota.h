#pragma once
// ===========================================================================
// sp_ota — signed over-the-air firmware updates for the puck.
//
// Pulls a new firmware image from the server, but installs it ONLY if it's
// signed by the operator's key (verified on-device with mbedTLS). The server
// half (signing, manifest) lives in server/firmware_signing.py +
// firmware_routes.py; the matching public key is embedded in sp_ota_pubkey.h.
//
// Flow (checkAndUpdate):
//   1. GET /firmware/version?puck_id=N  -> {version, signed, signature, sha256, url}
//   2. refuse if not `signed` (fail-closed; no signature => no install)
//   3. stream the binary into the inactive OTA partition via Update.h, hashing
//      it incrementally (mbedTLS SHA-256) as it lands
//   4. verify SHA-256 == manifest sha256 (integrity) AND the ECDSA P-256
//      signature over the binary (authenticity). ANY failure -> Update.abort()
//      and report-failure; the running partition is untouched.
//   5. only on full success -> Update.end(true) + reboot into the new image.
//
// Rollback: markHealthy() cancels the pending-verify rollback after the new
// image has booted AND reconnected. With the bootloader rollback feature
// enabled (CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE), an image that boot-loops
// before markHealthy() is auto-reverted to the last good partition. Without
// that build option markHealthy() is a safe no-op (see docs/firmware-ota.md).
//
// COMPILE-VERIFIED ONLY — must pass the 4-step hardware smoke in
// docs/firmware-ota.md before it drives a real venue.
// ===========================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>

#include "mbedtls/version.h"
#include "mbedtls/pk.h"
#include "mbedtls/sha256.h"
#include "esp_ota_ops.h"

#include "sp_json.h"
#include "sp_ota_pubkey.h"

#ifndef SP_FW_VERSION
#define SP_FW_VERSION "0.0.0"
#endif

namespace sp_ota {

// How often the idle loop is allowed to check (ms). Bar pucks sit idle for
// long stretches; an update lands within this window without hammering.
static constexpr uint32_t kCheckIntervalMs = 30UL * 60UL * 1000UL;  // 30 min
inline uint32_t _last_check_ms = 0;

// --- mbedTLS SHA-256: 2.x uses *_ret(), 3.x dropped the suffix. ------------
inline int _sha_starts(mbedtls_sha256_context* c) {
#if MBEDTLS_VERSION_NUMBER >= 0x03000000
  return mbedtls_sha256_starts(c, 0);
#else
  return mbedtls_sha256_starts_ret(c, 0);
#endif
}
inline int _sha_update(mbedtls_sha256_context* c, const uint8_t* d, size_t n) {
#if MBEDTLS_VERSION_NUMBER >= 0x03000000
  return mbedtls_sha256_update(c, d, n);
#else
  return mbedtls_sha256_update_ret(c, d, n);
#endif
}
inline int _sha_finish(mbedtls_sha256_context* c, uint8_t out[32]) {
#if MBEDTLS_VERSION_NUMBER >= 0x03000000
  return mbedtls_sha256_finish(c, out);
#else
  return mbedtls_sha256_finish_ret(c, out);
#endif
}

inline int _hexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

inline bool _hexToBytes(const String& hex, uint8_t* out, size_t outMax, size_t* outLen) {
  size_t n = hex.length() / 2;
  if (n == 0 || n > outMax || (hex.length() % 2) != 0) return false;
  for (size_t i = 0; i < n; i++) {
    int hi = _hexNibble(hex[2 * i]);
    int lo = _hexNibble(hex[2 * i + 1]);
    if (hi < 0 || lo < 0) return false;
    out[i] = (uint8_t)((hi << 4) | lo);
  }
  *outLen = n;
  return true;
}

inline String _hashToHex(const uint8_t h[32]) {
  static const char* hx = "0123456789abcdef";
  String s;
  s.reserve(64);
  for (int i = 0; i < 32; i++) {
    s += hx[(h[i] >> 4) & 0xF];
    s += hx[h[i] & 0xF];
  }
  return s;
}

// Verify an ECDSA P-256 DER signature over `hash32` against the embedded key.
inline bool _verifySignature(const uint8_t hash32[32], const uint8_t* sig, size_t sigLen) {
  mbedtls_pk_context pk;
  mbedtls_pk_init(&pk);
  int rc = mbedtls_pk_parse_public_key(
      &pk, (const unsigned char*)FIRMWARE_PUBKEY_PEM, strlen(FIRMWARE_PUBKEY_PEM) + 1);
  if (rc != 0) {  // bad/placeholder key -> refuse
    mbedtls_pk_free(&pk);
    return false;
  }
  rc = mbedtls_pk_verify(&pk, MBEDTLS_MD_SHA256, hash32, 32, sig, sigLen);
  mbedtls_pk_free(&pk);
  return rc == 0;
}

inline void _report(const String& serverBase, const char* path, const String& body) {
  HTTPClient http;
  if (!http.begin(serverBase + path)) return;
  http.addHeader("Content-Type", "application/json");
  http.POST(body);
  http.end();
}

// Cancel the rollback once we've proven the freshly-OTA'd image actually runs
// (booted + reconnected). Call this AFTER the puck is back online. No-op unless
// the running image is in the pending-verify state.
inline void markHealthy() {
  const esp_partition_t* running = esp_ota_get_running_partition();
  if (running == nullptr) return;
  esp_ota_img_states_t state;
  if (esp_ota_get_state_partition(running, &state) == ESP_OK &&
      state == ESP_OTA_IMG_PENDING_VERIFY) {
    esp_ota_mark_app_valid_cancel_rollback();
    Serial.println("[ota] image marked valid (rollback cancelled)");
  }
}

// Check for + apply a signed update. Returns true if an update was installed
// (the device reboots and does not return). Fail-closed at every step.
inline bool checkAndUpdate(const String& serverBase, int puckId) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String verUrl = serverBase + "/firmware/version?puck_id=" + String(puckId);
  if (!http.begin(verUrl)) return false;
  int code = http.GET();
  if (code != 200) { http.end(); return false; }
  String body = http.getString();
  http.end();

  bool available = false, signedImg = false;
  sp_json::extract_bool(body, "update_available", &available);
  sp_json::extract_bool(body, "signed", &signedImg);
  if (!available) return false;
  if (!signedImg) {
    Serial.println("[ota] refused: server image is UNSIGNED");
    return false;
  }

  String version, sig_hex, sha_hex, url;
  sp_json::extract_string(body, "version", &version);
  sp_json::extract_string(body, "signature", &sig_hex);
  sp_json::extract_string(body, "sha256", &sha_hex);
  sp_json::extract_string(body, "url", &url);
  if (sig_hex.length() == 0 || url.length() == 0) return false;

  // Download + stream into the inactive partition, hashing as we go.
  HTTPClient dl;
  String dlUrl = serverBase + url + "?puck_id=" + String(puckId);
  if (!dl.begin(dlUrl)) return false;
  int dcode = dl.GET();
  if (dcode != 200) { dl.end(); return false; }
  int len = dl.getSize();
  if (len <= 0) { dl.end(); return false; }
  if (!Update.begin((size_t)len)) {
    dl.end();
    _report(serverBase, "/firmware/report-failure",
            String("{\"puck_id\":") + puckId + ",\"version\":\"" + version +
            "\",\"error\":\"Update.begin failed\"}");
    return false;
  }

  mbedtls_sha256_context sha;
  mbedtls_sha256_init(&sha);
  _sha_starts(&sha);
  WiFiClient* stream = dl.getStreamPtr();
  uint8_t buf[1024];
  int got = 0;
  uint32_t idleStart = millis();
  while (got < len) {
    size_t avail = stream->available();
    if (avail == 0) {
      if (!dl.connected() || (millis() - idleStart) > 15000) break;  // stalled
      delay(2);
      continue;
    }
    idleStart = millis();
    size_t want = sizeof(buf);
    if (want > (size_t)(len - got)) want = (size_t)(len - got);
    if (want > avail) want = avail;
    int n = stream->readBytes(buf, want);
    if (n <= 0) break;
    if (Update.write(buf, (size_t)n) != (size_t)n) { got = -1; break; }
    _sha_update(&sha, buf, (size_t)n);
    got += n;
  }
  dl.end();

  uint8_t hash[32];
  _sha_finish(&sha, hash);
  mbedtls_sha256_free(&sha);

  auto fail = [&](const char* why) -> bool {
    Update.abort();
    Serial.printf("[ota] refused: %s\n", why);
    _report(serverBase, "/firmware/report-failure",
            String("{\"puck_id\":") + puckId + ",\"version\":\"" + version +
            "\",\"error\":\"" + why + "\"}");
    return false;
  };

  if (got != len) return fail("short/failed download");
  if (sha_hex.length() && !sha_hex.equalsIgnoreCase(_hashToHex(hash)))
    return fail("sha256 mismatch");

  uint8_t sig[80];
  size_t sigLen = 0;
  if (!_hexToBytes(sig_hex, sig, sizeof(sig), &sigLen))
    return fail("bad signature encoding");
  if (!_verifySignature(hash, sig, sigLen))
    return fail("SIGNATURE INVALID");

  if (!Update.end(true)) return fail("Update.end failed");

  Serial.printf("[ota] verified + installed %s -> rebooting\n", version.c_str());
  _report(serverBase, "/firmware/report-success",
          String("{\"puck_id\":") + puckId + ",\"version\":\"" + version +
          "\",\"previous_version\":\"" SP_FW_VERSION "\"}");
  delay(500);
  ESP.restart();
  return true;  // unreachable
}

// Idle-loop hook: rate-limited check. Call from the puck's IDLE state only, so
// an update never lands mid-question.
inline void maybePeriodicCheck(const String& serverBase, int puckId) {
  uint32_t now = millis();
  if (_last_check_ms != 0 && (now - _last_check_ms) < kCheckIntervalMs) return;
  _last_check_ms = now;
  checkAndUpdate(serverBase, puckId);
}

}  // namespace sp_ota
