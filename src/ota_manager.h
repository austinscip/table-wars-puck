/**
 * OTA (Over-The-Air) Firmware Update Manager
 * Handles wireless firmware updates for Table Wars pucks
 *
 * Sprint 1A: Firmware OTA Updates
 */

#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

#define CURRENT_FIRMWARE_VERSION "1.0.0"
#define OTA_CHECK_INTERVAL 3600000  // Check every hour (milliseconds)
#define OTA_SERVER_URL "http://tablewars.local:5001"  // Update with your server

// ============================================================================
// OTA MANAGER CLASS
// ============================================================================

class OTAManager {
private:
    String serverUrl;
    int puckId;
    unsigned long lastCheckTime;
    String currentVersion;

    /**
     * Check if a firmware update is available
     * Returns: true if update available, false otherwise
     */
    bool checkForUpdate(String &newVersion, String &downloadUrl, String &md5Checksum) {
        HTTPClient http;

        String checkUrl = serverUrl + "/firmware/version?puck_id=" + String(puckId);
        http.begin(checkUrl);

        int httpCode = http.GET();

        if (httpCode == 200) {
            String payload = http.getString();

            // Parse JSON response
            StaticJsonDocument<512> doc;
            DeserializationError error = deserializeJson(doc, payload);

            if (error) {
                Serial.println("❌ OTA: JSON parse error");
                http.end();
                return false;
            }

            bool updateAvailable = doc["update_available"];

            if (updateAvailable) {
                newVersion = doc["version"].as<String>();
                downloadUrl = doc["url"].as<String>();
                md5Checksum = doc["md5"].as<String>();

                Serial.println("✅ OTA: Update available!");
                Serial.printf("   Current: %s\n", currentVersion.c_str());
                Serial.printf("   New: %s\n", newVersion.c_str());

                http.end();
                return true;
            }
        }

        http.end();
        return false;
    }

    /**
     * Download and install firmware update
     */
    bool downloadAndInstall(String downloadUrl, String expectedMD5) {
        HTTPClient http;

        String fullUrl = serverUrl + downloadUrl + "?puck_id=" + String(puckId);
        http.begin(fullUrl);

        Serial.println("📥 OTA: Downloading firmware...");

        int httpCode = http.GET();

        if (httpCode != 200) {
            Serial.printf("❌ OTA: Download failed (HTTP %d)\n", httpCode);
            reportFailure("HTTP error " + String(httpCode));
            http.end();
            return false;
        }

        int contentLength = http.getSize();

        if (contentLength <= 0) {
            Serial.println("❌ OTA: Invalid content length");
            reportFailure("Invalid content length");
            http.end();
            return false;
        }

        bool canBegin = Update.begin(contentLength);

        if (!canBegin) {
            Serial.println("❌ OTA: Not enough space for update");
            reportFailure("Insufficient space");
            http.end();
            return false;
        }

        // Set MD5 checksum for verification
        Update.setMD5(expectedMD5.c_str());

        Serial.printf("📦 OTA: Firmware size: %d bytes\n", contentLength);

        // Get stream
        WiFiClient *stream = http.getStreamPtr();

        // Write firmware
        size_t written = Update.writeStream(*stream);

        if (written != contentLength) {
            Serial.printf("❌ OTA: Written bytes mismatch (%d vs %d)\n", written, contentLength);
            reportFailure("Write incomplete");
            http.end();
            return false;
        }

        if (!Update.end()) {
            Serial.println("❌ OTA: Update.end() failed");
            reportFailure("Update end failed: " + String(Update.errorString()));
            http.end();
            return false;
        }

        if (!Update.isFinished()) {
            Serial.println("❌ OTA: Update not finished");
            reportFailure("Update incomplete");
            http.end();
            return false;
        }

        Serial.println("✅ OTA: Update successful!");
        http.end();
        return true;
    }

    /**
     * Report successful update to server
     */
    void reportSuccess(String newVersion) {
        HTTPClient http;

        String url = serverUrl + "/firmware/report-success";
        http.begin(url);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<256> doc;
        doc["puck_id"] = puckId;
        doc["version"] = newVersion;
        doc["previous_version"] = currentVersion;

        String jsonBody;
        serializeJson(doc, jsonBody);

        http.POST(jsonBody);
        http.end();

        // Update current version
        currentVersion = newVersion;
    }

    /**
     * Report failed update to server
     */
    void reportFailure(String error) {
        HTTPClient http;

        String url = serverUrl + "/firmware/report-failure";
        http.begin(url);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<256> doc;
        doc["puck_id"] = puckId;
        doc["version"] = currentVersion;
        doc["error"] = error;

        String jsonBody;
        serializeJson(doc, jsonBody);

        http.POST(jsonBody);
        http.end();
    }

public:
    /**
     * Constructor
     */
    OTAManager(String server, int id) {
        serverUrl = server;
        puckId = id;
        currentVersion = CURRENT_FIRMWARE_VERSION;
        lastCheckTime = 0;
    }

    /**
     * Initialize OTA manager
     */
    void begin() {
        Serial.println("🔧 OTA Manager initialized");
        Serial.printf("   Puck ID: %d\n", puckId);
        Serial.printf("   Current version: %s\n", currentVersion.c_str());
        Serial.printf("   Server: %s\n", serverUrl.c_str());
    }

    /**
     * Check for updates (call periodically from loop)
     * Non-blocking - only checks at specified intervals
     */
    void checkForUpdates() {
        unsigned long now = millis();

        // Only check at intervals
        if (now - lastCheckTime < OTA_CHECK_INTERVAL) {
            return;
        }

        lastCheckTime = now;

        // Check WiFi connection
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("⚠️  OTA: WiFi not connected, skipping update check");
            return;
        }

        Serial.println("🔍 OTA: Checking for updates...");

        String newVersion, downloadUrl, md5Checksum;

        if (checkForUpdate(newVersion, downloadUrl, md5Checksum)) {
            Serial.println("📥 OTA: Starting update process...");

            if (downloadAndInstall(downloadUrl, md5Checksum)) {
                reportSuccess(newVersion);

                Serial.println("🔄 OTA: Rebooting in 5 seconds...");
                delay(5000);
                ESP.restart();
            } else {
                Serial.println("❌ OTA: Update failed");
            }
        } else {
            Serial.println("✅ OTA: Firmware is up to date");
        }
    }

    /**
     * Force immediate update check (for manual triggers)
     */
    void forceUpdateCheck() {
        lastCheckTime = 0;  // Reset timer to trigger immediate check
        checkForUpdates();
    }

    /**
     * Get current firmware version
     */
    String getCurrentVersion() {
        return currentVersion;
    }
};

#endif // OTA_MANAGER_H
