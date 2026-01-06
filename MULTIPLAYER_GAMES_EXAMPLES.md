# Multiplayer Games Using ESP-NOW

## 🎮 5 New Games You Can Build This Weekend

With ESP-NOW, your pucks can talk to each other wirelessly (no WiFi router needed!). Here are complete game implementations you can use right now.

---

## Game 1: Puck Wars (Battle Royale)

**Concept**: Last puck standing wins
**Players**: 2-6
**Duration**: 2-5 minutes

### How It Works:

1. Each puck starts with 100 HP
2. Shake to attack nearest puck (20 damage)
3. Take damage → LEDs turn red, vibrate
4. At 0 HP → eliminated (LEDs off, game over)
5. Winner gets victory animation

### Code Implementation:

```cpp
// Game state
int myHealth = 100;
bool isAlive = true;
uint8_t targetPuckId = 0;

void game_PuckWars() {
    Serial.println("🎮 PUCK WARS - Battle Royale!");

    // Reset state
    myHealth = 100;
    isAlive = true;

    // Start countdown
    countdownSequence(3);

    // Game loop
    while (isAlive) {
        readAccelerometer();
        readTouchPads();

        // Show health on LEDs
        showHealthBar(myHealth);

        // Attack on shake
        if (detectShake()) {
            // Find nearest puck
            targetPuckId = findNearestPuck();

            if (targetPuckId > 0) {
                attackPuck(targetPuckId, 20);  // 20 damage

                // Attack feedback
                setAllLEDs(255, 0, 0);  // Flash red
                tone(BUZZER_PIN, 800, 100);
                delay(100);
                setAllLEDs(0, 0, 0);

                Serial.printf("⚔️  Attacked Puck %d!\n", targetPuckId);
            }
        }

        // Handle incoming attacks (from esp_now_multiplayer.h callback)
        if (incomingDamage > 0) {
            myHealth -= incomingDamage;

            // Damage feedback
            vibrate(200);
            flashRed(3);
            tone(BUZZER_PIN, 400, 300);

            Serial.printf("💥 Hit! Health: %d\n", myHealth);

            incomingDamage = 0;  // Reset
        }

        // Check if eliminated
        if (myHealth <= 0) {
            isAlive = false;
            eliminated();
        }

        // Touch to select different target
        if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
            targetPuckId = (targetPuckId % 6) + 1;  // Cycle targets
            if (targetPuckId == PUCK_ID) targetPuckId++;  // Skip self
            Serial.printf("🎯 Target: Puck %d\n", targetPuckId);
        }

        delay(50);
    }

    // Game over - check if winner
    delay(2000);
    if (checkIfWinner()) {
        victoryAnimation();
    }
}

void showHealthBar(int health) {
    int ledsOn = map(health, 0, 100, 0, NUM_LEDS);

    for (int i = 0; i < NUM_LEDS; i++) {
        if (i < ledsOn) {
            // Healthy = green, low health = red
            if (health > 60) {
                leds[i] = CRGB(0, 255, 0);  // Green
            } else if (health > 30) {
                leds[i] = CRGB(255, 255, 0);  // Yellow
            } else {
                leds[i] = CRGB(255, 0, 0);  // Red
            }
        } else {
            leds[i] = CRGB(0, 0, 0);  // Off
        }
    }
    FastLED.show();
}

void eliminated() {
    Serial.println("☠️  ELIMINATED!");

    // Death animation
    for (int i = 0; i < 3; i++) {
        setAllLEDs(255, 0, 0);
        tone(BUZZER_PIN, 200, 200);
        delay(200);
        setAllLEDs(0, 0, 0);
        delay(200);
    }

    // Broadcast elimination
    broadcast(MSG_ELIMINATED);
}

bool checkIfWinner() {
    // Request status from all pucks
    broadcast(MSG_STATUS_REQUEST);
    delay(1000);  // Wait for responses

    // If we're alive and others aren't, we won!
    return (isAlive && otherPucksEliminated());
}
```

### Strategy Tips:

- **Defensive**: Stay far from others, wait for them to fight
- **Aggressive**: Attack immediately, eliminate weak players first
- **Team up**: Coordinate with another puck to take down strongest player

---

## Game 2: Hot Potato Relay

**Concept**: Pass the "potato" before it explodes
**Players**: 3-6
**Duration**: 1-3 minutes

### How It Works:

1. One random puck gets the "hot potato" (red pulsing LEDs)
2. Timer counts down (15 seconds)
3. Shake to pass potato to nearest puck
4. When timer hits 0 → explosion (eliminated)
5. Continue until one puck remains

### Code Implementation:

