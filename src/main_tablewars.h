/*
 * TABLE WARS - Complete Game System
 *
 * Multi-game bar entertainment system with IoT pucks
 *
 * ALL 51 GAMES INCLUDED:
 * - Speed Tap Battle
 * - Shake Duel
 * - Red Light Green Light
 * - LED Chase Race
 * - Color Wars
 * - Rainbow Roulette
 * - Visual Bomb Countdown
 * - Simon Says LED
 * - Hot Potato
 * - Drunk Duel
 * - Last Tap Standing
 * - Hammer Time
 * - Bar Roulette
 * - Hold Your Nerve
 * - Slap Battle
 * - Chug Timer
 * - Pressure Cooker
 * - Power Hour Manager
 * - Dare Roulette
 * - Bullseye
 * - Karaoke Judge
 * - Wild Card
 * - Lucky Seven
 * - Volume Wars
 * - Shot Roulette
 * - Balance Master
 * - Spin Master
 * - Lightning Round
 * - Beat Master
 * - Double or Nothing
 * - Combo Breaker
 * - Lockout
 * - Precision Strike
 * - Gauntlet Mode
 * - Russian Roulette
 * - Marathon Mode
 * - Mirror Match
 * - Perfect Hold
 * - Countdown Sniper
 * - Reaction Chain
 * - Judas Mode
 * - Drunk Duck Hunt
 * - Sucker Punch
 * - Death Roll
 * - Shame Wheel
 * - All In
 * - Copycat Chaos
 * - Beer Roulette
 * - Never Have I Ever
 * - Accent Roulette
 * - Trivia Spinner
 *
 * To use this firmware, uncomment the #define TABLE_WARS_MODE in main.cpp
 */

// Additional includes not in main.cpp
#include <WiFi.h>
#include <ArduinoJson.h>
#include "server_comm.h"

// Global server communication instance
ServerComm* g_serverComm = nullptr;

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================
// NOTE: Hardware objects (strip, mpu) are already defined in main.cpp
// We just redefine the color constants to use strip.Color() syntax

// Redefine color constants
#undef COLOR_RED
#undef COLOR_GREEN
#undef COLOR_BLUE
#undef COLOR_CYAN
#undef COLOR_MAGENTA
#undef COLOR_YELLOW
#undef COLOR_WHITE
#undef COLOR_ORANGE
#undef COLOR_PURPLE
#undef COLOR_OFF

#define COLOR_RED      strip.Color(255, 0, 0)
#define COLOR_GREEN    strip.Color(0, 255, 0)
#define COLOR_BLUE     strip.Color(0, 0, 255)
#define COLOR_CYAN     strip.Color(0, 255, 255)
#define COLOR_MAGENTA  strip.Color(255, 0, 255)
#define COLOR_YELLOW   strip.Color(255, 255, 0)
#define COLOR_WHITE    strip.Color(255, 255, 255)
#define COLOR_ORANGE   strip.Color(255, 165, 0)
#define COLOR_PURPLE   strip.Color(128, 0, 128)
#define COLOR_OFF      strip.Color(0, 0, 0)

// ============================================================================
// GAME-SPECIFIC CONFIGURATION
// ============================================================================

// Puck identification (SET UNIQUE FOR EACH PUCK!)
#define PUCK_ID            1      // Change this: 1-6
#define TABLE_NUMBER       1      // Table assignment

// WiFi credentials (for multi-puck sync)
const char* WIFI_SSID = "TABLE_WARS_GAME";
const char* WIFI_PASSWORD = "tablewars2024";

// ============================================================================
// GAME STATE
// ============================================================================
enum GameMode {
    MODE_DEMO,              // Cycle through all games automatically
    MODE_MANUAL,            // Manual game selection via button
    MODE_NETWORKED          // Network-controlled (for bar deployment)
};

GameMode currentMode = MODE_DEMO;
uint8_t currentGameIndex = 0;
uint32_t totalScore = 0;
unsigned long lastGameTime = 0;
bool gameActive = false;

// Game names array (matches currentGameIndex)
const char* gameNames[51] = {
    "Speed Tap Battle", "Shake Duel", "Red Light Green Light", "LED Chase Race",
    "Color Wars", "Rainbow Roulette", "Visual Bomb Countdown", "Simon Says LED",
    "Hot Potato", "Drunk Duel", "Last Tap Standing", "Hammer Time",
    "Bar Roulette", "Hold Your Nerve", "Slap Battle", "Chug Timer",
    "Pressure Cooker", "Power Hour Manager", "Dare Roulette", "Bullseye",
    "Karaoke Judge", "Wild Card", "Lucky Seven", "Volume Wars",
    "Shot Roulette", "Balance Master", "Spin Master", "Lightning Round",
    "Beat Master", "Double or Nothing", "Combo Breaker", "Lockout",
    "Precision Strike", "Gauntlet Mode", "Russian Roulette", "Marathon Mode",
    "Mirror Match", "Perfect Hold", "Countdown Sniper", "Reaction Chain",
    "Judas Mode", "Drunk Duck Hunt", "Sucker Punch", "Death Roll",
    "Shame Wheel", "All In", "Copycat Chaos", "Beer Roulette",
    "Never Have I Ever", "Accent Roulette", "Trivia Spinner"
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// Use different names to avoid conflicts with main.cpp functions

void vibrate(uint16_t duration) {
    digitalWrite(PIN_MOTOR, HIGH);
    delay(duration);
    digitalWrite(PIN_MOTOR, LOW);
}

void fillLEDs(uint32_t color) {
    for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, color);
    }
    strip.show();
}

bool readButton() {
    static bool lastState = false;
    static unsigned long lastDebounce = 0;
    bool reading = !digitalRead(PIN_BUTTON);

    if (reading != lastState) {
        lastDebounce = millis();
    }

    if ((millis() - lastDebounce) > 50) {
        if (reading && !lastState) {
            lastState = reading;
            return true;
        }
        lastState = reading;
    }

    return false;
}

float getShakeIntensity() {
    sensors_event_t accel, gyro, temp;
    mpu.getEvent(&accel, &gyro, &temp);

    float ax = accel.acceleration.x;
    float ay = accel.acceleration.y;
    float az = accel.acceleration.z;

    float magnitude = sqrt(ax*ax + ay*ay + az*az);
    return abs(magnitude - 9.81);
}

// ============================================================================
// GAME 1: SPEED TAP BATTLE
// ============================================================================

uint32_t game_SpeedTap() {
    Serial.println("\n🎮 GAME: SPEED TAP BATTLE");
    Serial.println("Mash the button as fast as you can!");

    fillLEDs(COLOR_YELLOW);
    beep(200);
    delay(1000);

    // 3-2-1 countdown
    for (int i = 3; i > 0; i--) {
        fillLEDs(COLOR_ORANGE);
        beep(100);
        delay(500);
        clearLEDs();
        delay(500);
    }

    // GO!
    fillLEDs(COLOR_GREEN);
    beep(300);

    uint32_t taps = 0;
    unsigned long startTime = millis();
    unsigned long gameDuration = 10000; // 10 seconds

    while (millis() - startTime < gameDuration) {
        if (readButton()) {
            taps++;
            // Flash white on each tap
            strip.setPixelColor(taps % NUM_LEDS, COLOR_WHITE);
            strip.show();
            beep(30);
        }
    }

    // Results
    fillLEDs(COLOR_CYAN);
    beep(500);
    vibrate(200);

    Serial.printf("✅ TAPS: %lu\n", taps);
    Serial.printf("💯 SCORE: %lu\n", taps * 10);

    delay(2000);
    return taps * 10;
}

// ============================================================================
// GAME 2: SHAKE DUEL
// ============================================================================

