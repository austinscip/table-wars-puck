/**
 * esp_now_multiplayer.h
 *
 * ESP-NOW Puck-to-Puck Communication
 * Direct communication between pucks WITHOUT WiFi router
 *
 * Features:
 *   - 250m range (way more than Bluetooth's 10m)
 *   - Up to 20 pucks can communicate
 *   - Very low power (20-30 mA vs WiFi's 250 mA)
 *   - No router needed
 *   - 1ms latency (instant!)
 *   - Works alongside WiFi (can use both)
 *
 * Perfect For:
 *   - Multiplayer battle games
 *   - Team coordination
 *   - Relay races
 *   - Synchronized challenges
 *   - Puck-to-puck attacks
 *
 * Hardware: NONE - built into ESP32!
 * Cost: $0
 */

#ifndef ESP_NOW_MULTIPLAYER_H
#define ESP_NOW_MULTIPLAYER_H

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

#define MAX_PUCKS 10  // Maximum pucks in network
#define CHANNEL 1     // WiFi channel (1-13)

// Message types
enum MessageType {
    MSG_PING,           // "Are you there?"
    MSG_PONG,           // "Yes I'm here!"
    MSG_ATTACK,         // Send damage to target
    MSG_DEFEND,         // Block incoming attack
    MSG_HEAL,           // Heal another puck
    MSG_POWER_UP,       // Share power-up
    MSG_SCORE,          // Broadcast score
    MSG_SYNC,           // Synchronize action
    MSG_TEAM_JOIN,      // Join a team
    MSG_TEAM_LEAVE,     // Leave team
    MSG_GAME_START,     // Start game
    MSG_GAME_END        // End game
};

// Message structure
struct PuckMessage {
    uint8_t type;          // MessageType
    uint8_t senderPuckId;  // Who sent this
    uint8_t targetPuckId;  // Who it's for (0 = broadcast)
    int16_t value1;        // Payload data
    int16_t value2;        // Payload data
    uint32_t timestamp;    // When sent
    char text[32];         // Optional text message
};

// Puck info
struct PuckInfo {
    uint8_t puckId;
    uint8_t macAddress[6];
    bool online;
    unsigned long lastSeen;
    int health;
    int score;
    uint8_t team;
};

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

bool espNowInitialized = false;
PuckInfo puckNetwork[MAX_PUCKS];
int discoveredPucks = 0;

// Callback function pointers
void (*onMessageReceived)(PuckMessage msg) = nullptr;
void (*onPuckDiscovered)(uint8_t puckId) = nullptr;
void (*onPuckLost)(uint8_t puckId) = nullptr;

// ============================================================================
// ESP-NOW INITIALIZATION
// ============================================================================

/**
 * Callback when data is sent
 */
void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    if (status == ESP_NOW_SEND_SUCCESS) {
        // Message delivered successfully
    } else {
        Serial.println("⚠️ Message send failed");
    }
}

/**
 * Callback when data is received
 */
void onDataReceive(const uint8_t *mac, const uint8_t *incomingData, int len) {
    PuckMessage msg;
    memcpy(&msg, incomingData, sizeof(msg));

    // Update last seen time
    for (int i = 0; i < discoveredPucks; i++) {
        if (puckNetwork[i].puckId == msg.senderPuckId) {
            puckNetwork[i].lastSeen = millis();
            puckNetwork[i].online = true;
            break;
        }
    }

    // Call user callback
    if (onMessageReceived != nullptr) {
        onMessageReceived(msg);
    }

    // Handle built-in message types
    switch (msg.type) {
        case MSG_PING:
            // Respond to ping
            sendPong(msg.senderPuckId);
            break;

        case MSG_PONG:
            Serial.printf("📡 Puck %d is online\n", msg.senderPuckId);
            break;

        case MSG_ATTACK:
            Serial.printf("⚔️ Puck %d attacked for %d damage!\n",
                         msg.senderPuckId, msg.value1);
            // Flash red
            setAllLEDs(255, 0, 0);
            delay(200);
            setAllLEDs(0, 0, 0);
            break;

        case MSG_HEAL:
            Serial.printf("💚 Puck %d healed you for %d HP!\n",
                         msg.senderPuckId, msg.value1);
            // Flash green
            setAllLEDs(0, 255, 0);
            delay(200);
            setAllLEDs(0, 0, 0);
            break;

        case MSG_POWER_UP:
            Serial.printf("⚡ Puck %d shared a power-up!\n", msg.senderPuckId);
            // Flash yellow
            setAllLEDs(255, 255, 0);
            delay(200);
            setAllLEDs(0, 0, 0);
            break;
    }
}

/**
 * Initialize ESP-NOW
 */