```cpp
bool hasHotPotato = false;
unsigned long potatoStartTime = 0;
int potatoTimer = 15000;  // 15 seconds

void game_HotPotatoRelay() {
    Serial.println("🥔 HOT POTATO RELAY!");

    // Random puck starts with potato
    delay(random(0, 3000));  // Randomize
    if (PUCK_ID == 1) {  // First puck starts
        hasHotPotato = true;
        potatoStartTime = millis();
        broadcast(MSG_HOT_POTATO_START);
    }

    countdownSequence(3);

    // Game loop
    while (true) {
        if (hasHotPotato) {
            // Calculate time remaining
            unsigned long elapsed = millis() - potatoStartTime;
            int timeLeft = (potatoTimer - elapsed) / 1000;

            // Show timer on LEDs
            showTimer(timeLeft);

            // Beep faster as time runs out
            if (timeLeft < 5) {
                tone(BUZZER_PIN, 1000, 50);
                delay(200);
            } else if (timeLeft < 10) {
                tone(BUZZER_PIN, 800, 50);
                delay(500);
            }

            Serial.printf("🔥 HOT POTATO! %d seconds left!\n", timeLeft);

            // Check for explosion
            if (elapsed >= potatoTimer) {
                explode();
                break;
            }

            // Pass on shake
            if (detectShake()) {
                passPotato();
            }
        } else {
            // Waiting to receive potato
            idleAnimation();
        }

        delay(50);
    }
}

void passPotato() {
    uint8_t targetPuck = findNearestPuck();

    if (targetPuck > 0) {
        // Send potato
        sendMessage(targetPuck, MSG_HOT_POTATO, potatoTimer);

        hasHotPotato = false;

        // Feedback
        setAllLEDs(0, 255, 0);  // Green = safe!
        tone(BUZZER_PIN, 1000, 100);
        delay(200);

        Serial.printf("✅ Passed potato to Puck %d\n", targetPuck);
    }
}

void explode() {
    Serial.println("💥 BOOM! You exploded!");

    // Explosion animation
    for (int i = 0; i < 5; i++) {
        setAllLEDs(255, 100, 0);  // Orange
        vibrate(100);
        tone(BUZZER_PIN, 200, 100);
        delay(100);
        setAllLEDs(255, 0, 0);  // Red
        delay(100);
    }

    setAllLEDs(0, 0, 0);

    // Broadcast elimination
    broadcast(MSG_ELIMINATED);
}

void showTimer(int seconds) {
    int ledsOn = map(seconds, 0, 15, 0, NUM_LEDS);

    for (int i = 0; i < NUM_LEDS; i++) {
        if (i < ledsOn) {
            leds[i] = CHSV((seconds * 10), 255, 255);  // Color changes with time
        } else {
            leds[i] = CRGB(0, 0, 0);
        }
    }
    FastLED.show();
}

// Callback when receiving hot potato (in esp_now_multiplayer.h)
void onReceiveHotPotato(int timeRemaining) {
    hasHotPotato = true;
    potatoStartTime = millis();
    potatoTimer = timeRemaining;

    // Panic animation
    flashRed(3);
    tone(BUZZER_PIN, 1500, 300);

    Serial.println("🔥 OH NO! You have the hot potato!");
}
```

---

## Game 3: Sync Shake Challenge

**Concept**: All pucks must shake in sync
**Players**: 2-6
**Duration**: 30 seconds - 2 minutes

### How It Works:

1. Leader puck announces "Shake NOW!"
2. All players shake within 1-second window
3. If all shake together → +10 points, next round
4. If anyone misses → -5 points, try again
5. First to 50 points wins

### Code Implementation:

```cpp
bool isLeader = false;
int syncScore = 0;
bool shookInWindow = false;

void game_SyncShakeChallenge() {
    Serial.println("📳 SYNC SHAKE CHALLENGE!");

    // Lowest ID becomes leader
    isLeader = (PUCK_ID == 1);

    if (isLeader) {
        Serial.println("👑 You are the LEADER!");
    }

    countdownSequence(3);

    // Game loop
    while (syncScore < 50) {
        if (isLeader) {
            // Leader announces shake command
            delay(random(2000, 5000));  // Random interval

            Serial.println("📢 SHAKE NOW!");
            broadcast(MSG_SYNC_COMMAND);

            // Visual cue
            for (int i = 0; i < 3; i++) {
                setAllLEDs(255, 255, 0);
                tone(BUZZER_PIN, 1000, 100);
                delay(100);
                setAllLEDs(0, 0, 0);
                delay(100);
            }

            // Wait for shake window
            shookInWindow = false;
            unsigned long windowStart = millis();

            while (millis() - windowStart < 1000) {  // 1 second window
                if (detectShake()) {
                    shookInWindow = true;
                    break;
                }
                delay(10);
            }

            // Broadcast result
            if (shookInWindow) {
                sendMessage(0xFF, MSG_SYNC_SUCCESS, 1);
            } else {
                sendMessage(0xFF, MSG_SYNC_FAIL, 0);
            }

            delay(1000);

        } else {
            // Wait for command from leader
            if (syncCommandReceived) {
                Serial.println("⏰ SHAKE NOW!");

                // Visual cue
                flashGreen(2);
                tone(BUZZER_PIN, 1500, 200);

                // Detect shake in window
                shookInWindow = false;
                unsigned long windowStart = millis();

                while (millis() - windowStart < 1000) {
                    if (detectShake()) {
                        shookInWindow = true;
                        Serial.println("✅ Shook in time!");
                        break;
                    }
                    delay(10);
                }

                if (!shookInWindow) {
                    Serial.println("❌ Too slow!");
                }

                syncCommandReceived = false;
            }
        }

        // Update score based on sync results
        if (syncSuccess) {
            syncScore += 10;
            Serial.printf("✅ SYNC SUCCESS! Score: %d\n", syncScore);
            victoryBeep();
            syncSuccess = false;
        }

        if (syncFail) {
            syncScore -= 5;
            if (syncScore < 0) syncScore = 0;
            Serial.printf("❌ SYNC FAIL! Score: %d\n", syncScore);
            failBeep();
            syncFail = false;
        }

        // Show score
        showScore(syncScore);

        delay(100);
    }

    // Winner!
    Serial.println("🏆 YOU WIN!");
    victoryAnimation();
}
```

