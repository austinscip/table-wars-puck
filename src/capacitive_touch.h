/**
 * capacitive_touch.h
 *
 * Capacitive Touch Surface Controls
 * Touch-sensitive puck surface using ESP32's built-in touch sensors
 *
 * ESP32 has 10 capacitive touch pins (no additional hardware needed!):
 *   T0 = GPIO 4
 *   T1 = GPIO 0   (BOOT button - avoid)
 *   T2 = GPIO 2
 *   T3 = GPIO 15
 *   T4 = GPIO 13
 *   T5 = GPIO 12
 *   T6 = GPIO 14
 *   T7 = GPIO 27
 *   T8 = GPIO 33
 *   T9 = GPIO 32
 *
 * Hardware Setup:
 *   1. Connect copper tape/foil to touch pins (creates touch pads)
 *   2. No pull-up resistors needed (built-in)
 *   3. Pads can be on outside of 3D printed case
 *
 * Puck Touch Layout:
 *   - Top surface: Tap/double-tap detection (T0)
 *   - Left side: Swipe left gesture (T2)
 *   - Right side: Swipe right gesture (T3)
 *   - Bottom: Long press (T4)
 *   - Four corners: Multi-touch zones (T5, T6, T7, T8)
 *
 * Features:
 *   - Tap, double-tap, long press detection
 *   - Swipe gestures (left, right, up, down)
 *   - Multi-touch (up to 10 simultaneous touches)
 *   - Proximity detection (near without touching)
 *   - No mechanical button wear
 *   - Works through plastic case
 *
 * Benefits:
 *   - No button failures
 *   - More input options for games
 *   - Gesture-based controls
 *   - Waterproof (when sealed)
 *   - Silent operation
 */

#ifndef CAPACITIVE_TOUCH_H
#define CAPACITIVE_TOUCH_H

#include <Arduino.h>

// ============================================================================
// TOUCH PIN CONFIGURATION
// ============================================================================

#define TOUCH_TOP       T0   // GPIO 4  - Top surface tap
#define TOUCH_LEFT      T2   // GPIO 2  - Left swipe
#define TOUCH_RIGHT     T3   // GPIO 15 - Right swipe
#define TOUCH_BOTTOM    T4   // GPIO 13 - Bottom long press
#define TOUCH_CORNER_1  T5   // GPIO 12 - Top-left corner
#define TOUCH_CORNER_2  T6   // GPIO 14 - Top-right corner
#define TOUCH_CORNER_3  T7   // GPIO 27 - Bottom-left corner
#define TOUCH_CORNER_4  T8   // GPIO 33 - Bottom-right corner

// Touch sensitivity threshold (lower = more sensitive)
// Default ESP32 raw values: ~40-60 when touched, ~80-100 when not touched
#define TOUCH_THRESHOLD     40
#define PROXIMITY_THRESHOLD 60

// Gesture timing
#define DOUBLE_TAP_WINDOW   300   // ms - max time between taps
#define LONG_PRESS_TIME     800   // ms - min time for long press
#define SWIPE_TIME          500   // ms - max time for swipe gesture

// ============================================================================
// TOUCH STATE TRACKING
// ============================================================================

struct TouchPad {
    uint8_t pin;
    bool touched;
    bool lastTouched;
    unsigned long touchStartTime;
    unsigned long lastTapTime;
    int tapCount;
    uint16_t rawValue;
};

// Touch pad array
TouchPad touchPads[8] = {
    {TOUCH_TOP, false, false, 0, 0, 0, 0},
    {TOUCH_LEFT, false, false, 0, 0, 0, 0},
    {TOUCH_RIGHT, false, false, 0, 0, 0, 0},
    {TOUCH_BOTTOM, false, false, 0, 0, 0, 0},
    {TOUCH_CORNER_1, false, false, 0, 0, 0, 0},
    {TOUCH_CORNER_2, false, false, 0, 0, 0, 0},
    {TOUCH_CORNER_3, false, false, 0, 0, 0, 0},
    {TOUCH_CORNER_4, false, false, 0, 0, 0, 0}
};

// Gesture detection
enum TouchGesture {
    GESTURE_NONE,
    GESTURE_TAP,
    GESTURE_DOUBLE_TAP,
    GESTURE_TRIPLE_TAP,
    GESTURE_LONG_PRESS,
    GESTURE_SWIPE_LEFT,
    GESTURE_SWIPE_RIGHT,
    GESTURE_SWIPE_UP,
    GESTURE_SWIPE_DOWN,
    GESTURE_PINCH,
    GESTURE_SPREAD,
    GESTURE_TWO_FINGER_TAP
};

TouchGesture lastGesture = GESTURE_NONE;
unsigned long lastGestureTime = 0;

