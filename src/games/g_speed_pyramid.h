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
  PAIRED,             // brief celebration before dropping to IN_GAME
  IN_GAME_IDLE,       // session bound, no question active yet
  IN_GAME_ANSWERING,  // question active, tilt-aim + tap
  IN_GAME_LOCKED,     // tap fired, awaiting server reveal
  MATCH_ENDED,        // all 7 rounds done — TAP=PlayAgain, HOLD_3S=NewPlayer
};

inline State _state = State::IDLE;
inline uint8_t _dial_digits[6] = {0, 0, 0, 0, 0, 0};
inline uint8_t _dial_pos = 0;     // 0..5
inline uint8_t _current_digit = 0;

// Session + question tracking (set after PAIR_CONFIRMING succeeds).
inline String _session_code = "";
inline int _current_question_id = -1;
inline uint32_t _question_started_at_ms = 0;  // millis() when puck saw it
inline uint32_t _question_time_limit_ms = 10000;
inline uint32_t _last_poll_ms = 0;

inline void _show_pair_mode_glow() {
  // Soft rotating dot in --host palette so the player knows they're
  // in pair mode but no digit is being dialed yet.
  static uint32_t last_step = 0;
  static uint8_t pos = 0;
  if (millis() - last_step < 100) return;
  last_step = millis();
  pos = (pos + 1) % 16;
  for (int i = 0; i < 16; ++i) {
    if (i == pos) {
      FastLED.leds()[i] = sp_led::color_host();
    } else {
      FastLED.leds()[i] = sp_led::color_host();
      FastLED.leds()[i].fadeToBlackBy(240);
    }
  }
  FastLED.show();
}

// Request a fresh pair code by POST /api/pair/request. Doesn't read the
// returned code on the puck side (the TV displays it); just confirms
// the server is ready before letting the player dial.
inline bool _request_pair_code() {
  String body = "{\"puck_id\":" + String(PUCK_ID) + "}";
  String resp;
  const int code = sp_net::post_json("/api/pair/request", body, &resp);
  return code == 200;
}

inline bool _post_dial(uint8_t index, uint8_t digit) {
  String body =
      "{\"puck_id\":" + String(PUCK_ID) +
      ",\"digit_index\":" + String(index) +
      ",\"digit\":" + String(digit) + "}";
  const int code = sp_net::post_json("/api/pair/dial", body, nullptr);
  return code == 200;
}

