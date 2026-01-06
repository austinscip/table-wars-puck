/**
 * camera_module.h
 *
 * Camera Module Interface for AR Games & Gesture Recognition
 * ESP32-CAM integration for advanced gameplay features
 *
 * Recommended Hardware:
 *   - ESP32-CAM module ($6) - includes OV2640 2MP camera
 *   - Or use external camera via I2S/UART:
 *     * OV7670 VGA camera ($3)
 *     * OV5640 5MP camera ($8)
 *
 * ESP32-CAM Wiring (if using separate ESP32):
 *   Main ESP32 ↔ ESP32-CAM via UART:
 *     GPIO 16 (RX) → GPIO 1 (TX)
 *     GPIO 17 (TX) → GPIO 3 (RX)
 *     GND → GND
 *
 * Features:
 *   1. AR Games:
 *      - Point puck at targets in real world
 *      - Scan QR codes for power-ups
 *      - "Puck Hunt" - find hidden objects
 *      - Gesture-based controls
 *
 *   2. Computer Vision:
 *      - Face detection (multiplayer ID)
 *      - Hand gesture recognition
 *      - Object tracking
 *      - Color detection
 *      - Motion detection
 *
 *   3. Social Features:
 *      - Take victory selfies
 *      - Scan player badges
 *      - Team photo after game
 *      - Live streaming to TV
 *
 *   4. Enhanced Gameplay:
 *      - Aim assist using camera
 *      - Environmental interaction
 *      - Physical object scanning
 *      - Augmented reality overlays
 *
 * Power Consumption:
 *   - Camera active: +150-200 mA
 *   - Solution: Only activate camera for AR games
 *   - Deep sleep camera when not in use
 *
 * Dependencies:
 *   - esp32-camera library (Arduino Library Manager)
 *   - ArduCAM (for external cameras)
 */

#ifndef CAMERA_MODULE_H
#define CAMERA_MODULE_H

#include <Arduino.h>

#ifdef CAMERA_MODEL_AI_THINKER
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27

  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22
#endif

// ============================================================================
// CAMERA CONFIGURATION
// ============================================================================

// Image settings
#define CAMERA_WIDTH      640
#define CAMERA_HEIGHT     480
#define CAMERA_JPEG_QUALITY 10  // 0-63 (lower = higher quality)

bool cameraInitialized = false;
bool cameraActive = false;

// ============================================================================
// SERIAL CAMERA COMMUNICATION (for external ESP32-CAM)
// ============================================================================

#define CAMERA_SERIAL_RX  16
#define CAMERA_SERIAL_TX  17
#define CAMERA_BAUD_RATE  115200

HardwareSerial CameraSerial(2);  // UART2

/**
 * Initialize serial communication with ESP32-CAM module
 */
bool initCameraSerial() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📷 INITIALIZING CAMERA MODULE");
    Serial.println("═══════════════════════════════════");

    CameraSerial.begin(CAMERA_BAUD_RATE, SERIAL_8N1, CAMERA_SERIAL_RX, CAMERA_SERIAL_TX);

    Serial.println("✅ Camera serial initialized");
    Serial.printf("   RX: GPIO %d\n", CAMERA_SERIAL_RX);
    Serial.printf("   TX: GPIO %d\n", CAMERA_SERIAL_TX);
    Serial.printf("   Baud: %d\n", CAMERA_BAUD_RATE);

    // Test communication
    delay(1000);
    CameraSerial.println("CAM_PING");
    delay(100);

    if (CameraSerial.available()) {
        String response = CameraSerial.readStringUntil('\n');
        if (response.indexOf("PONG") >= 0) {
            cameraInitialized = true;
            Serial.println("✅ Camera module responded");
            Serial.println("═══════════════════════════════════\n");
            return true;
        }
    }

    Serial.println("⚠️ No response from camera module");
    Serial.println("   Make sure ESP32-CAM is powered and connected");
    Serial.println("═══════════════════════════════════\n");
    return false;
}

/**
 * Power on camera
 */
void cameraOn() {
    if (!cameraInitialized) {
        Serial.println("⚠️ Camera not initialized");
        return;
    }

    CameraSerial.println("CAM_ON");
    cameraActive = true;
    Serial.println("📷 Camera powered ON");
}

/**
 * Power off camera (save battery)
 */
void cameraOff() {
    if (!cameraInitialized) return;

    CameraSerial.println("CAM_OFF");
    cameraActive = false;
    Serial.println("📷 Camera powered OFF");
}

// ============================================================================
// IMAGE CAPTURE
// ============================================================================

/**
 * Capture photo and save to SD card
 */