---

## Game 4: Team Boss Battle

**Concept**: All pucks cooperate to defeat a giant boss
**Players**: 3-6
**Duration**: 3-5 minutes

### How It Works:

1. Boss has 500 HP (virtual, tracked by server)
2. Players shake to attack (deals 10-30 damage)
3. Boss counterattacks random puck every 5 seconds
4. Team must heal each other (touch to heal)
5. Win if boss reaches 0 HP
6. Lose if all players eliminated

### Code Implementation:

```cpp
int bossHealth = 500;
int myHealth = 100;
unsigned long lastBossAttack = 0;

void game_BossBattle() {
    Serial.println("🐉 TEAM BOSS BATTLE!");
    Serial.println("Work together to defeat the boss!");

    myHealth = 100;

    if (PUCK_ID == 1) {  // Leader tracks boss health
        bossHealth = 500;
    }

    countdownSequence(3);

    // Game loop
    while (bossHealth > 0 && myHealth > 0) {
        readAccelerometer();
        readTouchPads();

        // Show player health
        showHealthBar(myHealth);

        // Attack boss on shake
        if (detectShake()) {
            int damage = random(10, 31);  // 10-30 damage

            // Broadcast attack
            sendMessage(1, MSG_BOSS_ATTACK, damage);  // Send to leader

            // Attack animation
            setAllLEDs(255, 0, 0);
            tone(BUZZER_PIN, 800, 200);
            delay(200);
            setAllLEDs(0, 0, 0);

            Serial.printf("⚔️  Dealt %d damage to boss!\n", damage);
        }

        // Heal teammate on touch
        if (gestureDetected(GESTURE_TAP)) {
            uint8_t teammate = findNearestPuck();

            if (teammate > 0) {
                sendMessage(teammate, MSG_HEAL, 20);  // Heal 20 HP

                setAllLEDs(0, 255, 0);
                tone(BUZZER_PIN, 1000, 200);
                delay(200);
                setAllLEDs(0, 0, 0);

                Serial.printf("💚 Healed Puck %d!\n", teammate);
            }
        }

        // Boss attacks (leader decides target)
        if (PUCK_ID == 1 && millis() - lastBossAttack > 5000) {
            uint8_t targetPuck = random(1, 7);  // Random player
            sendMessage(targetPuck, MSG_BOSS_COUNTERATTACK, 30);

            Serial.printf("🐉 Boss attacked Puck %d!\n", targetPuck);
            lastBossAttack = millis();
        }

        // Handle incoming damage
        if (incomingBossDamage > 0) {
            myHealth -= incomingBossDamage;

            // Damage feedback
            flashRed(3);
            vibrate(300);
            tone(BUZZER_PIN, 300, 400);

            Serial.printf("💥 Boss hit you! Health: %d\n", myHealth);

            incomingBossDamage = 0;
        }

        // Handle incoming heal
        if (incomingHeal > 0) {
            myHealth += incomingHeal;
            if (myHealth > 100) myHealth = 100;

            // Heal feedback
            flashGreen(2);
            tone(BUZZER_PIN, 1200, 200);

            Serial.printf("💚 Healed! Health: %d\n", myHealth);

            incomingHeal = 0;
        }

        // Leader updates boss health
        if (PUCK_ID == 1 && incomingBossAttack > 0) {
            bossHealth -= incomingBossAttack;

            // Broadcast boss health to all
            sendMessage(0xFF, MSG_BOSS_HEALTH, bossHealth);

            Serial.printf("🐉 Boss health: %d\n", bossHealth);

            incomingBossAttack = 0;
        }

        delay(50);
    }

    // Check result
    if (bossHealth <= 0) {
        Serial.println("🏆 BOSS DEFEATED!");
        teamVictory();
    } else {
        Serial.println("☠️  DEFEATED BY BOSS!");
        defeatAnimation();
    }
}

void teamVictory() {
    // Synchronized victory celebration
    for (int i = 0; i < 5; i++) {
        rainbowCycle(10);
    }

    tone(BUZZER_PIN, 523, 200);
    delay(200);
    tone(BUZZER_PIN, 659, 200);
    delay(200);
    tone(BUZZER_PIN, 784, 400);
    delay(400);
}
```

