// Speed Pyramid v1 — WiFi + HTTP HAL.
//
// Connects to the bar's WiFi and POSTs JSON to the Flask server. SERVER_URL
// and WIFI_SSID / WIFI_PASS come from build_flags in platformio.ini (or
// can be #define'd before #include for testing).

#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

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

// POST JSON body to <SERVER_URL><path>. Writes response body into
// `response_out` (if non-null). Returns HTTP status code, or -1 on
// transport error.
inline int post_json(const char* path, const String& body, String* response_out = nullptr) {
  if (!is_connected()) return -1;
  HTTPClient http;
  http.begin(String(SPEED_PYRAMID_SERVER_URL) + path);
  http.addHeader("Content-Type", "application/json");
  const int code = http.POST(body);
  if (response_out && code > 0) {
    *response_out = http.getString();
  }
  http.end();
  return code;
}

}  // namespace sp_net
