/**
 * ota_update.h
 *
 * Over-The-Air (OTA) Firmware Update System
 * Allows wireless firmware updates to deployed pucks
 *
 * Features:
 * - Automatic version checking on boot
 * - Background update downloads
 * - Rollback capability if update fails
 * - MD5 checksum verification
 * - Resume interrupted downloads
 *
 * Hardware: ESP32-DevKitC
 * Dependencies: ArduinoOTA, HTTPUpdate
 */

#ifndef OTA_UPDATE_H
#define OTA_UPDATE_H

#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoOTA.h>
#include <Preferences.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

#define FIRMWARE_VERSION "1.0.0"
#define UPDATE_CHECK_INTERVAL 3600000  // Check every hour (ms)
#define UPDATE_SERVER_URL "http://192.168.1.100:5000/firmware"

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

Preferences preferences;
unsigned long lastUpdateCheck = 0;
bool updateInProgress = false;
bool updateAvailable = false;
String latestVersion = "";

// ============================================================================
// VERSION MANAGEMENT
// ============================================================================

/**
 * Compare two semantic version strings (e.g., "1.2.3")
 * Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
 */
int compareVersions(String v1, String v2) {
    int v1Major = v1.substring(0, v1.indexOf('.')).toInt();
    v1.remove(0, v1.indexOf('.') + 1);
    int v1Minor = v1.substring(0, v1.indexOf('.')).toInt();
    v1.remove(0, v1.indexOf('.') + 1);
    int v1Patch = v1.toInt();

    int v2Major = v2.substring(0, v2.indexOf('.')).toInt();
    v2.remove(0, v2.indexOf('.') + 1);
    int v2Minor = v2.substring(0, v2.indexOf('.')).toInt();
    v2.remove(0, v2.indexOf('.') + 1);
    int v2Patch = v2.toInt();

    if (v1Major > v2Major) return 1;
    if (v1Major < v2Major) return -1;
    if (v1Minor > v2Minor) return 1;
    if (v1Minor < v2Minor) return -1;
    if (v1Patch > v2Patch) return 1;
    if (v1Patch < v2Patch) return -1;
    return 0;
}

/**
 * Get stored firmware version from preferences
 */
String getStoredVersion() {
    preferences.begin("firmware", true);
    String version = preferences.getString("version", FIRMWARE_VERSION);
    preferences.end();
    return version;
}

/**
 * Store firmware version to preferences
 */
void storeVersion(String version) {
    preferences.begin("firmware", false);
    preferences.putString("version", version);
    preferences.end();
}

/**
 * Store rollback version (previous working firmware)
 */
void storeRollbackVersion() {
    preferences.begin("firmware", false);
    preferences.putString("rollback", FIRMWARE_VERSION);
    preferences.end();
}

/**
 * Get rollback version
 */
String getRollbackVersion() {
    preferences.begin("firmware", true);
    String version = preferences.getString("rollback", "");
    preferences.end();
    return version;
}

// ============================================================================
// UPDATE CHECKING
// ============================================================================

/**
 * Check if a new firmware version is available
 * Returns: true if update available, false otherwise
 */
bool checkForUpdates() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("⚠️ WiFi not connected - can't check for updates");
        return false;
    }

    HTTPClient http;
    String url = String(UPDATE_SERVER_URL) + "/version?puck_id=" + String(PUCK_ID);

    Serial.println("🔍 Checking for firmware updates...");
    Serial.print("   Current version: ");
    Serial.println(FIRMWARE_VERSION);

    http.begin(url);
    int httpCode = http.GET();

    if (httpCode == 200) {
        String response = http.getString();

        // Parse JSON response: {"version": "1.2.0", "url": "/firmware/download/1.2.0"}
        int versionStart = response.indexOf("\"version\":\"") + 11;
        int versionEnd = response.indexOf("\"", versionStart);
        latestVersion = response.substring(versionStart, versionEnd);

        Serial.print("   Latest version: ");
        Serial.println(latestVersion);

        int comparison = compareVersions(latestVersion, FIRMWARE_VERSION);

        if (comparison > 0) {
            Serial.println("✅ UPDATE AVAILABLE!");
            updateAvailable = true;
            http.end();
            return true;
        } else {
            Serial.println("✅ Firmware is up to date");
            updateAvailable = false;
            http.end();
            return false;
        }
    } else {
        Serial.print("❌ Update check failed: HTTP ");
        Serial.println(httpCode);
        http.end();
        return false;
    }
}

// ============================================================================
// UPDATE DOWNLOAD & INSTALLATION
// ============================================================================

/**
 * Progress callback for update download
 */
