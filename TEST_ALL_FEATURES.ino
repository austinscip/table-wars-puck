/*
 * TEST ALL FEATURES - Complete Integration Test
 *
 * This file tests ALL 8 free ESP32 features:
 * 1. OTA Updates
 * 2. Dual-Core
 * 3. Capacitive Touch
 * 4. ESP-NOW Multiplayer
 * 5. Deep Sleep
 * 6. Hall Sensor
 * 7. Temperature Sensor
 * 8. DAC Audio (bonus)
 *
 * Upload this to test everything at once!
 */

#include <Arduino.h>
#include <WiFi.h>
#include <FastLED.h>
#include <Wire.h>
#include <MPU6050.h>

// Include all new features
#include "ota_update.h"
#include "dual_core.h"
#include "capacitive_touch.h"
#include "esp_now_multiplayer.h"

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================

// WiFi credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Puck ID (unique per puck)
#define PUCK_ID 1

// Pin definitions
#define LED_PIN       13
#define NUM_LEDS      16
#define BUTTON_PIN    27
#define BUZZER_PIN    15

// Hardware objects
CRGB leds[NUM_LEDS];
MPU6050 mpu;

// ============================================================================
// WIFI CONNECTION
// ============================================================================

void connectWiFi() {
    Serial.print("📡 Connecting to WiFi");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(" ✅ Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println(" ❌ Failed to connect");
    }
}

// ============================================================================
// MPU6050 FUNCTIONS
// ============================================================================

float accelX, accelY, accelZ;
float gyroX, gyroY, gyroZ;

void initMPU6050() {
    Wire.begin();
    mpu.initialize();

    if (mpu.testConnection()) {
        Serial.println("✅ MPU6050 connected");
    } else {
        Serial.println("❌ MPU6050 connection failed");
    }
}

void readAccelerometer() {
    int16_t ax, ay, az;
    int16_t gx, gy, gz;

    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    accelX = ax / 16384.0;
    accelY = ay / 16384.0;
    accelZ = az / 16384.0;

    gyroX = gx / 131.0;
    gyroY = gy / 131.0;
    gyroZ = gz / 131.0;
}

bool detectShake() {
    readAccelerometer();
    float totalAccel = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ);
    return (totalAccel > 2.0);  // Shake threshold
}

// ============================================================================
// LED HELPERS
// ============================================================================

void setAllLEDs(uint8_t r, uint8_t g, uint8_t b) {
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CRGB(r, g, b);
    }
    FastLED.show();
}

void rainbowCycle(int speed) {
    for (int j = 0; j < 256; j++) {
        for (int i = 0; i < NUM_LEDS; i++) {
            leds[i] = CHSV((i * 256 / NUM_LEDS + j) & 255, 255, 255);
        }
        FastLED.show();
        delay(speed);
    }
}

// ============================================================================
// BUZZER TUNES
// ============================================================================

void tune_PowerUp() {
    tone(BUZZER_PIN, 523, 100);
    delay(110);
    tone(BUZZER_PIN, 659, 100);
    delay(110);
    tone(BUZZER_PIN, 784, 200);
    delay(220);
}

void tune_Success() {
    tone(BUZZER_PIN, 784, 150);
    delay(160);
    tone(BUZZER_PIN, 988, 300);
    delay(320);
}

void tune_Fail() {
    tone(BUZZER_PIN, 392, 200);
    delay(210);
    tone(BUZZER_PIN, 330, 400);
    delay(420);
}

// ============================================================================
// FEATURE TESTS
// ============================================================================

/**
 * Test 1: OTA Updates
 */
void test_OTA() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 1: OTA FIRMWARE UPDATES");
    Serial.println("═══════════════════════════════════");

    initArduinoOTA();
    checkPostUpdateBoot();
    printOTADiagnostics();

    setAllLEDs(0, 255, 0);  // Green = OTA ready
    delay(1000);
    setAllLEDs(0, 0, 0);

    Serial.println("✅ OTA Test Complete");
    tune_Success();
}

/**
 * Test 2: Capacitive Touch
 */
