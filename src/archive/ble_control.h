/*
 * TABLE WARS - BLE Remote Control Module
 *
 * Enables bar staff to control pucks via Bluetooth using the mobile app
 * Works alongside WiFi for dual connectivity
 *
 * Features:
 * - Remote game start/stop
 * - Battery level monitoring
 * - Puck status reporting
 * - Firmware version info
 */

#ifndef BLE_CONTROL_H
#define BLE_CONTROL_H

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ============================================================================
// BLE SERVICE UUIDs (Match mobile app expectations)
// ============================================================================

// Battery Service (Standard Bluetooth SIG)
#define BATTERY_SERVICE_UUID        "0000180f-0000-1000-8000-00805f9b34fb"
#define BATTERY_LEVEL_CHAR_UUID     "00002a19-0000-1000-8000-00805f9b34fb"

// Game Control Service (Custom)
#define GAME_SERVICE_UUID           "00001800-0000-1000-8000-00805f9b34fb"
#define GAME_COMMAND_CHAR_UUID      "00002a00-0000-1000-8000-00805f9b34fb"
#define GAME_STATE_CHAR_UUID        "00002a01-0000-1000-8000-00805f9b34fb"

// Device Info Service (Standard Bluetooth SIG)
#define DEVICE_INFO_SERVICE_UUID    "0000180a-0000-1000-8000-00805f9b34fb"
#define FIRMWARE_VERSION_CHAR_UUID  "00002a26-0000-1000-8000-00805f9b34fb"
#define PUCK_ID_CHAR_UUID           "00002a24-0000-1000-8000-00805f9b34fb"

// ============================================================================
// GAME COMMAND CODES
// ============================================================================

#define GAME_CMD_STOP              0x00
#define GAME_CMD_SPEED_TAP         0x01
#define GAME_CMD_SHAKE_DUEL        0x02
#define GAME_CMD_RED_LIGHT         0x03
#define GAME_CMD_LED_CHASE         0x04
#define GAME_CMD_COLOR_WARS        0x05
#define GAME_CMD_RAINBOW_ROULETTE  0x06
#define GAME_CMD_VISUAL_BOMB       0x07
#define GAME_CMD_SIMON_SAYS        0x08
#define GAME_CMD_HOT_POTATO        0x09
#define GAME_CMD_DRUNK_DUEL        0x0A
// Add more game codes as needed...

// ============================================================================
// BLE CONTROL CLASS
// ============================================================================

class BLEControl {
private:
    BLEServer* pServer;
    BLECharacteristic* pBatteryChar;
    BLECharacteristic* pGameCommandChar;
    BLECharacteristic* pGameStateChar;
    BLECharacteristic* pFirmwareVersionChar;
    BLECharacteristic* pPuckIDChar;

    bool deviceConnected;
    uint8_t currentBatteryLevel;
    uint8_t currentGameID;
    bool gameRunning;

    // Callback for game commands from mobile app
    void (*gameCommandCallback)(uint8_t gameID);

public:
    BLEControl() :
        pServer(nullptr),
        pBatteryChar(nullptr),
        pGameCommandChar(nullptr),
        pGameStateChar(nullptr),
        pFirmwareVersionChar(nullptr),
        pPuckIDChar(nullptr),
        deviceConnected(false),
        currentBatteryLevel(100),
        currentGameID(0),
        gameRunning(false),
        gameCommandCallback(nullptr)
    {}

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    void begin(uint8_t puckID, const char* deviceName = "TableWars_Puck") {
        char fullName[32];
        snprintf(fullName, sizeof(fullName), "%s_%d", deviceName, puckID);

        Serial.println("\n🔵 Initializing BLE...");
        Serial.printf("   Device Name: %s\n", fullName);

        // Initialize BLE
        BLEDevice::init(fullName);

        // Create BLE Server
        pServer = BLEDevice::createServer();
        pServer->setCallbacks(new ServerCallbacks(this));

        // Create services
        setupBatteryService();
        setupGameControlService();
        setupDeviceInfoService(puckID);

        // Start advertising
        startAdvertising();

        Serial.println("✅ BLE initialized and advertising");
        Serial.printf("   Ready for mobile app connection!\n\n");
    }

    // ========================================================================
    // SERVICE SETUP
    // ========================================================================

    void setupBatteryService() {
        BLEService* pService = pServer->createService(BATTERY_SERVICE_UUID);

        pBatteryChar = pService->createCharacteristic(
            BATTERY_LEVEL_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );
        pBatteryChar->addDescriptor(new BLE2902());

        // Set initial battery level
        uint8_t batteryLevel = 100;
        pBatteryChar->setValue(&batteryLevel, 1);

        pService->start();
    }