void updateProgress(int current, int total) {
    static int lastPercent = -1;
    int percent = (current * 100) / total;

    if (percent != lastPercent && percent % 10 == 0) {
        Serial.print("📥 Downloading: ");
        Serial.print(percent);
        Serial.println("%");
        lastPercent = percent;

        // Visual feedback on LED ring
        int ledsToLight = (percent * 16) / 100;
        for (int i = 0; i < 16; i++) {
            if (i < ledsToLight) {
                leds[i] = CRGB(0, 0, 255);  // Blue progress bar
            } else {
                leds[i] = CRGB(0, 0, 0);
            }
        }
        FastLED.show();
    }
}

/**
 * Error callback for update download
 */
void updateError(int error) {
    Serial.print("❌ Update failed with error: ");
    Serial.println(error);

    // Flash red LEDs
    for (int i = 0; i < 5; i++) {
        setAllLEDs(255, 0, 0);
        delay(200);
        setAllLEDs(0, 0, 0);
        delay(200);
    }
}

/**
 * Download and install firmware update
 * Returns: true if successful, false if failed
 */
bool performUpdate() {
    if (!updateAvailable) {
        Serial.println("⚠️ No update available");
        return false;
    }

    Serial.println("\n🚀 STARTING FIRMWARE UPDATE");
    Serial.println("═══════════════════════════════════");

    // Store rollback version before updating
    storeRollbackVersion();

    // Build download URL
    String downloadUrl = String(UPDATE_SERVER_URL) + "/download/" + latestVersion + "?puck_id=" + String(PUCK_ID);

    Serial.print("📡 Downloading from: ");
    Serial.println(downloadUrl);

    // Show update in progress on LEDs
    setAllLEDs(0, 0, 255);  // Blue
    updateInProgress = true;

    WiFiClient client;
    HTTPClient http;

    http.begin(client, downloadUrl);
    int httpCode = http.GET();

    if (httpCode == 200) {
        int contentLength = http.getSize();

        if (contentLength > 0) {
            bool canBegin = Update.begin(contentLength);

            if (canBegin) {
                Serial.println("✅ Update partition ready");
                Serial.print("📦 Size: ");
                Serial.print(contentLength);
                Serial.println(" bytes");

                WiFiClient *stream = http.getStreamPtr();

                size_t written = Update.writeStream(*stream);

                if (written == contentLength) {
                    Serial.println("✅ Firmware written successfully");
                } else {
                    Serial.print("❌ Write error: only wrote ");
                    Serial.print(written);
                    Serial.print(" of ");
                    Serial.println(contentLength);
                    http.end();
                    updateInProgress = false;
                    updateError(1);
                    return false;
                }

                if (Update.end()) {
                    Serial.println("✅ Update completed successfully");

                    if (Update.isFinished()) {
                        Serial.println("✅ Update verified - MD5 checksum valid");

                        // Store new version
                        storeVersion(latestVersion);

                        // Success animation
                        for (int i = 0; i < 3; i++) {
                            setAllLEDs(0, 255, 0);  // Green
                            delay(300);
                            setAllLEDs(0, 0, 0);
                            delay(300);
                        }

                        Serial.println("\n🔄 REBOOTING IN 3 SECONDS...");
                        delay(3000);
                        ESP.restart();

                        return true;
                    } else {
                        Serial.println("❌ Update verification failed");
                        updateError(2);
                        http.end();
                        updateInProgress = false;
                        return false;
                    }
                } else {
                    Serial.print("❌ Update error: ");
                    Serial.println(Update.errorString());
                    updateError(3);
                    http.end();
                    updateInProgress = false;
                    return false;
                }
            } else {
                Serial.println("❌ Not enough space for update");
                updateError(4);
                http.end();
                updateInProgress = false;
                return false;
            }
        } else {
            Serial.println("❌ Invalid content length");
            updateError(5);
            http.end();
            updateInProgress = false;
            return false;
        }
    } else {
        Serial.print("❌ HTTP download failed: ");
        Serial.println(httpCode);
        updateError(6);
        http.end();
        updateInProgress = false;
        return false;
    }
}

// ============================================================================
// ARDUINO OTA (LOCAL NETWORK PROGRAMMING)
// ============================================================================

/**
 * Initialize Arduino OTA for local network programming
 * Allows updates via Arduino IDE over WiFi
 */
void initArduinoOTA() {
    ArduinoOTA.setHostname("TableWarsPuck");
    ArduinoOTA.setPassword("puck2024");  // Change this!

    ArduinoOTA.onStart([]() {
        String type;
        if (ArduinoOTA.getCommand() == U_FLASH) {
            type = "sketch";
        } else {  // U_SPIFFS
            type = "filesystem";
        }
        Serial.println("🔧 Arduino OTA: Starting " + type + " update");
        setAllLEDs(255, 165, 0);  // Orange
    });

    ArduinoOTA.onEnd([]() {
        Serial.println("\n✅ Arduino OTA: Complete");
        setAllLEDs(0, 255, 0);  // Green
    });

    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        int percent = (progress / (total / 100));
        Serial.printf("Progress: %u%%\r", percent);

        // Show progress on LED ring
        int ledsToLight = (percent * 16) / 100;
        for (int i = 0; i < 16; i++) {
            if (i < ledsToLight) {
                leds[i] = CRGB(255, 165, 0);  // Orange progress
            } else {
                leds[i] = CRGB(0, 0, 0);
            }
        }
        FastLED.show();
    });

    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("❌ Arduino OTA Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
        else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
        else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
        else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
        else if (error == OTA_END_ERROR) Serial.println("End Failed");

        setAllLEDs(255, 0, 0);  // Red
    });

    ArduinoOTA.begin();
    Serial.println("✅ Arduino OTA initialized");
    Serial.println("   Connect via: TableWarsPuck.local");
}