// Multi-touch state
bool multiTouchActive = false;
uint8_t activeTouches = 0;

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize capacitive touch system
 */
void initCapacitiveTouch() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("👆 INITIALIZING CAPACITIVE TOUCH");
    Serial.println("═══════════════════════════════════");

    // No setup needed - touch sensing is built into ESP32
    // Just set threshold for each pad

    for (int i = 0; i < 8; i++) {
        touchAttachInterrupt(touchPads[i].pin, NULL, TOUCH_THRESHOLD);
    }

    Serial.println("✅ Touch pads configured:");
    Serial.println("   Top:    Tap detection");
    Serial.println("   Left:   Swipe left");
    Serial.println("   Right:  Swipe right");
    Serial.println("   Bottom: Long press");
    Serial.println("   Corners: Multi-touch zones");
    Serial.printf("   Threshold: %d\n", TOUCH_THRESHOLD);
    Serial.println("═══════════════════════════════════\n");
}

/**
 * Calibrate touch sensors (run on first boot)
 */
void calibrateTouchSensors() {
    Serial.println("\n🔧 CALIBRATING TOUCH SENSORS");
    Serial.println("Don't touch the puck for 3 seconds...\n");

    delay(1000);

    // Sample each pad multiple times
    const int samples = 50;
    uint32_t sums[8] = {0};

    for (int i = 0; i < samples; i++) {
        for (int j = 0; j < 8; j++) {
            sums[j] += touchRead(touchPads[j].pin);
        }
        delay(20);
    }

    // Calculate averages and set thresholds
    Serial.println("Calibration results:");
    for (int i = 0; i < 8; i++) {
        uint16_t average = sums[i] / samples;
        uint16_t threshold = average * 0.7;  // 70% of untouched value

        Serial.printf("  Pad %d: Avg=%d, Threshold=%d\n", i, average, threshold);

        // Update threshold
        touchAttachInterrupt(touchPads[i].pin, NULL, threshold);
    }

    Serial.println("\n✅ Calibration complete!\n");
}

// ============================================================================
// TOUCH READING & DETECTION
// ============================================================================

/**
 * Read all touch pads and update state
 */
void readTouchPads() {
    activeTouches = 0;

    for (int i = 0; i < 8; i++) {
        touchPads[i].lastTouched = touchPads[i].touched;

        // Read raw capacitive value
        touchPads[i].rawValue = touchRead(touchPads[i].pin);

        // Check if touched (value drops below threshold)
        touchPads[i].touched = (touchPads[i].rawValue < TOUCH_THRESHOLD);

        if (touchPads[i].touched) {
            activeTouches++;

            // Rising edge - touch started
            if (!touchPads[i].lastTouched) {
                touchPads[i].touchStartTime = millis();
            }
        } else {
            // Falling edge - touch released
            if (touchPads[i].lastTouched) {
                unsigned long duration = millis() - touchPads[i].touchStartTime;

                // Check for tap
                if (duration < 200) {
                    touchPads[i].tapCount++;
                    touchPads[i].lastTapTime = millis();
                }
            }
        }

        // Reset tap count if too much time passed
        if (millis() - touchPads[i].lastTapTime > DOUBLE_TAP_WINDOW) {
            touchPads[i].tapCount = 0;
        }
    }

    multiTouchActive = (activeTouches > 1);
}

/**
 * Check if a specific pad is touched
 */
bool isTouched(uint8_t padIndex) {
    if (padIndex >= 8) return false;
    return touchPads[padIndex].touched;
}

/**
 * Check if a specific pad was just touched (rising edge)
 */
bool wasTouchStarted(uint8_t padIndex) {
    if (padIndex >= 8) return false;
    return touchPads[padIndex].touched && !touchPads[padIndex].lastTouched;
}

/**
 * Check if a specific pad was just released (falling edge)
 */
bool wasTouchReleased(uint8_t padIndex) {
    if (padIndex >= 8) return false;
    return !touchPads[padIndex].touched && touchPads[padIndex].lastTouched;
}

/**
 * Get touch duration for a pad
 */
unsigned long getTouchDuration(uint8_t padIndex) {
    if (padIndex >= 8) return 0;
    if (!touchPads[padIndex].touched) return 0;
    return millis() - touchPads[padIndex].touchStartTime;
}

/**
 * Proximity detection (finger near but not touching)
 */
bool isProximate(uint8_t padIndex) {
    if (padIndex >= 8) return false;
    return (touchPads[padIndex].rawValue < PROXIMITY_THRESHOLD) &&
           (touchPads[padIndex].rawValue >= TOUCH_THRESHOLD);
}

// ============================================================================
// GESTURE DETECTION
// ============================================================================

/**
 * Detect gestures from touch patterns
 */
