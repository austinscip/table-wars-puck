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
inline uint32_t _last_edge_ms = 0;
inline bool _hold_1s_emitted = false;
inline bool _hold_3s_emitted = false;

// Debounce window. Any raw state transition within this many ms after
// the last accepted edge is ignored as bounce. Empirically 30-50ms
// covers most through-hole tactile switches.
constexpr uint32_t kDebounceMs = 40;

inline void begin() {
#if defined(PUCK_REV_B)
  // Rev B has an external 10K pull-DOWN on the button line (per
  // hardware spec: GPIO 33 + R15 pull-down). The button connects the
  // pin to VCC when pressed. So we use plain INPUT and treat HIGH as
  // pressed.
  pinMode(SP_PIN_BUTTON, INPUT);
#else
  // Rev A: no external pull, we use the internal pull-up. Button
  // pulls the line to GND on press, so LOW = pressed.
  pinMode(SP_PIN_BUTTON, INPUT_PULLUP);
#endif
  Serial.println("[BTN] begin");
}

// Call every loop. Returns at most one event per call. Edges within
// kDebounceMs of the previous edge are filtered out so a single physical
// press doesn't fire multiple events.
inline SpButtonEvent poll() {
#if defined(PUCK_REV_B)
  // Rev B: HIGH = pressed (external pull-down keeps it LOW at rest).
  const bool raw_down = (digitalRead(SP_PIN_BUTTON) == HIGH);
#else
  // Rev A: LOW = pressed (internal pull-up keeps it HIGH at rest).
  const bool raw_down = (digitalRead(SP_PIN_BUTTON) == LOW);
#endif
  const uint32_t now = millis();

  // Edge-debounce: a raw state transition only "counts" if we haven't
  // accepted an edge very recently.
  if (raw_down && !_down) {
    if (now - _last_edge_ms < kDebounceMs) return SpButtonEvent::NONE;
    _last_edge_ms = now;
    _down = true;
    _down_at_ms = now;
    _hold_1s_emitted = false;
    _hold_3s_emitted = false;
    Serial.println("[BTN] press");
    return SpButtonEvent::NONE;
  }

  if (_down && raw_down) {
    const uint32_t held = now - _down_at_ms;
    if (!_hold_3s_emitted && held >= 5000) {
      _hold_3s_emitted = true;
      Serial.println("[BTN] HOLD_3S");
      return SpButtonEvent::HOLD_3S;
    }
    if (!_hold_1s_emitted && held >= 1000) {
      _hold_1s_emitted = true;
      Serial.println("[BTN] HOLD_1S");
      return SpButtonEvent::HOLD_1S;
    }
    return SpButtonEvent::NONE;
  }

  if (!raw_down && _down) {
    if (now - _last_edge_ms < kDebounceMs) return SpButtonEvent::NONE;
    _last_edge_ms = now;
    _down = false;
    const uint32_t held = now - _down_at_ms;
    if (held < 1000 && !_hold_1s_emitted) {
      Serial.printf("[BTN] TAP (held=%lums)\n", (unsigned long)held);
      return SpButtonEvent::TAP;
    }
    Serial.printf("[BTN] release (held=%lums, no event)\n", (unsigned long)held);
    return SpButtonEvent::NONE;
  }

  return SpButtonEvent::NONE;
}

}  // namespace sp_button
