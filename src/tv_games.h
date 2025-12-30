/*
 * TV-INTEGRATED GAMES (52-61) - ESP32 FIRMWARE
 *
 * Games that stream puck input to server via WebSocket
 * and display on TV screen in real-time.
 *
 * Games:
 * 52 - Puck Racer (car driving)
 * 53 - Obstacle Dodger (2D movement)
 * 54 - Puck Golf (swing & aim)
 * 55 - Space Invaders (tilt & shoot)
 * 56 - Pong Puck (paddle control)
 * 57 - Claw Machine (3D claw control)
 * 58 - Stack the Boxes (timing game)
 * 59 - Duck Hunt (aim & shoot)
 * 60 - Correlation Word Game (word matching)
 * 61 - Greyhound Racing (betting game)
 */

#ifndef TV_GAMES_H
#define TV_GAMES_H

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>

// ============================================================================
// WEBSOCKET CLIENT
// ============================================================================

WebSocketsClient webSocket;
bool ws_connected = false;
int current_tv_game = 0;  // 52-56, 0 = not playing

// WebSocket event handler
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected!");
            ws_connected = false;
            break;

        case WStype_CONNECTED:
            Serial.println("[WS] Connected to server!");
            ws_connected = true;
            break;

        case WStype_TEXT:
            Serial.printf("[WS] Message: %s\n", payload);
            // Handle server messages (game_over, error, etc.)
            break;

        case WStype_ERROR:
            Serial.println("[WS] Error!");
            break;
    }
}

// Initialize WebSocket connection
void initWebSocket(const char* serverIP, int serverPort) {
    Serial.println("🌐 Connecting to WebSocket server...");
    webSocket.begin(serverIP, serverPort, "/socket.io/?EIO=4&transport=websocket");
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    Serial.println("✅ WebSocket initialized");
}

// ============================================================================
// HTTP API FUNCTIONS
// ============================================================================

bool startTVGame(int gameId, int puckId, const char* serverURL) {
    HTTPClient http;

    String url = String(serverURL) + "/tv-games/start/" + String(gameId);
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"puck_id\": " + String(puckId) + "}";

    Serial.printf("🎮 Starting TV Game %d...\n", gameId);
    int httpCode = http.POST(payload);

    if (httpCode == 200) {
        Serial.println("✅ TV Game started!");
        current_tv_game = gameId;
        http.end();
        return true;
    } else {
        Serial.printf("❌ Failed to start game: %d\n", httpCode);
        http.end();
        return false;
    }
}

bool endTVGame(int puckId, const char* serverURL) {
    HTTPClient http;

    String url = String(serverURL) + "/tv-games/end/" + String(puckId);
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    Serial.println("🛑 Ending TV Game...");
    int httpCode = http.POST("");

    http.end();
    current_tv_game = 0;

    return (httpCode == 200);
}

// ============================================================================
// SEND PUCK INPUT TO SERVER
// ============================================================================

void sendPuckInput(int puckId, float tiltX, float tiltY, float shakeIntensity,
                   bool shakeDetected, bool buttonHeld) {
    if (!ws_connected) {
        Serial.println("⚠️  WebSocket not connected");
        return;
    }

    // Create JSON payload
    StaticJsonDocument<256> doc;
    doc["puck_id"] = puckId;
    doc["tilt_x"] = tiltX;
    doc["tilt_y"] = tiltY;
    doc["shake_intensity"] = shakeIntensity;
    doc["shake_detected"] = shakeDetected;
    doc["button_held"] = buttonHeld;
    doc["timestamp"] = millis();

    String json;
    serializeJson(doc, json);

    // Send via WebSocket with Socket.IO format
    String socketIOMessage = "42[\"puck_input\"," + json + "]";
    webSocket.sendTXT(socketIOMessage);
}

// ============================================================================
// GAME 52: PUCK RACER
// ============================================================================