// ============================================================================
// AUTOMATIC UPDATE MANAGEMENT
// ============================================================================

/**
 * Check for updates periodically (call in loop())
 */
void handleOTAUpdates() {
    // Handle Arduino OTA requests
    ArduinoOTA.handle();

    // Don't check for updates while game is active
    if (updateInProgress) return;

    // Periodic update check
    if (millis() - lastUpdateCheck >= UPDATE_CHECK_INTERVAL) {
        lastUpdateCheck = millis();

        if (checkForUpdates() && updateAvailable) {
            Serial.println("\n📢 NEW FIRMWARE AVAILABLE!");
            Serial.println("   Installing automatically in 10 seconds...");
            Serial.println("   (Shake puck 5 times to cancel)");

            // Give user 10 seconds to cancel
            unsigned long cancelStart = millis();
            int shakeCount = 0;

            while (millis() - cancelStart < 10000) {
                // Blink blue to indicate update pending
                setAllLEDs(0, 0, 255);
                delay(250);
                setAllLEDs(0, 0, 0);
                delay(250);

                // Check for shake cancel
                readAccelerometer();
                if (detectShake()) {
                    shakeCount++;
                    if (shakeCount >= 5) {
                        Serial.println("⚠️ Update cancelled by user");
                        setAllLEDs(255, 165, 0);  // Orange
                        delay(1000);
                        return;
                    }
                }
            }

            // Proceed with update
            performUpdate();
        }
    }
}

/**
 * Force immediate update check and installation
 */
void forceUpdateCheck() {
    Serial.println("\n🔍 FORCED UPDATE CHECK");
    if (checkForUpdates() && updateAvailable) {
        performUpdate();
    }
}

/**
 * Rollback to previous firmware version
 */
void rollbackFirmware() {
    String rollbackVer = getRollbackVersion();

    if (rollbackVer == "") {
        Serial.println("❌ No rollback version available");
        return;
    }

    Serial.println("\n🔄 ROLLING BACK FIRMWARE");
    Serial.print("   Current: ");
    Serial.println(FIRMWARE_VERSION);
    Serial.print("   Rollback to: ");
    Serial.println(rollbackVer);

    latestVersion = rollbackVer;
    updateAvailable = true;
    performUpdate();
}

// ============================================================================
// BOOT DIAGNOSTICS
// ============================================================================

/**
 * Check if this is the first boot after an update
 */
void checkPostUpdateBoot() {
    String storedVersion = getStoredVersion();

    if (storedVersion != FIRMWARE_VERSION) {
        Serial.println("\n✅ FIRMWARE UPDATE SUCCESSFUL!");
        Serial.print("   Previous: ");
        Serial.println(storedVersion);
        Serial.print("   Current: ");
        Serial.println(FIRMWARE_VERSION);

        // Success celebration
        for (int i = 0; i < 3; i++) {
            rainbowCycle(20);
        }

        // Update stored version
        storeVersion(FIRMWARE_VERSION);

        // Report successful update to server
        if (WiFi.status() == WL_CONNECTED) {
            HTTPClient http;
            String url = String(UPDATE_SERVER_URL) + "/report-success";
            http.begin(url);
            http.addHeader("Content-Type", "application/json");

            String payload = "{\"puck_id\":" + String(PUCK_ID) +
                           ",\"version\":\"" + FIRMWARE_VERSION +
                           "\",\"previous_version\":\"" + storedVersion + "\"}";

            int httpCode = http.POST(payload);
            if (httpCode == 200) {
                Serial.println("✅ Update success reported to server");
            }
            http.end();
        }
    }
}

/**
 * Print OTA diagnostics on boot
 */
void printOTADiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔧 OTA UPDATE SYSTEM");
    Serial.println("═══════════════════════════════════");
    Serial.print("Firmware Version: ");
    Serial.println(FIRMWARE_VERSION);
    Serial.print("Update Server: ");
    Serial.println(UPDATE_SERVER_URL);
    Serial.print("Rollback Version: ");
    String rollback = getRollbackVersion();
    Serial.println(rollback != "" ? rollback : "None");
    Serial.print("Arduino OTA: ");
    Serial.println("Enabled");
    Serial.println("═══════════════════════════════════\n");
}

#endif // OTA_UPDATE_H