bool initESPNow() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📡 INITIALIZING ESP-NOW");
    Serial.println("═══════════════════════════════════");

    // Set WiFi mode to station
    WiFi.mode(WIFI_STA);

    // Print MAC address
    Serial.print("   MAC Address: ");
    Serial.println(WiFi.macAddress());

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("❌ ESP-NOW initialization failed");
        return false;
    }

    espNowInitialized = true;

    // Register callbacks
    esp_now_register_send_cb(onDataSent);
    esp_now_register_recv_cb(onDataReceive);

    // Initialize puck network
    for (int i = 0; i < MAX_PUCKS; i++) {
        puckNetwork[i].online = false;
        puckNetwork[i].health = 100;
        puckNetwork[i].score = 0;
        puckNetwork[i].team = 0;
    }

    Serial.println("✅ ESP-NOW initialized");
    Serial.printf("   Puck ID: %d\n", PUCK_ID);
    Serial.printf("   Max Range: 250 meters\n");
    Serial.printf("   Max Pucks: %d\n", MAX_PUCKS);
    Serial.println("═══════════════════════════════════\n");

    return true;
}

/**
 * Add a puck to the network
 */
bool addPuck(const uint8_t *macAddress) {
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, macAddress, 6);
    peerInfo.channel = CHANNEL;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("❌ Failed to add peer");
        return false;
    }

    return true;
}

/**
 * Add broadcast address (send to all pucks)
 */
void addBroadcastPeer() {
    uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    addPuck(broadcastAddress);
}

// ============================================================================
// SENDING MESSAGES
// ============================================================================

/**
 * Send message to specific puck
 */
void sendMessage(uint8_t targetPuckId, MessageType type, int16_t value1 = 0, int16_t value2 = 0, const char* text = "") {
    if (!espNowInitialized) {
        Serial.println("⚠️ ESP-NOW not initialized");
        return;
    }

    PuckMessage msg;
    msg.type = type;
    msg.senderPuckId = PUCK_ID;
    msg.targetPuckId = targetPuckId;
    msg.value1 = value1;
    msg.value2 = value2;
    msg.timestamp = millis();
    strncpy(msg.text, text, 31);
    msg.text[31] = '\0';

    // Broadcast or direct send
    uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    esp_now_send(broadcastAddress, (uint8_t*)&msg, sizeof(msg));
}

/**
 * Broadcast to all pucks
 */
void broadcast(MessageType type, int16_t value1 = 0, int16_t value2 = 0, const char* text = "") {
    sendMessage(0, type, value1, value2, text);
}

/**
 * Send ping to discover nearby pucks
 */
void sendPing() {
    broadcast(MSG_PING);
}

/**
 * Respond to ping
 */
void sendPong(uint8_t targetPuckId) {
    sendMessage(targetPuckId, MSG_PONG);
}

/**
 * Attack another puck
 */
void attackPuck(uint8_t targetPuckId, int damage) {
    sendMessage(targetPuckId, MSG_ATTACK, damage);
    Serial.printf("⚔️ Attacking Puck %d for %d damage!\n", targetPuckId, damage);
}

/**
 * Heal another puck
 */
void healPuck(uint8_t targetPuckId, int healAmount) {
    sendMessage(targetPuckId, MSG_HEAL, healAmount);
    Serial.printf("💚 Healing Puck %d for %d HP!\n", targetPuckId, healAmount);
}

/**
 * Share power-up with another puck
 */
void sharePowerUp(uint8_t targetPuckId, int powerUpType) {
    sendMessage(targetPuckId, MSG_POWER_UP, powerUpType);
}

/**
 * Broadcast your score
 */
void broadcastScore(int score) {
    broadcast(MSG_SCORE, score);
}

// ============================================================================
// PUCK DISCOVERY
// ============================================================================

/**
 * Discover nearby pucks
 */
void discoverPucks() {
    Serial.println("\n🔍 DISCOVERING NEARBY PUCKS");
    Serial.println("Sending ping...");

    discoveredPucks = 0;
    sendPing();

    // Wait for responses
    delay(2000);

    Serial.printf("✅ Found %d pucks\n", discoveredPucks);

    for (int i = 0; i < discoveredPucks; i++) {
        if (puckNetwork[i].online) {
            Serial.printf("   Puck %d: Online\n", puckNetwork[i].puckId);
        }
    }

    Serial.println();
}

/**
 * Check for offline pucks
 */
void checkPuckStatus() {
    unsigned long now = millis();

    for (int i = 0; i < discoveredPucks; i++) {
        if (puckNetwork[i].online && (now - puckNetwork[i].lastSeen > 10000)) {
            // Puck offline for 10 seconds
            puckNetwork[i].online = false;

            Serial.printf("📴 Puck %d went offline\n", puckNetwork[i].puckId);

            if (onPuckLost != nullptr) {
                onPuckLost(puckNetwork[i].puckId);
            }
        }
    }
}