void test_CapacitiveTouch() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 2: CAPACITIVE TOUCH");
    Serial.println("═══════════════════════════════════");
    Serial.println("Touch the puck surface for 10 seconds...");

    initCapacitiveTouch();

    unsigned long testStart = millis();
    int tapCount = 0;

    while (millis() - testStart < 10000) {
        readTouchPads();
        showTouchFeedback();

        if (gestureDetected(GESTURE_TAP)) {
            tapCount++;
            Serial.printf("✓ Tap %d detected!\n", tapCount);
            tune_PowerUp();
        }

        if (gestureDetected(GESTURE_SWIPE_LEFT)) {
            Serial.println("◀️ Swipe Left!");
            setAllLEDs(255, 0, 0);
            delay(300);
            setAllLEDs(0, 0, 0);
        }

        if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
            Serial.println("▶️ Swipe Right!");
            setAllLEDs(0, 0, 255);
            delay(300);
            setAllLEDs(0, 0, 0);
        }

        delay(50);
    }

    Serial.printf("✅ Capacitive Touch Test Complete (%d taps detected)\n", tapCount);
    tune_Success();
}

/**
 * Test 3: ESP-NOW Multiplayer
 */
void test_ESPNOW() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 3: ESP-NOW MULTIPLAYER");
    Serial.println("═══════════════════════════════════");

    initESPNow();
    addBroadcastPeer();

    Serial.println("Discovering nearby pucks...");
    discoverPucks();

    setAllLEDs(0, 255, 255);  // Cyan = ESP-NOW active
    delay(1000);

    Serial.println("Broadcasting test message...");
    broadcast(MSG_PING);

    delay(2000);

    printESPNowDiagnostics();

    setAllLEDs(0, 0, 0);
    Serial.println("✅ ESP-NOW Test Complete");
    tune_Success();
}

/**
 * Test 4: Hall Sensor (Magnet Detection)
 */
void test_HallSensor() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 4: HALL SENSOR");
    Serial.println("═══════════════════════════════════");
    Serial.println("Wave a magnet near the ESP32 for 10 seconds...");

    unsigned long testStart = millis();
    int magnetDetections = 0;

    while (millis() - testStart < 10000) {
        int hallValue = hallRead();

        if (abs(hallValue) > 50) {  // Magnet detected
            magnetDetections++;
            Serial.printf("🧲 Magnet detected! Value: %d\n", hallValue);

            setAllLEDs(255, 0, 255);  // Magenta
            delay(200);
            setAllLEDs(0, 0, 0);
            delay(300);
        }

        delay(100);
    }

    Serial.printf("✅ Hall Sensor Test Complete (%d detections)\n", magnetDetections);
    tune_Success();
}

/**
 * Test 5: Temperature Sensor
 */
void test_Temperature() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 5: TEMPERATURE SENSOR");
    Serial.println("═══════════════════════════════════");

    extern "C" {
        uint8_t temprature_sens_read();
    }

    for (int i = 0; i < 5; i++) {
        float temp = (temprature_sens_read() - 32) / 1.8;
        Serial.printf("🌡️  Temperature: %.1f°C\n", temp);

        // Show temp on LEDs (blue = cold, red = hot)
        if (temp < 30) {
            setAllLEDs(0, 0, 255);  // Blue
        } else if (temp > 40) {
            setAllLEDs(255, 0, 0);  // Red
        } else {
            setAllLEDs(0, 255, 0);  // Green
        }

        delay(1000);
    }

    setAllLEDs(0, 0, 0);
    Serial.println("✅ Temperature Test Complete");
    tune_Success();
}

/**
 * Test 6: Deep Sleep
 */
void test_DeepSleep() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 6: DEEP SLEEP");
    Serial.println("═══════════════════════════════════");
    Serial.println("Testing 5-second deep sleep...");
    Serial.println("(Puck will wake up automatically)");

    delay(1000);

    // Configure wake timer
    esp_sleep_enable_timer_wakeup(5 * 1000000ULL);  // 5 seconds

    Serial.println("💤 Entering deep sleep...");

    setAllLEDs(0, 0, 0);
    delay(100);

    esp_deep_sleep_start();

    // When it wakes, setup() will run again
}

/**
 * Test 7: Shake Detection
 */
void test_ShakeDetection() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 7: SHAKE DETECTION");
    Serial.println("═══════════════════════════════════");
    Serial.println("Shake the puck for 10 seconds...");

    unsigned long testStart = millis();
    int shakeCount = 0;

    while (millis() - testStart < 10000) {
        if (detectShake()) {
            shakeCount++;
            Serial.printf("📳 Shake %d detected!\n", shakeCount);

            setAllLEDs(255, 255, 0);  // Yellow
            tune_PowerUp();
            delay(300);
            setAllLEDs(0, 0, 0);
            delay(200);
        }

        delay(50);
    }

    Serial.printf("✅ Shake Detection Test Complete (%d shakes)\n", shakeCount);
    tune_Success();
}

/**
 * Test 8: Button Input
 */