void game_PuckRacer() {
    Serial.println("\n🏎️  GAME 52: PUCK RACER");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT LEFT/RIGHT = Steer car");
    Serial.println("  HOLD BUTTON = Accelerate");
    Serial.println("  SHAKE = Nitro boost!");
    Serial.println("  [3 crashes = game over]");
    Serial.println("═══════════════════════════════════\n");

    // Start game on server
    if (!startTVGame(52, PUCK_ID, SERVER_URL)) {
        Serial.println("❌ Failed to start Puck Racer");
        return;
    }

    // Green LEDs for ready
    setAllLEDs(0, 255, 0);
    delay(1000);

    // Game loop
    unsigned long gameStart = millis();
    unsigned long lastSend = 0;
    const int SEND_INTERVAL = 33;  // 30fps updates

    while (millis() - gameStart < 90000) {  // 90 second game
        webSocket.loop();  // Process WebSocket

        // Read puck sensors
        readAccelerometer();
        float tiltX = getTiltAngle_X();  // -45 to +45 degrees
        float tiltY = getTiltAngle_Y();
        float shakeIntensity = getShakeIntensity();
        bool shakeDetected = shakeIntensity > 15.0;
        bool buttonHeld = !digitalRead(BUTTON_PIN);

        // Send input to server at 30fps
        if (millis() - lastSend >= SEND_INTERVAL) {
            sendPuckInput(PUCK_ID, tiltX, tiltY, shakeIntensity,
                         shakeDetected, buttonHeld);
            lastSend = millis();
        }

        // Visual feedback
        if (buttonHeld) {
            setAllLEDs(255, 255, 0);  // Yellow when accelerating
        } else {
            setAllLEDs(0, 255, 0);  // Green otherwise
        }

        if (shakeDetected) {
            setAllLEDs(255, 0, 255);  // Purple for nitro!
            delay(100);
        }

        // Check for early exit
        if (digitalRead(BUTTON_PIN) == LOW) {
            unsigned long pressStart = millis();
            while (digitalRead(BUTTON_PIN) == LOW && millis() - pressStart < 3000) {
                delay(10);
            }
            if (millis() - pressStart >= 3000) {
                Serial.println("\n🛑 Player exited early");
                break;
            }
        }
    }

    // End game
    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🏁 PUCK RACER COMPLETE!");
}

// ============================================================================
// GAME 53: OBSTACLE DODGER
// ============================================================================

void game_ObstacleDodger() {
    Serial.println("\n☄️  GAME 53: OBSTACLE DODGER");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT = Move in 2D");
    Serial.println("  Dodge falling meteors!");
    Serial.println("  Collect yellow stars for points");
    Serial.println("  [5 hits = game over]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(53, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(0, 0, 255);
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 60000) {  // 60 second game
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float tiltY = getTiltAngle_Y();

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, tiltY, 0, false, false);
            lastSend = millis();
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n✅ OBSTACLE DODGER COMPLETE!");
}

// ============================================================================
// GAME 54: PUCK GOLF
// ============================================================================

void game_PuckGolf() {
    Serial.println("\n⛳ GAME 54: PUCK GOLF");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT = Aim direction");
    Serial.println("  HOLD BUTTON = Charge power");
    Serial.println("  SHAKE = Swing!");
    Serial.println("  [9 holes, lowest score wins]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(54, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(0, 255, 0);

    // Play until 9 holes complete (or timeout)
    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 300000) {  // 5 minute game
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float shakeIntensity = getShakeIntensity();
        bool buttonHeld = !digitalRead(BUTTON_PIN);

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, 0, shakeIntensity,
                         shakeIntensity > 15, buttonHeld);
            lastSend = millis();
        }

        // Visual: Show power charging
        if (buttonHeld) {
            int hue = (millis() / 10) % 255;
            setAllLEDs(hue, 255 - hue, 0);
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🏌️ PUCK GOLF COMPLETE!");
}

// ============================================================================
// GAME 55: SPACE INVADERS PUCK
// ============================================================================