// ============================================================================
// GAME EXAMPLES
// ============================================================================

/**
 * GAME 1: Puck Wars (Battle Royale)
 */
void gameePuckWars() {
    Serial.println("\n⚔️ PUCK WARS - BATTLE ROYALE");
    Serial.println("Last puck standing wins!");

    initESPNow();
    addBroadcastPeer();

    // Discover opponents
    discoverPucks();

    int health = 100;
    int ammo = 10;

    while (health > 0) {
        // Check for incoming attacks in onDataReceive callback

        // Attack: Press button
        if (digitalRead(BUTTON_PIN) == LOW && ammo > 0) {
            // Shake to aim at nearest puck
            readAccelerometer();
            int targetPuck = random(1, 7);  // Random target (improve with shake detection)

            attackPuck(targetPuck, 20);
            ammo--;

            // Show attack animation
            for (int i = 0; i < 16; i++) {
                leds[i] = CRGB(255, 0, 0);
            }
            FastLED.show();
            delay(500);
            setAllLEDs(0, 0, 0);

            delay(1000);  // Attack cooldown
        }

        // Show health on LEDs
        int healthLEDs = (health * 16) / 100;
        for (int i = 0; i < 16; i++) {
            if (i < healthLEDs) {
                leds[i] = CRGB(0, 255, 0);  // Green = health
            } else {
                leds[i] = CRGB(0, 0, 0);
            }
        }
        FastLED.show();

        delay(100);
    }

    Serial.println("💀 YOU DIED!");
    broadcast(MSG_GAME_END, PUCK_ID);
}

/**
 * GAME 2: Hot Potato Relay
 */
void gameHotPotato() {
    Serial.println("\n🥔 HOT POTATO RELAY");
    Serial.println("Pass the potato before time runs out!");

    initESPNow();
    addBroadcastPeer();
    discoverPucks();

    bool hasPotato = (PUCK_ID == 1);  // Puck 1 starts
    unsigned long potatoTimer = 0;
    int explosionTime = 10000;  // 10 seconds

    while (true) {
        if (hasPotato) {
            unsigned long timeLeft = explosionTime - (millis() - potatoTimer);

            // Show countdown on LEDs
            int ledsLit = (timeLeft * 16) / explosionTime;
            for (int i = 0; i < 16; i++) {
                if (i < ledsLit) {
                    leds[i] = CRGB(255, 165, 0);  // Orange
                } else {
                    leds[i] = CRGB(0, 0, 0);
                }
            }
            FastLED.show();

            // Pass potato: Shake puck
            if (detectShake()) {
                int targetPuck = random(1, discoveredPucks + 1);
                if (targetPuck != PUCK_ID) {
                    sendMessage(targetPuck, MSG_POWER_UP, 1, 0, "potato");
                    hasPotato = false;
                    Serial.printf("🥔 Passed potato to Puck %d\n", targetPuck);
                }
            }

            // Check if time's up
            if (timeLeft <= 0) {
                Serial.println("💥 BOOM! YOU EXPLODED!");

                // Explosion animation
                for (int i = 0; i < 10; i++) {
                    setAllLEDs(255, 0, 0);
                    delay(100);
                    setAllLEDs(255, 255, 0);
                    delay(100);
                }

                break;
            }
        }

        delay(50);
    }
}

/**
 * GAME 3: Synchronized Shake Challenge
 */
void gameSyncShake() {
    Serial.println("\n🤝 SYNCHRONIZED SHAKE CHALLENGE");
    Serial.println("All pucks must shake at the same time!");

    initESPNow();
    addBroadcastPeer();
    discoverPucks();

    for (int round = 1; round <= 5; round++) {
        Serial.printf("\n📍 Round %d\n", round);

        // Random countdown
        int countdown = random(3, 8);
        Serial.printf("Shake in %d seconds!\n", countdown);

        // Countdown animation
        for (int i = countdown; i > 0; i--) {
            Serial.printf("%d...\n", i);
            setAllLEDs(255, 255, 0);
            delay(500);
            setAllLEDs(0, 0, 0);
            delay(500);
        }

        Serial.println("NOW!");
        setAllLEDs(0, 255, 0);

        // Check if shake detected within 1 second window
        unsigned long windowStart = millis();
        bool shaked = false;

        while (millis() - windowStart < 1000) {
            if (detectShake()) {
                shaked = true;
                broadcast(MSG_SYNC, PUCK_ID, round);
                Serial.println("✅ Shaked in time!");
                break;
            }
            delay(10);
        }

        if (!shaked) {
            Serial.println("❌ Too slow!");
        }

        setAllLEDs(0, 0, 0);
        delay(2000);
    }
}

