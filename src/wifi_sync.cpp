/*
 * TABLE WARS - WiFi Sync Implementation
 */

#include "wifi_sync.h"

// Global instance for callbacks
WiFiSync* g_wifiSync = nullptr;

// ============================================================================
// CONSTRUCTOR
// ============================================================================

WiFiSync::WiFiSync(uint8_t puckID) {
    myPuckID = puckID;
    activePuckCount = 0;
    messageSequence = 0;

    // Initialize puck list
    for (int i = 0; i < MAX_PUCKS; i++) {
        pucks[i].id = i + 1;
        pucks[i].isOnline = false;
        pucks[i].lastSeen = 0;
        pucks[i].batteryLevel = 0;
        pucks[i].isReady = false;
        pucks[i].rssi = -100;
    }

    // Initialize callbacks to nullptr
    onPuckDiscovered = nullptr;
    onPuckLost = nullptr;
    onBombReceived = nullptr;
    onGameStart = nullptr;
    onScoreReceived = nullptr;

    g_wifiSync = this;
}

// ============================================================================
// INITIALIZATION
// ============================================================================

bool WiFiSync::begin() {
    Serial.println("[WiFi] Starting WiFi Sync...");

    // Set WiFi mode
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Get MAC address
    WiFi.macAddress(myMacAddress);
    Serial.printf("[WiFi] My MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                  myMacAddress[0], myMacAddress[1], myMacAddress[2],
                  myMacAddress[3], myMacAddress[4], myMacAddress[5]);

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("[WiFi] ❌ ESP-NOW init failed");
        return false;
    }

    Serial.println("[WiFi] ✅ ESP-NOW initialized");

    // Register callbacks
    esp_now_register_send_cb(onDataSent);
    esp_now_register_recv_cb(onDataReceived);

    // Set WiFi channel and power
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_max_tx_power(84); // Max power for better range

    return true;
}

void WiFiSync::stop() {
    Serial.println("[WiFi] Stopping WiFi Sync...");
    esp_now_deinit();
    WiFi.disconnect();
    WiFi.mode(WIFI_OFF);
}

// ============================================================================
// ESP-NOW CALLBACKS
// ============================================================================

void WiFiSync::onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    // Optional: Track send success/failure
    if (status != ESP_NOW_SEND_SUCCESS) {
        Serial.println("[WiFi] ⚠️  Send failed");
    }
}

void WiFiSync::onDataReceived(const uint8_t *mac_addr, const uint8_t *data, int len) {
    if (!g_wifiSync) return;

    // Parse message header
    if (len < sizeof(MessageHeader)) return;

    MessageHeader* header = (MessageHeader*)data;

    // Ignore messages from self
    if (header->senderID == g_wifiSync->myPuckID) return;

    // Handle based on message type
    switch (header->type) {
        case MSG_DISCOVERY:
            if (len >= sizeof(DiscoveryMessage)) {
                g_wifiSync->handleDiscovery((DiscoveryMessage*)data, mac_addr);
            }
            break;

        case MSG_BOMB_PASS:
            if (len >= sizeof(BombPassMessage)) {
                g_wifiSync->handleBombPass((BombPassMessage*)data);
            }
            break;

        case MSG_TEAM_COLOR:
            if (len >= sizeof(TeamColorMessage)) {
                g_wifiSync->handleTeamColor((TeamColorMessage*)data);
            }
            break;

        case MSG_SCORE_UPDATE:
            if (len >= sizeof(ScoreMessage)) {
                g_wifiSync->handleScore((ScoreMessage*)data);
            }
            break;

        case MSG_GAME_STATE:
            if (len >= sizeof(GameStateMessage)) {
                g_wifiSync->handleGameState((GameStateMessage*)data);
            }
            break;
    }
}

// ============================================================================
// MESSAGE HANDLERS
// ============================================================================

