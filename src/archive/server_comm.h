/*
 * TABLE WARS - Server Communication Module
 *
 * HTTP WiFi + BLE support for cloud scoreboard integration
 * - WiFi: Connect to router and submit scores to Flask API
 * - BLE: Advertise for Web Bluetooth connection from phones
 */

#ifndef SERVER_COMM_H
#define SERVER_COMM_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLEBeacon.h>
#include <BLE2902.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// WiFi credentials (set these for your network)
#define TW_WIFI_SSID       "ATT2UJj3HT"     // Your WiFi SSID
#define TW_WIFI_PASSWORD   "9dmg67p8ydq4"   // Your WiFi password
#define TW_WIFI_TIMEOUT    15000            // 15 seconds to connect

// Server configuration
#define SERVER_URL      "http://192.168.1.67:5001"  // Flask server URL
#define BAR_SLUG        "demo-bar"                  // Bar identifier
#define TABLE_NUMBER    1                           // Table number

// BLE configuration
#define BLE_DEVICE_NAME "TableWars_Puck_"  // Will append puck ID
#define SERVICE_UUID    "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_UUID_CMD   "beb5483e-36e1-4688-b7f5-ea07361b26a8"  // Command characteristic
#define CHAR_UUID_DATA  "cba1d466-344c-4be3-ab3f-189f80dd7518"  // Data characteristic

// ============================================================================
// SERVER COMM CLASS
// ============================================================================

class ServerComm {
private:
    uint8_t puckID;
    String barSlug;
    int tableNumber;
    bool wifiConnected;
    bool bleEnabled;

    // BLE objects
    BLEServer* pBLEServer;
    BLECharacteristic* pCommandCharacteristic;
    BLECharacteristic* pDataCharacteristic;
    bool bleClientConnected;

    // WiFi connection
    bool connectWiFi();
    void disconnectWiFi();

    // BLE setup
    bool setupBLE();
    void stopBLE();

public:
    ServerComm(uint8_t puckID);

    // Initialization
    bool begin(const char* ssid = TW_WIFI_SSID, const char* password = TW_WIFI_PASSWORD);
    bool beginBLE();
    void stop();

    // Server communication
    bool submitScore(const char* gameName, uint32_t score);
    bool registerPuck(const char* puckName, int batteryLevel = 100);
    bool startGame(uint8_t gameID, const char* gameName);

    // Configuration
    void setBarSlug(const char* slug) { barSlug = String(slug); }
    void setTableNumber(int table) { tableNumber = table; }

    // Status
    bool isWiFiConnected() { return wifiConnected; }
    bool isBLEConnected() { return bleClientConnected; }
    String getServerURL() { return String(SERVER_URL); }

    // BLE callbacks (must be public for static callbacks)
    void onBLEConnect();
    void onBLEDisconnect();
    void handleBLECommand(String command);
};

// ============================================================================
// BLE CALLBACKS
// ============================================================================

class MyServerCallbacks : public BLEServerCallbacks {
private:
    ServerComm* serverComm;
public:
    MyServerCallbacks(ServerComm* sc) : serverComm(sc) {}

    void onConnect(BLEServer* pServer) {
        serverComm->onBLEConnect();
    }

    void onDisconnect(BLEServer* pServer) {
        serverComm->onBLEDisconnect();
    }
};

class MyCommandCallbacks : public BLECharacteristicCallbacks {
private:
    ServerComm* serverComm;
public:
    MyCommandCallbacks(ServerComm* sc) : serverComm(sc) {}

    void onWrite(BLECharacteristic* pCharacteristic) {
        std::string value = pCharacteristic->getValue();
        if (value.length() > 0) {
            String command = String(value.c_str());
            serverComm->handleBLECommand(command);
        }
    }
};

#endif // SERVER_COMM_H