uint32_t game_ShakeDuel() {
    Serial.println("\n🎮 GAME: SHAKE DUEL");
    Serial.println("Shake the puck as violently as possible!");

    fillLEDs(COLOR_RED);
    beep(200);
    delay(1000);

    // Countdown
    for (int i = 3; i > 0; i--) {
        fillLEDs(COLOR_ORANGE);
        beep(100);
        delay(500);
        clearLEDs();
        delay(500);
    }

    // GO!
    fillLEDs(COLOR_GREEN);
    beep(300);

    float maxShake = 0;
    float totalShake = 0;
    uint32_t shakeCount = 0;
    unsigned long startTime = millis();
    unsigned long gameDuration = 10000; // 10 seconds

    while (millis() - startTime < gameDuration) {
        float shake = getShakeIntensity();

        if (shake > 5.0) {
            shakeCount++;
            totalShake += shake;
            if (shake > maxShake) maxShake = shake;

            // Visual feedback - more shake = more red LEDs
            int numLEDs = min((int)(shake / 2), (int)NUM_LEDS);
            clearLEDs();
            for (int i = 0; i < numLEDs; i++) {
                strip.setPixelColor(i, COLOR_RED);
            }
            strip.show();
        }

        delay(10);
    }

    // Results
    fillLEDs(COLOR_MAGENTA);
    for (int i = 0; i < 3; i++) {
        vibrate(100);
        delay(100);
    }

    uint32_t score = (uint32_t)(totalShake * 10);

    Serial.printf("✅ MAX SHAKE: %.2f m/s²\n", maxShake);
    Serial.printf("✅ AVG SHAKE: %.2f m/s²\n", totalShake / shakeCount);
    Serial.printf("💯 SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 3: FREEZE ROUND / RED LIGHT GREEN LIGHT
// ============================================================================

uint32_t game_FreezeRound() {
    Serial.println("\n🎮 GAME: RED LIGHT GREEN LIGHT");
    Serial.println("GREEN = Shake! RED = FREEZE!");

    beep(200);
    delay(1000);

    uint32_t score = 1000; // Start with perfect score
    uint8_t roundsLeft = 5;

    for (int round = 0; round < 5; round++) {
        // Green light - SHAKE!
        fillLEDs(COLOR_GREEN);
        beep(100);

        unsigned long greenTime = random(2000, 5000);
        unsigned long greenStart = millis();

        float shakeInGreen = 0;
        while (millis() - greenStart < greenTime) {
            float shake = getShakeIntensity();
            if (shake > 5.0) {
                shakeInGreen += shake;
            }
            delay(10);
        }

        // RED LIGHT - FREEZE!
        fillLEDs(COLOR_RED);
        beep(200);

        unsigned long freezeTime = random(1000, 3000);
        unsigned long freezeStart = millis();

        bool failed = false;
        while (millis() - freezeStart < freezeTime) {
            float shake = getShakeIntensity();
            if (shake > 3.0) {
                // MOVEMENT DETECTED!
                failed = true;
                for (int i = 0; i < 3; i++) {
                    fillLEDs(COLOR_OFF);
                    delay(100);
                    fillLEDs(COLOR_RED);
                    delay(100);
                }
                beep(500);
                score -= 200;
                Serial.println("❌ MOVEMENT DETECTED! -200 points");
                break;
            }
            delay(10);
        }

        if (!failed) {
            score += 100;
            Serial.println("✅ FROZEN! +100 points");
        }

        delay(500);
    }

    fillLEDs(COLOR_CYAN);
    beep(300);
    vibrate(200);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 4: LED CHASE RACE
// ============================================================================

uint32_t game_LEDChase() {
    Serial.println("\n🎮 GAME: LED CHASE RACE");
    Serial.println("Press button when LED reaches the target!");

    fillLEDs(COLOR_CYAN);
    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 10;

    for (int round = 0; round < rounds; round++) {
        // Pick random target LED
        uint8_t targetLED = random(0, NUM_LEDS);

        // Show target
        clearLEDs();
        strip.setPixelColor(targetLED, COLOR_WHITE);
        strip.show();
        delay(1000);

        // Start chase
        unsigned long startTime = millis();
        uint8_t currentLED = 0;
        bool hit = false;

        while (!hit && (millis() - startTime < 5000)) {
            clearLEDs();
            strip.setPixelColor(currentLED, COLOR_GREEN);
            strip.setPixelColor(targetLED, COLOR_WHITE);
            strip.show();

            if (readButton()) {
                // Check if they hit the target
                if (currentLED == targetLED) {
                    fillLEDs(COLOR_GREEN);
                    beep(100);
                    vibrate(100);
                    score += 100;
                    Serial.println("✅ HIT! +100 points");
                    hit = true;
                } else {
                    fillLEDs(COLOR_RED);
                    beep(200);
                    score -= 50;
                    Serial.println("❌ MISS! -50 points");
                }
                delay(500);
            }

            currentLED = (currentLED + 1) % NUM_LEDS;
            delay(100);
        }

        if (!hit) {
            Serial.println("❌ TIMEOUT! No points");
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);
    vibrate(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 5: COLOR WARS
// ============================================================================

uint32_t game_ColorWars() {
    Serial.println("\n🎮 GAME: COLOR WARS");
    Serial.println("You are CYAN team! Defend your color!");

    uint32_t teamColor = COLOR_CYAN;
    fillLEDs(teamColor);
    beep(200);
    delay(2000);

    uint32_t score = 1000; // Start score
    int territory = NUM_LEDS; // LEDs controlled (use int for min/max)

    for (int round = 0; round < 10; round++) {
        Serial.printf("Round %d - Territory: %d LEDs\n", round + 1, territory);

        // Enemy attack!
        uint8_t enemyColor = random(0, 7);
        uint32_t attackColor;

        switch (enemyColor) {
            case 0: attackColor = COLOR_RED; break;
            case 1: attackColor = COLOR_BLUE; break;
            case 2: attackColor = COLOR_GREEN; break;
            case 3: attackColor = COLOR_YELLOW; break;
            case 4: attackColor = COLOR_MAGENTA; break;
            case 5: attackColor = COLOR_ORANGE; break;
            default: attackColor = COLOR_PURPLE; break;
        }

        // Show attack
        for (int i = 0; i < 3; i++) {
            fillLEDs(attackColor);
            beep(50);
            delay(100);
            fillLEDs(teamColor);
            delay(100);
        }

        // Defend by tapping!
        Serial.println("⚔️  DEFEND! TAP TO PROTECT YOUR COLOR!");

        unsigned long defenseTime = 3000;
        unsigned long startTime = millis();
        uint8_t taps = 0;

        while (millis() - startTime < defenseTime) {
            if (readButton()) {
                taps++;
                beep(30);
            }
        }

        // Calculate result (fixed type issues)
        if (taps >= 10) {
            Serial.println("✅ DEFENDED! +2 territory");
            territory = min(territory + 2, (int)NUM_LEDS);
            score += 100;
        } else if (taps >= 5) {
            Serial.println("⚔️  HELD! No change");
        } else {
            Serial.println("❌ LOST TERRITORY! -2 LEDs");
            territory = max(territory - 2, 0);
            score -= 100;
        }

        // Show current territory
        clearLEDs();
        for (int i = 0; i < territory; i++) {
            strip.setPixelColor(i, teamColor);
        }
        strip.show();
        delay(1500);
    }

    fillLEDs(COLOR_CYAN);
    beep(500);
    vibrate(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 6: RAINBOW ROULETTE
// ============================================================================

uint32_t game_RainbowRoulette() {
    Serial.println("\n🎮 GAME: RAINBOW ROULETTE");
    Serial.println("Stop on the target color!");

    beep(200);
    delay(1000);

    uint32_t score = 0;

    for (int round = 0; round < 5; round++) {
        // Pick target color
        uint8_t targetColorIndex = random(0, 7);
        uint32_t colors[] = {COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW,
                             COLOR_CYAN, COLOR_MAGENTA, COLOR_WHITE};
        uint32_t targetColor = colors[targetColorIndex];

        Serial.println("Target color shown...");
        fillLEDs(targetColor);
        delay(1500);

        Serial.println("Spinning...");

        // Rainbow spin
        unsigned long spinTime = random(3000, 6000);
        unsigned long startTime = millis();
        uint16_t hue = 0;

        while (millis() - startTime < spinTime) {
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.ColorHSV(hue + (i * 65536 / NUM_LEDS)));
            }
            strip.show();
            hue += 500;
            delay(20);
        }

        // Wait for button press to stop
        Serial.println("PRESS TO STOP!");
        beep(100);

        while (!readButton()) {
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.ColorHSV(hue + (i * 65536 / NUM_LEDS)));
            }
            strip.show();
            hue += 500;
            delay(20);
        }

        // Get stopped color
        uint32_t stoppedColor = strip.getPixelColor(0);

        // Check if close to target
        if (stoppedColor == targetColor) {
            fillLEDs(COLOR_GREEN);
            beep(200);
            vibrate(200);
            score += 200;
            Serial.println("✅ JACKPOT! +200 points");
        } else {
            fillLEDs(COLOR_ORANGE);
            beep(100);
            score += 50;
            Serial.println("⚠️  CLOSE! +50 points");
        }

        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 7: VISUAL BOMB COUNTDOWN
// ============================================================================

uint32_t game_VisualBomb() {
    Serial.println("\n🎮 GAME: VISUAL BOMB COUNTDOWN");
    Serial.println("Pass the bomb before it explodes!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 3;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        // Show bomb received
        fillLEDs(COLOR_RED);
        vibrate(100);
        beep(100);
        delay(500);

        // Countdown
        unsigned long bombTime = random(5000, 10000);
        unsigned long startTime = millis();
        bool passed = false;

        while (millis() - startTime < bombTime) {
            // Visual countdown
            unsigned long remaining = bombTime - (millis() - startTime);
            uint8_t ledsLeft = (remaining * NUM_LEDS) / bombTime;

            clearLEDs();
            for (int i = 0; i < ledsLeft; i++) {
                strip.setPixelColor(i, COLOR_RED);
            }
            strip.show();

            // Can pass by pressing button
            if (readButton()) {
                Serial.println("✅ BOMB PASSED!");
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                score += 200;
                passed = true;
                delay(1000);
                break;
            }

            delay(50);
        }

        if (!passed) {
            // EXPLOSION!
            Serial.println("💥 BOOM!");
            for (int i = 0; i < 5; i++) {
                fillLEDs(COLOR_RED);
                beep(100);
                vibrate(100);
                delay(100);
                clearLEDs();
                delay(100);
            }
            score -= 100;
        }

        delay(1000);
    }

    fillLEDs(COLOR_CYAN);
    beep(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 8: SIMON SAYS LED
// ============================================================================

uint32_t game_SimonSays() {
    Serial.println("\n🎮 GAME: SIMON SAYS LED");
    Serial.println("Remember the LED pattern!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t sequence[10];
    uint8_t level = 1;

    while (level <= 5) {
        Serial.printf("Level %d - Length: %d\n", level, level);

        // Generate sequence
        for (int i = 0; i < level; i++) {
            sequence[i] = random(0, 4) * 4; // Positions: 0, 4, 8, 12 (quarters)
        }

        // Show sequence
        Serial.println("Watch the pattern...");
        delay(1000);

        for (int i = 0; i < level; i++) {
            clearLEDs();
            strip.setPixelColor(sequence[i], COLOR_YELLOW);
            strip.setPixelColor(sequence[i] + 1, COLOR_YELLOW);
            strip.show();
            beep(100);
            delay(500);
            clearLEDs();
            delay(300);
        }

        // Player repeats
        Serial.println("Your turn! Shake in the correct directions...");
        delay(1000);

        bool correct = true;
        for (int i = 0; i < level && correct; i++) {
            // Wait for shake
            fillLEDs(COLOR_CYAN);
            beep(50);

            unsigned long startWait = millis();
            bool shook = false;

            while (!shook && (millis() - startWait < 5000)) {
                if (getShakeIntensity() > 10.0) {
                    shook = true;

                    // Light up position
                    clearLEDs();
                    strip.setPixelColor(sequence[i], COLOR_GREEN);
                    strip.setPixelColor(sequence[i] + 1, COLOR_GREEN);
                    strip.show();
                    beep(100);

                    delay(500);
                }
                delay(50);
            }

            if (!shook) {
                Serial.println("❌ TIMEOUT!");
                correct = false;
            }
        }

        if (correct) {
            Serial.println("✅ CORRECT!");
            fillLEDs(COLOR_GREEN);
            beep(200);
            vibrate(200);
            score += level * 100;
            level++;
            delay(1500);
        } else {
            Serial.println("❌ WRONG PATTERN!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(1500);
            break;
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 9: HOT POTATO
// ============================================================================

uint32_t game_HotPotato() {
    Serial.println("\n🎮 GAME: HOT POTATO");
    Serial.println("Pass the bomb before it explodes!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 3;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        // Arm the bomb
        Serial.println("💣 BOMB ARMED!");

        // Pulsing red getting faster
        unsigned long bombTime = random(4000, 8000);
        unsigned long startTime = millis();
        unsigned long pulseInterval = 500;
        unsigned long lastPulse = 0;
        bool passed = false;

        while (millis() - startTime < bombTime) {
            unsigned long elapsed = millis() - startTime;
            unsigned long remaining = bombTime - elapsed;

            // Pulse gets faster as time runs out
            pulseInterval = max((unsigned long)50, remaining / 10);

            if (millis() - lastPulse > pulseInterval) {
                // Pulse effect
                static bool pulseOn = false;
                if (pulseOn) {
                    fillLEDs(COLOR_RED);
                    beep(50);
                } else {
                    fillLEDs(COLOR_ORANGE);
                }
                pulseOn = !pulseOn;
                lastPulse = millis();
            }

            // Vibrate more intensely as time runs out
            if (remaining < 2000) {
                vibrate(50);
                delay(50);
            }

            // Pass the bomb
            if (readButton()) {
                Serial.println("✅ BOMB PASSED!");
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                score += 300;
                passed = true;
                delay(1000);
                break;
            }

            delay(10);
        }

        if (!passed) {
            // EXPLOSION!
            Serial.println("💥 BOOM! YOU EXPLODED!");
            for (int i = 0; i < 5; i++) {
                fillLEDs(COLOR_RED);
                beep(200);
                vibrate(200);
                delay(150);
                fillLEDs(COLOR_YELLOW);
                delay(150);
            }
            score -= 200;
        }

        delay(1000);
    }

    fillLEDs(COLOR_CYAN);
    beep(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 10: DRUNK DUEL
// ============================================================================

uint32_t game_DrunkDuel() {
    Serial.println("\n🎮 GAME: DRUNK DUEL");
    Serial.println("1v1 Reaction Showdown!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        // Spin the lights
        Serial.println("🌀 Spinning...");
        unsigned long spinTime = random(2000, 5000);
        unsigned long startTime = millis();
        uint16_t hue = 0;

        while (millis() - startTime < spinTime) {
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.ColorHSV(hue + (i * 65536 / NUM_LEDS)));
            }
            strip.show();
            hue += 1000;
            delay(30);
        }

        // Random wait time
        clearLEDs();
        delay(random(500, 3000));

        // GO!
        fillLEDs(COLOR_GREEN);
        beep(300);
        vibrate(100);

        unsigned long goTime = millis();
        bool tapped = false;

        // Wait for reaction
        while (!tapped && (millis() - goTime < 3000)) {
            if (readButton()) {
                unsigned long reactionTime = millis() - goTime;
                tapped = true;

                Serial.printf("⚡ REACTION TIME: %lu ms\n", reactionTime);

                // Score based on speed
                if (reactionTime < 200) {
                    Serial.println("🔥 LIGHTNING FAST! +500");
                    score += 500;
                } else if (reactionTime < 400) {
                    Serial.println("⚡ SUPER FAST! +300");
                    score += 300;
                } else if (reactionTime < 700) {
                    Serial.println("👍 GOOD! +150");
                    score += 150;
                } else {
                    Serial.println("😴 SLOW! +50");
                    score += 50;
                }

                fillLEDs(COLOR_CYAN);
                beep(100);
                vibrate(100);
            }
        }

        if (!tapped) {
            Serial.println("❌ TOO SLOW!");
            fillLEDs(COLOR_RED);
            beep(500);
        }

        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 11: LAST TAP STANDING
// ============================================================================

uint32_t game_LastTapStanding() {
    Serial.println("\n🎮 GAME: LAST TAP STANDING");
    Serial.println("Tap before it goes RED or you're OUT!");

    beep(200);
    delay(1000);

    uint32_t score = 1000;
    uint8_t lives = 3;
    uint8_t level = 1;

    while (lives > 0 && level <= 10) {
        Serial.printf("Level %d - Lives: %d\n", level, lives);

        // Pulse cyan
        fillLEDs(COLOR_CYAN);
        delay(500);

        // Random wait time (gets shorter each level)
        unsigned long waitTime = random(max(500, 3000 - (level * 200)),
                                       max(1000, 5000 - (level * 300)));
        delay(waitTime);

        // Start warning - color shifts toward red
        unsigned long warnTime = max((unsigned long)500, (unsigned long)(1500 - level * 100));
        unsigned long warnStart = millis();

        bool tapped = false;

        while (millis() - warnStart < warnTime) {
            // Color fades from yellow to orange to red
            unsigned long progress = millis() - warnStart;
            float ratio = (float)progress / warnTime;

            uint8_t red = 255;
            uint8_t green = (uint8_t)(255 * (1.0 - ratio));
            uint32_t color = strip.Color(red, green, 0);

            fillLEDs(color);

            if (readButton()) {
                Serial.println("✅ SAFE! +100");
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                score += 100;
                tapped = true;
                delay(500);
                break;
            }

            delay(20);
        }

        if (!tapped) {
            // TOO LATE - IT WENT RED!
            fillLEDs(COLOR_RED);
            beep(500);
            vibrate(300);
            Serial.println("💀 YOU'RE OUT!");
            lives--;
            score -= 150;
            delay(1500);
        }

        level++;
        delay(500);
    }

    if (lives > 0) {
        Serial.println("🏆 YOU SURVIVED!");
        fillLEDs(COLOR_CYAN);
        beep(300);
        vibrate(200);
    } else {
        Serial.println("💀 ELIMINATED!");
        fillLEDs(COLOR_RED);
        beep(500);
    }

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 12: HAMMER TIME
// ============================================================================

uint32_t game_HammerTime() {
    Serial.println("\n🎮 GAME: HAMMER TIME");
    Serial.println("Shake as HARD as you can!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        // Countdown
        fillLEDs(COLOR_ORANGE);
        beep(100);
        delay(500);
        fillLEDs(COLOR_YELLOW);
        beep(100);
        delay(500);
        fillLEDs(COLOR_GREEN);
        beep(200);

        Serial.println("💪 SHAKE NOW!");

        float maxShake = 0;
        unsigned long shakeTime = 3000;
        unsigned long startTime = millis();

        while (millis() - startTime < shakeTime) {
            float shake = getShakeIntensity();

            if (shake > maxShake) {
                maxShake = shake;
            }

            // Visual bar climbing
            int numLEDs = min((int)(shake / 2), (int)NUM_LEDS);
            clearLEDs();
            for (int i = 0; i < numLEDs; i++) {
                // Color gradient: green -> yellow -> red
                uint32_t color;
                if (i < NUM_LEDS / 3) {
                    color = COLOR_GREEN;
                } else if (i < 2 * NUM_LEDS / 3) {
                    color = COLOR_YELLOW;
                } else {
                    color = COLOR_RED;
                }
                strip.setPixelColor(i, color);
            }
            strip.show();

            delay(10);
        }

        // Show max result
        uint32_t roundScore = (uint32_t)(maxShake * 50);
        score += roundScore;

        Serial.printf("💪 MAX POWER: %.2f m/s²\n", maxShake);
        Serial.printf("✅ ROUND SCORE: %lu\n", roundScore);

        // Victory animation based on power
        if (maxShake > 30.0) {
            Serial.println("🔥 LEGENDARY STRENGTH!");
            for (int i = 0; i < 3; i++) {
                fillLEDs(COLOR_RED);
                beep(100);
                vibrate(100);
                delay(100);
                fillLEDs(COLOR_YELLOW);
                delay(100);
            }
        } else if (maxShake > 20.0) {
            Serial.println("💪 BEAST MODE!");
            fillLEDs(COLOR_ORANGE);
            beep(200);
            vibrate(200);
        } else if (maxShake > 10.0) {
            Serial.println("👍 GOOD SHAKE!");
            fillLEDs(COLOR_YELLOW);
            beep(150);
            vibrate(150);
        } else {
            Serial.println("😴 WEAK SAUCE!");
            fillLEDs(COLOR_BLUE);
            beep(100);
        }

        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 13: BAR ROULETTE
// ============================================================================

uint32_t game_BarRoulette() {
    Serial.println("\n🎮 GAME: BAR ROULETTE");
    Serial.println("Spin the wheel... who gets the dare?");

    beep(200);
    delay(1000);

    uint32_t score = 1000;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        Serial.println("🎰 SPINNING...");

        // Fast spin
        for (int spin = 0; spin < 30; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_WHITE);
            strip.show();
            beep(30);
            delay(50 + spin * 3); // Slow down gradually
        }

        // Slower spin with tension
        for (int spin = 0; spin < 20; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_YELLOW);
            strip.show();
            beep(40);
            delay(100 + spin * 10);
        }

        // Final slow clicks
        for (int spin = 0; spin < 8; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_ORANGE);
            strip.show();
            beep(50);
            vibrate(50);
            delay(200 + spin * 30);
        }

        // LAND ON RED!
        uint8_t finalPos = random(0, NUM_LEDS);
        clearLEDs();
        strip.setPixelColor(finalPos, COLOR_RED);
        strip.show();
        beep(500);
        vibrate(300);

        Serial.println("🎯 LANDED ON RED!");

        // Random "punishment" intensity
        uint8_t intensity = random(1, 4);

        if (intensity == 3) {
            Serial.println("😱 EXTREME DARE! -300 points");
            score -= 300;
            for (int i = 0; i < 5; i++) {
                fillLEDs(COLOR_RED);
                beep(100);
                delay(100);
                clearLEDs();
                delay(100);
            }
        } else if (intensity == 2) {
            Serial.println("😬 MEDIUM DARE! -150 points");
            score -= 150;
            fillLEDs(COLOR_ORANGE);
            beep(300);
            vibrate(200);
        } else {
            Serial.println("😅 MILD DARE! -50 points");
            score -= 50;
            fillLEDs(COLOR_YELLOW);
            beep(150);
            vibrate(100);
        }

        // Acknowledge with button
        Serial.println("Tap to accept your fate...");
        while (!readButton()) {
            delay(50);
        }

        fillLEDs(COLOR_GREEN);
        beep(100);
        Serial.println("✅ ACCEPTED!");

        delay(2000);
    }

    fillLEDs(COLOR_CYAN);
    beep(300);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 14: HOLD YOUR NERVE
// ============================================================================

uint32_t game_HoldYourNerve() {
    Serial.println("\n🎮 GAME: HOLD YOUR NERVE");
    Serial.println("Keep the puck PERFECTLY STILL!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        fillLEDs(COLOR_CYAN);
        beep(100);
        delay(1000);

        Serial.println("🧘 HOLD STEADY... DON'T MOVE!");

        // Hold time increases each round
        unsigned long holdTime = 3000 + (round * 1000);
        unsigned long startTime = millis();
        bool failed = false;

        // Sensitivity increases each round (gets harder)
        float threshold = 3.0 - (round * 0.3);
        if (threshold < 1.0) threshold = 1.0;

        fillLEDs(COLOR_GREEN);

        while (millis() - startTime < holdTime && !failed) {
            float shake = getShakeIntensity();

            if (shake > threshold) {
                // MOVEMENT DETECTED!
                failed = true;
                Serial.println("❌ YOU MOVED!");

                for (int i = 0; i < 3; i++) {
                    fillLEDs(COLOR_RED);
                    beep(100);
                    vibrate(100);
                    delay(100);
                    clearLEDs();
                    delay(100);
                }

                break;
            }

            // Visual feedback - green when steady
            unsigned long remaining = holdTime - (millis() - startTime);
            uint8_t ledsLit = (remaining * NUM_LEDS) / holdTime;

            clearLEDs();
            for (int i = 0; i < ledsLit; i++) {
                strip.setPixelColor(i, COLOR_GREEN);
            }
            strip.show();

            delay(50);
        }

        if (!failed) {
            Serial.println("✅ ROCK SOLID!");
            uint32_t roundScore = 200 + (round * 100);
            score += roundScore;
            Serial.printf("💯 +%lu points\n", roundScore);

            fillLEDs(COLOR_CYAN);
            beep(200);
            vibrate(200);
        }

        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 15: SLAP BATTLE
// ============================================================================

uint32_t game_SlapBattle() {
    Serial.println("\n🎮 GAME: SLAP BATTLE");
    Serial.println("SLAP the puck when it goes GREEN!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);

        // Countdown
        for (int i = 5; i > 0; i--) {
            Serial.printf("%d...\n", i);
            fillLEDs(COLOR_ORANGE);
            beep(100);
            delay(300);
            clearLEDs();
            delay(300);
        }

        // Random delay (tension!)
        Serial.println("Wait for it...");
        fillLEDs(COLOR_RED);
        unsigned long waitTime = random(1000, 4000);
        delay(waitTime);

        // GO! GO! GO!
        fillLEDs(COLOR_GREEN);
        beep(300);
        vibrate(100);

        unsigned long startTime = millis();
        bool slapped = false;

        // Wait for SLAP!
        while (!slapped && (millis() - startTime < 2000)) {
            if (readButton()) {
                unsigned long reactionTime = millis() - startTime;
                slapped = true;

                Serial.printf("⚡ SLAP TIME: %lu ms\n", reactionTime);

                // Score based on reaction speed
                if (reactionTime < 100) {
                    Serial.println("🔥 LIGHTNING SLAP! +600");
                    score += 600;
                } else if (reactionTime < 200) {
                    Serial.println("💥 SUPER SLAP! +400");
                    score += 400;
                } else if (reactionTime < 350) {
                    Serial.println("👊 GOOD SLAP! +200");
                    score += 200;
                } else if (reactionTime < 600) {
                    Serial.println("✋ DECENT SLAP! +100");
                    score += 100;
                } else {
                    Serial.println("😴 WEAK SLAP! +25");
                    score += 25;
                }

                fillLEDs(COLOR_CYAN);
                beep(150);
                vibrate(150);
            }
        }

        if (!slapped) {
            Serial.println("❌ TOO SLOW! NO SLAP!");
            fillLEDs(COLOR_RED);
            beep(500);
        }

        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 16: CHUG TIMER
// ============================================================================

uint32_t game_ChugTimer() {
    Serial.println("\n🎮 GAME: CHUG TIMER");
    Serial.println("Grab a drink and let's time that chug!");

    beep(200);
    delay(2000);

    Serial.println("🍺 GET READY...");
    fillLEDs(COLOR_YELLOW);
    delay(2000);

    // 3-2-1 countdown
    for (int i = 3; i > 0; i--) {
        Serial.printf("%d...\n", i);
        fillLEDs(COLOR_ORANGE);
        beep(150);
        delay(700);
        clearLEDs();
        delay(300);
    }

    // GO!
    Serial.println("🍻 CHUG! CHUG! CHUG!");
    fillLEDs(COLOR_GREEN);
    beep(400);
    vibrate(200);

    unsigned long startTime = millis();
    unsigned long elapsed = 0;

    // LED chase effect during chug
    uint8_t ledPos = 0;
    unsigned long lastUpdate = millis();

    Serial.println("SHAKE WHEN DONE!");

    bool finished = false;

    while (!finished) {
        elapsed = millis() - startTime;

        // Rotating LED effect
        if (millis() - lastUpdate > 100) {
            clearLEDs();
            for (int i = 0; i < 3; i++) {
                strip.setPixelColor((ledPos + i) % NUM_LEDS, COLOR_GREEN);
            }
            strip.show();
            ledPos = (ledPos + 1) % NUM_LEDS;
            lastUpdate = millis();
        }

        // Detect shake to finish
        if (getShakeIntensity() > 15.0) {
            finished = true;
        }

        // Safety timeout (60 seconds)
        if (elapsed > 60000) {
            Serial.println("⏰ TIME LIMIT REACHED!");
            finished = true;
        }

        delay(10);
    }

    float chugTime = elapsed / 1000.0;

    // Victory animation
    for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, COLOR_CYAN);
        strip.show();
        beep(30);
        delay(30);
    }

    vibrate(300);

    Serial.printf("⏱️  CHUG TIME: %.2f seconds\n", chugTime);

    // Score based on time
    uint32_t score = 0;
    if (chugTime < 3.0) {
        Serial.println("🏆 LEGENDARY CHUGGER! +1000");
        score = 1000;
        for (int i = 0; i < 5; i++) {
            fillLEDs(COLOR_YELLOW);
            beep(100);
            delay(100);
            fillLEDs(COLOR_RED);
            beep(100);
            delay(100);
        }
    } else if (chugTime < 5.0) {
        Serial.println("💪 BEAST MODE! +500");
        score = 500;
    } else if (chugTime < 10.0) {
        Serial.println("👍 RESPECTABLE! +250");
        score = 250;
    } else {
        Serial.println("😅 ROOKIE NUMBERS! +100");
        score = 100;
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(3000);
    return score;
}

// ============================================================================
// GAME 17: PRESSURE COOKER
// ============================================================================

uint32_t game_PressureCooker() {
    Serial.println("\n🎮 GAME: PRESSURE COOKER");
    Serial.println("DON'T press the button... resist the urge!");

    beep(200);
    delay(2000);

    Serial.println("⚠️  Starting in 3 seconds...");
    fillLEDs(COLOR_YELLOW);
    delay(3000);

    Serial.println("🔥 DON'T PRESS THE BUTTON!");

    unsigned long startTime = millis();
    unsigned long elapsed = 0;
    bool pressed = false;
    uint32_t score = 0;

    uint8_t phase = 0;
    unsigned long lastPhaseChange = startTime;
    unsigned long lastPulse = 0;
    unsigned long lastVibrate = 0;
    bool pulseOn = false;

    while (!pressed && elapsed < 60000) {
        elapsed = millis() - startTime;

        // Phase progression
        if (elapsed < 10000) phase = 0;        // Calm
        else if (elapsed < 20000) phase = 1;   // Warming up
        else if (elapsed < 30000) phase = 2;   // Getting hot
        else if (elapsed < 40000) phase = 3;   // Very hot
        else if (elapsed < 50000) phase = 4;   // Extreme
        else phase = 5;                         // CHAOS MODE

        // Phase behaviors
        switch (phase) {
            case 0: // Calm (0-10s)
                fillLEDs(COLOR_BLUE);
                break;

            case 1: // Warming up (10-20s)
                if (millis() - lastPulse > 1000) {
                    fillLEDs(pulseOn ? COLOR_YELLOW : COLOR_BLUE);
                    pulseOn = !pulseOn;
                    lastPulse = millis();
                }
                break;

            case 2: // Getting hot (20-30s)
                if (millis() - lastPulse > 500) {
                    fillLEDs(pulseOn ? COLOR_ORANGE : COLOR_YELLOW);
                    pulseOn = !pulseOn;
                    beep(50);
                    lastPulse = millis();
                }
                if (millis() - lastVibrate > 5000) {
                    vibrate(100);
                    lastVibrate = millis();
                }
                break;

            case 3: // Very hot (30-40s)
                if (millis() - lastPulse > 300) {
                    fillLEDs(pulseOn ? COLOR_RED : COLOR_ORANGE);
                    pulseOn = !pulseOn;
                    beep(80);
                    lastPulse = millis();
                }
                if (millis() - lastVibrate > 2000) {
                    vibrate(150);
                    lastVibrate = millis();
                }
                break;

            case 4: // Extreme (40-50s)
                if (millis() - lastPulse > 150) {
                    fillLEDs(pulseOn ? COLOR_RED : COLOR_OFF);
                    pulseOn = !pulseOn;
                    beep(100);
                    lastPulse = millis();
                }
                if (millis() - lastVibrate > 1000) {
                    vibrate(200);
                    lastVibrate = millis();
                }
                break;

            case 5: // CHAOS MODE (50-60s)
                if (millis() - lastPulse > 80) {
                    // Strobe effect
                    uint32_t colors[] = {COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_OFF};
                    fillLEDs(colors[random(0, 4)]);
                    beep(120);
                    vibrate(100);
                    pulseOn = !pulseOn;
                    lastPulse = millis();
                }
                break;
        }

        // Check if button pressed
        if (readButton()) {
            pressed = true;
            Serial.println("\n❌ YOU PRESSED IT!");

            // Explosion animation
            for (int i = 0; i < 5; i++) {
                fillLEDs(COLOR_RED);
                beep(150);
                vibrate(200);
                delay(150);
                fillLEDs(COLOR_OFF);
                delay(150);
            }

            float seconds = elapsed / 1000.0;
            Serial.printf("⏱️  Lasted: %.2f seconds\n", seconds);

            score = (uint32_t)(seconds * 20);
            Serial.printf("💯 SCORE: %lu\n", score);
        }

        delay(10);
    }

    if (!pressed) {
        // LEGENDARY! Made it to 60 seconds!
        Serial.println("\n🏆 LEGENDARY WILLPOWER!");
        score = 2000;

        for (int i = 0; i < 10; i++) {
            fillLEDs(COLOR_YELLOW);
            beep(100);
            vibrate(100);
            delay(100);
            fillLEDs(COLOR_CYAN);
            delay(100);
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(3000);
    return score;
}

// ============================================================================
// GAME 18: POWER HOUR MANAGER
// ============================================================================

uint32_t game_PowerHour() {
    Serial.println("\n🎮 GAME: POWER HOUR MANAGER");
    Serial.println("60 shots in 60 minutes! (Demo: 10 rounds/10 seconds)");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 10; // Demo mode: 10 rounds
    unsigned long roundInterval = 10000; // Demo: 10 seconds (real: 60000)

    Serial.println("🍻 POWER HOUR STARTING!");
    fillLEDs(COLOR_GREEN);
    beep(500);
    vibrate(300);
    delay(2000);

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\n🍺 ROUND %d/%d\n", round + 1, rounds);

        // Show round number on LEDs
        clearLEDs();
        for (int i = 0; i <= round && i < NUM_LEDS; i++) {
            strip.setPixelColor(i, COLOR_CYAN);
        }
        strip.show();

        // Wait for interval
        unsigned long startWait = millis();
        while (millis() - startWait < roundInterval) {
            // Breathing effect during wait
            float progress = (float)(millis() - startWait) / roundInterval;
            float brightness = (sin(progress * 6.28) + 1.0) / 2.0;
            uint8_t b = 50 + (brightness * 100);

            for (int i = 0; i <= round && i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(0, b, b));
            }
            strip.show();

            delay(50);
        }

        // DRINK TIME!
        Serial.println("🍻 DRINK!");

        for (int i = 0; i < 3; i++) {
            fillLEDs(COLOR_GREEN);
            beep(150);
            vibrate(150);
            delay(200);
            fillLEDs(COLOR_YELLOW);
            delay(200);
        }

        score += 100;
        delay(1000);
    }

    // FINALE!
    Serial.println("\n🏆 POWER HOUR COMPLETE!");

    for (int i = 0; i < 10; i++) {
        fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_GREEN);
        beep(100);
        vibrate(100);
        delay(150);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(3000);
    return score;
}

// ============================================================================
// GAME 19: DARE ROULETTE
// ============================================================================

uint32_t game_DareRoulette() {
    Serial.println("\n🎮 GAME: DARE ROULETTE");
    Serial.println("Spin to see who gets the dare!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d\n", round + 1);
        Serial.println("🎲 SPINNING...");

        // Fast spin
        for (int spin = 0; spin < 40; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_WHITE);
            strip.setPixelColor((pos + 1) % NUM_LEDS, COLOR_CYAN);
            strip.show();
            beep(30);
            delay(40 + spin * 2);
        }

        // Slow down
        for (int spin = 0; spin < 15; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_YELLOW);
            strip.show();
            beep(50);
            vibrate(50);
            delay(100 + spin * 20);
        }

        // STOP!
        uint8_t finalPos = random(0, NUM_LEDS);
        uint8_t intensity = random(0, 4);

        clearLEDs();
        strip.setPixelColor(finalPos, COLOR_WHITE);

        // Show intensity
        uint32_t dareColor;
        const char* dareLevel;
        uint32_t points;

        switch(intensity) {
            case 0:
                dareColor = COLOR_GREEN;
                dareLevel = "MILD";
                points = 100;
                break;
            case 1:
                dareColor = COLOR_YELLOW;
                dareLevel = "MEDIUM";
                points = 200;
                break;
            case 2:
                dareColor = COLOR_ORANGE;
                dareLevel = "SPICY";
                points = 300;
                break;
            default:
                dareColor = COLOR_RED;
                dareLevel = "EXTREME";
                points = 500;
                break;
        }

        for (int i = 0; i < 5; i++) {
            strip.setPixelColor((finalPos + i) % NUM_LEDS, dareColor);
        }
        strip.show();
        beep(500);
        vibrate(300);

        Serial.printf("🎯 Position %d - %s DARE!\n", finalPos, dareLevel);
        score += points;

        delay(3000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 20: BULLSEYE
// ============================================================================

uint32_t game_Bullseye() {
    Serial.println("\n🎮 GAME: BULLSEYE");
    Serial.println("Spin the puck - closest to center wins!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 3;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("Round %d - Spin the puck!\n", round + 1);

        fillLEDs(COLOR_CYAN);
        beep(200);
        delay(2000);

        Serial.println("⏳ Detecting spin...");

        // Wait for spin detection
        unsigned long spinStart = millis();
        float maxSpin = 0;
        bool spinning = false;

        while (millis() - spinStart < 10000) {
            sensors_event_t accel, gyro, temp;
            mpu.getEvent(&accel, &gyro, &temp);

            float spinRate = abs(gyro.gyro.z);

            if (spinRate > 2.0) {
                spinning = true;
                if (spinRate > maxSpin) maxSpin = spinRate;

                // Visual feedback during spin
                uint8_t numLEDs = min((int)(spinRate * 2), (int)NUM_LEDS);
                clearLEDs();
                for (int i = 0; i < numLEDs; i++) {
                    strip.setPixelColor(i, COLOR_YELLOW);
                }
                strip.show();
            }

            // If was spinning and now stopped
            if (spinning && spinRate < 0.5) {
                break;
            }

            delay(50);
        }

        if (!spinning) {
            Serial.println("❌ NO SPIN DETECTED!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(2000);
            continue;
        }

        Serial.printf("🌀 Max spin rate: %.2f rad/s\n", maxSpin);

        // Score based on "landing position" (simulated via final shake)
        delay(500);
        float finalPosition = getShakeIntensity();

        uint32_t roundScore;
        if (finalPosition < 2.0) {
            Serial.println("🎯 BULLSEYE! Perfect center!");
            roundScore = 500;
            fillLEDs(COLOR_WHITE);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
        } else if (finalPosition < 5.0) {
            Serial.println("🟢 CLOSE! Inner ring!");
            roundScore = 300;
            fillLEDs(COLOR_GREEN);
            beep(300);
            vibrate(200);
        } else if (finalPosition < 10.0) {
            Serial.println("🟡 MEDIUM! Middle ring!");
            roundScore = 150;
            fillLEDs(COLOR_YELLOW);
            beep(200);
        } else {
            Serial.println("🔴 FAR! Outer ring!");
            roundScore = 50;
            fillLEDs(COLOR_RED);
            beep(100);
        }

        score += roundScore;
        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 21: KARAOKE JUDGE
// ============================================================================

uint32_t game_KaraokeJudge() {
    Serial.println("\n🎮 GAME: KARAOKE JUDGE");
    Serial.println("Sing loud and the puck will judge you!");

    beep(200);
    delay(2000);

    Serial.println("🎤 START SINGING! (30 seconds)");
    fillLEDs(COLOR_MAGENTA);
    beep(300);
    delay(2000);

    unsigned long songDuration = 30000;
    unsigned long startTime = millis();

    float totalEnergy = 0;
    float peakEnergy = 0;
    uint32_t measurements = 0;

    while (millis() - startTime < songDuration) {
        float energy = getShakeIntensity();

        totalEnergy += energy;
        measurements++;

        if (energy > peakEnergy) peakEnergy = energy;

        // Visual feedback - reacts to volume
        uint8_t numLEDs = min((int)(energy * 1.5), (int)NUM_LEDS);
        clearLEDs();

        for (int i = 0; i < numLEDs; i++) {
            uint32_t color;
            if (i < NUM_LEDS / 3) {
                color = COLOR_GREEN;
            } else if (i < 2 * NUM_LEDS / 3) {
                color = COLOR_YELLOW;
            } else {
                color = COLOR_RED;
            }
            strip.setPixelColor(i, color);
        }
        strip.show();

        delay(100);
    }

    float avgEnergy = totalEnergy / measurements;

    Serial.println("\n🎤 PERFORMANCE COMPLETE!");
    Serial.printf("📊 Average Energy: %.2f\n", avgEnergy);
    Serial.printf("📊 Peak Energy: %.2f\n", peakEnergy);

    // Judge the performance
    uint32_t score;
    if (avgEnergy > 15.0) {
        Serial.println("🏆 LEGENDARY PERFORMANCE! 10/10");
        score = 1000;
        for (int i = 0; i < 10; i++) {
            fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_MAGENTA);
            beep(100);
            vibrate(100);
            delay(100);
        }
    } else if (avgEnergy > 10.0) {
        Serial.println("⭐ GREAT PERFORMANCE! 8/10");
        score = 800;
        fillLEDs(COLOR_YELLOW);
        beep(300);
        vibrate(200);
    } else if (avgEnergy > 6.0) {
        Serial.println("👍 GOOD EFFORT! 6/10");
        score = 600;
        fillLEDs(COLOR_CYAN);
        beep(200);
    } else {
        Serial.println("😅 NEEDS PRACTICE! 4/10");
        score = 400;
        fillLEDs(COLOR_BLUE);
        beep(150);
    }

    delay(3000);
    return score;
}

// ============================================================================
// GAME 22: WILD CARD
// ============================================================================

uint32_t game_WildCard() {
    Serial.println("\n🎮 GAME: WILD CARD");
    Serial.println("Random commands for the table!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 8;

    const char* commands[] = {
        "Everyone drinks!",
        "Pick someone to drink",
        "Trade seats with someone",
        "Tell your best joke",
        "Group photo time!",
        "Arm wrestle your neighbor",
        "Share an embarrassing story",
        "Do your best dance move"
    };

    uint32_t commandColors[] = {
        COLOR_RED,
        COLOR_GREEN,
        COLOR_BLUE,
        COLOR_YELLOW,
        COLOR_PURPLE,
        COLOR_ORANGE,
        COLOR_CYAN,
        COLOR_MAGENTA
    };

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);
        Serial.println("🎲 Drawing wild card...");

        // Shuffle animation
        for (int i = 0; i < 20; i++) {
            fillLEDs(commandColors[i % 8]);
            beep(40);
            delay(50 + i * 10);
        }

        // Select command
        uint8_t cmdIndex = random(0, 8);
        fillLEDs(commandColors[cmdIndex]);
        beep(300);
        vibrate(200);

        Serial.printf("🎴 WILD CARD: %s\n", commands[cmdIndex]);

        delay(5000);

        score += 100;
    }

    fillLEDs(COLOR_WHITE);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 23: LUCKY SEVEN
// ============================================================================

uint32_t game_LuckySeven() {
    Serial.println("\n🎮 GAME: LUCKY SEVEN");
    Serial.println("Roll the puck like dice!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rolls = 5;
    uint8_t results[5];

    for (int roll = 0; roll < rolls; roll++) {
        Serial.printf("\nRoll %d - Shake to roll!\n", roll + 1);

        fillLEDs(COLOR_CYAN);
        delay(1000);

        // Wait for shake
        bool rolled = false;
        unsigned long waitStart = millis();

        while (!rolled && (millis() - waitStart < 10000)) {
            if (getShakeIntensity() > 20.0) {
                rolled = true;
            }
            delay(50);
        }

        if (!rolled) {
            Serial.println("❌ No roll detected!");
            results[roll] = 0;
            continue;
        }

        // Rolling animation
        Serial.println("🎲 ROLLING...");
        for (int i = 0; i < 20; i++) {
            uint8_t num = random(1, 8);
            clearLEDs();
            for (int j = 0; j < num; j++) {
                strip.setPixelColor(j, COLOR_WHITE);
            }
            strip.show();
            beep(40);
            delay(50 + i * 10);
        }

        // Final result
        uint8_t result = random(1, 8);
        results[roll] = result;

        clearLEDs();
        for (int i = 0; i < result; i++) {
            strip.setPixelColor(i, COLOR_GREEN);
        }
        strip.show();
        beep(200);
        vibrate(150);

        Serial.printf("🎲 Rolled: %d\n", result);
        delay(2000);
    }

    // Check for combos
    Serial.println("\n📊 Checking combos...");

    // Check for three 7s
    int sevenCount = 0;
    for (int i = 0; i < rolls; i++) {
        if (results[i] == 7) sevenCount++;
    }

    if (sevenCount >= 3) {
        Serial.println("🎰 JACKPOT! Three 7s!");
        score += 2000;
        for (int i = 0; i < 10; i++) {
            uint16_t hue = i * 6553;
            fillLEDs(strip.ColorHSV(hue));
            beep(100);
            vibrate(100);
            delay(100);
        }
    } else {
        // Regular scoring
        for (int i = 0; i < rolls; i++) {
            score += results[i] * 50;
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 24: VOLUME WARS
// ============================================================================

uint32_t game_VolumeWars() {
    Serial.println("\n🎮 GAME: VOLUME WARS");
    Serial.println("Who can make the loudest noise?");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);
        Serial.println("🔊 GET READY TO SCREAM!");

        fillLEDs(COLOR_ORANGE);
        delay(2000);

        Serial.println("🔊 SCREAM NOW! (5 seconds)");
        fillLEDs(COLOR_RED);
        beep(300);

        float maxVolume = 0;
        unsigned long screamTime = 5000;
        unsigned long startTime = millis();

        while (millis() - startTime < screamTime) {
            float volume = getShakeIntensity();

            if (volume > maxVolume) maxVolume = volume;

            // Visual meter
            uint8_t numLEDs = min((int)(volume * 1.5), (int)NUM_LEDS);
            clearLEDs();
            for (int i = 0; i < numLEDs; i++) {
                strip.setPixelColor(i, COLOR_RED);
            }
            strip.show();

            delay(50);
        }

        uint32_t roundScore = (uint32_t)(maxVolume * 30);
        score += roundScore;

        Serial.printf("📊 Peak Volume: %.2f\n", maxVolume);
        Serial.printf("💯 Round Score: %lu\n", roundScore);

        if (maxVolume > 25.0) {
            Serial.println("🔥 EARDRUM DESTROYER!");
            fillLEDs(COLOR_RED);
        } else if (maxVolume > 15.0) {
            Serial.println("📢 LOUD!");
            fillLEDs(COLOR_ORANGE);
        } else {
            Serial.println("😴 WEAK!");
            fillLEDs(COLOR_YELLOW);
        }

        beep(200);
        vibrate(200);
        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 25: SHOT ROULETTE
// ============================================================================

uint32_t game_ShotRoulette() {
    Serial.println("\n🎮 GAME: SHOT ROULETTE");
    Serial.println("Who drinks first?");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);
        Serial.println("🎲 Rolling for shot order...");

        // Spin animation
        for (int spin = 0; spin < 30; spin++) {
            uint8_t pos = spin % NUM_LEDS;
            clearLEDs();
            strip.setPixelColor(pos, COLOR_WHITE);
            strip.show();
            beep(35);
            delay(50 + spin * 3);
        }

        // Land on position
        uint8_t position = random(0, NUM_LEDS);
        uint8_t shotType = random(0, 3);

        clearLEDs();

        uint32_t shotColor;
        const char* shotAction;

        switch(shotType) {
            case 0:
                shotColor = COLOR_RED;
                shotAction = "CHUG IT!";
                score += 300;
                break;
            case 1:
                shotColor = COLOR_YELLOW;
                shotAction = "TAKE A SIP";
                score += 150;
                break;
            default:
                shotColor = COLOR_GREEN;
                shotAction = "PASS IT!";
                score += 50;
                break;
        }

        for (int i = 0; i < 3; i++) {
            strip.setPixelColor((position + i) % NUM_LEDS, shotColor);
        }
        strip.show();
        beep(500);
        vibrate(300);

        Serial.printf("🎯 Position %d: %s\n", position + 1, shotAction);

        delay(3000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 26: BALANCE MASTER
// ============================================================================

uint32_t game_BalanceMaster() {
    Serial.println("\n🎮 GAME: BALANCE MASTER");
    Serial.println("Balance the puck on your finger!");

    beep(200);
    delay(2000);

    Serial.println("⚖️  Start balancing... NOW!");
    fillLEDs(COLOR_CYAN);
    beep(300);

    unsigned long balanceTime = 20000; // 20 seconds
    unsigned long startTime = millis();
    unsigned long totalBalanced = 0;
    unsigned long lastGood = millis();

    while (millis() - startTime < balanceTime) {
        sensors_event_t accel, gyro, temp;
        mpu.getEvent(&accel, &gyro, &temp);

        // Check tilt (want it level)
        float tilt = abs(accel.acceleration.x) + abs(accel.acceleration.y);

        bool balanced = (tilt < 12.0); // Well balanced threshold

        if (balanced) {
            totalBalanced += (millis() - lastGood);
            fillLEDs(COLOR_GREEN);

            if (millis() % 1000 < 100) {
                beep(50);
            }
        } else if (tilt < 15.0) {
            fillLEDs(COLOR_YELLOW);
            if (millis() % 500 < 50) {
                vibrate(30);
            }
        } else {
            fillLEDs(COLOR_RED);
            vibrate(100);
            delay(100);
        }

        lastGood = millis();
        delay(50);
    }

    float balancePercent = (float)totalBalanced / balanceTime * 100.0;
    uint32_t score = (uint32_t)(balancePercent * 10);

    Serial.printf("⚖️  Balanced: %.1f%% of time\n", balancePercent);

    if (balancePercent > 80.0) {
        Serial.println("🏆 BALANCE MASTER!");
        fillLEDs(COLOR_YELLOW);
        for (int i = 0; i < 5; i++) {
            beep(100);
            vibrate(100);
            delay(100);
        }
    } else if (balancePercent > 50.0) {
        Serial.println("👍 GOOD BALANCE!");
        fillLEDs(COLOR_GREEN);
        beep(300);
    } else {
        Serial.println("😅 WOBBLY!");
        fillLEDs(COLOR_ORANGE);
        beep(150);
    }

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(3000);
    return score;
}

// ============================================================================
// GAME 27: SPIN MASTER
// ============================================================================

uint32_t game_SpinMaster() {
    Serial.println("\n🎮 GAME: SPIN MASTER");
    Serial.println("Spin the puck as fast as possible!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 3;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d - Spin the puck!\n", round + 1);

        fillLEDs(COLOR_CYAN);
        delay(2000);

        Serial.println("🌀 Detecting spin...");

        float maxSpinRate = 0;
        unsigned long spinDuration = 0;
        unsigned long spinStart = millis();
        bool spinning = false;
        unsigned long spinStarted = 0;

        while (millis() - spinStart < 15000) {
            sensors_event_t accel, gyro, temp;
            mpu.getEvent(&accel, &gyro, &temp);

            float spinRate = abs(gyro.gyro.z);

            if (spinRate > 3.0) {
                if (!spinning) {
                    spinning = true;
                    spinStarted = millis();
                }

                if (spinRate > maxSpinRate) maxSpinRate = spinRate;

                // Visual during spin
                uint8_t intensity = min((int)(spinRate * 3), 255);
                for (int i = 0; i < NUM_LEDS; i++) {
                    strip.setPixelColor(i, strip.Color(0, intensity, intensity));
                }
                strip.show();
            } else if (spinning && spinRate < 1.0) {
                // Spin ended
                spinDuration = millis() - spinStarted;
                break;
            }

            delay(50);
        }

        if (!spinning) {
            Serial.println("❌ NO SPIN DETECTED!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(2000);
            continue;
        }

        uint32_t roundScore = (uint32_t)(maxSpinRate * 100) + (spinDuration / 10);
        score += roundScore;

        Serial.printf("🌀 Max RPM: %.2f rad/s\n", maxSpinRate);
        Serial.printf("⏱️  Duration: %lu ms\n", spinDuration);
        Serial.printf("💯 Round Score: %lu\n", roundScore);

        if (maxSpinRate > 15.0) {
            Serial.println("🔥 TORNADO SPIN!");
            fillLEDs(COLOR_RED);
        } else if (maxSpinRate > 10.0) {
            Serial.println("💨 FAST SPIN!");
            fillLEDs(COLOR_YELLOW);
        } else {
            Serial.println("😅 SLOW SPIN!");
            fillLEDs(COLOR_GREEN);
        }

        beep(300);
        vibrate(200);
        delay(2000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 28: LIGHTNING ROUND
// ============================================================================

uint32_t game_LightningRound() {
    Serial.println("\n🎮 GAME: LIGHTNING ROUND");
    Serial.println("Follow random commands FAST!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t totalCommands = 15;
    uint8_t correctCount = 0;

    const char* commandNames[] = {"TAP 3X!", "SHAKE!", "FREEZE!", "HOLD BUTTON!", "TAP ONCE!"};
    uint8_t commandTypes[] = {0, 1, 2, 3, 4}; // 0=tap3, 1=shake, 2=freeze, 3=hold, 4=tap1
    uint32_t commandColors[] = {COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW, COLOR_CYAN};

    Serial.println("⚡ LIGHTNING ROUND STARTING!");
    delay(2000);

    for (int cmd = 0; cmd < totalCommands; cmd++) {
        uint8_t cmdType = random(0, 5);

        // Show command
        fillLEDs(commandColors[cmdType]);
        beep(100);
        Serial.printf("[%d/%d] %s\n", cmd + 1, totalCommands, commandNames[cmdType]);

        bool success = false;
        unsigned long cmdStart = millis();
        unsigned long cmdDuration = 2000; // 2 seconds per command

        if (cmdType == 0) {
            // TAP 3X
            uint8_t taps = 0;
            while (millis() - cmdStart < cmdDuration) {
                if (readButton()) {
                    taps++;
                    beep(30);
                    if (taps >= 3) {
                        success = true;
                        break;
                    }
                }
                delay(10);
            }
        } else if (cmdType == 1) {
            // SHAKE
            while (millis() - cmdStart < cmdDuration) {
                if (getShakeIntensity() > 15.0) {
                    success = true;
                    break;
                }
                delay(10);
            }
        } else if (cmdType == 2) {
            // FREEZE (don't move)
            success = true; // Assume success unless movement detected
            while (millis() - cmdStart < cmdDuration) {
                if (getShakeIntensity() > 3.0) {
                    success = false;
                    break;
                }
                delay(10);
            }
        } else if (cmdType == 3) {
            // HOLD BUTTON
            unsigned long holdStart = 0;
            bool holding = false;
            while (millis() - cmdStart < cmdDuration) {
                if (!digitalRead(PIN_BUTTON)) { // Button pressed
                    if (!holding) {
                        holding = true;
                        holdStart = millis();
                    }
                    if (millis() - holdStart > 1000) { // Held for 1 second
                        success = true;
                        break;
                    }
                } else {
                    holding = false;
                }
                delay(10);
            }
        } else if (cmdType == 4) {
            // TAP ONCE
            while (millis() - cmdStart < cmdDuration) {
                if (readButton()) {
                    success = true;
                    break;
                }
                delay(10);
            }
        }

        if (success) {
            Serial.println("✅ CORRECT!");
            fillLEDs(COLOR_WHITE);
            beep(100);
            vibrate(100);
            score += 100;
            correctCount++;
        } else {
            Serial.println("❌ MISS!");
            fillLEDs(COLOR_RED);
            beep(300);
            score -= 50;
        }

        delay(300);
        clearLEDs();
        delay(200);
    }

    // Perfect round bonus
    if (correctCount == totalCommands) {
        Serial.println("🏆 PERFECT ROUND! +500 BONUS");
        score += 500;
        for (int i = 0; i < 5; i++) {
            fillLEDs(COLOR_YELLOW);
            beep(100);
            vibrate(100);
            delay(100);
            clearLEDs();
            delay(100);
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("✅ Correct: %d/%d\n", correctCount, totalCommands);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 29: BEAT MASTER
// ============================================================================

uint32_t game_BeatMaster() {
    Serial.println("\n🎮 GAME: BEAT MASTER");
    Serial.println("Keep the rhythm!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t level = 1;
    uint16_t bpm = 60; // Beats per minute

    Serial.println("🎵 Watch the beat...");
    delay(2000);

    while (level <= 8 && bpm <= 120) {
        Serial.printf("Level %d - %d BPM\n", level, bpm);

        unsigned long beatInterval = 60000 / bpm; // Milliseconds per beat
        uint8_t beatsInLevel = 8;
        bool failed = false;

        // Show the pattern first
        Serial.println("Listen to the rhythm...");
        for (int i = 0; i < 3; i++) {
            fillLEDs(COLOR_CYAN);
            beep(100);
            delay(beatInterval);
            clearLEDs();
            delay(beatInterval);
        }

        delay(500);
        Serial.println("Your turn! TAP THE BEAT!");

        unsigned long lastBeat = millis();
        uint8_t correctBeats = 0;

        for (int beat = 0; beat < beatsInLevel; beat++) {
            // LED pulse for timing
            fillLEDs(COLOR_YELLOW);

            unsigned long beatStart = millis();
            bool tapped = false;
            unsigned long tapTime = 0;

            // Wait for tap
            while (millis() - beatStart < beatInterval * 2) {
                if (readButton()) {
                    tapTime = millis() - beatStart;
                    tapped = true;
                    break;
                }
                delay(10);
            }

            clearLEDs();

            if (tapped) {
                // Check timing (±150ms window, narrows as tempo increases)
                uint16_t tolerance = 200 - (level * 15);
                if (tolerance < 75) tolerance = 75;

                long timingError = abs((long)tapTime - (long)beatInterval);

                if (timingError < tolerance) {
                    Serial.println("✅ ON BEAT!");
                    beep(50);
                    vibrate(50);
                    score += 50 * level; // Tempo multiplier
                    correctBeats++;
                } else {
                    Serial.println("❌ OFF BEAT!");
                    beep(200);
                    failed = true;
                    break;
                }
            } else {
                Serial.println("❌ MISSED BEAT!");
                beep(300);
                failed = true;
                break;
            }

            // Wait for next beat
            delay(max((long)0, (long)beatInterval - (long)(millis() - beatStart)));
            lastBeat = millis();
        }

        if (failed) {
            Serial.println("💀 RHYTHM BROKEN!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(1500);
            break;
        } else {
            Serial.println("🎵 LEVEL COMPLETE!");
            fillLEDs(COLOR_GREEN);
            beep(200);
            vibrate(200);
            delay(1500);
            level++;
            bpm += 10; // Speed up
        }
    }

    if (level > 8) {
        Serial.println("🏆 RHYTHM MASTER!");
        for (int i = 0; i < 5; i++) {
            fillLEDs(i % 2 ? COLOR_MAGENTA : COLOR_CYAN);
            beep(100);
            vibrate(100);
            delay(150);
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 30: DOUBLE OR NOTHING
// ============================================================================

uint32_t game_DoubleOrNothing() {
    Serial.println("\n🎮 GAME: DOUBLE OR NOTHING");
    Serial.println("Bank it or risk it all!");

    beep(200);
    delay(1000);

    uint32_t totalBanked = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);

        uint32_t currentPoints = 100;
        uint8_t multiplier = 1;
        bool busted = false;

        Serial.printf("Starting with: %lu points\n", currentPoints);
        delay(1000);

        while (!busted && multiplier <= 8) {
            fillLEDs(COLOR_CYAN);

            Serial.printf("💰 Current: %lu points (x%d)\n", currentPoints, multiplier);
            Serial.println("Doubling...");

            // Wait period with increasing bust chance
            unsigned long waitTime = random(2000, 4000);
            unsigned long waitStart = millis();
            bool banked = false;

            while (millis() - waitStart < waitTime) {
                // Flash green = bank option
                if ((millis() / 300) % 2 == 0) {
                    fillLEDs(COLOR_GREEN);
                } else {
                    fillLEDs(COLOR_OFF);
                }

                if (readButton()) {
                    banked = true;
                    break;
                }

                delay(10);
            }

            if (banked) {
                Serial.printf("✅ BANKED: %lu points\n", currentPoints);
                fillLEDs(COLOR_GREEN);
                beep(200);
                vibrate(200);
                totalBanked += currentPoints;
                delay(1500);
                break;
            }

            // Check for bust (probability increases with multiplier)
            uint8_t bustChance = 10 + (multiplier * 10); // 20%, 30%, 40%...
            if (random(0, 100) < bustChance) {
                Serial.println("💥 BUST! Lost everything!");
                for (int i = 0; i < 5; i++) {
                    fillLEDs(COLOR_RED);
                    beep(100);
                    vibrate(100);
                    delay(100);
                    clearLEDs();
                    delay(100);
                }
                busted = true;
                delay(1000);
            } else {
                // Successful double!
                currentPoints *= 2;
                multiplier++;
                Serial.printf("⬆️  DOUBLED to %lu points!\n", currentPoints);
                fillLEDs(COLOR_YELLOW);
                beep(150);
                vibrate(150);
                delay(1000);
            }
        }

        if (multiplier > 8 && !busted) {
            Serial.printf("🏆 MAX MULTIPLIER! Auto-bank: %lu\n", currentPoints);
            totalBanked += currentPoints;
        }

        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 TOTAL BANKED: %lu\n", totalBanked);

    delay(2000);
    return totalBanked;
}

// ============================================================================
// GAME 31: COMBO BREAKER
// ============================================================================

uint32_t game_ComboBreaker() {
    Serial.println("\n🎮 GAME: COMBO BREAKER");
    Serial.println("Execute the combo sequence!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t level = 1;

    // Move types: 0=tap, 1=shake, 2=hold, 3=double-tap
    uint32_t moveColors[] = {COLOR_BLUE, COLOR_RED, COLOR_YELLOW, COLOR_GREEN};
    const char* moveNames[] = {"TAP", "SHAKE", "HOLD 2s", "DOUBLE TAP"};

    while (level <= 7) {
        Serial.printf("\nLevel %d - ", level);

        uint8_t comboLength = min(level + 2, 7); // 3 to 7 moves
        uint8_t combo[7];

        // Generate random combo
        Serial.print("Combo: ");
        for (int i = 0; i < comboLength; i++) {
            combo[i] = random(0, 4);
            Serial.print(moveNames[combo[i]]);
            if (i < comboLength - 1) Serial.print(" → ");
        }
        Serial.println();

        delay(1000);

        // Show combo
        Serial.println("Watch the combo...");
        for (int i = 0; i < comboLength; i++) {
            fillLEDs(moveColors[combo[i]]);
            beep(100);
            delay(800);
            clearLEDs();
            delay(400);
        }

        delay(1000);
        Serial.println("Execute it NOW!");

        // Execute combo
        bool failed = false;
        for (int i = 0; i < comboLength; i++) {
            fillLEDs(COLOR_CYAN);
            beep(50);

            Serial.printf("Move %d: %s\n", i + 1, moveNames[combo[i]]);

            bool moveSuccess = false;
            unsigned long moveStart = millis();
            unsigned long moveTimeout = 5000;

            if (combo[i] == 0) {
                // TAP
                while (millis() - moveStart < moveTimeout) {
                    if (readButton()) {
                        moveSuccess = true;
                        break;
                    }
                    delay(10);
                }
            } else if (combo[i] == 1) {
                // SHAKE
                while (millis() - moveStart < moveTimeout) {
                    if (getShakeIntensity() > 15.0) {
                        moveSuccess = true;
                        break;
                    }
                    delay(10);
                }
            } else if (combo[i] == 2) {
                // HOLD 2s
                unsigned long holdStart = 0;
                bool holding = false;
                while (millis() - moveStart < moveTimeout) {
                    if (!digitalRead(PIN_BUTTON)) {
                        if (!holding) {
                            holding = true;
                            holdStart = millis();
                        }
                        if (millis() - holdStart > 2000) {
                            moveSuccess = true;
                            break;
                        }
                    } else {
                        holding = false;
                    }
                    delay(10);
                }
            } else if (combo[i] == 3) {
                // DOUBLE TAP
                uint8_t taps = 0;
                while (millis() - moveStart < moveTimeout && taps < 2) {
                    if (readButton()) {
                        taps++;
                        beep(30);
                        if (taps == 2) {
                            moveSuccess = true;
                            break;
                        }
                        delay(100);
                    }
                    delay(10);
                }
            }

            if (moveSuccess) {
                Serial.println("✅ CORRECT!");
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                delay(300);
            } else {
                Serial.println("❌ COMBO BROKEN!");
                fillLEDs(COLOR_RED);
                beep(500);
                vibrate(300);
                failed = true;
                delay(1500);
                break;
            }

            clearLEDs();
            delay(200);
        }

        if (failed) {
            break;
        } else {
            Serial.println("🔥 COMBO COMPLETE!");
            uint32_t comboScore = comboLength * 100;
            score += comboScore;
            Serial.printf("+%lu points\n", comboScore);

            fillLEDs(COLOR_YELLOW);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }

            level++;
            delay(1500);
        }
    }

    if (level > 7) {
        Serial.println("🏆 COMBO MASTER!");
        for (int i = 0; i < 5; i++) {
            fillLEDs(i % 2 ? COLOR_RED : COLOR_YELLOW);
            beep(100);
            vibrate(100);
            delay(100);
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 32: LOCKOUT
// ============================================================================

uint32_t game_Lockout() {
    Serial.println("\n🎮 GAME: LOCKOUT");
    Serial.println("Tap GREEN, avoid RED!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 10;
    uint8_t hitCount = 0;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);

        // Determine if this is a fake-out (increases with round)
        uint8_t fakeChance = round * 5; // 0%, 5%, 10%... up to 45%
        bool isFake = (random(0, 100) < fakeChance);

        // Random wait
        fillLEDs(COLOR_OFF);
        Serial.println("Wait for it...");
        delay(random(1000, 3000));

        // Flash!
        uint32_t flashColor = isFake ? COLOR_RED : COLOR_GREEN;
        fillLEDs(flashColor);
        beep(300);
        vibrate(100);

        unsigned long flashStart = millis();
        bool tapped = false;
        unsigned long reactionTime = 0;

        // Wait for reaction (max 1 second)
        while (millis() - flashStart < 1000) {
            if (readButton()) {
                reactionTime = millis() - flashStart;
                tapped = true;
                break;
            }
            delay(10);
        }

        clearLEDs();

        if (isFake) {
            if (tapped) {
                Serial.println("💀 LOCKOUT! You tapped on RED!");
                fillLEDs(COLOR_RED);
                for (int i = 0; i < 5; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                    clearLEDs();
                    delay(100);
                    fillLEDs(COLOR_RED);
                }
                score -= 500;
                delay(1000);
            } else {
                Serial.println("✅ AVOIDED THE TRAP!");
                fillLEDs(COLOR_CYAN);
                beep(100);
                delay(1000);
            }
        } else {
            if (tapped) {
                Serial.printf("✅ HIT! (%lu ms)\n", reactionTime);
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                score += 200;
                hitCount++;
                delay(1000);
            } else {
                Serial.println("❌ TOO SLOW!");
                fillLEDs(COLOR_YELLOW);
                beep(200);
                delay(1000);
            }
        }

        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("✅ Successful hits: %d/%d\n", hitCount, rounds);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 33: PRECISION STRIKE
// ============================================================================

uint32_t game_PrecisionStrike() {
    Serial.println("\n🎮 GAME: PRECISION STRIKE");
    Serial.println("Hit the target EXACTLY!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 10;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);

        // Pick random target LED
        uint8_t targetLED = random(0, NUM_LEDS);

        // Show target
        clearLEDs();
        strip.setPixelColor(targetLED, COLOR_WHITE);
        strip.show();
        Serial.printf("Target: Position %d\n", targetLED);
        delay(1500);

        // Sweep speed increases with rounds
        uint16_t sweepDelay = max(30, 150 - (round * 12));
        uint8_t tolerance = max(0, 3 - (round / 3)); // 3 LEDs tolerance, down to 0

        Serial.println("Sweeping...");

        uint8_t currentPos = 0;
        bool hit = false;
        unsigned long sweepStart = millis();

        while (!hit && (millis() - sweepStart < 10000)) {
            clearLEDs();
            // Show sweep LED
            strip.setPixelColor(currentPos, COLOR_GREEN);
            // Show target
            strip.setPixelColor(targetLED, COLOR_WHITE);
            strip.show();

            if (readButton()) {
                // Check precision
                uint8_t distance = min(abs(currentPos - targetLED),
                                      NUM_LEDS - abs(currentPos - targetLED));

                if (distance == 0) {
                    Serial.println("🎯 PERFECT HIT!");
                    fillLEDs(COLOR_YELLOW);
                    beep(100);
                    vibrate(200);
                    score += 300;
                } else if (distance <= tolerance) {
                    Serial.println("✅ CLOSE!");
                    fillLEDs(COLOR_GREEN);
                    beep(150);
                    vibrate(100);
                    score += 100;
                } else {
                    Serial.println("❌ MISS!");
                    fillLEDs(COLOR_RED);
                    beep(300);
                }

                hit = true;
                delay(1500);
            }

            currentPos = (currentPos + 1) % NUM_LEDS;
            delay(sweepDelay);
        }

        if (!hit) {
            Serial.println("⏰ TIMEOUT!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(1500);
        }

        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 34: GAUNTLET MODE
// ============================================================================

uint32_t game_GauntletMode() {
    Serial.println("\n🎮 GAME: GAUNTLET MODE");
    Serial.println("Complete 5 challenges!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t attempts = 3;
    unsigned long startTime = millis();

    const char* challengeNames[] = {
        "Tap 15 times in 3 seconds",
        "Hold still for 4 seconds",
        "Shake to 20 m/s²",
        "Hit the moving target",
        "Repeat 3-LED pattern"
    };

    for (int attempt = 1; attempt <= attempts; attempt++) {
        Serial.printf("\n🎯 ATTEMPT %d/%d\n", attempt, attempts);
        delay(1500);

        bool allPassed = true;

        for (int challenge = 0; challenge < 5; challenge++) {
            Serial.printf("\nChallenge %d: %s\n", challenge + 1, challengeNames[challenge]);

            fillLEDs(COLOR_CYAN);
            beep(100);
            delay(1500);

            bool passed = false;

            if (challenge == 0) {
                // Tap 15 times in 3 seconds
                Serial.println("TAP FAST!");
                fillLEDs(COLOR_GREEN);
                beep(200);

                uint8_t taps = 0;
                unsigned long tapStart = millis();

                while (millis() - tapStart < 3000) {
                    if (readButton()) {
                        taps++;
                        beep(30);
                    }
                    delay(10);
                }

                Serial.printf("Taps: %d\n", taps);
                passed = (taps >= 15);

            } else if (challenge == 1) {
                // Hold still for 4 seconds
                Serial.println("FREEZE!");
                fillLEDs(COLOR_BLUE);
                beep(200);

                passed = true;
                unsigned long freezeStart = millis();

                while (millis() - freezeStart < 4000) {
                    if (getShakeIntensity() > 3.0) {
                        passed = false;
                        break;
                    }
                    delay(10);
                }

            } else if (challenge == 2) {
                // Shake to 20 m/s²
                Serial.println("SHAKE HARD!");
                fillLEDs(COLOR_RED);
                beep(200);

                float maxShake = 0;
                unsigned long shakeStart = millis();

                while (millis() - shakeStart < 5000) {
                    float shake = getShakeIntensity();
                    if (shake > maxShake) maxShake = shake;
                    if (maxShake >= 20.0) {
                        passed = true;
                        break;
                    }
                    delay(10);
                }

                Serial.printf("Peak: %.2f m/s²\n", maxShake);

            } else if (challenge == 3) {
                // Hit the moving target
                Serial.println("HIT THE TARGET!");

                uint8_t targetLED = random(0, NUM_LEDS);
                uint8_t currentLED = 0;
                unsigned long targetStart = millis();

                while (!passed && (millis() - targetStart < 5000)) {
                    clearLEDs();
                    strip.setPixelColor(currentLED, COLOR_GREEN);
                    strip.setPixelColor(targetLED, COLOR_WHITE);
                    strip.show();

                    if (readButton() && currentLED == targetLED) {
                        passed = true;
                    }

                    currentLED = (currentLED + 1) % NUM_LEDS;
                    delay(100);
                }

            } else if (challenge == 4) {
                // Repeat 3-LED pattern
                Serial.println("WATCH PATTERN...");

                uint8_t pattern[3];
                for (int i = 0; i < 3; i++) {
                    pattern[i] = random(0, 4) * 4;
                }

                // Show pattern
                for (int i = 0; i < 3; i++) {
                    clearLEDs();
                    strip.setPixelColor(pattern[i], COLOR_YELLOW);
                    strip.setPixelColor(pattern[i] + 1, COLOR_YELLOW);
                    strip.show();
                    beep(100);
                    delay(600);
                    clearLEDs();
                    delay(300);
                }

                Serial.println("SHAKE TO REPEAT!");

                passed = true;
                for (int i = 0; i < 3; i++) {
                    fillLEDs(COLOR_CYAN);
                    beep(50);

                    unsigned long waitStart = millis();
                    bool shook = false;

                    while (!shook && (millis() - waitStart < 5000)) {
                        if (getShakeIntensity() > 10.0) {
                            shook = true;
                            clearLEDs();
                            strip.setPixelColor(pattern[i], COLOR_GREEN);
                            strip.setPixelColor(pattern[i] + 1, COLOR_GREEN);
                            strip.show();
                            beep(100);
                            delay(500);
                        }
                        delay(50);
                    }

                    if (!shook) {
                        passed = false;
                        break;
                    }
                }
            }

            if (passed) {
                Serial.println("✅ PASSED!");
                fillLEDs(COLOR_GREEN);
                beep(100);
                vibrate(100);
                delay(1000);
            } else {
                Serial.println("❌ FAILED!");
                fillLEDs(COLOR_RED);
                beep(500);
                vibrate(300);
                allPassed = false;
                delay(1500);
                break;
            }
        }

        if (allPassed) {
            unsigned long completionTime = (millis() - startTime) / 1000;
            score = max((uint32_t)1000, (uint32_t)(5000 - (completionTime * 50)));

            if (attempt == 1) {
                score += 1000; // First attempt bonus
            }

            Serial.println("\n🏆 GAUNTLET COMPLETE!");
            Serial.printf("⏱️  Time: %lu seconds\n", completionTime);

            for (int i = 0; i < 5; i++) {
                fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_GREEN);
                beep(100);
                vibrate(100);
                delay(150);
            }

            break;
        } else {
            if (attempt < attempts) {
                Serial.println("\n🔄 TRY AGAIN!");
                delay(2000);
            }
        }
    }

    if (score == 0) {
        Serial.println("\n💀 GAUNTLET FAILED!");
        score = 100; // Consolation points
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 35: RUSSIAN ROULETTE
// ============================================================================

uint32_t game_RussianRoulette() {
    Serial.println("\n🎮 GAME: RUSSIAN ROULETTE");
    Serial.println("Bank before you BANG!");

    beep(200);
    delay(1000);

    uint32_t totalBanked = 0;
    uint8_t rounds = 3;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\n🔫 ROUND %d\n", round + 1);

        uint8_t loadedPosition = random(0, 6);
        uint8_t currentPosition = 0;
        uint32_t roundPoints = 0;
        bool banged = false;

        Serial.println("Chamber loaded...");
        delay(1500);

        while (currentPosition < 6 && !banged) {
            // Show current position
            clearLEDs();
            for (int i = 0; i <= currentPosition; i++) {
                strip.setPixelColor(i * (NUM_LEDS / 6), COLOR_CYAN);
            }
            strip.show();

            Serial.printf("\nPosition %d/6 - %lu points\n", currentPosition + 1, roundPoints + 100);
            Serial.println("TAP to advance (risk) or HOLD 3s to bank");

            unsigned long waitStart = millis();
            bool banked = false;
            bool advanced = false;
            unsigned long holdStart = 0;
            bool holding = false;

            while (!banked && !advanced) {
                // Check for button hold (bank)
                if (!digitalRead(PIN_BUTTON)) {
                    if (!holding) {
                        holding = true;
                        holdStart = millis();
                        fillLEDs(COLOR_GREEN);
                    }
                    if (millis() - holdStart > 3000) {
                        banked = true;
                    }
                } else {
                    if (holding && millis() - holdStart < 500) {
                        // Quick tap = advance
                        advanced = true;
                    }
                    holding = false;
                    // Restore position display
                    clearLEDs();
                    for (int i = 0; i <= currentPosition; i++) {
                        strip.setPixelColor(i * (NUM_LEDS / 6), COLOR_CYAN);
                    }
                    strip.show();
                }

                delay(10);
            }

            if (banked) {
                Serial.printf("✅ BANKED: %lu points\n", roundPoints);
                fillLEDs(COLOR_GREEN);
                beep(200);
                vibrate(200);
                totalBanked += roundPoints;
                delay(1500);
                break;
            } else if (advanced) {
                roundPoints += 100;

                if (currentPosition == loadedPosition) {
                    // BANG!
                    Serial.println("\n💥 BANG! Lost everything!");
                    for (int i = 0; i < 6; i++) {
                        fillLEDs(COLOR_RED);
                        beep(100);
                        vibrate(150);
                        delay(100);
                        clearLEDs();
                        delay(100);
                    }
                    banged = true;
                    delay(1500);
                } else {
                    Serial.println("*click* Safe!");
                    fillLEDs(COLOR_YELLOW);
                    beep(100);
                    vibrate(100);
                    delay(800);
                    currentPosition++;
                }
            }
        }

        if (currentPosition == 6 && !banged) {
            Serial.printf("🏆 SURVIVED ALL 6! Auto-bank: %lu\n", roundPoints);
            totalBanked += roundPoints;
        }

        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 TOTAL BANKED: %lu\n", totalBanked);

    delay(2000);
    return totalBanked;
}

// ============================================================================
// GAME 36: MARATHON MODE
// ============================================================================

uint32_t game_MarathonMode() {
    Serial.println("\n🎮 GAME: MARATHON MODE");
    Serial.println("Tap once per second - how long can you last?");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint16_t tapCount = 0;
    uint16_t tolerance = 150; // Start at ±150ms
    bool failed = false;

    Serial.println("🏃 MARATHON STARTING!");
    Serial.println("Tap with the LED pulse...");
    delay(2000);

    unsigned long lastTap = millis();

    while (!failed) {
        // LED pulse (1 Hz)
        unsigned long pulseStart = millis();

        // Breathing effect for 1 second
        for (int i = 0; i < 20; i++) {
            float brightness = (sin(i * 0.314) + 1.0) / 2.0; // Full cycle in 1 second
            uint8_t b = 100 + (brightness * 155);
            fillLEDs(strip.Color(0, b, b));
            delay(50);
        }

        // Wait for tap
        bool tapped = false;
        unsigned long tapTime = 0;
        unsigned long windowStart = millis();

        while (millis() - windowStart < 500) { // 500ms window after pulse
            if (readButton()) {
                tapTime = millis() - pulseStart;
                tapped = true;
                break;
            }
            delay(10);
        }

        if (tapped) {
            // Check timing
            long error = abs((long)tapTime - 1000);

            if (error < tolerance) {
                tapCount++;
                score += 10;

                // Streak bonuses
                if (tapCount % 50 == 0) {
                    Serial.printf("🔥 %d TAP STREAK! +500 BONUS\n", tapCount);
                    score += 500;
                    for (int i = 0; i < 3; i++) {
                        fillLEDs(COLOR_YELLOW);
                        beep(100);
                        vibrate(100);
                        delay(100);
                        clearLEDs();
                        delay(100);
                    }
                }

                // Increase difficulty every 20 taps
                if (tapCount % 20 == 0 && tolerance > 75) {
                    tolerance -= 15;
                    Serial.printf("⚠️  Tolerance narrowed to ±%dms\n", tolerance);
                }

                beep(50);

                if (tapCount % 10 == 0) {
                    Serial.printf("✅ %d taps - Score: %lu\n", tapCount, score);
                }

            } else {
                Serial.printf("❌ OFF RHYTHM! (Error: %ld ms)\n", error);
                fillLEDs(COLOR_RED);
                beep(500);
                vibrate(300);
                failed = true;
                delay(1500);
            }
        } else {
            Serial.println("❌ MISSED TAP!");
            fillLEDs(COLOR_RED);
            beep(500);
            vibrate(300);
            failed = true;
            delay(1500);
        }

        lastTap = millis();
    }

    Serial.println("\n🏁 MARATHON ENDED!");
    Serial.printf("🏃 Total taps: %d\n", tapCount);

    if (tapCount >= 100) {
        Serial.println("🏆 LEGENDARY ENDURANCE!");
        for (int i = 0; i < 5; i++) {
            fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_MAGENTA);
            beep(100);
            vibrate(100);
            delay(150);
        }
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 37: MIRROR MATCH
// ============================================================================

uint32_t game_MirrorMatch() {
    Serial.println("\n🎮 GAME: MIRROR MATCH");
    Serial.println("Tap when the pattern repeats!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 8;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d\n", round + 1);

        // Pattern length increases
        uint8_t patternLength = min(3 + (round / 2), 8);
        uint8_t pattern[8];

        // Generate pattern
        for (int i = 0; i < patternLength; i++) {
            pattern[i] = random(0, NUM_LEDS);
        }

        Serial.println("Watch the pattern...");
        delay(1000);

        // Show pattern 3 times
        for (int repeat = 0; repeat < 3; repeat++) {
            for (int i = 0; i < patternLength; i++) {
                clearLEDs();
                strip.setPixelColor(pattern[i], COLOR_CYAN);
                strip.show();
                beep(80);
                delay(400);
            }
            clearLEDs();
            delay(600);
        }

        Serial.println("Tap when it REPEATS!");
        delay(500);

        // Play pattern again, player should tap on 3rd repeat
        bool tappedCorrectly = false;
        bool tappedEarly = false;

        for (int repeat = 0; repeat < 3; repeat++) {
            for (int i = 0; i < patternLength; i++) {
                clearLEDs();
                strip.setPixelColor(pattern[i], COLOR_CYAN);
                strip.show();
                beep(80);

                // Check for tap
                unsigned long checkStart = millis();
                while (millis() - checkStart < 400) {
                    if (readButton()) {
                        if (repeat == 2) {
                            // Correct! Tapped on 3rd repeat
                            tappedCorrectly = true;
                        } else {
                            // Too early!
                            tappedEarly = true;
                        }
                        break;
                    }
                    delay(10);
                }

                if (tappedCorrectly || tappedEarly) break;
            }

            if (tappedCorrectly || tappedEarly) break;

            clearLEDs();
            delay(600);
        }

        if (tappedCorrectly) {
            Serial.println("✅ PERFECT ANTICIPATION!");
            fillLEDs(COLOR_GREEN);
            beep(200);
            vibrate(200);
            score += 200;
            delay(1500);
        } else if (tappedEarly) {
            Serial.println("❌ TOO EARLY!");
            fillLEDs(COLOR_YELLOW);
            beep(300);
            score -= 100;
            delay(1500);
        } else {
            Serial.println("❌ MISSED!");
            fillLEDs(COLOR_RED);
            beep(500);
            delay(1500);
        }

        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 38: PERFECT HOLD
// ============================================================================

uint32_t game_PerfectHold() {
    Serial.println("\n🎮 GAME: PERFECT HOLD");
    Serial.println("Hold the button for EXACTLY 5.00 seconds!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/5\n", round + 1);
        Serial.println("Get ready...");

        fillLEDs(COLOR_CYAN);
        delay(2000);

        Serial.println("PRESS AND HOLD NOW!");
        fillLEDs(COLOR_YELLOW);
        beep(300);
        vibrate(100);

        // Wait for button press
        unsigned long pressStart = 0;
        bool pressed = false;

        while (!pressed) {
            if (!digitalRead(PIN_BUTTON)) {
                pressStart = millis();
                pressed = true;
                Serial.println("⏱️  Timing started...");
                fillLEDs(COLOR_GREEN);
                beep(50);
            }
            delay(10);
        }

        // Wait for release while showing progress
        unsigned long holdDuration = 0;
        bool released = false;

        while (!released) {
            if (digitalRead(PIN_BUTTON)) { // Button released
                holdDuration = millis() - pressStart;
                released = true;
            } else {
                // Show progress with LED ring (fills up over 5 seconds)
                unsigned long elapsed = millis() - pressStart;
                uint8_t litLEDs = min((uint8_t)NUM_LEDS, (uint8_t)((elapsed * NUM_LEDS) / 5000));

                clearLEDs();
                for (int i = 0; i < litLEDs; i++) {
                    strip.setPixelColor(i, COLOR_GREEN);
                }
                strip.show();
            }
            delay(10);
        }

        // Calculate accuracy
        long error = abs((long)holdDuration - 5000); // Error in ms
        float errorSeconds = error / 1000.0;

        Serial.printf("⏱️  Hold time: %.3f seconds\n", holdDuration / 1000.0);
        Serial.printf("🎯 Target: 5.000 seconds\n");
        Serial.printf("📊 Error: %.3f seconds\n", errorSeconds);

        uint32_t roundScore = 0;

        if (error < 10) { // Within 10ms = PERFECT
            Serial.println("🏆 PERFECT! (±0.010s)");
            fillLEDs(COLOR_YELLOW);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
            roundScore = 1000;
        } else if (error < 50) { // Within 50ms
            Serial.println("🎯 EXCELLENT! (±0.050s)");
            fillLEDs(COLOR_GREEN);
            beep(200);
            vibrate(200);
            roundScore = 500;
        } else if (error < 100) { // Within 100ms
            Serial.println("✅ GREAT! (±0.100s)");
            fillLEDs(COLOR_CYAN);
            beep(150);
            vibrate(150);
            roundScore = 300;
        } else if (error < 250) { // Within 250ms
            Serial.println("👍 GOOD! (±0.250s)");
            fillLEDs(COLOR_BLUE);
            beep(100);
            vibrate(100);
            roundScore = 150;
        } else if (error < 500) { // Within 500ms
            Serial.println("😐 OKAY (±0.500s)");
            fillLEDs(COLOR_ORANGE);
            beep(100);
            roundScore = 50;
        } else {
            Serial.println("❌ MISSED!");
            fillLEDs(COLOR_RED);
            beep(300);
            roundScore = 0;
        }

        score += roundScore;
        Serial.printf("+%lu points\n", roundScore);

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 39: COUNTDOWN SNIPER
// ============================================================================

uint32_t game_CountdownSniper() {
    Serial.println("\n🎮 GAME: COUNTDOWN SNIPER");
    Serial.println("Tap at EXACTLY 0 on the countdown!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 8;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/8\n", round + 1);

        fillLEDs(COLOR_CYAN);
        delay(1500);

        Serial.println("🎯 Countdown starting...");
        delay(1000);

        // Countdown from 5 to 0
        for (int count = 5; count >= 0; count--) {
            // Show countdown on LEDs
            clearLEDs();
            int litCount = count * 3; // 0, 3, 6, 9, 12, 15 LEDs
            for (int i = 0; i < min(litCount, (int)NUM_LEDS); i++) {
                strip.setPixelColor(i, COLOR_YELLOW);
            }
            strip.show();

            if (count > 0) {
                Serial.printf("%d...\n", count);
                beep(100);
                delay(1000);
            }
        }

        // The moment of truth - exactly at 0
        Serial.println("NOW!");
        fillLEDs(COLOR_GREEN);
        beep(200);
        vibrate(100);

        unsigned long zeroMoment = millis();
        bool tapped = false;
        unsigned long tapTime = 0;

        // Wait for tap (1 second window)
        while (millis() - zeroMoment < 1000) {
            if (readButton()) {
                tapTime = millis() - zeroMoment;
                tapped = true;
                break;
            }
            delay(10);
        }

        clearLEDs();

        if (tapped) {
            Serial.printf("⏱️  Reaction time: %lu ms\n", tapTime);

            uint32_t roundScore = 0;

            if (tapTime < 50) { // Within 50ms
                Serial.println("🎯 PERFECT SNIPE!");
                fillLEDs(COLOR_YELLOW);
                for (int i = 0; i < 3; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
                roundScore = 500;
            } else if (tapTime < 100) {
                Serial.println("🔥 EXCELLENT!");
                fillLEDs(COLOR_GREEN);
                beep(150);
                vibrate(150);
                roundScore = 300;
            } else if (tapTime < 200) {
                Serial.println("✅ GREAT!");
                fillLEDs(COLOR_CYAN);
                beep(100);
                vibrate(100);
                roundScore = 150;
            } else if (tapTime < 350) {
                Serial.println("👍 GOOD!");
                fillLEDs(COLOR_BLUE);
                beep(100);
                roundScore = 75;
            } else {
                Serial.println("😐 TOO SLOW!");
                fillLEDs(COLOR_ORANGE);
                beep(200);
                roundScore = 25;
            }

            score += roundScore;
            Serial.printf("+%lu points\n", roundScore);

        } else {
            Serial.println("❌ MISSED!");
            fillLEDs(COLOR_RED);
            beep(500);
        }

        delay(1500);
        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 40: REACTION CHAIN
// ============================================================================

uint32_t game_ReactionChain() {
    Serial.println("\n🎮 GAME: REACTION CHAIN");
    Serial.println("Tap with EXACTLY 1 second between each tap!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t targetTaps = 10;
    uint16_t tolerance = 150; // ±150ms

    Serial.println("🔗 Starting chain...");
    Serial.println("Tap to begin, then keep 1-second rhythm!");
    delay(2000);

    // Wait for first tap
    fillLEDs(COLOR_CYAN);
    Serial.println("TAP to start the chain!");

    while (!readButton()) {
        delay(10);
    }

    unsigned long lastTap = millis();
    uint8_t tapCount = 1;
    uint8_t perfectCount = 0;
    bool chainBroken = false;

    fillLEDs(COLOR_GREEN);
    beep(100);
    Serial.println("1️⃣ Chain started! Keep the rhythm...");

    delay(200); // Debounce

    while (tapCount < targetTaps && !chainBroken) {
        // LED breathing at 1Hz to show rhythm
        unsigned long elapsed = millis() - lastTap;

        // Show progress
        float progress = (elapsed % 1000) / 1000.0;
        uint8_t brightness = 50 + (progress * 200);
        fillLEDs(strip.Color(0, brightness, brightness));

        // Check for tap
        if (readButton()) {
            unsigned long timeSinceLast = millis() - lastTap;
            long error = abs((long)timeSinceLast - 1000);

            tapCount++;

            Serial.printf("%d️⃣ Tap %d: %lu ms (", tapCount, tapCount, timeSinceLast);

            if (error < 50) { // Perfect
                Serial.println("PERFECT!)");
                fillLEDs(COLOR_YELLOW);
                beep(100);
                vibrate(100);
                score += 200;
                perfectCount++;
            } else if (error < tolerance) { // Good
                Serial.println("GOOD!)");
                fillLEDs(COLOR_GREEN);
                beep(80);
                vibrate(80);
                score += 100;
            } else { // Chain broken
                Serial.println("CHAIN BROKEN!)");
                fillLEDs(COLOR_RED);
                for (int i = 0; i < 3; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
                chainBroken = true;
            }

            lastTap = millis();
            delay(200); // Debounce
        }

        // Check for timeout (took too long)
        if (millis() - lastTap > 2000) {
            Serial.println("⏰ TIMEOUT! Chain broken!");
            fillLEDs(COLOR_RED);
            beep(500);
            chainBroken = true;
        }

        delay(10);
    }

    clearLEDs();

    if (tapCount >= targetTaps) {
        Serial.println("\n🏆 CHAIN COMPLETE!");

        // Bonus for perfect chain
        if (perfectCount == targetTaps - 1) { // All taps perfect (minus first tap)
            Serial.println("💎 FLAWLESS CHAIN! +1000 BONUS");
            score += 1000;
            for (int i = 0; i < 5; i++) {
                fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_MAGENTA);
                beep(100);
                vibrate(100);
                delay(150);
            }
        } else {
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
        }
    } else {
        Serial.printf("\n💔 Chain broken at tap %d/%d\n", tapCount, targetTaps);
    }

    delay(1500);

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("🔗 Successful taps: %d/%d\n", tapCount, targetTaps);
    Serial.printf("🎯 Perfect taps: %d\n", perfectCount);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 40: JUDAS MODE (Betrayal Game)
// ============================================================================

uint32_t game_JudasMode() {
    Serial.println("\n🎮 GAME: JUDAS MODE");
    Serial.println("Everyone shakes to contribute. One player is JUDAS...");
    Serial.println("Judas can STEAL by holding button for 3 seconds");
    Serial.println("Others can ACCUSE by tapping during countdown");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint32_t pot = 0;

    // Randomly become Judas (20% chance)
    bool isJudas = (random(100) < 20);

    if (isJudas) {
        Serial.println("🗡️ YOU ARE JUDAS! 🗡️");
        fillLEDs(COLOR_RED);
        vibrate(500);
        delay(2000);
    } else {
        Serial.println("👼 You are INNOCENT");
        fillLEDs(COLOR_GREEN);
        delay(2000);
    }

    // Everyone "contributes" by shaking
    Serial.println("\nShake to contribute to the pot!");
    fillLEDs(COLOR_CYAN);

    unsigned long phaseStart = millis();
    while (millis() - phaseStart < 5000) {
        float shake = getShakeIntensity();
        if (shake > 5.0) {
            pot += 10;
            beep(30);
            // Show pot filling
            int litLEDs = min((int)NUM_LEDS, (int)(pot / 50));
            clearLEDs();
            for (int i = 0; i < litLEDs; i++) {
                strip.setPixelColor(i, COLOR_YELLOW);
            }
            strip.show();
            delay(50);
        }
    }

    Serial.printf("💰 Total pot: %lu points\n", pot);
    delay(1000);

    // Judas decision phase
    if (isJudas) {
        Serial.println("\n🗡️ HOLD button for 3s to STEAL THE POT!");
        fillLEDs(COLOR_RED);

        unsigned long stealWindow = millis();
        bool stole = false;
        unsigned long holdStart = 0;
        bool holding = false;

        while (millis() - stealWindow < 8000 && !stole) {
            if (!digitalRead(PIN_BUTTON) && !holding) {
                holdStart = millis();
                holding = true;
                Serial.println("⏱️ Stealing...");
            }

            if (holding && digitalRead(PIN_BUTTON)) {
                holding = false;
                Serial.println("❌ Released too early!");
            }

            if (holding && (millis() - holdStart > 3000)) {
                stole = true;
                Serial.println("💰 YOU STOLE THE POT!");
                score = pot * 2; // Double points for successful betrayal
                fillLEDs(COLOR_MAGENTA);
                for (int i = 0; i < 5; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
            }

            delay(10);
        }

        if (!stole) {
            Serial.println("😇 You remained innocent...");
            score = pot / 2; // Half pot for not betraying
            fillLEDs(COLOR_GREEN);
            beep(200);
        }
    } else {
        // Innocent players wait
        Serial.println("\n⏱️ Waiting for betrayal...");
        fillLEDs(COLOR_BLUE);

        // Simulate suspense
        for (int i = 0; i < 8; i++) {
            beep(100);
            delay(1000);
        }

        // Random outcome for solo mode
        if (random(100) < 30) {
            Serial.println("😱 Someone STOLE the pot!");
            fillLEDs(COLOR_RED);
            beep(500);
            score = 0; // Lost the pot
        } else {
            Serial.println("😌 No betrayal! You get your share!");
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 3; i++) {
                beep(100);
                delay(150);
            }
            score = pot / 2;
        }
    }

    delay(2000);
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 41: DRUNK DUCK HUNT
// ============================================================================

uint32_t game_DrunkDuckHunt() {
    Serial.println("\n🎮 GAME: DRUNK DUCK HUNT");
    Serial.println("SLAP when you hear QUACK!");
    Serial.println("But DON'T hit the GOOSE!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 12;
    uint8_t hits = 0;
    uint8_t misses = 0;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/12\n", round + 1);

        fillLEDs(COLOR_CYAN);
        delay(random(1000, 3000)); // Random wait

        // 80% duck, 20% goose
        bool isDuck = (random(100) < 80);

        if (isDuck) {
            Serial.println("🦆 QUACK!");
            fillLEDs(COLOR_GREEN);
        } else {
            Serial.println("🦢 HONK! (GOOSE)");
            fillLEDs(COLOR_RED);
        }

        // Play sound
        for (int i = 0; i < 3; i++) {
            beep(isDuck ? 150 : 300);
            delay(isDuck ? 100 : 200);
        }

        // Wait for slap (300ms window)
        unsigned long windowStart = millis();
        bool slapped = false;

        while (millis() - windowStart < 300) {
            if (getShakeIntensity() > 15.0) {
                slapped = true;
                break;
            }
            delay(10);
        }

        if (slapped && isDuck) {
            Serial.println("✅ HIT!");
            fillLEDs(COLOR_YELLOW);
            vibrate(100);
            beep(200);
            score += 100;
            hits++;
        } else if (slapped && !isDuck) {
            Serial.println("❌ YOU HIT THE GOOSE! -200");
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
            score = (score >= 200) ? score - 200 : 0;
            misses++;
        } else if (!slapped && isDuck) {
            Serial.println("💔 MISSED!");
            fillLEDs(COLOR_ORANGE);
            beep(300);
            misses++;
        } else {
            Serial.println("😌 Good restraint!");
            fillLEDs(COLOR_BLUE);
            beep(100);
            score += 50;
        }

        delay(1500);
        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎯 Hits: %d\n", hits);
    Serial.printf("💔 Misses: %d\n", misses);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 42: SUCKER PUNCH (Reaction Duel)
// ============================================================================

uint32_t game_SuckerPunch() {
    Serial.println("\n🎮 GAME: SUCKER PUNCH");
    Serial.println("Hands ready... GRAB the puck when it flashes GREEN!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/5\n", round + 1);
        Serial.println("Get ready...");

        // Suspense phase
        fillLEDs(COLOR_YELLOW);
        delay(2000);

        Serial.println("Steady...");
        fillLEDs(COLOR_ORANGE);
        delay(random(1000, 4000)); // Random delay = unpredictable

        // GO!
        Serial.println("GRAB NOW!");
        fillLEDs(COLOR_GREEN);
        beep(300);

        unsigned long flashTime = millis();
        bool grabbed = false;
        unsigned long reactionTime = 0;

        // Wait for grab (shake + button)
        while (millis() - flashTime < 2000 && !grabbed) {
            if (getShakeIntensity() > 10.0 || !digitalRead(PIN_BUTTON)) {
                reactionTime = millis() - flashTime;
                grabbed = true;
            }
            delay(5);
        }

        if (grabbed) {
            Serial.printf("⚡ Reaction: %lu ms\n", reactionTime);

            uint32_t roundScore = 0;

            if (reactionTime < 100) {
                Serial.println("🏆 LIGHTNING FAST!");
                fillLEDs(COLOR_MAGENTA);
                for (int i = 0; i < 5; i++) {
                    beep(80);
                    vibrate(80);
                    delay(80);
                }
                roundScore = 500;
            } else if (reactionTime < 200) {
                Serial.println("🎯 EXCELLENT!");
                fillLEDs(COLOR_YELLOW);
                beep(200);
                vibrate(200);
                roundScore = 300;
            } else if (reactionTime < 400) {
                Serial.println("✅ GOOD!");
                fillLEDs(COLOR_GREEN);
                beep(150);
                vibrate(150);
                roundScore = 150;
            } else {
                Serial.println("😐 SLOW...");
                fillLEDs(COLOR_BLUE);
                beep(100);
                roundScore = 50;
            }

            score += roundScore;
            Serial.printf("+%lu points\n", roundScore);
        } else {
            Serial.println("❌ TOO SLOW!");
            fillLEDs(COLOR_RED);
            beep(500);
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 43: DEATH ROLL (Gambling Game)
// ============================================================================

uint32_t game_DeathRoll() {
    Serial.println("\n🎮 GAME: DEATH ROLL");
    Serial.println("Roll random numbers down to 1 = YOU LOSE!");

    beep(200);
    delay(1000);

    uint32_t currentMax = 100;
    uint32_t rollNumber = 1;

    Serial.println("Starting at 100...");
    fillLEDs(COLOR_GREEN);
    delay(2000);

    while (currentMax > 1) {
        Serial.printf("\n🎲 Roll #%lu (1-%lu)\n", rollNumber, currentMax);
        Serial.println("SHAKE to roll!");

        fillLEDs(COLOR_YELLOW);

        // Wait for shake
        while (getShakeIntensity() < 8.0) {
            delay(50);
        }

        // Rolling animation
        for (int i = 0; i < 20; i++) {
            clearLEDs();
            strip.setPixelColor(random(NUM_LEDS), COLOR_CYAN);
            strip.show();
            beep(50);
            delay(50);
        }

        // Roll result
        uint32_t roll = random(1, currentMax + 1);
        currentMax = roll;

        Serial.printf("📊 Rolled: %lu\n", roll);

        if (roll == 1) {
            // DEATH!
            Serial.println("\n💀 YOU ROLLED 1! DEATH! 💀");
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 10; i++) {
                beep(100);
                vibrate(100);
                delay(100);
                clearLEDs();
                delay(100);
                fillLEDs(COLOR_RED);
            }
            break;
        } else {
            // Show progress (closer to death = more red)
            float progress = 1.0 - (roll / 100.0);
            uint8_t red = progress * 255;
            uint8_t green = (1.0 - progress) * 255;

            int litLEDs = map(roll, 1, 100, 1, NUM_LEDS);
            clearLEDs();
            for (int i = 0; i < litLEDs; i++) {
                strip.setPixelColor(i, strip.Color(red, green, 0));
            }
            strip.show();

            beep(200);
            vibrate(100);
            delay(2000);
        }

        rollNumber++;
    }

    // Score = how many rolls survived
    uint32_t score = (rollNumber - 1) * 100;

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎲 Survived %lu rolls\n", rollNumber - 1);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 44: SHAME WHEEL (Humiliation Roulette)
// ============================================================================

uint32_t game_ShameWheel() {
    Serial.println("\n🎮 GAME: SHAME WHEEL");
    Serial.println("Spin for your punishment level!");

    beep(200);
    delay(1000);

    uint32_t score = 1000; // Start with points, lose them via shame
    uint8_t rounds = 3;

    const char* shameLevel1[] = {"Tell a dad joke", "Dance for 5 seconds", "Compliment someone"};
    const char* shameLevel2[] = {"Truth question", "Funny voice for 30s", "Do 10 pushups"};
    const char* shameLevel3[] = {"Embarrassing story", "Sing out loud", "Take a shot"};
    const char* shameLevel4[] = {"Group chooses dare", "Social media post", "Ultimate embarrassment"};

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/3\n", round + 1);
        Serial.println("SHAKE to spin the wheel!");

        fillLEDs(COLOR_CYAN);

        // Wait for big shake
        while (getShakeIntensity() < 10.0) {
            delay(50);
        }

        // Spinning animation
        Serial.println("🎡 Spinning...");
        for (int i = 0; i < 40; i++) {
            clearLEDs();
            strip.setPixelColor(i % NUM_LEDS, COLOR_MAGENTA);
            strip.show();
            beep(50);
            delay(50 + (i * 3)); // Slow down
        }

        // Determine shame level (1-4)
        uint8_t level = random(1, 17); // 16 LEDs total

        if (level <= 6) level = 1;        // Mild (1-6 LEDs)
        else if (level <= 11) level = 2;  // Medium (7-11)
        else if (level <= 15) level = 3;  // Spicy (12-15)
        else level = 4;                    // NUCLEAR (16)

        // Show result
        clearLEDs();
        for (int i = 0; i < level * 4; i++) {
            if (level == 1) strip.setPixelColor(i, COLOR_GREEN);
            else if (level == 2) strip.setPixelColor(i, COLOR_YELLOW);
            else if (level == 3) strip.setPixelColor(i, COLOR_ORANGE);
            else strip.setPixelColor(i, COLOR_RED);
        }
        strip.show();

        Serial.printf("\n🎪 SHAME LEVEL: %d\n", level);

        // Display punishment
        if (level == 1) {
            Serial.printf("😊 MILD: %s\n", shameLevel1[random(3)]);
            beep(200);
            score -= 100;
        } else if (level == 2) {
            Serial.printf("😬 MEDIUM: %s\n", shameLevel2[random(3)]);
            beep(300);
            vibrate(200);
            score -= 200;
        } else if (level == 3) {
            Serial.printf("😱 SPICY: %s\n", shameLevel3[random(3)]);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score -= 400;
        } else {
            Serial.printf("💀 NUCLEAR: %s\n", shameLevel4[random(3)]);
            for (int i = 0; i < 5; i++) {
                fillLEDs(i % 2 ? COLOR_RED : COLOR_MAGENTA);
                beep(150);
                vibrate(150);
                delay(150);
            }
            score -= 600;
        }

        Serial.printf("Points remaining: %lu\n", score);
        delay(3000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 45: ALL IN (Degenerate Gambling)
// ============================================================================

uint32_t game_AllIn() {
    Serial.println("\n🎮 GAME: ALL IN");
    Serial.println("Bet everything on a coin flip!");

    beep(200);
    delay(1000);

    uint32_t bankroll = 1000;
    uint8_t flips = 0;

    Serial.printf("💰 Starting bankroll: %lu\n", bankroll);
    delay(1500);

    while (bankroll > 0 && flips < 5) {
        flips++;
        Serial.printf("\n🎰 Flip #%d\n", flips);
        Serial.printf("💰 Current bankroll: %lu\n", bankroll);

        Serial.println("\nTAP to bet it all!");
        Serial.println("HOLD for 3s to walk away");

        fillLEDs(COLOR_YELLOW);

        unsigned long decisionStart = millis();
        bool betPlaced = false;
        bool walkedAway = false;
        unsigned long holdStart = 0;
        bool holding = false;

        while (millis() - decisionStart < 10000 && !betPlaced && !walkedAway) {
            if (!digitalRead(PIN_BUTTON) && !holding) {
                holdStart = millis();
                holding = true;
                fillLEDs(COLOR_BLUE);
            }

            if (holding && digitalRead(PIN_BUTTON)) {
                // Released - check if tap or cancelled hold
                unsigned long holdDuration = millis() - holdStart;
                if (holdDuration < 500) {
                    // Quick tap = BET
                    betPlaced = true;
                    Serial.println("\n💎 ALL IN!");
                } else {
                    // Was holding but released early
                    fillLEDs(COLOR_YELLOW);
                }
                holding = false;
            }

            if (holding && (millis() - holdStart > 3000)) {
                // Held for 3s = WALK AWAY
                walkedAway = true;
                Serial.println("\n🚶 Walking away...");
            }

            delay(10);
        }

        if (walkedAway) {
            Serial.println("😌 You kept your money!");
            fillLEDs(COLOR_GREEN);
            beep(300);
            delay(2000);
            break;
        }

        if (!betPlaced) {
            Serial.println("⏰ Timeout! Forced to bet!");
            betPlaced = true;
        }

        // Coin flip animation
        Serial.println("\n🪙 Flipping...");
        for (int i = 0; i < 20; i++) {
            fillLEDs(i % 2 ? COLOR_GREEN : COLOR_RED);
            beep(50);
            delay(100);
        }

        // Result
        bool won = random(2);

        if (won) {
            Serial.println("✅ WIN! DOUBLED!");
            bankroll *= 2;
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
        } else {
            Serial.println("❌ LOSE! BUSTED!");
            bankroll = 0;
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 10; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
            break;
        }

        Serial.printf("💰 New bankroll: %lu\n", bankroll);
        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎰 Flips survived: %d\n", flips);
    Serial.printf("💯 FINAL SCORE: %lu\n", bankroll);

    delay(2000);
    return bankroll;
}

// ============================================================================
// GAME 46: COPYCAT CHAOS (Dance/Movement Copy)
// ============================================================================

uint32_t game_CopycatChaos() {
    Serial.println("\n🎮 GAME: COPYCAT CHAOS");
    Serial.println("Copy the movement patterns!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    const char* moves[] = {"SHAKE HARD", "SPIN 360°", "JUMP", "FREEZE", "TAP RAPIDLY"};

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/5\n", round + 1);

        // Show the move
        int moveIndex = random(5);
        Serial.printf("🎭 DO THIS: %s\n", moves[moveIndex]);

        // Visual cue
        fillLEDs(COLOR_CYAN);
        beep(200);
        delay(2000);

        // GO!
        Serial.println("GO!");
        fillLEDs(COLOR_GREEN);
        beep(300);

        unsigned long moveStart = millis();
        bool success = false;

        // Check for correct move (3 second window)
        while (millis() - moveStart < 3000 && !success) {
            if (moveIndex == 0) { // SHAKE HARD
                if (getShakeIntensity() > 15.0) {
                    success = true;
                }
            } else if (moveIndex == 1) { // SPIN
                if (getShakeIntensity() > 10.0) {
                    success = true; // Simplified for single puck
                }
            } else if (moveIndex == 2) { // JUMP
                if (getShakeIntensity() > 20.0) {
                    success = true;
                }
            } else if (moveIndex == 3) { // FREEZE
                if (getShakeIntensity() < 1.0) {
                    success = true;
                }
            } else if (moveIndex == 4) { // TAP RAPIDLY
                static int taps = 0;
                if (readButton()) {
                    taps++;
                    if (taps >= 5) {
                        success = true;
                        taps = 0;
                    }
                }
            }
            delay(10);
        }

        if (success) {
            Serial.println("✅ PERFECT!");
            fillLEDs(COLOR_YELLOW);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score += 200;
        } else {
            Serial.println("❌ FAILED!");
            fillLEDs(COLOR_RED);
            beep(300);
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 47: BEER ROULETTE (Russian Roulette - Drink Edition)
// ============================================================================

uint32_t game_BeerRoulette() {
    Serial.println("\n🎮 GAME: BEER ROULETTE");
    Serial.println("6 drinks. 1 is 'loaded'. Don't pick it!");

    beep(200);
    delay(1000);

    uint32_t score = 0;

    // Pick the "loaded" drink (1-6)
    uint8_t loadedDrink = random(1, 7);
    Serial.printf("🎰 The loaded drink is... (hidden)\n");

    fillLEDs(COLOR_YELLOW);
    delay(2000);

    for (int round = 1; round <= 6; round++) {
        Serial.printf("\nDrink %d/6\n", round);
        Serial.println("SHAKE to select this drink");
        Serial.println("or wait 5 seconds to skip");

        fillLEDs(COLOR_CYAN);

        unsigned long decisionStart = millis();
        bool selected = false;

        while (millis() - decisionStart < 5000 && !selected) {
            if (getShakeIntensity() > 8.0) {
                selected = true;
            }
            delay(50);
        }

        if (selected) {
            Serial.printf("🍺 You picked drink #%d\n", round);

            // Suspense
            for (int i = 0; i < 10; i++) {
                fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_OFF);
                beep(100);
                delay(200);
            }

            if (round == loadedDrink) {
                Serial.println("\n💀 LOADED! YOU LOSE!");
                fillLEDs(COLOR_RED);
                for (int i = 0; i < 10; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
                score = 0;
                break;
            } else {
                Serial.println("✅ SAFE!");
                fillLEDs(COLOR_GREEN);
                for (int i = 0; i < 3; i++) {
                    beep(100);
                    vibrate(100);
                    delay(150);
                }
                score += 200;
            }
        } else {
            Serial.println("😌 Skipped this one");
            fillLEDs(COLOR_BLUE);
            beep(100);
            delay(1000);
        }

        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 48: NEVER HAVE I EVER (Digital Version)
// ============================================================================

uint32_t game_NeverHaveIEver() {
    Serial.println("\n🎮 GAME: NEVER HAVE I EVER");
    Serial.println("TAP if you HAVE done it");
    Serial.println("FREEZE if you HAVEN'T");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 8;

    const char* statements[] = {
        "Been skydiving",
        "Cheated on a test",
        "Broken a bone",
        "Met a celebrity",
        "Been arrested",
        "Traveled abroad",
        "Been in a fight",
        "Lied to a cop"
    };

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/8\n", round + 1);
        Serial.printf("Never have I ever... %s\n", statements[round]);

        fillLEDs(COLOR_CYAN);
        delay(2000);

        Serial.println("TAP = YES, FREEZE = NO");
        fillLEDs(COLOR_YELLOW);
        beep(200);

        unsigned long answerWindow = millis();
        bool answered = false;
        bool answer = false;

        while (millis() - answerWindow < 3000 && !answered) {
            if (readButton()) {
                answer = true;
                answered = true;
                Serial.println("👆 You HAVE!");
                fillLEDs(COLOR_GREEN);
                beep(100);
            } else if (getShakeIntensity() < 0.5) {
                // They're frozen
                if (millis() - answerWindow > 1000) {
                    answer = false;
                    answered = true;
                    Serial.println("🧊 You HAVEN'T");
                    fillLEDs(COLOR_BLUE);
                    beep(100);
                }
            }
            delay(10);
        }

        if (!answered) {
            Serial.println("⏰ No answer = skip");
            fillLEDs(COLOR_ORANGE);
            beep(200);
        } else {
            score += 100;
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 49: ACCENT ROULETTE
// ============================================================================

uint32_t game_AccentRoulette() {
    Serial.println("\n🎮 GAME: ACCENT ROULETTE");
    Serial.println("Speak in the assigned accent for 60 seconds!");

    beep(200);
    delay(1000);

    uint32_t score = 0;

    const char* accents[] = {"RUSSIAN", "IRISH", "FRENCH", "SOUTHERN", "PIRATE", "VALLEY GIRL"};
    uint32_t accentColors[] = {COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, COLOR_PURPLE, COLOR_CYAN};

    // Spin for accent
    Serial.println("SHAKE to spin for your accent!");
    fillLEDs(COLOR_CYAN);

    while (getShakeIntensity() < 8.0) {
        delay(50);
    }

    // Spinning
    Serial.println("🎡 Spinning...");
    for (int i = 0; i < 30; i++) {
        clearLEDs();
        strip.setPixelColor(i % NUM_LEDS, COLOR_MAGENTA);
        strip.show();
        beep(50);
        delay(80);
    }

    // Select accent
    int accentIndex = random(6);

    Serial.printf("\n🎭 YOUR ACCENT: %s\n", accents[accentIndex]);
    fillLEDs(accentColors[accentIndex]);
    for (int i = 0; i < 3; i++) {
        beep(200);
        delay(300);
    }

    Serial.println("\nSpeak in this accent for 60 seconds!");
    Serial.println("Group will vote: TAP if good, SHAKE if bad");

    // Countdown with LED ring
    for (int seconds = 60; seconds > 0; seconds--) {
        int litLEDs = map(seconds, 0, 60, 0, NUM_LEDS);
        clearLEDs();
        for (int i = 0; i < litLEDs; i++) {
            strip.setPixelColor(i, accentColors[accentIndex]);
        }
        strip.show();

        if (seconds % 10 == 0) {
            Serial.printf("%d seconds remaining...\n", seconds);
            beep(100);
        }

        delay(1000);
    }

    // Time's up!
    Serial.println("\n⏰ TIME'S UP!");
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    // Simulated voting (random for single player)
    Serial.println("\nVoting...");
    delay(2000);

    bool approved = random(2);
    if (approved) {
        Serial.println("✅ APPROVED!");
        fillLEDs(COLOR_GREEN);
        for (int i = 0; i < 5; i++) {
            beep(100);
            vibrate(100);
            delay(150);
        }
        score = 1000;
    } else {
        Serial.println("❌ REJECTED!");
        fillLEDs(COLOR_RED);
        beep(500);
        score = 0;
    }

    delay(2000);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 50: TRIVIA SPINNER (LED Answer Selection)
// ============================================================================

uint32_t game_TriviaSpinner() {
    Serial.println("\n🎮 GAME: TRIVIA SPINNER");
    Serial.println("Stop the spinner on your answer (A/B/C/D)");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t questions = 5;

    // Sample trivia questions (in real deployment, from server/app)
    const char* questionText[] = {
        "What is 2+2?",
        "Capital of France?",
        "Largest planet?",
        "H2O is?",
        "First US President?"
    };

    const char* answerA[] = {"3", "London", "Earth", "Oxygen", "Jefferson"};
    const char* answerB[] = {"4", "Paris", "Jupiter", "Water", "Washington"};
    const char* answerC[] = {"5", "Berlin", "Saturn", "Hydrogen", "Adams"};
    const char* answerD[] = {"6", "Madrid", "Neptune", "Helium", "Lincoln"};

    const char correctAnswers[] = {'B', 'B', 'B', 'B', 'B'}; // All B for demo

    for (int q = 0; q < questions; q++) {
        Serial.printf("\n━━━━━ QUESTION %d/5 ━━━━━\n", q + 1);
        Serial.println(questionText[q]);
        Serial.printf("A: %s\n", answerA[q]);
        Serial.printf("B: %s\n", answerB[q]);
        Serial.printf("C: %s\n", answerC[q]);
        Serial.printf("D: %s\n", answerD[q]);

        Serial.println("\n🎯 TAP to STOP the spinner on your answer!");
        delay(2000);

        // LED ring divided into 4 quadrants
        // LEDs 0-3 = A (RED)
        // LEDs 4-7 = B (GREEN)
        // LEDs 8-11 = C (BLUE)
        // LEDs 12-15 = D (YELLOW)

        // Spinner animation
        Serial.println("🎡 Spinner active...");

        int spinnerPos = 0;
        unsigned long spinStart = millis();
        bool stopped = false;
        int finalPos = 0;

        // Spin for up to 10 seconds or until stopped
        while (millis() - spinStart < 10000 && !stopped) {
            // Clear and show spinner
            clearLEDs();
            strip.setPixelColor(spinnerPos, COLOR_WHITE);
            strip.show();

            // Check for button press
            if (readButton()) {
                stopped = true;
                finalPos = spinnerPos;
                Serial.println("🛑 STOPPED!");

                // Flash the selected LED
                for (int i = 0; i < 5; i++) {
                    strip.setPixelColor(finalPos, i % 2 ? COLOR_WHITE : COLOR_OFF);
                    strip.show();
                    beep(100);
                    delay(150);
                }
            }

            // Move spinner (slower than other games for accuracy)
            spinnerPos = (spinnerPos + 1) % NUM_LEDS;
            beep(30);
            delay(120); // SLOWER spin = easier to target

            // Slightly randomize delay for unpredictability
            delay(random(0, 30));
        }

        if (!stopped) {
            Serial.println("⏰ Timeout! Random answer selected");
            finalPos = random(NUM_LEDS);
        }

        // Determine selected answer from LED position
        char selectedAnswer;
        uint32_t answerColor;

        if (finalPos < 4) {
            selectedAnswer = 'A';
            answerColor = COLOR_RED;
        } else if (finalPos < 8) {
            selectedAnswer = 'B';
            answerColor = COLOR_GREEN;
        } else if (finalPos < 12) {
            selectedAnswer = 'C';
            answerColor = COLOR_BLUE;
        } else {
            selectedAnswer = 'D';
            answerColor = COLOR_YELLOW;
        }

        Serial.printf("\n📍 You selected: %c\n", selectedAnswer);

        // Show selected answer quadrant
        clearLEDs();
        int startLED = (selectedAnswer - 'A') * 4;
        for (int i = 0; i < 4; i++) {
            strip.setPixelColor(startLED + i, answerColor);
        }
        strip.show();

        delay(2000);

        // Reveal answer
        Serial.println("\n🎓 Correct answer is...");
        delay(1500);

        for (int i = 0; i < 3; i++) {
            clearLEDs();
            delay(200);
            int correctStartLED = (correctAnswers[q] - 'A') * 4;
            for (int j = 0; j < 4; j++) {
                if (correctAnswers[q] == 'A') strip.setPixelColor(correctStartLED + j, COLOR_RED);
                else if (correctAnswers[q] == 'B') strip.setPixelColor(correctStartLED + j, COLOR_GREEN);
                else if (correctAnswers[q] == 'C') strip.setPixelColor(correctStartLED + j, COLOR_BLUE);
                else strip.setPixelColor(correctStartLED + j, COLOR_YELLOW);
            }
            strip.show();
            beep(100);
            delay(200);
        }

        Serial.printf("%c!\n", correctAnswers[q]);

        // Check if correct
        if (selectedAnswer == correctAnswers[q]) {
            Serial.println("\n✅ CORRECT!");
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score += 200;
        } else {
            Serial.println("\n❌ WRONG!");
            fillLEDs(COLOR_RED);
            beep(500);
            vibrate(500);
        }

        delay(2000);
        clearLEDs();

        if (q < questions - 1) {
            Serial.println("\nNext question in 3 seconds...");
            delay(3000);
        }
    }

    // Final results
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.println("\n━━━━━━━━━━━━━━━━━━━");
    Serial.printf("📊 Correct answers: %lu/5\n", score / 200);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    Serial.println("━━━━━━━━━━━━━━━━━━━");

    delay(3000);
    return score;
}
// ============================================================================
// SETUP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n\n╔═══════════════════════════════════════════╗");
    Serial.println("║      TABLE WARS - GAME SYSTEM v1.0       ║");
    Serial.println("╚═══════════════════════════════════════════╝\n");

    // Initialize hardware
    strip.begin();
    strip.setBrightness(100);  // Brighter for game mode
    strip.show();

    pinMode(PIN_BUTTON, INPUT_PULLUP);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_MOTOR, OUTPUT);

    Wire.begin(PIN_MPU_SDA, PIN_MPU_SCL);
    if (!mpu.begin()) {
        Serial.println("❌ MPU6050 not found!");
    } else {
        Serial.println("✅ MPU6050 initialized");
        mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
        mpu.setGyroRange(MPU6050_RANGE_250_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    }

    Serial.printf("\n🎮 Puck ID: %d\n", PUCK_ID);
    Serial.printf("🎲 Table: %d\n", TABLE_NUMBER);

    // Initialize server communication
    Serial.println("\n🌐 Initializing server communication...");
    g_serverComm = new ServerComm(PUCK_ID);
    g_serverComm->begin();      // Connect WiFi & register puck
    g_serverComm->beginBLE();   // Start BLE advertising
    Serial.println("");

    // Boot animation
    for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, COLOR_CYAN);
        strip.show();
        delay(30);
    }
    beep(200);
    delay(500);
    clearLEDs();

    Serial.println("\n🎮 DEMO MODE - Cycling through all 51 games");
    Serial.println("Press button anytime to skip to next game\n");

    delay(2000);
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
    // Check for manual skip
    if (readButton()) {
        Serial.println("⏭️  Skipping to next game...");
        delay(500);
        currentGameIndex = (currentGameIndex + 1) % 51;
    }

    // Run game
    uint32_t gameScore = 0;

    switch (currentGameIndex) {
        case 0:
            gameScore = game_SpeedTap();
            break;
        case 1:
            gameScore = game_ShakeDuel();
            break;
        case 2:
            gameScore = game_FreezeRound();
            break;
        case 3:
            gameScore = game_LEDChase();
            break;
        case 4:
            gameScore = game_ColorWars();
            break;
        case 5:
            gameScore = game_RainbowRoulette();
            break;
        case 6:
            gameScore = game_VisualBomb();
            break;
        case 7:
            gameScore = game_SimonSays();
            break;
        case 8:
            gameScore = game_HotPotato();
            break;
        case 9:
            gameScore = game_DrunkDuel();
            break;
        case 10:
            gameScore = game_LastTapStanding();
            break;
        case 11:
            gameScore = game_HammerTime();
            break;
        case 12:
            gameScore = game_BarRoulette();
            break;
        case 13:
            gameScore = game_HoldYourNerve();
            break;
        case 14:
            gameScore = game_SlapBattle();
            break;
        case 15:
            gameScore = game_ChugTimer();
            break;
        case 16:
            gameScore = game_PressureCooker();
            break;
        case 17:
            gameScore = game_PowerHour();
            break;
        case 18:
            gameScore = game_DareRoulette();
            break;
        case 19:
            gameScore = game_Bullseye();
            break;
        case 20:
            gameScore = game_KaraokeJudge();
            break;
        case 21:
            gameScore = game_WildCard();
            break;
        case 22:
            gameScore = game_LuckySeven();
            break;
        case 23:
            gameScore = game_VolumeWars();
            break;
        case 24:
            gameScore = game_ShotRoulette();
            break;
        case 25:
            gameScore = game_BalanceMaster();
            break;
        case 26:
            gameScore = game_SpinMaster();
            break;
        case 27:
            gameScore = game_LightningRound();
            break;
        case 28:
            gameScore = game_BeatMaster();
            break;
        case 29:
            gameScore = game_DoubleOrNothing();
            break;
        case 30:
            gameScore = game_ComboBreaker();
            break;
        case 31:
            gameScore = game_Lockout();
            break;
        case 32:
            gameScore = game_PrecisionStrike();
            break;
        case 33:
            gameScore = game_GauntletMode();
            break;
        case 34:
            gameScore = game_RussianRoulette();
            break;
        case 35:
            gameScore = game_MarathonMode();
            break;
        case 36:
            gameScore = game_MirrorMatch();
            break;
        case 37:
            gameScore = game_PerfectHold();
            break;
        case 38:
            gameScore = game_CountdownSniper();
            break;
        case 39:
            gameScore = game_ReactionChain();
            break;
        case 40:
            gameScore = game_JudasMode();
            break;
        case 41:
            gameScore = game_DrunkDuckHunt();
            break;
        case 42:
            gameScore = game_SuckerPunch();
            break;
        case 43:
            gameScore = game_DeathRoll();
            break;
        case 44:
            gameScore = game_ShameWheel();
            break;
        case 45:
            gameScore = game_AllIn();
            break;
        case 46:
            gameScore = game_CopycatChaos();
            break;
        case 47:
            gameScore = game_BeerRoulette();
            break;
        case 48:
            gameScore = game_NeverHaveIEver();
            break;
        case 49:
            gameScore = game_AccentRoulette();
            break;
        case 50:
            gameScore = game_TriviaSpinner();
            break;
    }

    totalScore += gameScore;

    // Submit score to server
    if (g_serverComm && g_serverComm->isWiFiConnected()) {
        const char* gameName = gameNames[currentGameIndex];
        Serial.printf("\n📤 Submitting to server: %s = %lu points\n", gameName, gameScore);
        g_serverComm->submitScore(gameName, gameScore);
    }

    Serial.println("\n" + String("═").substring(0, 40));
    Serial.printf("SESSION TOTAL: %lu points\n", totalScore);
    Serial.println(String("═").substring(0, 40) + "\n");

    // Next game
    currentGameIndex = (currentGameIndex + 1) % 51;

    // Wait before next game
    Serial.println("Next game in 5 seconds...");
    Serial.println("(Press button to skip)\n");

    for (int i = 0; i < 50; i++) {
        if (readButton()) {
            break;
        }
        // Breathing LEDs during wait
        float brightness = (sin(i * 0.1) + 1.0) / 2.0;
        uint8_t b = 100 * brightness;
        fillLEDs(strip.Color(0, b, b));
        delay(100);
    }

    clearLEDs();
}
