// Speed Pyramid v1 — LED ring HAL (WS2812B, 16 LEDs).
//
// Wraps FastLED with named palettes locked to the brand kit (see
// CONTEXT.md § "Locked brand tokens"). NO raw CRGB literals are allowed
// in game code — always go through a named palette.
//
// Palettes map 1:1 to the brand colors:
//   PRIMARY  = blue   (#3B82F6) — in-game tilt-aim quadrant
//   ACCENT   = pink   (#EC4899) — countdown depletion
//   CORRECT  = gold   (#FBBF24) — correct answer, victory
//   WRONG    = red    (#EF4444) — wrong answer, elimination
//   TEXT     = white  (#F8FAFC) — neutral fill
//   HOST     = white-blue mix   — pair mode indicator

#pragma once

#include <Arduino.h>
#include <FastLED.h>
#include "sp_pins.h"

namespace sp_led {

inline CRGB _leds[SP_NUM_LEDS];
inline uint8_t _brightness_gameplay = 80;
inline uint8_t _brightness_idle = 40;
inline uint8_t _brightness_punch = 200;

inline void begin() {
  FastLED.addLeds<NEOPIXEL, SP_PIN_LED>(_leds, SP_NUM_LEDS);
  FastLED.setBrightness(_brightness_gameplay);
  fill_solid(_leds, SP_NUM_LEDS, CRGB::Black);
  FastLED.show();
}

inline CRGB color_primary() { return CRGB(0x3B, 0x82, 0xF6); }
inline CRGB color_accent()  { return CRGB(0xEC, 0x48, 0x99); }
inline CRGB color_correct() { return CRGB(0xFB, 0xBF, 0x24); }
inline CRGB color_wrong()   { return CRGB(0xEF, 0x44, 0x44); }
inline CRGB color_text()    { return CRGB(0xF8, 0xFA, 0xFC); }
inline CRGB color_host()    { return CRGB(0x60, 0xA5, 0xFA); }  // softer blue

inline void clear() {
  fill_solid(_leds, SP_NUM_LEDS, CRGB::Black);
  FastLED.show();
}

inline void fill(CRGB c) {
  fill_solid(_leds, SP_NUM_LEDS, c);
  FastLED.show();
}

inline void set_brightness(uint8_t v) {
  FastLED.setBrightness(v);
  FastLED.show();
}

// Light a single ring position for the current digit. Direct 1:1
// mapping — digit N lights LED N. LEDs 10..15 are always dark.
//
// Result: every tilt moves the lit LED exactly one position around
// the ring (no 1-or-2 jumps from the previous even-spaced mapping).
// The 6 unused LEDs at positions 10-15 act as a visual gap so the
// user knows where the dial "wraps".
inline void show_dial_digit(uint8_t digit) {
  FastLED.setBrightness(_brightness_punch);
  fill_solid(_leds, SP_NUM_LEDS, CRGB::Black);
  if (digit < 10) _leds[digit] = color_primary();
  FastLED.show();
}

// Light the 4 LEDs in one quadrant of the ring (used for in-game tilt-aim).
//   0 = UP (LEDs 14,15,0,1)
//   1 = RIGHT (LEDs 2,3,4,5)
//   2 = DOWN (LEDs 6,7,8,9)
//   3 = LEFT (LEDs 10,11,12,13)
inline void show_quadrant(int8_t q, CRGB c) {
  fill_solid(_leds, SP_NUM_LEDS, CRGB::Black);
  if (q < 0) {
    FastLED.show();
    return;
  }
  static const uint8_t starts[4] = {14, 2, 6, 10};
  const uint8_t s = starts[q & 0x3];
  for (int i = 0; i < 4; ++i) {
    _leds[(s + i) % SP_NUM_LEDS] = c;
  }
  FastLED.show();
}

// Render the countdown timer as a depleting ring. `remaining_ms` /
// `total_ms` determines how many LEDs are still lit.
inline void show_timer(uint32_t remaining_ms, uint32_t total_ms, CRGB c) {
  if (total_ms == 0) return;
  const int lit =
      (int)((uint64_t)remaining_ms * SP_NUM_LEDS / total_ms);
  for (int i = 0; i < SP_NUM_LEDS; ++i) {
    _leds[i] = (i < lit) ? c : CRGB::Black;
  }
  FastLED.show();
}

// Brief pulse: flash a color at high brightness, then fade back.
inline void flash(CRGB c, uint16_t duration_ms) {
  uint8_t prev = FastLED.getBrightness();
  FastLED.setBrightness(_brightness_punch);
  fill_solid(_leds, SP_NUM_LEDS, c);
  FastLED.show();
  delay(duration_ms);
  FastLED.setBrightness(prev);
  fill_solid(_leds, SP_NUM_LEDS, CRGB::Black);
  FastLED.show();
}

// Match-end rainbow victory sweep.
inline void victory_sweep(uint16_t duration_ms) {
  const int steps = 32;
  const int step_ms = duration_ms / steps;
  for (int s = 0; s < steps; ++s) {
    for (int i = 0; i < SP_NUM_LEDS; ++i) {
      _leds[i] = CHSV(((i * 16) + (s * 8)) & 0xFF, 255, 255);
    }
    FastLED.show();
    delay(step_ms);
  }
  clear();
}

}  // namespace sp_led