void game_SpaceInvadersPuck() {
    Serial.println("\n👾 GAME 55: SPACE INVADERS PUCK");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT LEFT/RIGHT = Move ship");
    Serial.println("  SHAKE = Shoot aliens!");
    Serial.println("  [3 lives]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(55, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(0, 255, 0);
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 180000) {  // 3 minute game
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float shakeIntensity = getShakeIntensity();
        bool shooting = shakeIntensity > 15;

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, 0, shakeIntensity,
                         shooting, false);
            lastSend = millis();
        }

        // Flash red when shooting
        if (shooting) {
            setAllLEDs(255, 0, 0);
            tone(BUZZER_PIN, 1000, 50);
            delay(50);
        } else {
            setAllLEDs(0, 255, 0);
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🛸 SPACE INVADERS COMPLETE!");
}

// ============================================================================
// GAME 56: PONG PUCK
// ============================================================================

void game_PongPuck() {
    Serial.println("\n🏓 GAME 56: PONG PUCK");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT FORWARD/BACK = Move paddle");
    Serial.println("  [First to 7 points wins]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(56, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(255, 255, 255);
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 300000) {  // 5 minute max
        webSocket.loop();

        readAccelerometer();
        float tiltY = getTiltAngle_Y();

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, 0, tiltY, 0, false, false);
            lastSend = millis();
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🎾 PONG PUCK COMPLETE!");
}

// ============================================================================
// GAME 57: CLAW MACHINE
// ============================================================================

void game_ClawMachine() {
    Serial.println("\n🎰 GAME 57: CLAW MACHINE");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT = Move claw in 2D (X/Y)");
    Serial.println("  HOLD BUTTON = Drop claw and grab!");
    Serial.println("  Grab prizes from the machine");
    Serial.println("  [5 attempts total]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(57, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(255, 215, 0);  // Gold color
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 120000) {  // 2 minute game
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float tiltY = getTiltAngle_Y();
        bool buttonHeld = !digitalRead(BUTTON_PIN);

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, tiltY, 0, false, buttonHeld);
            lastSend = millis();
        }

        // LED feedback
        if (buttonHeld) {
            setAllLEDs(255, 0, 0);  // Red when grabbing
        } else {
            setAllLEDs(0, 255, 0);  // Green when positioning
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🎁 CLAW MACHINE COMPLETE!");
}

// ============================================================================
// GAME 58: STACK THE BOXES
// ============================================================================

