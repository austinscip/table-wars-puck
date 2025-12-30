/*
 * TABLE WARS - Server Communication Implementation
 */

#include "server_comm.h"

// ============================================================================
// CONSTRUCTOR
// ============================================================================

ServerComm::ServerComm(uint8_t id) {
    puckID = id;
    barSlug = String(BAR_SLUG);
    tableNumber = TABLE_NUMBER;
    wifiConnected = false;
    bleEnabled = false;
    bleClientConnected = false;
    pBLEServer = nullptr;
    pCommandCharacteristic = nullptr;
    pDataCharacteristic = nullptr;
}

// ============================================================================
// WIFI CONNECTION
// ============================================================================

bool ServerComm::connectWiFi() {
    Serial.println("\n📡 Connecting to WiFi...");
    Serial.printf("   SSID: %s\n", TW_WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(TW_WIFI_SSID, TW_WIFI_PASSWORD);

    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startTime < TW_WIFI_TIMEOUT)) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("\n✅ WiFi connected!");
        Serial.printf("   IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("   Server: %s\n", SERVER_URL);
        return true;
    } else {
        wifiConnected = false;
        Serial.println("\n❌ WiFi connection failed!");
        Serial.println("   Scores will be stored locally only.");
        return false;
    }
}

void ServerComm::disconnectWiFi() {
    if (wifiConnected) {
        WiFi.disconnect(true);
        wifiConnected = false;
        Serial.println("📡 WiFi disconnected");
    }
}

// ============================================================================
// BLE SETUP
// ============================================================================

bool ServerComm::setupBLE() {
    Serial.println("\n📱 Starting BLE server...");

    // Create device name with puck ID
    String deviceName = String(BLE_DEVICE_NAME) + String(puckID);

    // Initialize BLE
    BLEDevice::init(deviceName.c_str());

    // Create BLE Server
    pBLEServer = BLEDevice::createServer();
    pBLEServer->setCallbacks(new MyServerCallbacks(this));

    // Create BLE Service
    BLEService *pService = pBLEServer->createService(SERVICE_UUID);

    // Create Command Characteristic (Write)
    pCommandCharacteristic = pService->createCharacteristic(
        CHAR_UUID_CMD,
        BLECharacteristic::PROPERTY_WRITE
    );
    pCommandCharacteristic->setCallbacks(new MyCommandCallbacks(this));

    // Create Data Characteristic (Read/Notify)
    pDataCharacteristic = pService->createCharacteristic(
        CHAR_UUID_DATA,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
    );
    pDataCharacteristic->addDescriptor(new BLE2902());

    // Start the service
    pService->start();

    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);  // Functions for iPhone
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();

    bleEnabled = true;
    Serial.printf("✅ BLE server started: %s\n", deviceName.c_str());
    Serial.println("   Web Bluetooth ready!");

    return true;
}

void ServerComm::stopBLE() {
    if (bleEnabled) {
        BLEDevice::deinit(true);
        bleEnabled = false;
        Serial.println("📱 BLE stopped");
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

bool ServerComm::begin(const char* ssid, const char* password) {
    Serial.println("\n========================================");
    Serial.println("  TABLE WARS - Server Communication");
    Serial.println("========================================");

    bool success = true;

    // Try WiFi connection
    if (!connectWiFi()) {
        Serial.println("⚠️  Running in offline mode");
        success = false;
    }

    // Register puck if WiFi connected
    if (wifiConnected) {
        String puckName = "Puck_" + String(puckID);
        if (registerPuck(puckName.c_str(), 100)) {
            Serial.println("✅ Puck registered with server");
        }
    }

    return success;
}

bool ServerComm::beginBLE() {
    return setupBLE();
}

void ServerComm::stop() {
    disconnectWiFi();
    stopBLE();
}

// ============================================================================
// SERVER API CALLS
// ============================================================================

bool ServerComm::submitScore(const char* gameName, uint32_t score) {
    if (!wifiConnected) {
        Serial.println("⚠️  Not connected to WiFi - score not submitted");
        return false;
    }

    Serial.println("\n📤 Submitting score to server...");

    HTTPClient http;
    String url = String(SERVER_URL) + "/api/score";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    // Build JSON payload
    String payload = "{";
    payload += "\"puck_id\":" + String(puckID) + ",";
    payload += "\"game_type\":\"" + String(gameName) + "\",";
    payload += "\"score\":" + String(score);
    payload += "}";

    Serial.printf("   URL: %s\n", url.c_str());
    Serial.printf("   Payload: %s\n", payload.c_str());

    int httpResponseCode = http.POST(payload);

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("✅ Score submitted! (HTTP %d)\n", httpResponseCode);
        Serial.printf("   Response: %s\n", response.c_str());
        http.end();
        return true;
    } else {
        Serial.printf("❌ Score submission failed (Error %d)\n", httpResponseCode);
        http.end();
        return false;
    }
}

bool ServerComm::registerPuck(const char* puckName, int batteryLevel) {
    if (!wifiConnected) {
        return false;
    }

    Serial.println("\n📤 Registering puck with server...");

    HTTPClient http;
    String url = String(SERVER_URL) + "/api/register";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    // Build JSON payload
    String payload = "{";
    payload += "\"puck_id\":" + String(puckID) + ",";
    payload += "\"name\":\"" + String(puckName) + "\",";
    payload += "\"table_number\":" + String(tableNumber) + ",";
    payload += "\"battery_level\":" + String(batteryLevel);
    payload += "}";

    int httpResponseCode = http.POST(payload);

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("✅ Puck registered! (HTTP %d)\n", httpResponseCode);
        http.end();
        return true;
    } else {
        Serial.printf("❌ Registration failed (Error %d)\n", httpResponseCode);
        http.end();
        return false;
    }
}