bool capturePhoto(const char* filename) {
    if (!cameraActive) {
        Serial.println("⚠️ Camera not active");
        return false;
    }

    Serial.printf("📸 Capturing photo: %s\n", filename);

    // Request photo from ESP32-CAM
    CameraSerial.printf("CAM_CAPTURE:%s\n", filename);

    // Wait for confirmation
    unsigned long timeout = millis();
    while (millis() - timeout < 5000) {
        if (CameraSerial.available()) {
            String response = CameraSerial.readStringUntil('\n');
            if (response.indexOf("CAPTURE_OK") >= 0) {
                Serial.println("✅ Photo captured");
                return true;
            } else if (response.indexOf("CAPTURE_FAIL") >= 0) {
                Serial.println("❌ Capture failed");
                return false;
            }
        }
        delay(10);
    }

    Serial.println("❌ Camera timeout");
    return false;
}

/**
 * Take victory selfie after winning a game
 */
void takeVictorySelfie(int gameId, const char* playerName) {
    Serial.println("\n📸 VICTORY SELFIE!");
    Serial.println("Smile for the camera!");

    // LED countdown
    for (int i = 3; i > 0; i--) {
        Serial.printf("%d...\n", i);
        setAllLEDs(255, 255, 0);  // Yellow
        delay(500);
        setAllLEDs(0, 0, 0);
        delay(500);
    }

    // Flash on capture
    setAllLEDs(255, 255, 255);  // White flash

    char filename[64];
    sprintf(filename, "/photos/victory_game%d_%s.jpg", gameId, playerName);

    capturePhoto(filename);

    setAllLEDs(0, 0, 0);

    Serial.println("📤 Upload photo to server for leaderboard!");
}

// ============================================================================
// QR CODE SCANNING
// ============================================================================

/**
 * Scan QR code from camera
 */
String scanQRCode() {
    if (!cameraActive) {
        Serial.println("⚠️ Camera not active");
        return "";
    }

    Serial.println("📷 Scanning for QR code...");

    CameraSerial.println("CAM_QR_SCAN");

    unsigned long timeout = millis();
    while (millis() - timeout < 10000) {
        if (CameraSerial.available()) {
            String response = CameraSerial.readStringUntil('\n');

            if (response.startsWith("QR:")) {
                String qrData = response.substring(3);
                Serial.printf("✅ QR Code detected: %s\n", qrData.c_str());
                return qrData;
            } else if (response.indexOf("QR_NOT_FOUND") >= 0) {
                Serial.println("❌ No QR code found");
                return "";
            }
        }
        delay(100);

        // Visual feedback
        static int led = 0;
        leds[led] = CRGB(0, 0, 255);  // Blue scanning animation
        FastLED.show();
        leds[led] = CRGB(0, 0, 0);
        led = (led + 1) % NUM_LEDS;
    }

    Serial.println("⏱️ QR scan timeout");
    return "";
}

/**
 * Game: QR Code Scavenger Hunt
 * Players scan hidden QR codes around the bar for points
 */
void qrCodeScavengerHunt() {
    Serial.println("\n🔍 QR CODE SCAVENGER HUNT");
    Serial.println("Find and scan hidden QR codes!");

    cameraOn();

    int score = 0;
    int codesFound = 0;
    const int totalCodes = 5;

    String foundCodes[10];  // Track found codes to prevent duplicates

    while (codesFound < totalCodes) {
        Serial.printf("\nCodes found: %d/%d\n", codesFound, totalCodes);
        Serial.println("Point camera at QR code...");

        String qrData = scanQRCode();

        if (qrData != "") {
            // Check if already found
            bool duplicate = false;
            for (int i = 0; i < codesFound; i++) {
                if (foundCodes[i] == qrData) {
                    duplicate = true;
                    break;
                }
            }

            if (!duplicate) {
                foundCodes[codesFound] = qrData;
                codesFound++;

                // Award points
                int points = 100;
                score += points;

                Serial.printf("🎉 NEW CODE FOUND! +%d points\n", points);
                Serial.printf("Total score: %d\n", score);

                // Success animation
                for (int i = 0; i < 3; i++) {
                    setAllLEDs(0, 255, 0);
                    delay(200);
                    setAllLEDs(0, 0, 0);
                    delay(200);
                }
            } else {
                Serial.println("⚠️ Already found this code!");
                setAllLEDs(255, 165, 0);  // Orange
                delay(500);
                setAllLEDs(0, 0, 0);
            }
        }

        delay(1000);
    }

    Serial.println("\n🏆 SCAVENGER HUNT COMPLETE!");
    Serial.printf("Final Score: %d points\n", score);

    cameraOff();
}

// ============================================================================
// GESTURE RECOGNITION
// ============================================================================

/**
 * Detect hand gestures using camera
 */
