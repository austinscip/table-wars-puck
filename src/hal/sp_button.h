// Speed Pyramid v1 — button HAL.
//
// One physical button on SP_PIN_BUTTON (INPUT_PULLUP, active-low). Polled
// from the main loop. Emits debounced events: TAP (short press),
// HOLD_1S (held >= 1000ms), HOLD_3S (held >= 3000ms). Long press emits
// HOLD_1S on the 1s threshold AND HOLD_3S on the 3s threshold if the
// button stays down.

#pragma once

#include <Arduino.h>
#include "sp_pins.h"

enum class SpButtonEvent : uint8_t {
  NONE,
  TAP,
  HOLD_1S,
  HOLD_3S,
};

namespace sp_button {

inline bool _down = false;
inline uint32_t _down_at_ms = 0;
inline bool _hold_1s_emitted = false;
inline bool _hold_3s_emitted = false;

inline void begin() {
  pinMode(SP_PIN_BUTTON, INPUT_PULLUP);
}

// Call every loop. Returns at most one event per call. Debounce is
// implicit because we only act on transition edges.
inline SpButtonEvent poll() {
  const bool raw_down = (digitalRead(SP_PIN_BUTTON) == LOW);
  const uint32_t now = millis();

  if (raw_down && !_down) {
    // press start
    _down = true;
    _down_at_ms = now;
    _hold_1s_emitted = false;
    _hold_3s_emitted = false;
    return SpButtonEvent::NONE;
  }

  if (_down && raw_down) {
    const uint32_t held = now - _down_at_ms;
    if (!_hold_3s_emitted && held >= 3000) {
      _hold_3s_emitted = true;
      return SpButtonEvent::HOLD_3S;
    }
    if (!_hold_1s_emitted && held >= 1000) {
      _hold_1s_emitted = true;
      return SpButtonEvent::HOLD_1S;
    }
    return SpButtonEvent::NONE;
  }

  if (!raw_down && _down) {
    // release
    _down = false;
    const uint32_t held = now - _down_at_ms;
    if (held < 1000 && !_hold_1s_emitted) {
      return SpButtonEvent::TAP;
    }
    return SpButtonEvent::NONE;
  }

  return SpButtonEvent::NONE;
}

}  // namespace sp_button
