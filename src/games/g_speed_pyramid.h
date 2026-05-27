// Speed Pyramid v1 — game module.
//
// Two top-level states:
//   1. PAIR_MODE — wait for hold-1s to enter; then tilt-dial 6 digits;
//      on the 6th tap, POST /api/pair/confirm.
//   2. IN_GAME — tilt-aim quadrant + tap to lock; POST /api/trivia/answer.
//      (Wired in slice 1C — for now this header only exposes pair_mode_loop.)
//
// All event-driven feedback goes through the locked named palettes /
// audio patterns in sp_led.h and sp_feedback.h — no raw RGB/frequency
// literals in this file.

#pragma once

#include <Arduino.h>
#include "../hal/sp_button.h"
#include "../hal/sp_imu.h"
#include "../hal/sp_led.h"
#include "../hal/sp_feedback.h"
#include "../hal/sp_net.h"

#ifndef PUCK_ID
#define PUCK_ID 1
#endif

namespace sp_game {

enum class State : uint8_t {
  IDLE,
  PAIR_REQUESTING,
  PAIR_DIALING,
  PAIR_CONFIRMING,
  PAIRED,             // brief celebration before dropping to LOBBY_WAITING
  LOBBY_WAITING,      // v2: joined lobby, waiting for host to start
  IN_GAME_IDLE,       // session bound, no question active yet
  IN_GAME_CATEGORY_PICKING,  // Slice E1: picker is choosing 1 of 3 offers
  IN_GAME_MINIGAME,   // Slice E2: BULLSEYE or SHOT_CLOCK minigame active
  IN_GAME_ANSWERING,  // question active, tilt-aim + tap
  IN_GAME_LOCKED,     // tap fired, awaiting server reveal
  MATCH_ENDED,        // all 7 rounds done — TAP=PlayAgain, HOLD_3S=NewPlayer
};

// Slice E1 — category pick state. _pick_offer_ids holds up to 3
// category IDs; _pick_idx is the currently-aimed index; _pick_picker
// is the puck_id that's allowed to commit the pick.
inline int  _pick_offer_ids[3] = {0, 0, 0};
inline int  _pick_picker = 0;
inline int  _pick_idx = 0;
inline char _last_pick_quadrant = 0;

// Slice E2 — minigame state. _mg_flavor: 'B' = BULLSEYE, 'S' =
// SHOT_CLOCK. _mg_target is the BULLSEYE target letter ('A'/'B'/'C'
// /'D'). _mg_started_ms is local-millis at minigame entry — used to
// compute t_ms when the puck fires. Slice F: _mg_last_preview_quad
// is the last quadrant sent via /api/sp/minigame/preview — used to
// edge-trigger preview POSTs on tilt change.
inline char     _mg_flavor = 0;
inline char     _mg_target = 0;
inline uint32_t _mg_started_ms = 0;
inline bool     _mg_fired = false;
inline char     _mg_last_preview_quad = 0;

inline State _state = State::IDLE;
inline uint8_t _dial_digits[6] = {0, 0, 0, 0, 0, 0};
inline uint8_t _dial_pos = 0;     // 0..5
inline uint8_t _current_digit = 0;

// Lobby + session tracking. lobby_code is set after PAIR_CONFIRMING;
// session_code is set after host taps start (or polling sees the
// lobby's started=true with a session_code).
inline String _lobby_code = "";
inline String _session_code = "";
inline bool _is_host = false;
inline uint32_t _last_lobby_poll_ms = 0;

inline int _current_question_id = -1;
inline uint32_t _question_started_at_ms = 0;  // millis() when puck saw it
inline uint32_t _question_time_limit_ms = 10000;
inline uint32_t _last_poll_ms = 0;
inline uint32_t _last_dial_tap_ms = 0;  // for post-TAP input lockout in PAIR_DIALING

// Track the last quadrant we mirrored to the server during answering
// so we only POST when it actually changes (network is expensive, the
// IMU read happens every loop tick).
inline char _last_preview_letter = 0;

inline void _show_pair_mode_glow() {
  // Soft rotating dot in this puck's identity color so the player knows
  // they're in pair / idle mode AND can tell which puck they're holding
  // at a glance (matches the TV avatar color).
  static uint32_t last_step = 0;
  static uint8_t pos = 0;
  if (millis() - last_step < 100) return;
  last_step = millis();
  pos = (pos + 1) % 16;
  const CRGB c = sp_led::color_for_puck(PUCK_ID);
  for (int i = 0; i < 16; ++i) {
    FastLED.leds()[i] = c;
    if (i != pos) FastLED.leds()[i].fadeToBlackBy(240);
  }
  FastLED.show();
}

// Forward-declare _extract_string (defined further down) so _request_pair_code
// can parse role + pair_code out of the response.
inline bool _extract_string(const String& json, const char* key, String* out);

// Request a fresh pair code by POST /api/pair/request. Captures the
// role + lobby_code from the response so callers can short-circuit
// joiners straight to LOBBY_WAITING.
inline bool _request_pair_code(String* role_out, String* lobby_code_out) {
  String body = "{\"puck_id\":" + String(PUCK_ID) + "}";
  String resp;
  const int code = sp_net::post_json("/api/pair/request", body, &resp);
  if (code != 200) return false;
  if (role_out) _extract_string(resp, "role", role_out);
  if (lobby_code_out) _extract_string(resp, "pair_code", lobby_code_out);
  return true;
}

inline bool _post_dial(uint8_t index, uint8_t digit) {
  String body =
      "{\"puck_id\":" + String(PUCK_ID) +
      ",\"digit_index\":" + String(index) +
      ",\"digit\":" + String(digit) + "}";
  const int code = sp_net::post_json("/api/pair/dial", body, nullptr);
  return code == 200;
}

// Live preview broadcast — every tilt posts the current digit so the
// TV shows what's about to be locked BEFORE the user taps.
inline void _post_preview(uint8_t index, uint8_t digit) {
  String body =
      "{\"puck_id\":" + String(PUCK_ID) +
      ",\"digit_index\":" + String(index) +
      ",\"digit\":" + String(digit) + "}";
  sp_net::post_json("/api/pair/preview", body, nullptr);
}

// Extract a quoted-string JSON field. Returns true if found, writes to
// `out`. Crude but works for the small response shapes we use.
inline bool _extract_string(const String& json, const char* key, String* out) {
  String needle = String("\"") + key + "\":\"";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  int end = json.indexOf("\"", i);
  if (end < 0) return false;
  *out = json.substring(i, end);
  return true;
}

// v2 /api/pair/confirm response shape: {role, color, color_name,
// players, host_puck_id, lobby_code}. We need lobby_code + role.
inline bool _post_confirm_v2(String* lobby_code_out, bool* is_host_out) {
  String code_str = "";
  for (uint8_t i = 0; i < 6; ++i) code_str += String(_dial_digits[i]);
  String body =
      "{\"puck_id\":" + String(PUCK_ID) +
      ",\"code\":\"" + code_str + "\"}";
  String resp;
  const int code = sp_net::post_json("/api/pair/confirm", body, &resp);
  if (code != 200) return false;

  String role;
  if (!_extract_string(resp, "lobby_code", lobby_code_out)) return false;
  if (!_extract_string(resp, "role", &role)) return false;
  *is_host_out = (role == "host");
  return true;
}

// v2 /api/pair/start — host-only. Server creates trivia session and
// emits match_started. We don't read the response; we'll learn the
// session_code from the next /api/pair/lobby-state poll.
inline bool _post_start() {
  String body = "{\"puck_id\":" + String(PUCK_ID) + "}";
  return sp_net::post_json("/api/pair/start", body, nullptr) == 200;
}

// v2 /api/pair/cancel — HOLD_3S in lobby/pair. Host kills the lobby
// for everyone; joiner just drops themselves.
inline bool _post_cancel() {
  String body = "{\"puck_id\":" + String(PUCK_ID) + "}";
  return sp_net::post_json("/api/pair/cancel", body, nullptr) == 200;
}

// Poll /api/pair/lobby-state. Returns true if the match has started and
// writes the session_code to the out param.
inline bool _poll_lobby_state(String* session_code_out) {
  String body;
  const int code = sp_net::get_json("/api/pair/lobby-state", &body);
  if (code != 200) return false;
  // Inline bool check rather than calling _extract_bool, which is
  // defined later in this header (forward-reference problem).
  if (body.indexOf("\"started\":true") < 0) return false;
  if (!_extract_string(body, "session_code", session_code_out)) return false;
  return session_code_out->length() > 0;
}

// Extract an integer JSON field (very small parser — works for fields
// shaped like "<key>":<int>).
inline bool _extract_int(const String& json, const char* key, int* out) {
  String needle = String("\"") + key + "\":";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  while (i < (int)json.length() && (json[i] == ' ' || json[i] == '\t')) i++;
  int start = i;
  if (i < (int)json.length() && (json[i] == '-' || json[i] == '+')) i++;
  while (i < (int)json.length() && isDigit(json[i])) i++;
  if (i == start) return false;
  *out = json.substring(start, i).toInt();
  return true;
}

inline bool _extract_bool(const String& json, const char* key, bool* out) {
  String needle = String("\"") + key + "\":";
  int i = json.indexOf(needle);
  if (i < 0) return false;
  i += needle.length();
  while (i < (int)json.length() && (json[i] == ' ' || json[i] == '\t')) i++;
  if (json.substring(i, i + 4) == "true") { *out = true; return true; }
  if (json.substring(i, i + 5) == "false") { *out = false; return true; }
  return false;
}

// GET /api/sp/match-state/<session_code>. Returns whether the match is
// truly complete. Server flips `complete` true only AFTER the post-Q7
// load attempt fails — so simply seeing round=7 doesn't trigger an
// end-of-match (Q7 is still being played at that point).
inline bool _poll_match_state_complete() {
  if (_session_code.length() == 0) return false;
  String path = "/api/sp/match-state/" + _session_code;
  String body;
  const int code = sp_net::get_json(path.c_str(), &body);
  if (code != 200) return false;
  bool complete = false;
  _extract_bool(body, "complete", &complete);
  return complete;
}

// Slice E1 — peek into match-state for a pending category-pick phase.
// Sets _pick_picker and _pick_offer_ids[0..2] (zero-padded for short
// offers). Returns true if a pick is pending.
inline bool _poll_pending_pick() {
  if (_session_code.length() == 0) return false;
  String path = "/api/sp/match-state/" + _session_code;
  String body;
  const int code = sp_net::get_json(path.c_str(), &body);
  if (code != 200) return false;
  const int pp_at = body.indexOf("\"pending_category_pick\":");
  if (pp_at < 0) return false;
  // null sentinel after the key means no pending pick.
  int probe = pp_at + 24;
  while (probe < (int)body.length() && (body[probe] == ' ' || body[probe] == '\t')) probe++;
  if (probe < (int)body.length() && body[probe] == 'n') return false;  // "null"
  // Parse picker_puck_id (first match wins — only one in pending block).
  int picker = 0;
  if (!_extract_int(body.substring(pp_at), "picker_puck_id", &picker)) return false;
  _pick_picker = picker;
  // Parse up to 3 "id":N occurrences within the pending block. The
  // pending block is delimited by the outer match-state object — good
  // enough since no other "id" field exists at top-level of
  // match-state.
  String slice = body.substring(pp_at);
  for (int k = 0; k < 3; k++) _pick_offer_ids[k] = 0;
  int cursor = 0;
  for (int k = 0; k < 3; k++) {
    int hit = slice.indexOf("\"id\":", cursor);
    if (hit < 0) break;
    String tail = slice.substring(hit);
    int v = 0;
    if (!_extract_int(tail, "id", &v)) break;
    _pick_offer_ids[k] = v;
    cursor = hit + 5;
  }
  return _pick_offer_ids[0] > 0;
}

// POST /api/sp/select-category. Returns true on 200.
inline bool _post_select_category(int category_id) {
  if (_session_code.length() == 0) return false;
  String body =
      String("{\"puck_id\":") + PUCK_ID +
      ",\"category_id\":" + category_id + "}";
  String path = "/api/sp/select-category/" + _session_code;
  return sp_net::post_json(path.c_str(), body, nullptr) == 200;
}

// Slice E2 — peek into match-state for a pending minigame phase.
// Sets _mg_flavor ('B'/'S') and _mg_target (BULLSEYE only, else 0).
// Returns true if a minigame is pending.
inline bool _poll_pending_minigame() {
  if (_session_code.length() == 0) return false;
  String path = "/api/sp/match-state/" + _session_code;
  String body;
  const int code = sp_net::get_json(path.c_str(), &body);
  if (code != 200) return false;
  const int mg_at = body.indexOf("\"pending_minigame\":");
  if (mg_at < 0) return false;
  int probe = mg_at + 19;
  while (probe < (int)body.length() && (body[probe] == ' ' || body[probe] == '\t')) probe++;
  if (probe < (int)body.length() && body[probe] == 'n') return false;  // "null"
  String slice = body.substring(mg_at);
  String flavor;
  if (!_extract_string(slice, "flavor", &flavor)) return false;
  _mg_flavor = flavor.length() > 0 ? flavor[0] : 0;  // 'B' or 'S'
  String target;
  if (_extract_string(slice, "target_quadrant", &target) && target.length() > 0
      && target != "null") {
    _mg_target = target[0];
  } else {
    _mg_target = 0;
  }
  return _mg_flavor == 'B' || _mg_flavor == 'S';
}

// Slice F — POST /api/sp/minigame/preview. Best-effort aim broadcast
// during BULLSEYE so the TV can render per-puck reticles in real
// time. Throttled by the caller (~100ms) so the puck doesn't flood
// the server with HTTP requests on every IMU sample.
inline void _post_minigame_preview(char quadrant) {
  if (_session_code.length() == 0) return;
  String body =
      String("{\"session_code\":\"") + _session_code +
      "\",\"puck_id\":" + PUCK_ID;
  if (quadrant) {
    body += ",\"quadrant\":\"";
    body += quadrant;
    body += "\"}";
  } else {
    body += ",\"quadrant\":null}";
  }
  sp_net::post_json("/api/sp/minigame/preview", body, nullptr);
}

// POST /api/sp/minigame/fire. Returns true on 200.
inline bool _post_minigame_fire(uint32_t t_ms, char quadrant) {
  if (_session_code.length() == 0) return false;
  String body =
      String("{\"session_code\":\"") + _session_code +
      "\",\"puck_id\":" + PUCK_ID +
      ",\"t_ms\":" + t_ms;
  if (quadrant) {
    body += ",\"quadrant\":\"";
    body += quadrant;
    body += "\"}";
  } else {
    body += ",\"quadrant\":null}";
  }
  return sp_net::post_json("/api/sp/minigame/fire", body, nullptr) == 200;
}

// POST /api/sp/reset/<session_code>. Clears the round counter for a
// Play Again. Returns true on 200.
inline bool _post_reset() {
  if (_session_code.length() == 0) return false;
  String path = "/api/sp/reset/" + _session_code;
  return sp_net::post_json(path.c_str(), "{}", nullptr) == 200;
}

// GET /api/sp/current-question/<session_code>. Returns true if an active
// question was found and populates _current_question_id / time tracking.
inline bool _poll_current_question() {
  if (_session_code.length() == 0) return false;
  String path = "/api/sp/current-question/" + _session_code;
  String body;
  const int code = sp_net::get_json(path.c_str(), &body);
  if (code != 200) {
    Serial.printf("[POLL] %s -> HTTP %d\n", path.c_str(), code);
    return false;
  }

  bool active = false;
  if (!_extract_bool(body, "active", &active) || !active) {
    Serial.printf("[POLL] no active question (body=%s)\n", body.c_str());
    return false;
  }

  int qid = -1, time_limit_s = 10;
  if (!_extract_int(body, "question_id", &qid)) {
    Serial.println("[POLL] active but no question_id?");
    return false;
  }
  _extract_int(body, "time_limit", &time_limit_s);

  if (qid != _current_question_id) {
    Serial.printf("[POLL] NEW question_id=%d time_limit=%ds\n", qid, time_limit_s);
    _current_question_id = qid;
    _question_started_at_ms = millis();
    _question_time_limit_ms = (uint32_t)time_limit_s * 1000;
    return true;
  }
  return false;
}

// POST /api/sp/answer (multi-player aware). Server records this puck's
// answer for the round; reveal is emitted by the server only once every
// expected puck has answered (or the puck calls force-reveal on timeout).
inline bool _post_answer(char letter, uint32_t response_time_ms, bool* is_correct_out) {
  String body =
      "{\"session_code\":\"" + _session_code + "\"" +
      ",\"puck_id\":" + String(PUCK_ID) +
      ",\"question_id\":" + String(_current_question_id) +
      ",\"answer\":\"" + String(letter) + "\"" +
      ",\"response_time_ms\":" + String(response_time_ms) + "}";
  String resp;
  const int code = sp_net::post_json("/api/sp/answer", body, &resp);
  if (code != 200) return false;
  bool ok = false;
  _extract_bool(resp, "is_correct", &ok);
  if (is_correct_out) *is_correct_out = ok;
  return true;
}

// POST /api/trivia/answer-preview — real-time mirror of the currently
// aimed quadrant so the TV can softly highlight which pill the player
// is hovering on before they tap to lock.
inline void _post_answer_preview(char letter) {
  if (_session_code.length() == 0) return;
  String body =
      "{\"session_code\":\"" + _session_code + "\"" +
      ",\"puck_id\":" + String(PUCK_ID) +
      ",\"answer\":";
  if (letter == 0) body += "null";
  else { body += "\""; body += letter; body += "\""; }
  body += "}";
  sp_net::post_json("/api/trivia/answer-preview", body, nullptr);
}

// Map sp_imu::SpQuadrant -> A/B/C/D letter. UP=A, RIGHT=B, DOWN=C, LEFT=D.
inline char _quadrant_to_letter(SpQuadrant q) {
  switch (q) {
    case SpQuadrant::UP:    return 'A';
    case SpQuadrant::RIGHT: return 'B';
    case SpQuadrant::DOWN:  return 'C';
    case SpQuadrant::LEFT:  return 'D';
    default:                return 0;
  }
}

inline int8_t _quadrant_to_ring(SpQuadrant q) {
  switch (q) {
    case SpQuadrant::UP:    return 0;
    case SpQuadrant::RIGHT: return 1;
    case SpQuadrant::DOWN:  return 2;
    case SpQuadrant::LEFT:  return 3;
    default:                return -1;
  }
}

inline void begin() {
  sp_button::begin();
  sp_imu::begin();
  sp_led::begin();
  sp_feedback::begin();
  sp_net::connect();
  sp_led::clear();
  _state = State::IDLE;
  _dial_pos = 0;
  _current_digit = 0;
  for (uint8_t i = 0; i < 6; ++i) _dial_digits[i] = 0;
}

// Call from loop(). Returns true while the puck is engaged in pair-mode
// (so the main sketch knows not to fire other game state machines).
inline bool pair_mode_loop() {
  const SpButtonEvent be = sp_button::poll();

  // Idle: HOLD_1S enters pair mode.
  if (_state == State::IDLE) {
    if (be == SpButtonEvent::HOLD_1S) {
      _state = State::PAIR_REQUESTING;
      sp_feedback::beep(1500, 60);
      sp_led::flash(sp_led::color_for_puck(PUCK_ID), 100);
      String role;
      String lobby_code;
      if (_request_pair_code(&role, &lobby_code)) {
        // "Pair mode active" confirmation flash + beep.
        sp_led::flash(sp_led::color_correct(), 200);
        sp_feedback::beep(1800, 120);

        if (role == "joiner") {
          // Joiners skip the dial entirely — server already added them
          // to the lobby on /request. Jump straight to LOBBY_WAITING.
          Serial.printf("[PAIR] joiner -> LOBBY_WAITING lobby=%s\n",
                        lobby_code.c_str());
          _lobby_code = lobby_code;
          _is_host = false;
          _state = State::LOBBY_WAITING;
          _last_lobby_poll_ms = 0;
        } else {
          // Host: dial the 6 digits, then confirm.
          _state = State::PAIR_DIALING;
          _dial_pos = 0;
          _current_digit = 0;
          sp_led::show_dial_digit(_current_digit);
          _post_preview(_dial_pos, _current_digit);
        }
      } else {
        _state = State::IDLE;
        sp_led::flash(sp_led::color_wrong(), 150);
      }
      return true;
    }
    return false;
  }

  if (_state == State::PAIR_DIALING) {
    // Post-TAP input lockout: pressing the button physically jolts the
    // puck, which generates spurious IMU tilts AND a finger pulse can
    // double-trigger the button. Block all dial input for a short window
    // after each TAP so the physical impulse can settle out.
    const uint32_t kPostTapLockoutMs = 500;
    const bool in_lockout = (_last_dial_tap_ms != 0) &&
                            (millis() - _last_dial_tap_ms < kPostTapLockoutMs);

    const SpTiltEvent tilt = in_lockout ? SpTiltEvent::NONE : sp_imu::poll_tilt();
    if (tilt == SpTiltEvent::UP) {
      _current_digit = (_current_digit + 1) % 10;
      sp_led::show_dial_digit(_current_digit);
      sp_feedback::beep(900, 30);
      Serial.printf("[DIAL] slot=%u digit=%u\n", _dial_pos, _current_digit);
      _post_preview(_dial_pos, _current_digit);
    } else if (tilt == SpTiltEvent::DOWN) {
      _current_digit = (_current_digit + 9) % 10;
      sp_led::show_dial_digit(_current_digit);
      sp_feedback::beep(700, 30);
      Serial.printf("[DIAL] slot=%u digit=%u\n", _dial_pos, _current_digit);
      _post_preview(_dial_pos, _current_digit);
    }

    if (!in_lockout && be == SpButtonEvent::TAP) {
      _last_dial_tap_ms = millis();
      _dial_digits[_dial_pos] = _current_digit;
      _post_dial(_dial_pos, _current_digit);
      sp_feedback::lock_in();
      _dial_pos++;
      _current_digit = 0;
      if (_dial_pos >= 6) {
        _state = State::PAIR_CONFIRMING;
        String lobby_code;
        bool is_host = false;
        const bool ok = _post_confirm_v2(&lobby_code, &is_host);
        if (ok) {
          _lobby_code = lobby_code;
          _is_host = is_host;
          Serial.printf("[PAIR] joined lobby=%s as %s\n",
                        _lobby_code.c_str(), is_host ? "HOST" : "joiner");
          _state = State::LOBBY_WAITING;
          _last_lobby_poll_ms = 0;
          sp_led::flash(sp_led::color_correct(), 400);
          sp_feedback::pair_confirmed();
        } else {
          _state = State::IDLE;
          sp_led::flash(sp_led::color_wrong(), 400);
          sp_feedback::wrong();
        }
      } else {
        sp_led::show_dial_digit(_current_digit);
        _post_preview(_dial_pos, _current_digit);
      }
    }

    // HOLD_3S mid-dial cancels and releases the lobby. (Removed once
    // for accidental fires; re-added in v2E because the joiner cancel
    // path is the same gesture and consistency wins. If accidents
    // resurface, gate by "only after first digit dialed" later.)
    if (be == SpButtonEvent::HOLD_3S) {
      Serial.println("[PAIR] HOLD_3S mid-dial -> cancel");
      _post_cancel();
      sp_led::flash(sp_led::color_wrong(), 250);
      sp_feedback::wrong();
      _state = State::IDLE;
      _dial_pos = 0;
      _current_digit = 0;
      return true;
    }
    return true;
  }

  if (_state == State::PAIRED) {
    // v2: hand off to LOBBY_WAITING (not directly to IN_GAME_IDLE) —
    // we don't know the session_code until the host starts.
    Serial.println("[STATE] PAIRED -> LOBBY_WAITING");
    _state = State::LOBBY_WAITING;
    _last_lobby_poll_ms = 0;
    return true;
  }

  // -----------------------------
  // LOBBY_WAITING state (v2)
  // -----------------------------
  if (_state == State::LOBBY_WAITING) {
    // Any puck: HOLD_3S cancels (host kills the lobby, joiner leaves).
    if (be == SpButtonEvent::HOLD_3S) {
      Serial.printf("[LOBBY] HOLD_3S cancel (host=%d)\n", _is_host ? 1 : 0);
      _post_cancel();
      sp_led::flash(sp_led::color_wrong(), 250);
      sp_feedback::wrong();
      _state = State::IDLE;
      _lobby_code = "";
      _is_host = false;
      _session_code = "";
      return true;
    }

    // Host: tap-to-start.
    if (_is_host && be == SpButtonEvent::TAP) {
      Serial.println("[LOBBY] host TAP -> /api/pair/start");
      sp_feedback::lock_in();
      if (!_post_start()) {
        Serial.println("[LOBBY] start POST failed");
      }
    }

    // Poll every 1s for match_started.
    const uint32_t now = millis();
    if (now - _last_lobby_poll_ms > 1000) {
      _last_lobby_poll_ms = now;
      String session_code;
      if (_poll_lobby_state(&session_code)) {
        _session_code = session_code;
        Serial.printf("[LOBBY] match started! session=%s\n",
                      _session_code.c_str());
        _state = State::IN_GAME_IDLE;
        _current_question_id = -1;
        _last_poll_ms = 0;
      }
    }

    // Visual: gentle rotating glow in this puck's role color. Host gets
    // a slightly brighter pulse so the human can see "I am the host".
    _show_pair_mode_glow();
    return true;
  }

  // -----------------------------
  // In-game state machine (slice 1C + E1 + E2)
  // -----------------------------
  if (_state == State::IN_GAME_IDLE ||
      _state == State::IN_GAME_CATEGORY_PICKING ||
      _state == State::IN_GAME_MINIGAME ||
      _state == State::IN_GAME_ANSWERING ||
      _state == State::IN_GAME_LOCKED) {

    // Poll for active question every 500ms while idle / locked / pick
    // / minigame. Also check match-state for end-of-match, pending
    // category-pick (E1), pending minigame (E2).
    const uint32_t now = millis();
    if ((_state == State::IN_GAME_IDLE ||
         _state == State::IN_GAME_LOCKED ||
         _state == State::IN_GAME_CATEGORY_PICKING ||
         _state == State::IN_GAME_MINIGAME) &&
        now - _last_poll_ms > 500) {
      _last_poll_ms = now;

      if (_poll_match_state_complete()) {
        Serial.println("[STATE] -> MATCH_ENDED");
        _state = State::MATCH_ENDED;
        sp_led::victory_sweep(1500);
        sp_feedback::victory();
      } else if (_poll_pending_pick()) {
        if (_state != State::IN_GAME_CATEGORY_PICKING) {
          Serial.print("[STATE] -> IN_GAME_CATEGORY_PICKING picker=");
          Serial.println(_pick_picker);
          _state = State::IN_GAME_CATEGORY_PICKING;
          _pick_idx = 0;
          _last_pick_quadrant = 0;
        }
      } else if (_state == State::IN_GAME_CATEGORY_PICKING) {
        Serial.println("[STATE] IN_GAME_CATEGORY_PICKING -> IN_GAME_IDLE");
        _state = State::IN_GAME_IDLE;
        sp_led::clear();
      } else if (_poll_pending_minigame()) {
        if (_state != State::IN_GAME_MINIGAME) {
          Serial.print("[STATE] -> IN_GAME_MINIGAME flavor=");
          Serial.print(_mg_flavor);
          Serial.print(" target=");
          Serial.println(_mg_target);
          _state = State::IN_GAME_MINIGAME;
          _mg_started_ms = millis();
          _mg_fired = false;
          _mg_last_preview_quad = 0;
        }
      } else if (_state == State::IN_GAME_MINIGAME) {
        Serial.println("[STATE] IN_GAME_MINIGAME -> IN_GAME_IDLE");
        _state = State::IN_GAME_IDLE;
        sp_led::clear();
      } else if (_poll_current_question()) {
        Serial.println("[STATE] IN_GAME_IDLE -> IN_GAME_ANSWERING");
        _state = State::IN_GAME_ANSWERING;
      }
    }

    // Picker interaction: tilt LEFT/RIGHT scrolls offer index, tap
    // commits the selected category. Non-pickers idle visually.
    if (_state == State::IN_GAME_CATEGORY_PICKING) {
      if (PUCK_ID == _pick_picker) {
        const SpQuadrant q = sp_imu::read_quadrant();
        const char ql = _quadrant_to_letter(q);
        // Treat RIGHT as next, LEFT as prev. Up/Down ignored. Edge-
        // trigger on quadrant changes so a held-tilt doesn't auto-
        // scroll.
        if (ql != _last_pick_quadrant) {
          if (ql == 'B' && _pick_idx < 2 && _pick_offer_ids[_pick_idx + 1] > 0) {
            _pick_idx++;
            sp_feedback::beep(900, 30);
          } else if (ql == 'D' && _pick_idx > 0) {
            _pick_idx--;
            sp_feedback::beep(900, 30);
          }
          _last_pick_quadrant = ql;
        }
        // Render: LED ring shows _pick_idx as a colored arc (3 slots).
        sp_led::show_quadrant(_pick_idx, sp_led::color_accent());
        if (be == SpButtonEvent::TAP) {
          const int chosen = _pick_offer_ids[_pick_idx];
          if (chosen > 0) {
            sp_feedback::lock_in();
            if (_post_select_category(chosen)) {
              _state = State::IN_GAME_IDLE;
              sp_led::clear();
            }
          }
        }
      } else {
        // Not the picker — just glow softly while waiting.
        _show_pair_mode_glow();
      }
      return true;
    }

    // Slice E2 — minigame interaction. BULLSEYE: render current tilt
    // quadrant on the LED ring (mirrors ANSWERING aim). SHOT_CLOCK:
    // ignore tilt; tap fires with t_ms only (server scores from
    // sweep position).
    if (_state == State::IN_GAME_MINIGAME) {
      if (_mg_fired) {
        // Already locked in — soft glow until server resolves.
        _show_pair_mode_glow();
        return true;
      }
      const SpQuadrant q = sp_imu::read_quadrant();
      const int8_t ring_q = _quadrant_to_ring(q);
      if (_mg_flavor == 'B') {
        sp_led::show_quadrant(ring_q, sp_led::color_accent());
        // Slice F — broadcast aim preview on tilt change. Edge-
        // triggered so we only POST when the quadrant actually
        // shifts; held-tilt at a stable quadrant doesn't spam.
        const char preview_q = _quadrant_to_letter(q);
        if (preview_q != _mg_last_preview_quad) {
          _mg_last_preview_quad = preview_q;
          _post_minigame_preview(preview_q);
        }
      } else {
        // SHOT_CLOCK — pulse the ring in accent to signal "tap now".
        _show_pair_mode_glow();
      }
      if (be == SpButtonEvent::TAP) {
        const uint32_t t_ms = millis() - _mg_started_ms;
        const char quadrant = (_mg_flavor == 'B') ? _quadrant_to_letter(q) : 0;
        sp_feedback::lock_in();
        sp_led::flash(sp_led::color_for_puck(PUCK_ID), 300);
        if (_post_minigame_fire(t_ms, quadrant)) {
          _mg_fired = true;
        }
      }
      return true;
    }

    if (_state == State::IN_GAME_ANSWERING) {
      // Render: 4 LEDs lit in current tilt quadrant; remaining LEDs
      // around the ring show the timer depletion in accent pink.
      const SpQuadrant q = sp_imu::read_quadrant();
      const int8_t ring_q = _quadrant_to_ring(q);
      const char preview_letter = _quadrant_to_letter(q);
      if (preview_letter != _last_preview_letter) {
        _last_preview_letter = preview_letter;
        _post_answer_preview(preview_letter);
      }

      // Recapture millis() here; `now` was sampled BEFORE the poll
      // block, which (if we just transitioned to ANSWERING) set
      // _question_started_at_ms to a NEWER millis. The subtraction
      // would underflow as unsigned and report the timer as already
      // expired.
      const uint32_t now_in_game = millis();
      const uint32_t elapsed =
          (now_in_game >= _question_started_at_ms)
              ? (now_in_game - _question_started_at_ms)
              : 0;
      const uint32_t remaining = (elapsed >= _question_time_limit_ms)
                                     ? 0
                                     : _question_time_limit_ms - elapsed;

      // Clean visual: only the tilt-quadrant LEDs lit in blue. No
      // timer ring on the puck — the browser's TimerBar is the
      // single source of truth for time-remaining. Center / no tilt =
      // ring goes dark.
      sp_led::show_quadrant(ring_q, sp_led::color_primary());

      // Timeout: no answer submitted. Drop to LOCKED quietly — no
      // wrong-answer cue yet (that would leak the outcome before the
      // reveal phase). Reveal-time feedback will fire from
      // IN_GAME_LOCKED once the server's reveal is published.
      if (remaining == 0) {
        _state = State::IN_GAME_LOCKED;
        sp_led::clear();
        _last_preview_letter = 0;
        return true;
      }

      if (be == SpButtonEvent::TAP) {
        _last_preview_letter = 0;  // reset for next question
        const char letter = _quadrant_to_letter(q);
        if (letter == 0) {
          // No commitable tilt -- short reject buzz.
          sp_feedback::beep(400, 60);
        } else {
          // Lock-in + immediate per-player correct/wrong cue. Earlier
          // builds suppressed the result here to avoid neighbour-peek,
          // but per-player feedback at the moment of commit is more
          // valuable than that mild leak — and in a real bar the puck
          // sits in the player's hand, not on a shared surface, so the
          // beep isn't broadcast.
          sp_feedback::lock_in();
          sp_led::flash(sp_led::color_for_puck(PUCK_ID), 300);
          bool is_correct = false;
          if (_post_answer(letter, elapsed, &is_correct)) {
            if (is_correct) sp_feedback::correct();
            else sp_feedback::wrong();
          }
          _state = State::IN_GAME_LOCKED;
        }
      }
    } else {
      // Idle / locked between questions — soft host-mode glow so the
      // puck still feels alive.
      _show_pair_mode_glow();
    }

    return true;
  }

  // -----------------------------
  // Match ended — Play Again / New Player
  // -----------------------------
  if (_state == State::MATCH_ENDED) {
    _show_pair_mode_glow();
    if (be == SpButtonEvent::TAP) {
      // Play Again — reset server-side counter, re-arm in-game loop.
      sp_feedback::lock_in();
      if (_post_reset()) {
        _state = State::IN_GAME_IDLE;
        _current_question_id = -1;
        _last_poll_ms = 0;
      } else {
        sp_led::flash(sp_led::color_wrong(), 200);
      }
    }
    if (be == SpButtonEvent::HOLD_3S) {
      // New Player — drop back to pair mode (fresh code, fresh session).
      _state = State::IDLE;
      _session_code = "";
      _current_question_id = -1;
      _dial_pos = 0;
      sp_led::clear();
    }
    return true;
  }

  return _state != State::IDLE;
}

}  // namespace sp_game