bool ServerComm::startGame(uint8_t gameID, const char* gameName) {
    if (!wifiConnected) {
        return false;
    }

    HTTPClient http;
    String url = String(SERVER_URL) + "/api/game-start";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    // Build JSON payload
    String payload = "{";
    payload += "\"bar\":\"" + barSlug + "\",";
    payload += "\"table\":" + String(tableNumber) + ",";
    payload += "\"puck_id\":" + String(puckID) + ",";
    payload += "\"game_id\":" + String(gameID) + ",";
    payload += "\"game_name\":\"" + String(gameName) + "\"";
    payload += "}";

    int httpResponseCode = http.POST(payload);

    http.end();
    return (httpResponseCode > 0);
}

// ============================================================================
// BLE CALLBACKS
// ============================================================================

void ServerComm::onBLEConnect() {
    bleClientConnected = true;
    Serial.println("📱 Phone connected via BLE!");

    // Send welcome message
    if (pDataCharacteristic) {
        String msg = "{\"status\":\"connected\",\"puck\":" + String(puckID) + "}";
        pDataCharacteristic->setValue(msg.c_str());
        pDataCharacteristic->notify();
    }
}

void ServerComm::onBLEDisconnect() {
    bleClientConnected = false;
    Serial.println("📱 Phone disconnected from BLE");

    // Restart advertising
    delay(500);
    BLEDevice::startAdvertising();
}

void ServerComm::handleBLECommand(String command) {
    Serial.printf("📱 BLE Command received: %s\n", command.c_str());

    // Parse JSON command (simple string parsing for now)
    // Expected format: {"action":"start_game","game_id":1}

    if (command.indexOf("\"start_game\"") > 0) {
        // Extract game ID
        int gameIDIndex = command.indexOf("\"game_id\"");
        if (gameIDIndex > 0) {
            int colonIndex = command.indexOf(":", gameIDIndex);
            int commaIndex = command.indexOf(",", colonIndex);
            if (commaIndex < 0) commaIndex = command.indexOf("}", colonIndex);

            String gameIDStr = command.substring(colonIndex + 1, commaIndex);
            gameIDStr.trim();
            int gameID = gameIDStr.toInt();

            Serial.printf("   Starting game %d via BLE\n", gameID);

            // Send acknowledgment
            if (pDataCharacteristic) {
                String response = "{\"status\":\"game_starting\",\"game_id\":" + String(gameID) + "}";
                pDataCharacteristic->setValue(response.c_str());
                pDataCharacteristic->notify();
            }
        }
    }
    else if (command.indexOf("\"get_status\"") > 0) {
        // Send status
        if (pDataCharacteristic) {
            String response = "{";
            response += "\"wifi_connected\":" + String(wifiConnected ? "true" : "false") + ",";
            response += "\"puck_id\":" + String(puckID) + ",";
            response += "\"table\":" + String(tableNumber);
            response += "}";
            pDataCharacteristic->setValue(response.c_str());
            pDataCharacteristic->notify();
        }
    }
}