void WiFiSync::handleDiscovery(const DiscoveryMessage* msg, const uint8_t* senderMac) {
    uint8_t puckID = msg->header.senderID;

    if (puckID < 1 || puckID > MAX_PUCKS) return;

    uint8_t index = puckID - 1;
    bool wasOffline = !pucks[index].isOnline;

    // Update puck info
    pucks[index].id = puckID;
    memcpy(pucks[index].macAddress, senderMac, 6);
    strncpy(pucks[index].name, msg->puckName, 15);
    pucks[index].name[15] = '\0';
    pucks[index].isOnline = true;
    pucks[index].lastSeen = millis();
    pucks[index].batteryLevel = msg->batteryLevel;
    pucks[index].isReady = msg->isReady;

    // Add as peer if new
    if (wasOffline) {
        addPeer(senderMac);
        activePuckCount++;

        Serial.printf("[WiFi] 🎮 Discovered: %s (Puck %d)\n",
                      pucks[index].name, puckID);

        if (onPuckDiscovered) {
            onPuckDiscovered(puckID);
        }

        // Send acknowledgment
        DiscoveryMessage ack;
        ack.header.type = MSG_DISCOVERY_ACK;
        ack.header.senderID = myPuckID;
        ack.header.targetID = puckID;
        ack.header.timestamp = millis();
        ack.header.sequenceNum = messageSequence++;
        snprintf(ack.puckName, sizeof(ack.puckName), "Puck_%d", myPuckID);
        ack.batteryLevel = 100; // TODO: Implement real battery monitoring
        ack.isReady = true;

        esp_now_send(senderMac, (uint8_t*)&ack, sizeof(ack));
    }
}

void WiFiSync::handleBombPass(const BombPassMessage* msg) {
    if (msg->receiverID != myPuckID) return;

    Serial.printf("[WiFi] 💣 Bomb received from Puck %d! Time: %lums\n",
                  msg->passerID, msg->timeRemaining);

    if (onBombReceived) {
        onBombReceived(msg->passerID, msg->timeRemaining);
    }
}

void WiFiSync::handleTeamColor(const TeamColorMessage* msg) {
    Serial.printf("[WiFi] 🎨 Team color update from Puck %d\n",
                  msg->header.senderID);
    // TODO: Implement team color handling
}

void WiFiSync::handleScore(const ScoreMessage* msg) {
    Serial.printf("[WiFi] 💯 Score update from Puck %d: %lu\n",
                  msg->header.senderID, msg->score);

    if (onScoreReceived) {
        onScoreReceived(msg->header.senderID, msg->score);
    }
}

void WiFiSync::handleGameState(const GameStateMessage* msg) {
    Serial.printf("[WiFi] 🎮 Game state from Puck %d: Game %d, Round %d\n",
                  msg->header.senderID, msg->gameID, msg->roundNumber);

    if (msg->gameID > 0 && onGameStart && msg->roundNumber == 1) {
        onGameStart(msg->gameID);
    }
}

// ============================================================================
// DISCOVERY
// ============================================================================

bool WiFiSync::discoverPucks(uint16_t timeoutMs) {
    Serial.println("[WiFi] 🔍 Starting puck discovery...");

    unsigned long startTime = millis();
    activePuckCount = 0;

    // Reset puck list
    for (int i = 0; i < MAX_PUCKS; i++) {
        pucks[i].isOnline = false;
    }

    // Send discovery beacons
    while (millis() - startTime < timeoutMs) {
        sendDiscoveryBeacon();
        delay(BROADCAST_INTERVAL);

        // Count active pucks
        uint8_t count = 0;
        for (int i = 0; i < MAX_PUCKS; i++) {
            if (pucks[i].isOnline && pucks[i].id != myPuckID) {
                count++;
            }
        }
        activePuckCount = count;

        Serial.printf("[WiFi] Found %d pucks...\n", activePuckCount);
    }

    Serial.printf("[WiFi] ✅ Discovery complete: %d pucks found\n", activePuckCount);
    printPuckList();

    return activePuckCount > 0;
}

void WiFiSync::sendDiscoveryBeacon() {
    DiscoveryMessage msg;
    msg.header.type = MSG_DISCOVERY;
    msg.header.senderID = myPuckID;
    msg.header.targetID = 0; // Broadcast
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;

    snprintf(msg.puckName, sizeof(msg.puckName), "Puck_%d", myPuckID);
    msg.batteryLevel = 100; // TODO: Real battery monitoring
    msg.isReady = true;

    broadcastMessage(&msg, sizeof(msg));
}

// ============================================================================
// MESSAGING
// ============================================================================

bool WiFiSync::sendBombPass(uint8_t targetPuckID, uint32_t timeRemaining) {
    if (targetPuckID < 1 || targetPuckID > MAX_PUCKS) return false;
    if (!pucks[targetPuckID - 1].isOnline) return false;

    BombPassMessage msg;
    msg.header.type = MSG_BOMB_PASS;
    msg.header.senderID = myPuckID;
    msg.header.targetID = targetPuckID;
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;
    msg.timeRemaining = timeRemaining;
    msg.passerID = myPuckID;
    msg.receiverID = targetPuckID;

    Serial.printf("[WiFi] 💣 Passing bomb to Puck %d (%lums left)\n",
                  targetPuckID, timeRemaining);

    esp_err_t result = esp_now_send(pucks[targetPuckID - 1].macAddress,
                                     (uint8_t*)&msg, sizeof(msg));

    return result == ESP_OK;
}