enum HandGesture {
    GESTURE_NONE_CAM,
    GESTURE_THUMBS_UP,
    GESTURE_THUMBS_DOWN,
    GESTURE_PEACE_SIGN,
    GESTURE_OK_SIGN,
    GESTURE_ROCK_ON,
    GESTURE_FIST
};

HandGesture detectHandGesture() {
    if (!cameraActive) return GESTURE_NONE_CAM;

    CameraSerial.println("CAM_GESTURE");

    unsigned long timeout = millis();
    while (millis() - timeout < 3000) {
        if (CameraSerial.available()) {
            String response = CameraSerial.readStringUntil('\n');

            if (response.indexOf("THUMBS_UP") >= 0) return GESTURE_THUMBS_UP;
            if (response.indexOf("THUMBS_DOWN") >= 0) return GESTURE_THUMBS_DOWN;
            if (response.indexOf("PEACE") >= 0) return GESTURE_PEACE_SIGN;
            if (response.indexOf("OK") >= 0) return GESTURE_OK_SIGN;
            if (response.indexOf("ROCK") >= 0) return GESTURE_ROCK_ON;
            if (response.indexOf("FIST") >= 0) return GESTURE_FIST;
        }
        delay(50);
    }

    return GESTURE_NONE_CAM;
}

/**
 * Game: Gesture Simon Says
 * Camera detects if player makes correct gesture
 */
void gestureSimonSays() {
    Serial.println("\n✋ GESTURE SIMON SAYS");

    cameraOn();

    const char* gestures[] = {"Thumbs Up", "Peace Sign", "OK Sign", "Rock On"};
    HandGesture gestureTargets[] = {GESTURE_THUMBS_UP, GESTURE_PEACE_SIGN, GESTURE_OK_SIGN, GESTURE_ROCK_ON};

    int round = 1;
    int score = 0;

    while (round <= 5) {
        int targetIndex = random(4);

        Serial.printf("\nRound %d\n", round);
        Serial.printf("Show: %s\n", gestures[targetIndex]);

        // Wait for gesture
        unsigned long startTime = millis();
        bool gestureDetected = false;

        while (millis() - startTime < 5000 && !gestureDetected) {
            HandGesture detected = detectHandGesture();

            if (detected == gestureTargets[targetIndex]) {
                Serial.println("✅ CORRECT!");
                score += 100;
                gestureDetected = true;

                setAllLEDs(0, 255, 0);  // Green
                delay(1000);
                setAllLEDs(0, 0, 0);
            } else if (detected != GESTURE_NONE_CAM) {
                Serial.println("❌ WRONG GESTURE!");
                setAllLEDs(255, 0, 0);  // Red
                delay(1000);
                setAllLEDs(0, 0, 0);
                break;
            }

            delay(100);
        }

        if (!gestureDetected) {
            Serial.println("⏱️ TIME'S UP!");
        }

        round++;
    }

    Serial.printf("\n🏆 FINAL SCORE: %d\n", score);

    cameraOff();
}

// ============================================================================
// MOTION DETECTION
// ============================================================================

/**
 * Detect motion in camera view
 */
bool detectMotion() {
    if (!cameraActive) return false;

    CameraSerial.println("CAM_MOTION");

    delay(100);

    if (CameraSerial.available()) {
        String response = CameraSerial.readStringUntil('\n');
        return (response.indexOf("MOTION_DETECTED") >= 0);
    }

    return false;
}

/**
 * Game: Motion Detector
 * Don't move when camera is watching!
 */
void motionDetectorGame() {
    Serial.println("\n👁️ MOTION DETECTOR GAME");
    Serial.println("DON'T MOVE when the red light is on!");

    cameraOn();
    delay(1000);

    int lives = 3;
    int round = 1;

    while (lives > 0 && round <= 5) {
        Serial.printf("\nRound %d - Lives: %d\n", round, lives);

        // Watching phase (red LEDs)
        Serial.println("🔴 DON'T MOVE!");
        setAllLEDs(255, 0, 0);  // Red

        unsigned long watchStart = millis();
        unsigned long watchDuration = 3000 + random(2000);  // 3-5 seconds

        bool caughtMoving = false;

        while (millis() - watchStart < watchDuration) {
            if (detectMotion()) {
                Serial.println("❌ CAUGHT MOVING!");
                lives--;
                caughtMoving = true;

                // Flash red
                for (int i = 0; i < 5; i++) {
                    setAllLEDs(255, 0, 0);
                    delay(100);
                    setAllLEDs(0, 0, 0);
                    delay(100);
                }

                break;
            }
            delay(200);
        }

        if (!caughtMoving) {
            Serial.println("✅ SUCCESS!");
            setAllLEDs(0, 255, 0);  // Green
            delay(1000);
        }

        // Rest phase (green LEDs)
        Serial.println("🟢 You can move now");
        setAllLEDs(0, 255, 0);
        delay(2000);

        setAllLEDs(0, 0, 0);
        round++;
    }

    if (lives > 0) {
        Serial.println("\n🏆 YOU WIN!");
    } else {
        Serial.println("\n💀 GAME OVER!");
    }

    cameraOff();
}

