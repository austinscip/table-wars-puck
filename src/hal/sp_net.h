// Speed Pyramid v1 — WiFi + HTTP HAL.
//
// Connects to the bar's WiFi and POSTs JSON to the Flask server. SERVER_URL
// and WIFI_SSID / WIFI_PASS come from build_flags in platformio.ini (or
// can be #define'd before #include for testing).

#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>

#ifndef SPEED_PYRAMID_SERVER_URL
#define SPEED_PYRAMID_SERVER_URL "http://192.168.1.100:5001"
#endif

#ifndef SPEED_PYRAMID_WIFI_SSID
#define SPEED_PYRAMID_WIFI_SSID "TableWars"
#endif

#ifndef SPEED_PYRAMID_WIFI_PASS
#define SPEED_PYRAMID_WIFI_PASS "tablewars"
#endif

namespace sp_net {

inline bool connect(uint32_t timeout_ms = 15000) {
  WiFi.mode(WIFI_STA);
  // Let the IDF transparently re-associate if the AP blips (router reboot,
  // brief interference) without us having to notice and re-issue begin().
  // Without this a single drop strands the puck offline until power-cycle
  // (audit firmware-2026-06-06, finding H3).
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(SPEED_PYRAMID_WIFI_SSID, SPEED_PYRAMID_WIFI_PASS);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > timeout_ms) return false;
    delay(200);
  }
  return true;
}

inline bool is_connected() {
  return WiFi.status() == WL_CONNECTED;
}

// Best-effort, NON-blocking reconnect nudge. Call periodically from the main
// loop: if the link is down, re-issue WiFi.begin() so a puck that dropped
// while setAutoReconnect was still negotiating (or after a long outage) gets
// kicked back into associating. Returns the current link state. Does NOT
// busy-wait — the loop keeps polling input while the IDF reconnects in the
// background.
inline bool ensure_connected() {
  if (WiFi.status() == WL_CONNECTED) return true;
  static uint32_t _last_attempt_ms = 0;
  const uint32_t now = millis();
  // Throttle so we don't hammer begin() every tick during a real outage.
  if (_last_attempt_ms == 0 || now - _last_attempt_ms > 5000) {
    _last_attempt_ms = now;
    Serial.println("[NET] link down — re-issuing WiFi.begin()");
    WiFi.begin(SPEED_PYRAMID_WIFI_SSID, SPEED_PYRAMID_WIFI_PASS);
  }
  return false;
}

// GET <SERVER_URL><path>. Writes response body into `response_out` (if
// non-null). Returns HTTP status code, or -1 on transport error.
// Logs every step to Serial.
inline int get_json(const char* path, String* response_out = nullptr) {
  if (!is_connected()) {
    Serial.println("[GET] aborted — WiFi not connected");
    return -1;
  }

  const String url = String(SPEED_PYRAMID_SERVER_URL) + path;

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(3000);  // bound the per-request loop freeze (audit M1)

  if (!http.begin(client, url)) {
    Serial.println("[GET] http.begin() failed (URL parse?)");
    return -1;
  }

  const int code = http.GET();
  if (code < 0) {
    Serial.printf("[GET] %s -> transport error %d (%s)\n", url.c_str(), code,
                  HTTPClient::errorToString(code).c_str());
  } else if (response_out) {
    *response_out = http.getString();
  }

  http.end();
  return code;
}

// POST JSON body to <SERVER_URL><path>. Writes response body into
// `response_out` (if non-null). Returns HTTP status code, or -1 on
// transport error. Logs every step to Serial so we can diagnose the
// HTTPClient layer when it's silently failing.
inline int post_json(const char* path, const String& body, String* response_out = nullptr) {
  if (!is_connected()) {
    Serial.println("[POST] aborted — WiFi not connected");
    return -1;
  }

  const String url = String(SPEED_PYRAMID_SERVER_URL) + path;
  Serial.printf("[POST] %s  body=%s\n", url.c_str(), body.c_str());

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(3000);  // bound the per-request loop freeze (audit M1)

  if (!http.begin(client, url)) {
    Serial.println("[POST] http.begin() failed (URL parse?)");
    return -1;
  }
  http.addHeader("Content-Type", "application/json");

  const int code = http.POST(body);
  Serial.printf("[POST] -> HTTP %d\n", code);

  if (code < 0) {
    Serial.printf("[POST] transport error: %s\n",
                  HTTPClient::errorToString(code).c_str());
  } else if (response_out) {
    *response_out = http.getString();
    Serial.printf("[POST] body: %s\n", response_out->c_str());
  }

  http.end();
  return code;
}

}  // namespace sp_net
