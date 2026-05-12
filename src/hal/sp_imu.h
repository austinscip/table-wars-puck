// Speed Pyramid v1 — IMU HAL (MPU-6050).
//
// Exposes two event streams:
//
// 1. Discrete tilt-up / tilt-down events for digit dialing. Triggered
//    when the puck is tilted past ±0.4g on the Y axis (forward/back)
//    and re-armed only after the puck returns near level. Suitable for
//    "increment digit one step at a time" UX.
//
// 2. Continuous quadrant readout (A/B/C/D) for in-game tilt-aim. The
//    LED ring's named quadrants map to the dominant tilt direction.

#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "sp_pins.h"

enum class SpTiltEvent : uint8_t {
  NONE,
  UP,
  DOWN,
};

enum class SpQuadrant : uint8_t {
  CENTER,    // tilt magnitude below deadzone
  UP,        // A
  RIGHT,     // B
  DOWN,      // C
  LEFT,      // D
};

namespace sp_imu {

inline Adafruit_MPU6050 _mpu;
inline bool _ready = false;

// Latched flags so a sustained tilt emits exactly one event until
// the puck returns near level.
inline bool _tilt_up_armed = true;
inline bool _tilt_down_armed = true;

// Cooldown after any tilt fires. Prevents the wobble-back from
// firing the opposite direction.
inline uint32_t _tilt_last_fired_ms = 0;
constexpr uint32_t kTiltCooldownMs = 350;

// Manually clock the I2C bus to release any slave that's holding SDA
// low (a wedged bus from a previous bad transaction will look like
// "MPU not found" until this happens). Run BEFORE Wire.begin().
inline void _i2c_bus_recovery() {
  pinMode(SP_PIN_I2C_SDA, INPUT_PULLUP);
  pinMode(SP_PIN_I2C_SCL, OUTPUT_OPEN_DRAIN);
  digitalWrite(SP_PIN_I2C_SCL, HIGH);
  delayMicroseconds(10);
  // Pulse SCL until SDA goes high (slave released) or 16 cycles done.
  for (int i = 0; i < 16; ++i) {
    if (digitalRead(SP_PIN_I2C_SDA) == HIGH) break;
    digitalWrite(SP_PIN_I2C_SCL, LOW);
    delayMicroseconds(5);
    digitalWrite(SP_PIN_I2C_SCL, HIGH);
    delayMicroseconds(5);
  }
  // Generate a STOP condition: SDA low -> high while SCL high.
  pinMode(SP_PIN_I2C_SDA, OUTPUT_OPEN_DRAIN);
  digitalWrite(SP_PIN_I2C_SDA, LOW);
  delayMicroseconds(5);
  digitalWrite(SP_PIN_I2C_SDA, HIGH);
  delayMicroseconds(5);
}

inline bool begin() {
  // Bus recovery first — clears wedged-MPU state from a previous boot.
  _i2c_bus_recovery();

  Wire.begin(SP_PIN_I2C_SDA, SP_PIN_I2C_SCL);
  Wire.setClock(100000);  // 100kHz — most forgiving for marginal pull-ups

  // Try up to 3 times with a short delay between attempts. Some
  // MPU-6050 modules take a moment to wake up after the bus recovery.
  bool ok = false;
  for (int attempt = 1; attempt <= 3; ++attempt) {
    if (_mpu.begin()) { ok = true; break; }
    Serial.printf("[IMU] begin attempt %d failed, retrying...\n", attempt);
    delay(200);
  }

  if (!ok) {
    _ready = false;
    Serial.println("[IMU] MPU6050 NOT FOUND after retries — tilt input will be dead");
    return false;
  }
  _mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
  _mpu.setGyroRange(MPU6050_RANGE_250_DEG);
  _mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  _ready = true;
  Serial.println("[IMU] MPU6050 ready");
  return true;
}

inline bool _read(sensors_event_t& a) {
  if (!_ready) return false;
  sensors_event_t g, t;
  _mpu.getEvent(&a, &g, &t);
  return true;
}

// Returns at most one tilt-direction edge per call. To re-arm, the
// puck must return to nearly level (within RETURN_NEAR_ZERO) AND
// at least kTiltCooldownMs must have passed since the last fire.
// This prevents wobble-back from firing the opposite direction
// right after a real tilt.
inline SpTiltEvent poll_tilt() {
  sensors_event_t a;
  if (!_read(a)) return SpTiltEvent::NONE;

  const float ay = a.acceleration.y;  // m/s^2
  const float FIRE = 3.0f;             // ~0.3g — softer trigger
  const float RETURN_NEAR_ZERO = 1.5f;
  const uint32_t now = millis();

  // Periodic diagnostic so we can see what the IMU is reading even
  // when no tilt threshold has crossed.
  static uint32_t _last_ay_log = 0;
  if (now - _last_ay_log > 1000) {
    _last_ay_log = now;
    Serial.printf("[IMU] ay=%.2f up_armed=%d down_armed=%d\n",
                  ay, (int)_tilt_up_armed, (int)_tilt_down_armed);
  }

  // Cooldown blocks ALL events for the first 350ms after a fire so
  // a real tilt-up doesn't immediately register as tilt-down on the
  // recoil.
  if (now - _tilt_last_fired_ms < kTiltCooldownMs) {
    return SpTiltEvent::NONE;
  }

  if (ay > FIRE && _tilt_up_armed) {
    _tilt_up_armed = false;
    _tilt_last_fired_ms = now;
    Serial.printf("[TILT] UP (ay=%.2f)\n", ay);
    return SpTiltEvent::UP;
  }
  if (ay < -FIRE && _tilt_down_armed) {
    _tilt_down_armed = false;
    _tilt_last_fired_ms = now;
    Serial.printf("[TILT] DOWN (ay=%.2f)\n", ay);
    return SpTiltEvent::DOWN;
  }
  if (fabsf(ay) < RETURN_NEAR_ZERO) {
    _tilt_up_armed = true;
    _tilt_down_armed = true;
  }
  return SpTiltEvent::NONE;
}

// Continuous quadrant for in-game tilt-aim. Returns the dominant tilt
// direction (largest |axis| among X/Y), or CENTER if within deadzone.
inline SpQuadrant read_quadrant() {
  sensors_event_t a;
  if (!_read(a)) return SpQuadrant::CENTER;
  const float DEAD = 1.5f;  // ~0.15g
  const float ax = a.acceleration.x;
  const float ay = a.acceleration.y;
  if (fabsf(ax) < DEAD && fabsf(ay) < DEAD) return SpQuadrant::CENTER;
  if (fabsf(ay) >= fabsf(ax)) {
    return ay > 0 ? SpQuadrant::UP : SpQuadrant::DOWN;
  } else {
    return ax > 0 ? SpQuadrant::RIGHT : SpQuadrant::LEFT;
  }
}

}  // namespace sp_imu