void game_StackTheBoxes() {
    Serial.println("\n📦 GAME 58: STACK THE BOXES");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  Watch box swing on screen");
    Serial.println("  TAP BUTTON = Drop box to stack");
    Serial.println("  Perfect timing = higher score!");
    Serial.println("  [Stack 15 boxes to win]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(58, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(255, 165, 0);  // Orange
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;
    bool lastButtonState = false;

    while (millis() - gameStart < 180000) {  // 3 minute max
        webSocket.loop();

        readAccelerometer();
        float shakeIntensity = getShakeIntensity();
        bool shakeDetected = shakeIntensity > 15.0;
        bool buttonPressed = !digitalRead(BUTTON_PIN);

        // Detect button press (edge trigger)
        bool buttonHeld = buttonPressed && !lastButtonState;
        lastButtonState = buttonPressed;

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, 0, 0, shakeIntensity, shakeDetected, buttonHeld);
            lastSend = millis();
        }

        // Flash green on button press
        if (buttonPressed) {
            setAllLEDs(0, 255, 0);
        } else {
            setAllLEDs(255, 165, 0);
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🏗️  STACK THE BOXES COMPLETE!");
}

// ============================================================================
// GAME 59: DUCK HUNT
// ============================================================================

void game_DuckHunt() {
    Serial.println("\n🦆 GAME 59: DUCK HUNT");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  TILT = Aim crosshair");
    Serial.println("  SHAKE = SHOOT!");
    Serial.println("  Hit flying ducks for points");
    Serial.println("  Bonus ducks worth 2x!");
    Serial.println("  [5 rounds]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(59, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(139, 69, 19);  // Brown/wood color
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 180000) {  // 3 minute game (5 rounds)
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float tiltY = getTiltAngle_Y();
        float shakeIntensity = getShakeIntensity();
        bool shooting = shakeIntensity > 12;

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, tiltY, shakeIntensity, shooting, false);
            lastSend = millis();
        }

        // LED + sound feedback when shooting
        if (shooting) {
            setAllLEDs(255, 255, 0);  // Yellow flash
            tone(BUZZER_PIN, 800, 100);
            delay(100);
        } else {
            setAllLEDs(0, 255, 0);  // Green aiming reticle
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🎯 DUCK HUNT COMPLETE!");
}

// ============================================================================
// GAME 60: CORRELATION WORD GAME
// ============================================================================

void game_CorrelationWord() {
    Serial.println("\n📝 GAME 60: CORRELATION WORD GAME");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  Watch TV screen for words");
    Serial.println("  Stimulus word at top (e.g. VITAMIN)");
    Serial.println("  Press BUTTON when match scrolls by");
    Serial.println("  (e.g. B12, C, CALCIUM)");
    Serial.println("  Build combo for bonus points!");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(60, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(0, 191, 255);  // Sky blue
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 90000) {  // 90 second game
        webSocket.loop();

        bool buttonHeld = !digitalRead(BUTTON_PIN);

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, 0, 0, 0, false, buttonHeld);
            lastSend = millis();
        }

        // LED feedback
        if (buttonHeld) {
            setAllLEDs(255, 255, 0);  // Yellow when pressing
        } else {
            setAllLEDs(0, 191, 255);  // Blue otherwise
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🧠 CORRELATION WORD GAME COMPLETE!");
}

// ============================================================================
// GAME 61: GREYHOUND RACING
// ============================================================================

void game_GreyhoundRacing() {
    Serial.println("\n🐕 GAME 61: GREYHOUND RACING");
    Serial.println("═══════════════════════════════════");
    Serial.println("CONTROLS:");
    Serial.println("  PHASE 1 - BETTING:");
    Serial.println("    TILT LEFT/RIGHT = Select lane (1-6)");
    Serial.println("    BUTTON = Confirm bet");
    Serial.println("  PHASE 2 - RACING:");
    Serial.println("    SHAKE = Cheer your dog on!");
    Serial.println("  [5 races, multiply winnings!]");
    Serial.println("═══════════════════════════════════\n");

    if (!startTVGame(61, PUCK_ID, SERVER_URL)) return;

    setAllLEDs(0, 128, 0);  // Green (track color)
    delay(1000);

    unsigned long gameStart = millis();
    unsigned long lastSend = 0;

    while (millis() - gameStart < 300000) {  // 5 minute game (5 races)
        webSocket.loop();

        readAccelerometer();
        float tiltX = getTiltAngle_X();
        float shakeIntensity = getShakeIntensity();
        bool buttonHeld = !digitalRead(BUTTON_PIN);

        if (millis() - lastSend >= 33) {
            sendPuckInput(PUCK_ID, tiltX, 0, shakeIntensity, shakeIntensity > 12, buttonHeld);
            lastSend = millis();
        }

        // LED feedback
        if (buttonHeld) {
            setAllLEDs(255, 215, 0);  // Gold when betting
        } else if (shakeIntensity > 12) {
            setAllLEDs(255, 0, 0);  // Red when cheering
            tone(BUZZER_PIN, 1500, 100);
        } else {
            setAllLEDs(0, 255, 0);  // Green otherwise
        }

        delay(10);
    }

    endTVGame(PUCK_ID, SERVER_URL);
    Serial.println("\n🏁 GREYHOUND RACING COMPLETE!");
}

#endif // TV_GAMES_H
