# Firmware Agent Instructions

## Overview

This directory contains ESP32 firmware for Table Wars pucks. The firmware handles:
- Motion sensing (accelerometer/gyroscope)
- LED animations
- Audio feedback (buzzer)
- Haptic feedback (vibration motor)
- Wireless communication (WiFi, ESP-NOW)

## Architecture

```
main.cpp                    # Entry point, tune library
main_complete.h             # Master firmware (all 56 games)
main_tablewars.h            # Original 51 games (~6000 lines)
main_tablewars_v2_UPGRADED.h # Enhanced version

Feature Modules:
├── ota_update.h            # OTA firmware updates
├── dual_core.h             # FreeRTOS dual-core
├── capacitive_touch.h      # Touch sensor input
├── esp_now_multiplayer.h   # Puck-to-puck communication
├── tv_games.h              # Screen-centric games
└── archive/                # Legacy implementations
```

## Hardware Abstraction

### MPU6050 (Motion Sensor)

```cpp
#include <Adafruit_MPU6050.h>
Adafruit_MPU6050 mpu;

// Read accelerometer (m/s^2)
sensors_event_t a, g, temp;
mpu.getEvent(&a, &g, &temp);
float accel_x = a.acceleration.x;  // -10 to +10
float accel_y = a.acceleration.y;
float accel_z = a.acceleration.z;

// Read gyroscope (rad/s) - for spin detection
float gyro_z = g.gyro.z;  // Use for spin velocity
```

### LED Ring (WS2812B)

```cpp
#include <FastLED.h>
#define NUM_LEDS 16
#define LED_PIN 23
CRGB leds[NUM_LEDS];

// Set color
fill_solid(leds, NUM_LEDS, CRGB::Red);
FastLED.show();

// Rainbow effect
fill_rainbow(leds, NUM_LEDS, hue, 255/NUM_LEDS);
FastLED.show();
```

### Buzzer

```cpp
#define BUZZER_PIN 15
tone(BUZZER_PIN, frequency, duration);
noTone(BUZZER_PIN);
```

### Vibration Motor

```cpp
#define VIBRATION_PIN XX  // Define based on wiring
digitalWrite(VIBRATION_PIN, HIGH);
delay(100);
digitalWrite(VIBRATION_PIN, LOW);
```

## Game Implementation Pattern

```cpp
void game_NewGame() {
    // 1. Initialize game state
    int score = 0;
    unsigned long gameStart = millis();

    // 2. Main game loop
    while (millis() - gameStart < GAME_DURATION) {
        // Read sensors
        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);

        // Detect shake
        float magnitude = sqrt(a.acceleration.x * a.acceleration.x +
                              a.acceleration.y * a.acceleration.y +
                              a.acceleration.z * a.acceleration.z);
        bool isShaking = magnitude > SHAKE_THRESHOLD;

        // Update LEDs based on state
        if (isShaking) {
            fill_solid(leds, NUM_LEDS, CRGB::Green);
        } else {
            fill_solid(leds, NUM_LEDS, CRGB::Blue);
        }
        FastLED.show();

        delay(10);  // ~100Hz update rate
    }

    // 3. Game over - report score
    playVictoryTune();
    sendScoreToServer(score);
}
```

## Sensor Data Patterns

### Shake Detection

```cpp
#define SHAKE_THRESHOLD 15.0  // m/s^2
float magnitude = sqrt(ax*ax + ay*ay + az*az);
bool isShaking = magnitude > SHAKE_THRESHOLD;
```

### Spin Detection (Gyroscope Z-axis)

```cpp
// Convert rad/s to deg/s
float spin_velocity = g.gyro.z * 57.2958;  // rad/s to deg/s

// Classify spin intensity
if (abs(spin_velocity) < 100) {
    // Light spin
} else if (abs(spin_velocity) < 300) {
    // Medium spin
} else {
    // Hard spin
}
```

### Tilt Detection

```cpp
// Tilt angles from accelerometer
float tilt_x = atan2(a.acceleration.y, a.acceleration.z) * 180 / PI;
float tilt_y = atan2(a.acceleration.x, a.acceleration.z) * 180 / PI;
```

### Tap Detection

```cpp
// Simple tap: high acceleration spike followed by stillness
static float lastMag = 0;
float deltaMag = abs(magnitude - lastMag);
lastMag = magnitude;
bool isTap = deltaMag > TAP_THRESHOLD && previouslyStill;
```

## ESP-NOW Communication

```cpp
// See esp_now_multiplayer.h for full implementation
typedef struct {
    uint8_t puck_id;
    uint8_t message_type;
    float data[4];  // Flexible data payload
} esp_now_packet_t;

// Send to all peers
esp_now_send(broadcastAddress, (uint8_t *)&packet, sizeof(packet));
```

## Memory Constraints

- **Total RAM**: 320KB (use wisely!)
- **Avoid**: Large static arrays, string concatenation in loops
- **Prefer**: Stack allocation, fixed-size buffers
- **Watch**: FastLED + WiFi memory contention

## Key Gotchas

1. **FastLED.show() blocking**: Keep LED updates sparse during WiFi operations
2. **MPU6050 warmup**: Allow 500ms for sensor stabilization after power-on
3. **ESP-NOW channel**: Must match WiFi channel if both active
4. **OTA partition size**: Keep firmware under 1.3MB for OTA updates
5. **Deep sleep**: GPIO state is lost - reconfigure pins on wake

## Sprint 0 Nano-Stories (Firmware)

### Sprint 0A: MPU6050 Initialization
Stories US-001a-1 through US-001d-2 add:
1. Adafruit libraries to platformio.ini
2. #include statements to main.cpp
3. mpu.begin() initialization in setup()
4. Sensor config (8G accel, 500 deg/s gyro, 21Hz filter)
5. sensors_event_t reading in loop()
6. Computed values: shake_intensity, tilt_x, tilt_y, spin_speed

### Sprint 0B: ESP-NOW Message Extension
Stories US-002a-1 through US-002d-2 add:
1. New fields to PuckMessage struct (tilt_x, tilt_y, shake_intensity, spin_speed, gyro_z)
2. Assignment of computed values to msg before esp_now_send()
3. Rate limiting (200ms interval unless shake_detected)
4. Debug serial prints for verification

### Verification Commands
```bash
# Build firmware (required after each story)
pio run

# Upload to puck (if hardware connected)
pio run -e puck1 -t upload

# Monitor serial output
pio device monitor --baud 115200
```

### PuckMessage Struct (After Sprint 0B)
```cpp
typedef struct PuckMessage {
    uint8_t puck_id;
    float tilt_x;
    float tilt_y;
    float shake_intensity;
    float spin_speed;
    float gyro_z;
    bool shake_detected;
} PuckMessage;
```
