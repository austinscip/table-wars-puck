/*
 * TABLE WARS - WiFi Sync System
 *
 * ESP-NOW based puck-to-puck communication
 * Enables multiplayer games across 2-6 pucks
 */

#ifndef WIFI_SYNC_H
#define WIFI_SYNC_H

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

#define MAX_PUCKS           6
#define DISCOVERY_TIMEOUT   10000  // 10 seconds to find other pucks
#define MESSAGE_TIMEOUT     5000   // 5 seconds to wait for response
#define BROADCAST_INTERVAL  1000   // Send discovery every 1 second

// ============================================================================
// MESSAGE TYPES
// ============================================================================

enum MessageType {
    MSG_DISCOVERY,          // "I'm here!"
    MSG_DISCOVERY_ACK,      // "I see you!"
    MSG_GAME_START,         // Start a multiplayer game
    MSG_GAME_STATE,         // Sync game state
    MSG_BOMB_PASS,          // Pass the bomb to another puck
    MSG_TEAM_COLOR,         // Team assignment
    MSG_SCORE_UPDATE,       // Score update
    MSG_GAME_END,           // Game over
    MSG_HEARTBEAT           // Keep-alive
};

// ============================================================================
// MESSAGE STRUCTURES
// ============================================================================

// Base message header
struct MessageHeader {
    uint8_t type;           // MessageType
    uint8_t senderID;       // Puck ID of sender
    uint8_t targetID;       // 0 = broadcast, 1-6 = specific puck
    uint32_t timestamp;     // millis() when sent
    uint8_t sequenceNum;    // Message sequence number
};

// Discovery message
struct DiscoveryMessage {
    MessageHeader header;
    char puckName[16];      // "Puck_1", "Puck_2", etc.
    uint8_t batteryLevel;   // 0-100%
    bool isReady;           // Ready to play?
};

// Bomb pass message
struct BombPassMessage {
    MessageHeader header;
    uint32_t timeRemaining; // Milliseconds left on bomb
    uint8_t passerID;       // Who passed it
    uint8_t receiverID;     // Who receives it
};

// Team color message
struct TeamColorMessage {
    MessageHeader header;
    uint32_t teamColor;     // RGB color value
    uint8_t teamID;         // 0 or 1 (red team vs blue team)
};

// Score update message
struct ScoreMessage {
    MessageHeader header;
    uint32_t score;
    uint8_t gameID;         // Which game
};

// Game state message
struct GameStateMessage {
    MessageHeader header;
    uint8_t gameID;
    uint8_t roundNumber;
    uint32_t gameData;      // Generic data field
    bool isActive;
};

// ============================================================================
// PUCK INFO
// ============================================================================

struct PuckInfo {
    uint8_t id;
    uint8_t macAddress[6];
    char name[16];
    bool isOnline;
    unsigned long lastSeen;
    uint8_t batteryLevel;
    bool isReady;
    int16_t rssi;           // Signal strength
};

// ============================================================================
// WIFI SYNC CLASS
// ============================================================================

class WiFiSync {
private:
    uint8_t myPuckID;
    uint8_t myMacAddress[6];
    PuckInfo pucks[MAX_PUCKS];
    uint8_t activePuckCount;
    uint8_t messageSequence;

    // Callbacks
    void (*onPuckDiscovered)(uint8_t puckID);
    void (*onPuckLost)(uint8_t puckID);
    void (*onBombReceived)(uint8_t fromPuckID, uint32_t timeRemaining);
    void (*onGameStart)(uint8_t gameID);
    void (*onScoreReceived)(uint8_t puckID, uint32_t score);

    // ESP-NOW callbacks
    static void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status);
    static void onDataReceived(const uint8_t *mac_addr, const uint8_t *data, int len);

    // Message handlers
    void handleDiscovery(const DiscoveryMessage* msg, const uint8_t* senderMac);
    void handleBombPass(const BombPassMessage* msg);
    void handleTeamColor(const TeamColorMessage* msg);
    void handleScore(const ScoreMessage* msg);
    void handleGameState(const GameStateMessage* msg);

    // Helper functions
    bool addPeer(const uint8_t* macAddress);
    void updatePuckInfo(uint8_t puckID, const uint8_t* macAddress);
    uint8_t getPuckIndexByMac(const uint8_t* macAddress);

public:
    WiFiSync(uint8_t puckID);

    // Initialization
    bool begin();
    void stop();

    // Discovery
    bool discoverPucks(uint16_t timeoutMs = DISCOVERY_TIMEOUT);
    void sendDiscoveryBeacon();
    uint8_t getActivePuckCount() { return activePuckCount; }
    PuckInfo* getActivePucks() { return pucks; }

    // Messaging
    bool sendBombPass(uint8_t targetPuckID, uint32_t timeRemaining);
    bool sendTeamColor(uint8_t targetPuckID, uint32_t color, uint8_t teamID);
    bool sendScore(uint32_t score, uint8_t gameID);
    bool sendGameStart(uint8_t gameID);
    bool sendGameState(uint8_t gameID, uint8_t round, uint32_t data);
    bool broadcastMessage(const void* message, size_t size);

    // Callbacks
    void setOnPuckDiscovered(void (*callback)(uint8_t)) { onPuckDiscovered = callback; }
    void setOnPuckLost(void (*callback)(uint8_t)) { onPuckLost = callback; }
    void setOnBombReceived(void (*callback)(uint8_t, uint32_t)) { onBombReceived = callback; }
    void setOnGameStart(void (*callback)(uint8_t)) { onGameStart = callback; }
    void setOnScoreReceived(void (*callback)(uint8_t, uint32_t)) { onScoreReceived = callback; }

    // Utilities
    void update();  // Call in loop() to handle timeouts
    bool isPuckOnline(uint8_t puckID);
    int16_t getPuckRSSI(uint8_t puckID);
    void printPuckList();
};

// Global instance (needed for ESP-NOW callbacks)
extern WiFiSync* g_wifiSync;

#endif // WIFI_SYNC_H
