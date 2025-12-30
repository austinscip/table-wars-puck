/*
 * TABLE WARS - BLE + WiFi Dual Mode Test
 *
 * Tests both connectivity methods simultaneously:
 * - BLE: Remote control from mobile app
 * - WiFi: Score submission to server
 *
 * This demonstrates the full connectivity stack working together
 */

#ifndef MAIN_BLE_WIFI_TEST_H
#define MAIN_BLE_WIFI_TEST_H

#include "ble_control.h"
#include "server_comm.h"

// ============================================================================
// CONFIGURATION
// ============================================================================

#define PUCK_ID                1
// WiFi and server config is in server_comm.h

// Test game names (match BLE game codes)
const char* gameNamesForBLE[] = {
    "Stopped",
    "Speed Tap Battle",
    "Shake Duel",
    "Red Light Green Light",
    "LED Chase Race",
    "Color Wars",
    "Rainbow Roulette",
    "Visual Bomb Countdown",
    "Simon Says LED",
    "Hot Potato",
    "Drunk Duel"
};

// ============================================================================
// GLOBAL STATE
// ============================================================================

ServerComm* g_serverComm = nullptr;
uint8_t g_currentGameID = 0;
bool g_gameRunning = false;
unsigned long g_gameStartTime = 0;
unsigned long g_lastScoreSubmit = 0;
uint32_t g_testCounter = 0;
uint8_t g_batteryLevel = 100;

// ============================================================================
// GAME COMMAND HANDLER (Called from BLE)
// ============================================================================

void onGameCommandReceived(uint8_t gameID) {
    Serial.println("\n════════════════════════════════════════");
    Serial.printf("📱 BLE COMMAND: Game ID = 0x%02X\n", gameID);

    if (gameID == GAME_CMD_STOP) {
        // Stop game
        Serial.println("⏹️  Stopping game...");
        g_gameRunning = false;
        g_currentGameID = 0;

        // Turn off LEDs
        strip.clear();
        strip.show();

        Serial.println("✅ Game stopped");

    } else if (gameID > 0 && gameID <= 10) {
        // Start game
        const char* gameName = gameNamesForBLE[gameID];
        Serial.printf("▶️  Starting game: %s\n", gameName);

        g_currentGameID = gameID;
        g_gameRunning = true;
        g_gameStartTime = millis();

        // Visual feedback: Flash LEDs based on game ID
        uint32_t color = strip.Color(
            (gameID * 25) % 255,
            (gameID * 50) % 255,
            (gameID * 75) % 255
        );

        for (int i = 0; i < NUM_LEDS; i++) {
            strip.setPixelColor(i, color);
        }
        strip.show();

        // Send game start to server
        if (g_serverComm) {
            g_serverComm->startGame(gameID, gameName);
        }

        Serial.println("✅ Game started");
    }

    Serial.println("════════════════════════════════════════\n");
}

// ============================================================================
// SETUP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n\n");
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║   TABLE WARS - BLE + WiFi Dual Mode      ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();

    // Initialize hardware
    pinMode(PIN_MOTOR, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_BUTTON, INPUT_PULLUP);

    // Initialize LED strip
    strip.begin();
    strip.setBrightness(LED_BRIGHTNESS);
    strip.show();

    Serial.println("✅ Hardware initialized");

    // ========================================================================
    // INITIALIZE WIFI & SERVER COMMUNICATION
    // ========================================================================

    // ServerComm handles WiFi connection internally
    g_serverComm = new ServerComm(PUCK_ID);
    bool wifiOk = g_serverComm->begin();

    if (!wifiOk) {
        Serial.println("   Continuing with BLE only...");
    }

    // ========================================================================
    // INITIALIZE BLE
    // ========================================================================

    g_bleControl.begin(PUCK_ID, "TableWars");
    g_bleControl.onGameCommand(onGameCommandReceived);
    g_bleControl.updateBatteryLevel(g_batteryLevel);

    // ========================================================================
    // READY
    // ========================================================================

    Serial.println("\n╔═══════════════════════════════════════════╗");
    Serial.println("║          DUAL MODE ACTIVE                 ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("📱 BLE:  Ready for mobile app connection");
    Serial.println("📡 WiFi: Connected to server");
    Serial.println();
    Serial.println("🎮 Use mobile app to start games remotely!");
    Serial.println("   Scores will auto-submit to server");
    Serial.println();
}

// ============================================================================
// LOOP
// ============================================================================

void loop() {
    unsigned long now = millis();

    // ========================================================================
    // GAME SIMULATION (When game is running)
    // ========================================================================

    if (g_gameRunning) {
        // Simulate game running with LED animation
        uint8_t ledPos = (now / 50) % NUM_LEDS;
        strip.clear();

        uint32_t color = strip.Color(
            (g_currentGameID * 25) % 255,
            (g_currentGameID * 50) % 255,
            (g_currentGameID * 75) % 255
        );

        strip.setPixelColor(ledPos, color);
        strip.show();

        // Submit score every 10 seconds
        if (now - g_lastScoreSubmit >= 10000) {
            g_lastScoreSubmit = now;
            g_testCounter++;

            // Generate random score
            uint32_t randomScore = random(500, 10000);
            const char* gameName = gameNamesForBLE[g_currentGameID];

            Serial.println("\n════════════════════════════════════════");
            Serial.printf("📤 Auto-submitting score #%lu\n", g_testCounter);
            Serial.printf("   Game: %s\n", gameName);
            Serial.printf("   Score: %lu\n", randomScore);

            // Submit via WiFi
            if (g_serverComm) {
                bool success = g_serverComm->submitScore(gameName, randomScore);
                if (success) {
                    Serial.println("✅ Score submitted successfully!");
                } else {
                    Serial.println("❌ Score submission failed");
                }
            }

            Serial.println("════════════════════════════════════════\n");
        }

    } else {
        // Idle: Slow breathing animation
        uint8_t brightness = (sin(now / 1000.0) + 1.0) * 127;
        uint32_t color = strip.Color(0, brightness / 4, brightness / 2);

        for (int i = 0; i < NUM_LEDS; i++) {
            strip.setPixelColor(i, color);
        }
        strip.show();
    }

    // ========================================================================
    // BATTERY SIMULATION (Decreases slowly)
    // ========================================================================

    static unsigned long lastBatteryUpdate = 0;
    if (now - lastBatteryUpdate >= 60000) { // Every minute
        lastBatteryUpdate = now;

        if (g_batteryLevel > 0) {
            g_batteryLevel--;
            g_bleControl.updateBatteryLevel(g_batteryLevel);

            Serial.printf("🔋 Battery: %d%%\n", g_batteryLevel);
        }
    }

    // ========================================================================
    // CONNECTION STATUS
    // ========================================================================

    static bool wasConnected = false;
    bool isConnected = g_bleControl.isConnected();

    if (isConnected != wasConnected) {
        wasConnected = isConnected;

        if (isConnected) {
            // Connection established - flash green
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(0, 255, 0));
            }
            strip.show();
            delay(200);

        } else {
            // Disconnected - flash red
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(255, 0, 0));
            }
            strip.show();
            delay(200);
        }
    }

    delay(20);
}

#endif // MAIN_BLE_WIFI_TEST_H