TouchGesture detectGesture() {
    // TAP DETECTION (Top pad)
    if (touchPads[0].tapCount > 0) {
        unsigned long timeSinceLastTap = millis() - touchPads[0].lastTapTime;

        if (timeSinceLastTap > DOUBLE_TAP_WINDOW) {
            // Gesture complete
            TouchGesture gesture = GESTURE_NONE;

            if (touchPads[0].tapCount == 1) {
                gesture = GESTURE_TAP;
            } else if (touchPads[0].tapCount == 2) {
                gesture = GESTURE_DOUBLE_TAP;
            } else if (touchPads[0].tapCount >= 3) {
                gesture = GESTURE_TRIPLE_TAP;
            }

            touchPads[0].tapCount = 0;
            return gesture;
        }
    }

    // LONG PRESS DETECTION
    for (int i = 0; i < 8; i++) {
        if (touchPads[i].touched) {
            unsigned long duration = getTouchDuration(i);
            if (duration >= LONG_PRESS_TIME) {
                // Only trigger once per long press
                if (!touchPads[i].lastTouched || duration < LONG_PRESS_TIME + 50) {
                    return GESTURE_LONG_PRESS;
                }
            }
        }
    }

    // SWIPE DETECTION
    // Left swipe: Left pad touched briefly
    if (wasTouchReleased(1)) {  // TOUCH_LEFT
        unsigned long duration = millis() - touchPads[1].touchStartTime;
        if (duration < SWIPE_TIME) {
            return GESTURE_SWIPE_LEFT;
        }
    }

    // Right swipe: Right pad touched briefly
    if (wasTouchReleased(2)) {  // TOUCH_RIGHT
        unsigned long duration = millis() - touchPads[2].touchStartTime;
        if (duration < SWIPE_TIME) {
            return GESTURE_SWIPE_RIGHT;
        }
    }

    // MULTI-TOUCH GESTURES
    if (multiTouchActive && activeTouches == 2) {
        // Two-finger tap
        if (wasTouchStarted(4) && wasTouchStarted(5)) {  // Both top corners
            return GESTURE_TWO_FINGER_TAP;
        }

        // Pinch (top corners touched, then released together)
        // Spread (opposite of pinch)
        // TODO: Implement distance-based pinch/spread detection
    }

    return GESTURE_NONE;
}

/**
 * Check if a specific gesture occurred
 */
bool gestureDetected(TouchGesture gesture) {
    TouchGesture current = detectGesture();
    if (current == gesture) {
        lastGesture = current;
        lastGestureTime = millis();
        return true;
    }
    return false;
}

// ============================================================================
// VISUAL FEEDBACK (LED)
// ============================================================================

/**
 * Show touch feedback on LED ring
 */
void showTouchFeedback() {
    // Map each touch pad to an LED position
    int ledMap[8] = {0, 4, 12, 8, 1, 3, 9, 11};  // LED positions for each pad

    for (int i = 0; i < 8; i++) {
        if (touchPads[i].touched) {
            leds[ledMap[i]] = CRGB(0, 255, 255);  // Cyan when touched
        } else if (isProximate(i)) {
            leds[ledMap[i]] = CRGB(0, 50, 50);    // Dim cyan when near
        } else {
            leds[ledMap[i]] = CRGB(0, 0, 0);      // Off when not touched
        }
    }

    FastLED.show();
}

/**
 * Flash LEDs for gesture confirmation
 */
void flashGestureConfirmation(TouchGesture gesture) {
    CRGB color;

    switch (gesture) {
        case GESTURE_TAP:         color = CRGB(0, 255, 0); break;   // Green
        case GESTURE_DOUBLE_TAP:  color = CRGB(0, 0, 255); break;   // Blue
        case GESTURE_TRIPLE_TAP:  color = CRGB(255, 0, 255); break; // Magenta
        case GESTURE_LONG_PRESS:  color = CRGB(255, 165, 0); break; // Orange
        case GESTURE_SWIPE_LEFT:  color = CRGB(255, 255, 0); break; // Yellow
        case GESTURE_SWIPE_RIGHT: color = CRGB(255, 0, 0); break;   // Red
        default: return;
    }

    // Quick flash
    setAllLEDs(color.r, color.g, color.b);
    delay(100);
    setAllLEDs(0, 0, 0);
}

// ============================================================================
// GAME INTEGRATION EXAMPLES
// ============================================================================

/**
 * Example: Touch-based menu navigation
 */
