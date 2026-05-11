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
  PAIRED,  // hand-off to in-game state once slice 1C lands
};

inline State _state = State::IDLE;
inline uint8_t _dial_digits[6] = {0, 0, 0, 0, 0, 0};
inline uint8_t _dial_pos = 0;     // 0..5
inline uint8_t _current_digit = 0;

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
    // Slice 1C wires in_game_loop() here. For 1B, stay quiet.
    _show_pair_mode_glow();
    return true;
  }

  return _state != State::IDLE;
}

}  // namespace sp_game