/**
 * GAME 4: Team Relay Race
 */
void gameTeamRelay() {
    Serial.println("\n🏃 TEAM RELAY RACE");
    Serial.println("Pass the baton to your teammate!");

    initESPNow();
    addBroadcastPeer();
    discoverPucks();

    // Assign teams (odd vs even puck IDs)
    uint8_t team = (PUCK_ID % 2);
    broadcast(MSG_TEAM_JOIN, team);

    bool hasBaton = (PUCK_ID == 1) || (PUCK_ID == 2);  // Team leaders start
    int lapCount = 0;
    int targetLaps = 3;

    while (lapCount < targetLaps) {
        if (hasBaton) {
            // Show team color
            if (team == 0) {
                setAllLEDs(255, 0, 0);  // Red team
            } else {
                setAllLEDs(0, 0, 255);  // Blue team
            }

            // Complete lap: shake 10 times
            int shakes = 0;
            Serial.printf("Shake 10 times! (%d/10)\n", shakes);

            while (shakes < 10) {
                if (detectShake()) {
                    shakes++;
                    Serial.printf("Shakes: %d/10\n", shakes);

                    // Progress bar on LEDs
                    int ledsLit = (shakes * 16) / 10;
                    for (int i = 0; i < ledsLit; i++) {
                        leds[i] = CRGB(0, 255, 0);
                    }
                    FastLED.show();

                    delay(200);
                }
                delay(50);
            }

            lapCount++;
            Serial.printf("✅ Lap %d complete!\n", lapCount);

            if (lapCount < targetLaps) {
                // Pass baton to teammate
                int teammate = (team == 0) ? 3 : 4;  // Simplified
                sendMessage(teammate, MSG_POWER_UP, 1, 0, "baton");
                hasBaton = false;
                Serial.printf("🏃 Passed baton to Puck %d\n", teammate);

                setAllLEDs(0, 0, 0);
            }
        }

        delay(100);
    }

    Serial.println("🏆 YOUR TEAM FINISHED!");
    setAllLEDs(0, 255, 0);
}

/**
 * GAME 5: Cooperative Boss Battle
 */
void gameBossBattle() {
    Serial.println("\n🐲 COOPERATIVE BOSS BATTLE");
    Serial.println("Team up to defeat the boss!");

    initESPNow();
    addBroadcastPeer();
    discoverPucks();

    int bossHealth = 1000;
    int playerDamage = 50;

    while (bossHealth > 0) {
        Serial.printf("\n🐲 Boss Health: %d\n", bossHealth);

        // Attack: shake puck
        if (detectShake()) {
            broadcast(MSG_ATTACK, playerDamage);
            bossHealth -= playerDamage;

            Serial.printf("⚔️ You dealt %d damage!\n", playerDamage);

            // Attack animation
            for (int i = 0; i < 3; i++) {
                setAllLEDs(255, 0, 0);
                delay(100);
                setAllLEDs(0, 0, 0);
                delay(100);
            }

            // Cooldown
            delay(2000);
        }

        // Show boss health on LEDs
        int healthLEDs = (bossHealth * 16) / 1000;
        for (int i = 0; i < 16; i++) {
            if (i < healthLEDs) {
                leds[i] = CRGB(255, 0, 0);  // Red = boss health
            } else {
                leds[i] = CRGB(0, 0, 0);
            }
        }
        FastLED.show();

        delay(100);
    }

    Serial.println("\n🏆 BOSS DEFEATED!");
    broadcast(MSG_GAME_END, PUCK_ID);

    // Victory animation
    rainbowCycle(50);
}

// ============================================================================
// DIAGNOSTICS
// ============================================================================

/**
 * Print ESP-NOW diagnostics
 */
void printESPNowDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📡 ESP-NOW DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");

    Serial.printf("Initialized: %s\n", espNowInitialized ? "Yes" : "No");
    Serial.printf("Puck ID: %d\n", PUCK_ID);
    Serial.printf("MAC Address: %s\n", WiFi.macAddress().c_str());
    Serial.printf("Channel: %d\n", CHANNEL);
    Serial.printf("Discovered Pucks: %d\n", discoveredPucks);

    Serial.println("\nOnline Pucks:");
    for (int i = 0; i < discoveredPucks; i++) {
        if (puckNetwork[i].online) {
            Serial.printf("  Puck %d: Health=%d, Score=%d, Team=%d\n",
                         puckNetwork[i].puckId,
                         puckNetwork[i].health,
                         puckNetwork[i].score,
                         puckNetwork[i].team);
        }
    }

    Serial.println("═══════════════════════════════════\n");
}

#endif // ESP_NOW_MULTIPLAYER_H