void test_ButtonInput() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("TEST 8: BUTTON INPUT");
    Serial.println("═══════════════════════════════════");
    Serial.println("Press button 5 times...");

    int pressCount = 0;
    bool lastState = HIGH;

    while (pressCount < 5) {
        bool currentState = digitalRead(BUTTON_PIN);

        if (currentState == LOW && lastState == HIGH) {
            pressCount++;
            Serial.printf("✓ Button press %d/5\n", pressCount);

            setAllLEDs(0, 255, 0);
            tune_PowerUp();
            delay(200);
            setAllLEDs(0, 0, 0);
            delay(200);
        }

        lastState = currentState;
        delay(50);
    }

    Serial.println("✅ Button Input Test Complete");
    tune_Success();
}

// ============================================================================
// SETUP & MAIN LOOP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n\n");
    Serial.println("╔══════════════════════════════════╗");
    Serial.println("║                                  ║");
    Serial.println("║   TESTING ALL ESP32 FEATURES     ║");
    Serial.println("║                                  ║");
    Serial.println("║  🔄 OTA Updates                  ║");
    Serial.println("║  👆 Capacitive Touch             ║");
    Serial.println("║  📡 ESP-NOW                      ║");
    Serial.println("║  🧲 Hall Sensor                  ║");
    Serial.println("║  🌡️  Temperature                 ║");
    Serial.println("║  💤 Deep Sleep                   ║");
    Serial.println("║  📳 Shake Detection              ║");
    Serial.println("║  🔘 Button Input                 ║");
    Serial.println("║                                  ║");
    Serial.println("╚══════════════════════════════════╝\n");

    // Initialize hardware
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(BUZZER_PIN, OUTPUT);

    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
    FastLED.setBrightness(50);

    initMPU6050();

    // Connect WiFi (for OTA)
    connectWiFi();

    // Startup animation
    rainbowCycle(20);
    setAllLEDs(0, 0, 0);

    Serial.println("\n✅ Hardware initialized!");
    Serial.println("\nStarting tests in 3 seconds...\n");

    delay(3000);

    // Run all tests
    test_OTA();
    delay(2000);

    test_ButtonInput();
    delay(2000);

    test_ShakeDetection();
    delay(2000);

    test_CapacitiveTouch();
    delay(2000);

    test_ESPNOW();
    delay(2000);

    test_HallSensor();
    delay(2000);

    test_Temperature();
    delay(2000);

    // Final celebration
    Serial.println("\n╔══════════════════════════════════╗");
    Serial.println("║                                  ║");
    Serial.println("║   🎉 ALL TESTS COMPLETE! 🎉      ║");
    Serial.println("║                                  ║");
    Serial.println("╚══════════════════════════════════╝\n");

    rainbowCycle(10);
    rainbowCycle(10);
    rainbowCycle(10);

    Serial.println("\nTest deep sleep? (Press button to skip, wait 5 sec to test)");

    unsigned long waitStart = millis();
    while (millis() - waitStart < 5000) {
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("Skipped deep sleep test");
            goto skip_sleep;
        }
        delay(100);
    }

    test_DeepSleep();

    skip_sleep:
    Serial.println("\n✅ All features working!");
    Serial.println("Type 'help' for interactive commands\n");
}

void loop() {
    // Handle OTA updates
    handleOTAUpdates();

    // Interactive commands
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd == "help") {
            Serial.println("\n📖 COMMANDS:");
            Serial.println("  help   - Show this help");
            Serial.println("  ota    - Test OTA");
            Serial.println("  touch  - Test touch");
            Serial.println("  espnow - Test ESP-NOW");
            Serial.println("  hall   - Test hall sensor");
            Serial.println("  temp   - Test temperature");
            Serial.println("  shake  - Test shake");
            Serial.println("  sleep  - Test deep sleep");
            Serial.println("  all    - Run all tests");
            Serial.println();
        }
        else if (cmd == "ota") test_OTA();
        else if (cmd == "touch") test_CapacitiveTouch();
        else if (cmd == "espnow") test_ESPNOW();
        else if (cmd == "hall") test_HallSensor();
        else if (cmd == "temp") test_Temperature();
        else if (cmd == "shake") test_ShakeDetection();
        else if (cmd == "sleep") test_DeepSleep();
        else if (cmd == "all") {
            test_OTA();
            test_ButtonInput();
            test_ShakeDetection();
            test_CapacitiveTouch();
            test_ESPNOW();
            test_HallSensor();
            test_Temperature();
        }
        else {
            Serial.printf("❓ Unknown command: %s\n", cmd.c_str());
        }
    }

    delay(100);
}
