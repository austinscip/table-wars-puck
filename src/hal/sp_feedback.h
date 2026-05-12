// Speed Pyramid v1 — buzzer + motor feedback HAL.
//
// Lightweight wrappers around tone() and digitalWrite() with the named
// feedback patterns from the PRD. Game code calls high-level helpers
// (sp_feedback::lock(), correct(), wrong(), pair_confirmed(),
// victory()) — no raw freq/duty numbers in game code.

#pragma once

#include <Arduino.h>
#include "sp_pins.h"

namespace sp_feedback {

inline void begin() {
  pinMode(SP_PIN_MOTOR, OUTPUT);
  digitalWrite(SP_PIN_MOTOR, LOW);

  // Pre-attach a LEDC channel to the buzzer pin so the FIRST tone()
  // call doesn't trigger the "ledc_get_duty: LEDC is not initialized"
  // warning. Arduino-ESP32's tone() reads duty before configuring
  // the channel; doing it here once at boot silences that log.
  // Channel 0, 8-bit resolution, initial freq 1000 Hz.
  ledcSetup(0, 1000, 8);
  ledcAttachPin(SP_PIN_BUZZER, 0);
  ledcWrite(0, 0);  // start silent
}

inline void beep(uint16_t freq_hz, uint16_t duration_ms) {
  tone(SP_PIN_BUZZER, freq_hz, duration_ms);
}

inline void motor_pulse(uint16_t duration_ms) {
  digitalWrite(SP_PIN_MOTOR, HIGH);
  delay(duration_ms);
  digitalWrite(SP_PIN_MOTOR, LOW);
}

inline void motor_pattern(uint16_t on_ms, uint16_t off_ms, uint8_t count) {
  for (uint8_t i = 0; i < count; ++i) {
    digitalWrite(SP_PIN_MOTOR, HIGH);
    delay(on_ms);
    digitalWrite(SP_PIN_MOTOR, LOW);
    if (i < count - 1) delay(off_ms);
  }
}

// Sweep from start_freq to end_freq over duration_ms.
inline void sweep(uint16_t start_freq, uint16_t end_freq, uint16_t duration_ms) {
  const int steps = 20;
  const int step_ms = duration_ms / steps;
  for (int s = 0; s <= steps; ++s) {
    const float t = (float)s / steps;
    const int f = (int)(start_freq + (end_freq - start_freq) * t);
    tone(SP_PIN_BUZZER, f, step_ms);
    delay(step_ms);
  }
  noTone(SP_PIN_BUZZER);
}

// ---- Named feedback per PRD table ----

inline void lock_in() {
  motor_pulse(80);
  beep(1200, 80);
}

inline void correct() {
  motor_pulse(200);
  sweep(700, 1400, 250);
}

inline void wrong() {
  motor_pulse(500);
  sweep(200, 100, 300);
}

inline void pair_confirmed() {
  motor_pulse(200);
  beep(1000, 200);
}

inline void victory() {
  motor_pattern(100, 80, 3);
  // C4 -> C6 crescendo (262, 330, 392, 523, 659, 1047 Hz approx)
  static const uint16_t notes[6] = {262, 330, 392, 523, 659, 1047};
  for (uint8_t i = 0; i < 6; ++i) {
    tone(SP_PIN_BUZZER, notes[i], 120);
    delay(120);
  }
  noTone(SP_PIN_BUZZER);
}

}  // namespace sp_feedback