inline bool _post_confirm(String* session_code_out) {
  String code_str = "";
  for (uint8_t i = 0; i < 6; ++i) code_str += String(_dial_digits[i]);
  String body =
      "{\"puck_id\":" + String(PUCK_ID) +
      ",\"code\":\"" + code_str + "\"}";
  String resp;
  const int code = sp_net::post_json("/api/pair/confirm", body, &resp);
  if (code != 200) return false;
  // Crude JSON parse — extract "session_code":"XXXXXX". For v1 this is
  // fine; we move to ArduinoJson if we ever read more fields.
  const int idx = resp.indexOf("\"session_code\":\"");
  if (idx < 0) return false;
  const int start = idx + strlen("\"session_code\":\"");
  const int end = resp.indexOf("\"", start);
  if (end < 0) return false;
  *session_code_out = resp.substring(start, end);
  return true;
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

// GET /api/sp/match-state/<session_code>. Returns total round count
// so the puck can know when the match is done (round >= total).
inline bool _poll_match_state(int* round_out, int* total_out) {
  if (_session_code.length() == 0) return false;
  HTTPClient http;
  http.begin(String(SPEED_PYRAMID_SERVER_URL) + "/api/sp/match-state/" + _session_code);
  const int code = http.GET();
  if (code != 200) { http.end(); return false; }
  const String body = http.getString();
  http.end();
  int r = 0, t = 7;
  if (!_extract_int(body, "round", &r)) return false;
  _extract_int(body, "total_rounds", &t);
  if (round_out) *round_out = r;
  if (total_out) *total_out = t;
  return true;
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
  HTTPClient http;
  http.begin(String(SPEED_PYRAMID_SERVER_URL) + "/api/sp/current-question/" + _session_code);
  const int code = http.GET();
  if (code != 200) { http.end(); return false; }
  const String body = http.getString();
  http.end();

  bool active = false;
  if (!_extract_bool(body, "active", &active) || !active) return false;

  int qid = -1, time_limit_s = 10;
  if (!_extract_int(body, "question_id", &qid)) return false;
  _extract_int(body, "time_limit", &time_limit_s);

  if (qid != _current_question_id) {
    _current_question_id = qid;
    _question_started_at_ms = millis();
    _question_time_limit_ms = (uint32_t)time_limit_s * 1000;
    return true;
  }
  return false;
}

// POST /api/trivia/answer. Returns true on 200, populates is_correct.
inline bool _post_answer(char letter, uint32_t response_time_ms, bool* is_correct_out) {
  String body =
      "{\"session_code\":\"" + _session_code + "\"" +
      ",\"puck_id\":" + String(PUCK_ID) +
      ",\"question_id\":" + String(_current_question_id) +
      ",\"answer\":\"" + String(letter) + "\"" +
      ",\"response_time_ms\":" + String(response_time_ms) + "}";
  String resp;
  const int code = sp_net::post_json("/api/trivia/answer", body, &resp);
  if (code != 200) return false;
  bool ok = false;
  _extract_bool(resp, "is_correct", &ok);
  if (is_correct_out) *is_correct_out = ok;
  return true;
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
      sp_led::flash(sp_led::color_host(), 100);
      if (_request_pair_code()) {
        _state = State::PAIR_DIALING;
        _dial_pos = 0;
        _current_digit = 0;
        sp_led::show_dial_digit(_current_digit);
      } else {
        _state = State::IDLE;
        sp_led::flash(sp_led::color_wrong(), 150);
      }
      return true;
    }
    return false;
  }

  if (_state == State::PAIR_DIALING) {
    const SpTiltEvent tilt = sp_imu::poll_tilt();
    if (tilt == SpTiltEvent::UP) {
      _current_digit = (_current_digit + 1) % 10;
      sp_led::show_dial_digit(_current_digit);
      sp_feedback::beep(900, 30);
    } else if (tilt == SpTiltEvent::DOWN) {
      _current_digit = (_current_digit + 9) % 10;
      sp_led::show_dial_digit(_current_digit);
      sp_feedback::beep(700, 30);
    }

    if (be == SpButtonEvent::TAP) {
      _dial_digits[_dial_pos] = _current_digit;
      _post_dial(_dial_pos, _current_digit);
      sp_feedback::lock_in();
      _dial_pos++;
      _current_digit = 0;
      if (_dial_pos >= 6) {
        _state = State::PAIR_CONFIRMING;
        String session_code;
        const bool ok = _post_confirm(&session_code);
        if (ok) {
          _state = State::PAIRED;
          sp_led::flash(sp_led::color_correct(), 400);
          sp_feedback::pair_confirmed();
        } else {
          _state = State::IDLE;
          sp_led::flash(sp_led::color_wrong(), 400);
          sp_feedback::wrong();
        }
      } else {
        sp_led::show_dial_digit(_current_digit);
      }
    }

    if (be == SpButtonEvent::HOLD_3S) {
      // Cancel pair mode mid-dial.
      _state = State::IDLE;
      sp_led::flash(sp_led::color_wrong(), 200);
    }
    return true;
  }

  if (_state == State::PAIRED) {
    // Hand off to in-game state machine.
    _state = State::IN_GAME_IDLE;
    _current_question_id = -1;
    return true;
  }

  // -----------------------------
  // In-game state machine (slice 1C)
  // -----------------------------
  if (_state == State::IN_GAME_IDLE ||
      _state == State::IN_GAME_ANSWERING ||
      _state == State::IN_GAME_LOCKED) {

    // Poll for active question every 500ms while idle / locked. Also
    // check match-state to detect end-of-match.
    const uint32_t now = millis();
    if ((_state == State::IN_GAME_IDLE || _state == State::IN_GAME_LOCKED) &&
        now - _last_poll_ms > 500) {
      _last_poll_ms = now;

      int r = 0, t = 7;
      if (_poll_match_state(&r, &t) && r >= t && t > 0) {
        _state = State::MATCH_ENDED;
        sp_led::victory_sweep(1500);
        sp_feedback::victory();
      } else if (_poll_current_question()) {
        _state = State::IN_GAME_ANSWERING;
      }
    }

    if (_state == State::IN_GAME_ANSWERING) {
      // Render: 4 LEDs lit in current tilt quadrant; remaining LEDs
      // around the ring show the timer depletion in accent pink.
      const SpQuadrant q = sp_imu::read_quadrant();
      const int8_t ring_q = _quadrant_to_ring(q);

      const uint32_t elapsed = now - _question_started_at_ms;
      const uint32_t remaining = (elapsed >= _question_time_limit_ms)
                                     ? 0
                                     : _question_time_limit_ms - elapsed;

      // Show timer ring first, then overlay quadrant.
      sp_led::show_timer(remaining, _question_time_limit_ms, sp_led::color_accent());
      if (ring_q >= 0) {
        // Re-tint the quadrant LEDs with primary blue. show_quadrant
        // clears first, so we have to redo the timer fill manually.
        sp_led::show_quadrant(ring_q, sp_led::color_primary());
      }

      // Timeout: lock no answer, server will mark TIMEOUT on next reveal
      // when the puck sends an empty answer. For v1 we simply hold the
      // ring dark until the next question arrives.
      if (remaining == 0) {
        _state = State::IN_GAME_LOCKED;
        sp_led::clear();
        return true;
      }

      if (be == SpButtonEvent::TAP) {
        const char letter = _quadrant_to_letter(q);
        if (letter == 0) {
          // No commitable tilt -- short reject buzz.
          sp_feedback::beep(400, 60);
        } else {
          sp_feedback::lock_in();
          bool is_correct = false;
          if (_post_answer(letter, elapsed, &is_correct)) {
            if (is_correct) {
              sp_led::flash(sp_led::color_correct(), 500);
              sp_feedback::correct();
            } else {
              sp_led::flash(sp_led::color_wrong(), 400);
              sp_feedback::wrong();
            }
          } else {
            // Transport error — visible but non-fatal.
            sp_led::flash(sp_led::color_wrong(), 200);
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