    void setupGameControlService() {
        BLEService* pService = pServer->createService(GAME_SERVICE_UUID);

        // Game Command Characteristic (Write from app)
        pGameCommandChar = pService->createCharacteristic(
            GAME_COMMAND_CHAR_UUID,
            BLECharacteristic::PROPERTY_WRITE
        );
        pGameCommandChar->setCallbacks(new GameCommandCallbacks(this));

        // Game State Characteristic (Read by app)
        pGameStateChar = pService->createCharacteristic(
            GAME_STATE_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );
        pGameStateChar->addDescriptor(new BLE2902());

        // Initial state: no game running
        uint8_t state[2] = {0x00, 0x00}; // [gameID, isRunning]
        pGameStateChar->setValue(state, 2);

        pService->start();
    }

    void setupDeviceInfoService(uint8_t puckID) {
        BLEService* pService = pServer->createService(DEVICE_INFO_SERVICE_UUID);

        // Firmware Version
        pFirmwareVersionChar = pService->createCharacteristic(
            FIRMWARE_VERSION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ
        );
        pFirmwareVersionChar->setValue("v1.0.0");

        // Puck ID
        pPuckIDChar = pService->createCharacteristic(
            PUCK_ID_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ
        );
        pPuckIDChar->setValue(&puckID, 1);

        pService->start();
    }

    void startAdvertising() {
        BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
        pAdvertising->addServiceUUID(BATTERY_SERVICE_UUID);
        pAdvertising->addServiceUUID(GAME_SERVICE_UUID);
        pAdvertising->setScanResponse(true);
        pAdvertising->setMinPreferred(0x06);  // Help with iOS
        pAdvertising->setMinPreferred(0x12);
        BLEDevice::startAdvertising();
    }

    // ========================================================================
    // PUBLIC API
    // ========================================================================

    // Set callback for when game commands are received
    void onGameCommand(void (*callback)(uint8_t gameID)) {
        gameCommandCallback = callback;
    }

    // Update battery level (0-100%)
    void updateBatteryLevel(uint8_t level) {
        if (level > 100) level = 100;

        currentBatteryLevel = level;

        if (pBatteryChar && deviceConnected) {
            pBatteryChar->setValue(&level, 1);
            pBatteryChar->notify();
        }
    }

    // Update game state
    void updateGameState(uint8_t gameID, bool running) {
        currentGameID = gameID;
        gameRunning = running;

        if (pGameStateChar && deviceConnected) {
            uint8_t state[2] = {gameID, (uint8_t)(running ? 0x01 : 0x00)};
            pGameStateChar->setValue(state, 2);
            pGameStateChar->notify();
        }
    }

    // Get connection status
    bool isConnected() {
        return deviceConnected;
    }

    // ========================================================================
    // INTERNAL CALLBACKS
    // ========================================================================

    class ServerCallbacks: public BLEServerCallbacks {
    private:
        BLEControl* parent;
    public:
        ServerCallbacks(BLEControl* p) : parent(p) {}

        void onConnect(BLEServer* pServer) {
            parent->deviceConnected = true;
            Serial.println("📱 Mobile app connected!");
        }

        void onDisconnect(BLEServer* pServer) {
            parent->deviceConnected = false;
            Serial.println("📱 Mobile app disconnected");

            // Restart advertising
            delay(500);
            pServer->startAdvertising();
            Serial.println("🔵 BLE advertising restarted");
        }
    };

    class GameCommandCallbacks: public BLECharacteristicCallbacks {
    private:
        BLEControl* parent;
    public:
        GameCommandCallbacks(BLEControl* p) : parent(p) {}

        void onWrite(BLECharacteristic* pCharacteristic) {
            std::string value = pCharacteristic->getValue();

            if (value.length() > 0) {
                uint8_t gameID = value[0];

                Serial.printf("🎮 Game command received: 0x%02X\n", gameID);

                // Call user callback if set
                if (parent->gameCommandCallback) {
                    parent->gameCommandCallback(gameID);
                }

                // Update game state
                parent->updateGameState(gameID, gameID != GAME_CMD_STOP);
            }
        }
    };
};

// ============================================================================
// GLOBAL INSTANCE
// ============================================================================

// Create global BLE control instance
BLEControl g_bleControl;

#endif // BLE_CONTROL_H