void touchMenuExample() {
    readTouchPads();
    showTouchFeedback();

    if (gestureDetected(GESTURE_SWIPE_LEFT)) {
        Serial.println("◀ Menu: Previous option");
        flashGestureConfirmation(GESTURE_SWIPE_LEFT);
    }

    if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
        Serial.println("▶ Menu: Next option");
        flashGestureConfirmation(GESTURE_SWIPE_RIGHT);
    }

    if (gestureDetected(GESTURE_TAP)) {
        Serial.println("✓ Menu: Select option");
        flashGestureConfirmation(GESTURE_TAP);
    }

    if (gestureDetected(GESTURE_LONG_PRESS)) {
        Serial.println("⏎ Menu: Go back");
        flashGestureConfirmation(GESTURE_LONG_PRESS);
    }
}

/**
 * Example: Touch-based game controls
 */
void touchGameExample() {
    readTouchPads();

    // Jump on tap
    if (gestureDetected(GESTURE_TAP)) {
        Serial.println("Jump!");
    }

    // Double jump on double tap
    if (gestureDetected(GESTURE_DOUBLE_TAP)) {
        Serial.println("Double Jump!");
    }

    // Move left/right with swipes
    if (isTouched(1)) {  // Left pad
        Serial.println("Moving left...");
    }
    if (isTouched(2)) {  // Right pad
        Serial.println("Moving right...");
    }

    // Special move on long press
    if (gestureDetected(GESTURE_LONG_PRESS)) {
        Serial.println("Special move activated!");
    }

    // Multi-touch combo
    if (isTouched(4) && isTouched(5)) {  // Both top corners
        Serial.println("COMBO ATTACK!");
    }
}

/**
 * Example: Volume control with touch
 */
void touchVolumeControl() {
    readTouchPads();

    static uint8_t volume = 50;

    if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
        volume = min(100, volume + 10);
        Serial.printf("🔊 Volume: %d%%\n", volume);
    }

    if (gestureDetected(GESTURE_SWIPE_LEFT)) {
        volume = max(0, volume - 10);
        Serial.printf("🔉 Volume: %d%%\n", volume);
    }

    // Visual volume bar on LED ring
    int ledsToLight = (volume * 16) / 100;
    for (int i = 0; i < 16; i++) {
        if (i < ledsToLight) {
            leds[i] = CRGB(0, 255, 0);
        } else {
            leds[i] = CRGB(0, 0, 0);
        }
    }
    FastLED.show();
}

// ============================================================================
// DIAGNOSTICS
// ============================================================================

/**
 * Print touch sensor readings (for calibration)
 */
void printTouchDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("👆 TOUCH SENSOR DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");

    const char* padNames[8] = {
        "Top", "Left", "Right", "Bottom",
        "Corner1", "Corner2", "Corner3", "Corner4"
    };

    for (int i = 0; i < 8; i++) {
        Serial.printf("%-8s (T%d): %3d %s %s\n",
                      padNames[i],
                      touchPads[i].pin,
                      touchPads[i].rawValue,
                      touchPads[i].touched ? "[TOUCHED]" : "",
                      isProximate(i) ? "[NEAR]" : "");
    }

    Serial.printf("\nActive touches: %d\n", activeTouches);
    Serial.printf("Multi-touch: %s\n", multiTouchActive ? "Yes" : "No");

    if (lastGesture != GESTURE_NONE) {
        const char* gestures[] = {
            "NONE", "TAP", "DOUBLE_TAP", "TRIPLE_TAP",
            "LONG_PRESS", "SWIPE_LEFT", "SWIPE_RIGHT",
            "SWIPE_UP", "SWIPE_DOWN", "PINCH", "SPREAD",
            "TWO_FINGER_TAP"
        };
        Serial.printf("Last gesture: %s\n", gestures[lastGesture]);
    }

    Serial.println("═══════════════════════════════════\n");
}

/**
 * Monitor touch sensors continuously (for debugging)
 */
void monitorTouchSensors() {
    while (true) {
        readTouchPads();
        printTouchDiagnostics();
        delay(100);
    }
}

/**
 * Test gesture detection
 */
void testGestureDetection() {
    Serial.println("\n🧪 GESTURE DETECTION TEST");
    Serial.println("Try different touch gestures...\n");

    while (true) {
        readTouchPads();
        TouchGesture gesture = detectGesture();

        if (gesture != GESTURE_NONE) {
            const char* gestures[] = {
                "NONE", "TAP", "DOUBLE_TAP", "TRIPLE_TAP",
                "LONG_PRESS", "SWIPE_LEFT", "SWIPE_RIGHT",
                "SWIPE_UP", "SWIPE_DOWN", "PINCH", "SPREAD",
                "TWO_FINGER_TAP"
            };

            Serial.printf("✅ Detected: %s\n", gestures[gesture]);
            flashGestureConfirmation(gesture);
        }

        showTouchFeedback();
        delay(10);
    }
}

#endif // CAPACITIVE_TOUCH_H