// ============================================================================
// FACE DETECTION (Multiplayer Player ID)
// ============================================================================

/**
 * Detect faces in camera view
 */
int detectFaces() {
    if (!cameraActive) return 0;

    CameraSerial.println("CAM_FACE_COUNT");

    delay(500);

    if (CameraSerial.available()) {
        String response = CameraSerial.readStringUntil('\n');

        if (response.startsWith("FACES:")) {
            int count = response.substring(6).toInt();
            return count;
        }
    }

    return 0;
}

/**
 * Multiplayer: Auto-detect number of players
 */
int detectPlayerCount() {
    Serial.println("\n👥 DETECTING PLAYERS");
    Serial.println("Everyone look at the camera!");

    cameraOn();

    setAllLEDs(255, 255, 0);  // Yellow
    delay(2000);

    int playerCount = detectFaces();

    Serial.printf("✅ Detected %d player(s)\n", playerCount);

    setAllLEDs(0, 0, 0);
    cameraOff();

    return playerCount;
}

// ============================================================================
// AR GAMES
// ============================================================================

/**
 * AR Game: Point & Shoot
 * Point puck at targets in real world (e.g., bar items)
 */
void arPointAndShootGame() {
    Serial.println("\n🎯 AR POINT & SHOOT");
    Serial.println("Point puck at targets to shoot!");

    cameraOn();

    int score = 0;
    int shots = 10;

    const char* targets[] = {"Red Object", "Blue Object", "Face", "Hand"};

    while (shots > 0) {
        int targetIndex = random(4);
        Serial.printf("\nShots remaining: %d\n", shots);
        Serial.printf("TARGET: %s\n", targets[targetIndex]);
        Serial.println("Point puck and press button to shoot!");

        // Wait for button press
        while (digitalRead(BUTTON_PIN) == HIGH) {
            delay(10);
        }

        // Check if camera sees target
        CameraSerial.printf("CAM_DETECT:%s\n", targets[targetIndex]);

        delay(500);

        if (CameraSerial.available()) {
            String response = CameraSerial.readStringUntil('\n');

            if (response.indexOf("DETECTED") >= 0) {
                Serial.println("🎯 HIT!");
                score += 100;

                setAllLEDs(0, 255, 0);  // Green
                delay(500);
            } else {
                Serial.println("❌ MISS!");

                setAllLEDs(255, 0, 0);  // Red
                delay(500);
            }
        }

        setAllLEDs(0, 0, 0);
        shots--;

        // Debounce
        while (digitalRead(BUTTON_PIN) == LOW) {
            delay(10);
        }
    }

    Serial.printf("\n🏆 FINAL SCORE: %d\n", score);

    cameraOff();
}

// ============================================================================
// DIAGNOSTICS
// ============================================================================

/**
 * Print camera diagnostics
 */
void printCameraDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📷 CAMERA MODULE DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");

    Serial.printf("Initialized: %s\n", cameraInitialized ? "Yes" : "No");
    Serial.printf("Active: %s\n", cameraActive ? "Yes" : "No");
    Serial.printf("Resolution: %dx%d\n", CAMERA_WIDTH, CAMERA_HEIGHT);
    Serial.printf("JPEG Quality: %d\n", CAMERA_JPEG_QUALITY);

    if (cameraInitialized) {
        // Test communication
        CameraSerial.println("CAM_STATUS");
        delay(100);

        if (CameraSerial.available()) {
            String response = CameraSerial.readStringUntil('\n');
            Serial.printf("Camera Status: %s\n", response.c_str());
        }
    }

    Serial.println("═══════════════════════════════════\n");
}

/**
 * Test camera module
 */
void testCameraModule() {
    Serial.println("\n📷 CAMERA MODULE TEST\n");

    if (!cameraInitialized) {
        initCameraSerial();
    }

    if (cameraInitialized) {
        cameraOn();

        Serial.println("1. Testing photo capture...");
        capturePhoto("/test_photo.jpg");
        delay(1000);

        Serial.println("2. Testing QR scan...");
        scanQRCode();
        delay(1000);

        Serial.println("3. Testing face detection...");
        int faces = detectFaces();
        Serial.printf("   Faces detected: %d\n", faces);
        delay(1000);

        cameraOff();

        Serial.println("\n✅ Camera test complete\n");
    } else {
        Serial.println("❌ Camera not available\n");
    }
}

#endif // CAMERA_MODULE_H
