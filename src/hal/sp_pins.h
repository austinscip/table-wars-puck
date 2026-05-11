// Speed Pyramid v1 — pin map.
//
// Defaults to Rev A pins (matches the existing repo firmware). Define
// PUCK_REV_B before including to switch to Rev B (see memory/CONTEXT.md
// for the Rev B pin map). This header is the single source of truth for
// pins inside the Speed Pyramid firmware; no other file in src/games/ or
// src/hal/sp_*.h should hardcode GPIO numbers.

#pragma once

#if defined(PUCK_REV_B)
  #define SP_PIN_BUTTON  33
  #define SP_PIN_BUZZER  32
  #define SP_PIN_LED      5
  #define SP_PIN_MOTOR    4
  #define SP_PIN_I2C_SDA 21
  #define SP_PIN_I2C_SCL 22
#else  // Rev A (default)
  #define SP_PIN_BUTTON  27
  #define SP_PIN_BUZZER  15
  #define SP_PIN_LED     23
  #define SP_PIN_MOTOR   13
  #define SP_PIN_I2C_SDA 21
  #define SP_PIN_I2C_SCL 22
#endif

#define SP_NUM_LEDS 16