---

## Game 5: King of the Hill

**Concept**: Hold the "crown" longest to win
**Players**: 3-6
**Duration**: 2 minutes

### How It Works:

1. One puck has the "crown" (gold pulsing LEDs)
2. Others attack to steal crown
3. Crown holder gets +1 point per second
4. First to 60 points wins (or highest after 2 min)

### Code Implementation:

```cpp
bool hasCrown = false;
int hillScore = 0;
unsigned long crownTime = 0;

void game_KingOfTheHill() {
    Serial.println("👑 KING OF THE HILL!");

    // Random puck starts with crown
    if (PUCK_ID == random(1, 7)) {
        hasCrown = true;
        crownTime = millis();
        broadcast(MSG_CROWN_TAKEN);
    }

    countdownSequence(3);

    unsigned long gameStart = millis();

    // 2-minute game
    while (millis() - gameStart < 120000 && hillScore < 60) {
        if (hasCrown) {
            // Show crown
            showCrown();

            // Gain points
            if (millis() - crownTime > 1000) {
                hillScore++;
                crownTime = millis();
                Serial.printf("👑 Score: %d\n", hillScore);
            }

            // Check for attacks
            if (incomingAttack > 0) {
                // Crown stolen!
                hasCrown = false;

                flashRed(3);
                tone(BUZZER_PIN, 400, 400);

                Serial.println("☠️  Crown stolen!");

                incomingAttack = 0;
            }

        } else {
            // Try to steal crown
            idleAnimation();

            if (detectShake()) {
                // Attack random puck
                uint8_t target = findCrownHolder();

                if (target > 0) {
                    attackPuck(target, 1);  // Steal attempt

                    Serial.printf("⚔️  Attacking Puck %d for crown!\n", target);
                }
            }
        }

        delay(50);
    }

    // Game over
    broadcast(MSG_FINAL_SCORE, hillScore);
    delay(2000);

    if (checkHighestScore()) {
        Serial.println("🏆 YOU ARE KING!");
        victoryAnimation();
    }
}

void showCrown() {
    // Gold pulsing effect
    static uint8_t brightness = 0;
    static int8_t direction = 5;

    brightness += direction;
    if (brightness >= 255 || brightness <= 50) {
        direction = -direction;
    }

    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CRGB(brightness, brightness / 2, 0);  // Gold
    }
    FastLED.show();
}
```

---

## 🔧 ESP-NOW Setup Required

All games require ESP-NOW initialized:

```cpp
void setup() {
    // ... other init code ...

    // Initialize ESP-NOW
    initESPNow();
    addBroadcastPeer();
    discoverPucks();

    // Register callbacks
    esp_now_register_recv_cb(onDataReceive);
}
```

---

## 📡 Message Protocol

See `esp_now_multiplayer.h` for full protocol. Key messages:

```cpp
#define MSG_PING              1   // Discover pucks
#define MSG_ATTACK            2   // Attack another puck
#define MSG_HEAL              3   // Heal another puck
#define MSG_STATUS_REQUEST    4   // Request status
#define MSG_HOT_POTATO        5   // Pass hot potato
#define MSG_SYNC_COMMAND      6   // Leader sync command
#define MSG_BOSS_ATTACK       7   // Attack boss
#define MSG_CROWN_TAKEN       8   // Crown holder changed
```

---

## 🎮 Testing Games

### Single Puck Test:

Upload `TEST_ALL_FEATURES.ino` and type:
```
espnow    # Test ESP-NOW
```

### Multi-Puck Test:

1. Upload code to all pucks
2. Power on all pucks
3. Type game number in serial monitor:
   - `52` = Puck Wars
   - `53` = Hot Potato
   - `54` = Sync Shake
   - `55` = Boss Battle
   - `56` = King of the Hill

---

## 🏆 Scoreboard Integration

All games automatically report scores to server:

```cpp
// At end of each game
sendScoreToServer(gameId, score, gameTime);
```

Server displays on web dashboard at `http://localhost:5001/leaderboard`

---

**Ready to play? Upload `main_tablewars_v2_UPGRADED.h` and type a game number!** 🎮
