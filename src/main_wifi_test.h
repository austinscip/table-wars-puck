/*
 * TABLE WARS - WiFi Test Mode
 *
 * Simple WiFi connectivity test - NO HARDWARE REQUIRED
 * Just ESP32 + USB cable
 *
 * This mode:
 * - Connects to WiFi
 * - Submits test scores every 10 seconds
 * - Prints status to Serial
 */

#ifndef MAIN_WIFI_TEST_H
#define MAIN_WIFI_TEST_H

#include <Arduino.h>
#include "server_comm.h"

// Test configuration
#define TEST_INTERVAL_MS 10000  // Submit score every 10 seconds
#define PUCK_ID 1

// Global server comm instance
ServerComm* testServerComm = nullptr;

// Test counter
uint32_t testCounter = 0;
unsigned long lastTestTime = 0;

const char* testGameNames[] = {
    "WiFi Test Game 1",
    "WiFi Test Game 2",
    "WiFi Test Game 3",
    "Connection Test",
    "Server Ping"
};

void setup() {
    Serial.begin(115200);
    delay(2000);  // Wait for serial monitor

    Serial.println("\n\n");
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║   TABLE WARS - WiFi Test Mode            ║");
    Serial.println("║   NO HARDWARE REQUIRED                    ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println("");

    // Initialize server communication
    Serial.println("🌐 Initializing WiFi & Server Connection...");
    testServerComm = new ServerComm(PUCK_ID);

    // Connect to WiFi and register puck
    if (testServerComm->begin()) {
        Serial.println("✅ WiFi connected successfully!");
        Serial.printf("   Server: %s\n", testServerComm->getServerURL().c_str());
    } else {
        Serial.println("⚠️  WiFi connection failed - will retry");
    }

    // Start BLE advertising
    Serial.println("\n📱 Starting BLE advertising...");
    if (testServerComm->beginBLE()) {
        Serial.println("✅ BLE advertising started!");
    }

    Serial.println("\n📡 Starting WiFi test loop...");
    Serial.println("   Will submit test scores every 10 seconds");
    Serial.println("   Press RESET to restart test\n");

    lastTestTime = millis();
}

void loop() {
    unsigned long currentTime = millis();

    // Submit test score every 10 seconds
    if (currentTime - lastTestTime >= TEST_INTERVAL_MS) {
        lastTestTime = currentTime;
        testCounter++;

        // Pick a random test game
        const char* gameName = testGameNames[testCounter % 5];
        uint32_t randomScore = random(100, 10000);

        Serial.println("\n════════════════════════════════════════");
        Serial.printf("📤 Test #%lu - Submitting score...\n", testCounter);
        Serial.printf("   Game: %s\n", gameName);
        Serial.printf("   Score: %lu\n", randomScore);

        if (testServerComm->isWiFiConnected()) {
            bool success = testServerComm->submitScore(gameName, randomScore);

            if (success) {
                Serial.println("✅ Score submitted successfully!");
            } else {
                Serial.println("❌ Score submission failed!");
            }
        } else {
            Serial.println("⚠️  WiFi not connected - retrying...");
            testServerComm->begin();
        }

        Serial.println("════════════════════════════════════════\n");
    }

    // Small delay to prevent watchdog issues
    delay(100);
}

#endif // MAIN_WIFI_TEST_H
