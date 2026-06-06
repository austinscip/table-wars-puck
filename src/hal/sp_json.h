// Speed Pyramid v1 — minimal JSON field extractors.
//
// The puck only ever parses a handful of small, server-controlled response
// shapes, so we avoid pulling ArduinoJson into the hot path and use these
// bounded substring helpers instead. They are deliberately pure (operate on
// an Arduino String, no globals, no hardware) so they can be unit-tested on
// the host — see testing/firmware/test_sp_json.cpp. The game code wraps them
// as sp_game::_extract_* for backwards compatibility.
//
// Robustness rules baked in here (audit firmware-2026-06-06, finding M2):
//   - extract_string is length-bounded so a malformed/oversized response
//     can't balloon the heap.
//   - value_offset / value_is_null derive their skip distance from the
//     needle itself — no magic "+24"/"+19" offsets to drift out of sync.

#pragma once

#ifdef ARDUINO
#include <Arduino.h>
#include <string.h>
#endif

namespace sp_json {

// Extract a quoted-string field's value into `out`. Refuses values longer
// than max_len (guards the heap against a hostile/oversized field). Returns
// true on success; leaves *out untouched on failure.
inline bool extract_string(const String& json, const char* key, String* out,
                           int max_len = 256) {
  String needle = String("\"") + key + "\":\"";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  int end = json.indexOf("\"", i);
  if (end < 0) return false;
  if (end - i > max_len) return false;
  if (out) *out = json.substring(i, end);
  return true;
}

// Extract an integer field (shaped "<key>":<int>, optional leading sign and
// surrounding whitespace). Returns false if the key is absent or the value
// has no digits.
inline bool extract_int(const String& json, const char* key, int* out) {
  String needle = String("\"") + key + "\":";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  while (i < (int)json.length() && (json[i] == ' ' || json[i] == '\t')) i++;
  int start = i;
  if (i < (int)json.length() && (json[i] == '-' || json[i] == '+')) i++;
  while (i < (int)json.length() && isDigit(json[i])) i++;
  if (i == start) return false;
  if (out) *out = json.substring(start, i).toInt();
  return true;
}

// Extract a boolean field. Returns false if the key is absent or the value
// is neither `true` nor `false`.
inline bool extract_bool(const String& json, const char* key, bool* out) {
  String needle = String("\"") + key + "\":";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  while (i < (int)json.length() && (json[i] == ' ' || json[i] == '\t')) i++;
  if (json.substring(i, i + 4) == "true") { if (out) *out = true; return true; }
  if (json.substring(i, i + 5) == "false") { if (out) *out = false; return true; }
  return false;
}

// Index of the first non-whitespace character of `key`'s value, or -1 if the
// key is absent or only whitespace follows. `key` MUST include the
// surrounding quotes and the colon, e.g. "\"pending_minigame\":". The skip
// distance is taken from strlen(key), so there are no magic offsets to keep
// in sync with the key text.
inline int value_offset(const String& json, const char* key) {
  int i = json.indexOf(key);
  if (i < 0) return -1;
  i += (int)strlen(key);
  while (i < (int)json.length() && (json[i] == ' ' || json[i] == '\t')) i++;
  return i < (int)json.length() ? i : -1;
}

// True iff `key` is present and its value is JSON null. `key` includes the
// quotes + colon (see value_offset).
inline bool value_is_null(const String& json, const char* key) {
  const int i = value_offset(json, key);
  return i >= 0 && json[i] == 'n';
}

}  // namespace sp_json
