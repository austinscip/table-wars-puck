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

inline bool begin() {
  Wire.begin(SP_PIN_I2C_SDA, SP_PIN_I2C_SCL);
  if (!_mpu.begin()) {
    _ready = false;
    return false;
  }
  _mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
  _mpu.setGyroRange(MPU6050_RANGE_250_DEG);
  _mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  _ready = true;
  return true;
}

inline bool _read(sensors_event_t& a) {
  if (!_ready) return false;
  sensors_event_t g, t;
  _mpu.getEvent(&a, &g, &t);
  return true;
}

// Returns at most one tilt-direction edge per call. Re-armed when the
// puck returns to within ±2.0 m/s^2 on the Y axis.
inline SpTiltEvent poll_tilt() {
  sensors_event_t a;
  if (!_read(a)) return SpTiltEvent::NONE;

  const float ay = a.acceleration.y;  // m/s^2
  const float REARM = 2.0f;
  const float FIRE = 4.0f;  // ~0.4g

  if (ay > FIRE && _tilt_up_armed) {
    _tilt_up_armed = false;
    return SpTiltEvent::UP;
  }
  if (ay < -FIRE && _tilt_down_armed) {
    _tilt_down_armed = false;
    return SpTiltEvent::DOWN;
  }
  if (fabsf(ay) < REARM) {
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