bool WiFiSync::sendTeamColor(uint8_t targetPuckID, uint32_t color, uint8_t teamID) {
    if (targetPuckID < 1 || targetPuckID > MAX_PUCKS) return false;
    if (!pucks[targetPuckID - 1].isOnline) return false;

    TeamColorMessage msg;
    msg.header.type = MSG_TEAM_COLOR;
    msg.header.senderID = myPuckID;
    msg.header.targetID = targetPuckID;
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;
    msg.teamColor = color;
    msg.teamID = teamID;

    esp_err_t result = esp_now_send(pucks[targetPuckID - 1].macAddress,
                                     (uint8_t*)&msg, sizeof(msg));

    return result == ESP_OK;
}

bool WiFiSync::sendScore(uint32_t score, uint8_t gameID) {
    ScoreMessage msg;
    msg.header.type = MSG_SCORE_UPDATE;
    msg.header.senderID = myPuckID;
    msg.header.targetID = 0; // Broadcast
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;
    msg.score = score;
    msg.gameID = gameID;

    return broadcastMessage(&msg, sizeof(msg));
}

bool WiFiSync::sendGameStart(uint8_t gameID) {
    GameStateMessage msg;
    msg.header.type = MSG_GAME_START;
    msg.header.senderID = myPuckID;
    msg.header.targetID = 0; // Broadcast
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;
    msg.gameID = gameID;
    msg.roundNumber = 1;
    msg.gameData = 0;
    msg.isActive = true;

    return broadcastMessage(&msg, sizeof(msg));
}

bool WiFiSync::sendGameState(uint8_t gameID, uint8_t round, uint32_t data) {
    GameStateMessage msg;
    msg.header.type = MSG_GAME_STATE;
    msg.header.senderID = myPuckID;
    msg.header.targetID = 0; // Broadcast
    msg.header.timestamp = millis();
    msg.header.sequenceNum = messageSequence++;
    msg.gameID = gameID;
    msg.roundNumber = round;
    msg.gameData = data;
    msg.isActive = true;

    return broadcastMessage(&msg, sizeof(msg));
}

bool WiFiSync::broadcastMessage(const void* message, size_t size) {
    // Broadcast to all known peers
    uint8_t broadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    // Add broadcast address as peer if not already added
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastMac, 6);
    peerInfo.channel = 1;
    peerInfo.encrypt = false;

    if (!esp_now_is_peer_exist(broadcastMac)) {
        esp_now_add_peer(&peerInfo);
    }

    esp_err_t result = esp_now_send(broadcastMac, (uint8_t*)message, size);
    return result == ESP_OK;
}

// ============================================================================
// UTILITIES
// ============================================================================

bool WiFiSync::addPeer(const uint8_t* macAddress) {
    if (esp_now_is_peer_exist(macAddress)) {
        return true;
    }

    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, macAddress, 6);
    peerInfo.channel = 1;
    peerInfo.encrypt = false;

    esp_err_t result = esp_now_add_peer(&peerInfo);
    return result == ESP_OK;
}

void WiFiSync::update() {
    unsigned long now = millis();

    // Check for offline pucks (no heartbeat in 10 seconds)
    for (int i = 0; i < MAX_PUCKS; i++) {
        if (pucks[i].isOnline && (now - pucks[i].lastSeen > 10000)) {
            pucks[i].isOnline = false;
            activePuckCount--;

            Serial.printf("[WiFi] ⚠️  Puck %d went offline\n", pucks[i].id);

            if (onPuckLost) {
                onPuckLost(pucks[i].id);
            }
        }
    }
}

bool WiFiSync::isPuckOnline(uint8_t puckID) {
    if (puckID < 1 || puckID > MAX_PUCKS) return false;
    return pucks[puckID - 1].isOnline;
}

int16_t WiFiSync::getPuckRSSI(uint8_t puckID) {
    if (puckID < 1 || puckID > MAX_PUCKS) return -100;
    return pucks[puckID - 1].rssi;
}

void WiFiSync::printPuckList() {
    Serial.println("\n╔══════════════════════════════════════╗");
    Serial.println("║        ACTIVE PUCKS                  ║");
    Serial.println("╠══════════════════════════════════════╣");

    for (int i = 0; i < MAX_PUCKS; i++) {
        if (pucks[i].isOnline) {
            Serial.printf("║ %s - Battery: %d%% - Ready: %s ║\n",
                         pucks[i].name,
                         pucks[i].batteryLevel,
                         pucks[i].isReady ? "✅" : "❌");
        }
    }

    Serial.println("╚══════════════════════════════════════╝\n");
}
