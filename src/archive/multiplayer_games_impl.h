/*
 * TABLE WARS - Multiplayer Games Implementation
 *
 * NOTE: This file should be included from multiplayer_games.h
 * It assumes hardware objects (strip, mpu) and helper functions are available
 */

// ============================================================================
// GAME 1: PASS THE BOMB (MULTIPLAYER)
// ============================================================================

PassTheBombGame::PassTheBombGame(WiFiSync* wifiSync, uint8_t puckID) {
    wifi = wifiSync;
    myPuckID = puckID;
    hasBomb = false;
    bombStartTime = 0;
    bombDuration = 20000; // 20 seconds total
    passCount = 0;
    gameOver = false;
}

uint32_t PassTheBombGame::play() {
    Serial.println("\n🎮 MULTIPLAYER GAME: PASS THE BOMB");
    Serial.println("Pass the bomb before it explodes!");
    Serial.println("Button = Pass to next puck");

    fillLEDs(COLOR_ORANGE);
    beep(200);
    delay(2000);

    // Puck 1 starts with the bomb
    if (myPuckID == 1) {
        hasBomb = true;
        bombStartTime = millis();
        bombDuration = 20000;
        Serial.println("💣 YOU START WITH THE BOMB!");
    } else {
        Serial.println("⏳ Waiting for bomb...");
    }

    delay(2000);

    // Game loop
    while (!gameOver) {
        if (hasBomb) {
            showBombCountdown();

            // Check for pass
            if (readButton()) {
                // Find next online puck
                uint8_t nextPuck = (myPuckID % MAX_PUCKS) + 1;
                int attempts = 0;

                while (!wifi->isPuckOnline(nextPuck) && attempts < MAX_PUCKS) {
                    nextPuck = (nextPuck % MAX_PUCKS) + 1;
                    attempts++;
                }

                if (wifi->isPuckOnline(nextPuck)) {
                    unsigned long remaining = bombDuration - (millis() - bombReceivedTime);

                    if (wifi->sendBombPass(nextPuck, remaining)) {
                        Serial.printf("💣 Passed bomb to Puck %d!\n", nextPuck);
                        fillLEDs(COLOR_GREEN);
                        beep(100);
                        vibrate(100);
                        hasBomb = false;
                        passCount++;
                        delay(1000);
                        fillLEDs(COLOR_CYAN);
                    }
                } else {
                    Serial.println("⚠️  No other pucks online!");
                    beep(300);
                }

                delay(500); // Debounce
            }

            // Check for explosion
            if (millis() - bombReceivedTime > bombDuration) {
                explodeBomb();
                gameOver = true;
            }
        } else {
            // Waiting for bomb - show idle animation
            float brightness = (sin(millis() / 500.0) + 1.0) / 2.0;
            uint8_t b = 100 * brightness;
            for (int i = 0; i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(0, b, b));
            }
            strip.show();
        }

        delay(50);
    }

    uint32_t score = passCount * 200; // 200 points per pass
    Serial.printf("💯 FINAL SCORE: %lu (Passes: %d)\n", score, passCount);

    return score;
}

void PassTheBombGame::explodeBomb() {
    Serial.println("💥💥💥 BOOM! YOU LOSE! 💥💥💥");

    for (int i = 0; i < 10; i++) {
        fillLEDs(COLOR_RED);
        beep(100);
        vibrate(100);
        delay(100);
        clearLEDs();
        delay(100);
    }
}

void PassTheBombGame::showBombCountdown() {
    unsigned long elapsed = millis() - bombReceivedTime;
    unsigned long remaining = bombDuration - elapsed;

    if (remaining > bombDuration) remaining = 0; // Handle overflow

    uint8_t ledsLit = (remaining * NUM_LEDS) / bombDuration;

    clearLEDs();
    for (int i = 0; i < ledsLit && i < NUM_LEDS; i++) {
        strip.setPixelColor(i, COLOR_RED);
    }
    strip.show();

    // Faster beeping as time runs out
    if (remaining < 5000 && remaining % 500 < 100) {
        beep(50);
    }
}

// ============================================================================
// GAME 2: TEAM BATTLE (MULTIPLAYER) - SIMPLIFIED
// ============================================================================

TeamBattleGame::TeamBattleGame(WiFiSync* wifiSync, uint8_t puckID) {
    wifi = wifiSync;
    myPuckID = puckID;
    myTeam = 0;
    roundsPlayed = 0;
    teamScores[0] = 0;
    teamScores[1] = 0;
}

uint32_t TeamBattleGame::play() {
    Serial.println("\n🎮 MULTIPLAYER GAME: TEAM BATTLE");
    Serial.println("Red Team vs Blue Team!");

    assignTeams();
    delay(2000);

    for (int round = 0; round < 3; round++) {
        roundsPlayed++;
        Serial.printf("\n🔥 ROUND %d/3\n", round + 1);
        playRound();
        delay(2000);
    }

    showTeamScores();

    return teamScores[myTeam];
}

void TeamBattleGame::assignTeams() {
    // Odd IDs = Red team, Even IDs = Blue team
    myTeam = (myPuckID % 2);
    myTeamColor = (myTeam == 0) ? COLOR_RED : COLOR_BLUE;

    fillLEDs(myTeamColor);
    beep(200);

    Serial.printf("⚔️  You are on the %s TEAM!\n",
                 (myTeam == 0) ? "RED" : "BLUE");

    delay(2000);
}

void TeamBattleGame::syncTeamColors() {
    // Simplified - just broadcast our team info
    wifi->sendTeamColor(0, myTeamColor, myTeam);
}

void TeamBattleGame::playRound() {
    Serial.println("TAP TO SCORE FOR YOUR TEAM!");

    fillLEDs(myTeamColor);

    unsigned long startTime = millis();
    uint32_t taps = 0;

    while (millis() - startTime < 8000) {
        if (readButton()) {
            taps++;
            strip.setPixelColor(taps % NUM_LEDS, COLOR_WHITE);
            strip.show();
            beep(30);
        }
    }

    uint32_t roundScore = taps * 10;
    teamScores[myTeam] += roundScore;

    Serial.printf("✅ Round score: %lu (Team total: %lu)\n",
                 roundScore, teamScores[myTeam]);

    // Broadcast score
    wifi->sendScore(teamScores[myTeam], 2);

    fillLEDs(myTeamColor);
    beep(300);
    vibrate(200);
}

void TeamBattleGame::showTeamScores() {
    Serial.println("\n═══════════════════════════════");
    Serial.println("       TEAM BATTLE RESULTS      ");
    Serial.println("═══════════════════════════════");
    Serial.printf("YOUR TEAM: %lu points\n", teamScores[myTeam]);
    Serial.println("═══════════════════════════════\n");

    fillLEDs(COLOR_YELLOW);
    beep(500);
    vibrate(300);
    delay(3000);
}

// ============================================================================
// REMAINING GAMES - SIMPLIFIED STUBS
// ============================================================================

// NOTE: These are simplified versions. Full implementations would include
// proper WiFi sync and game state management.

KingOfTheHillGame::KingOfTheHillGame(WiFiSync* wifiSync, uint8_t puckID) {
    wifi = wifiSync;
    myPuckID = puckID;
    currentKing = 1;
    myScore = 0;
    kingStartTime = millis();
    kingColor = COLOR_YELLOW;
}

uint32_t KingOfTheHillGame::play() {
    Serial.println("\n🎮 MULTIPLAYER GAME: KING OF THE HILL");
    Serial.println("(Simplified version - full sync coming soon)");

    // Simple placeholder game logic
    for (int i = 0; i < 10; i++) {
        fillLEDs(COLOR_YELLOW);
        delay(1000);
        myScore += 10;
    }

    Serial.printf("💯 SCORE: %lu\n", myScore);
    return myScore;
}

void KingOfTheHillGame::challengeForKing() {}
void KingOfTheHillGame::showKingStatus() {}
void KingOfTheHillGame::syncScores() {}

RelayRaceGame::RelayRaceGame(WiFiSync* wifiSync, uint8_t puckID) {
    wifi = wifiSync;
    myPuckID = puckID;
    currentTurn = 1;
    myTurnActive = false;
    totalScore = 0;
}

uint32_t RelayRaceGame::play() {
    Serial.println("\n🎮 MULTIPLAYER GAME: RELAY RACE");
    Serial.println("(Simplified version - full sync coming soon)");

    // Simple placeholder
    playMyTurn();
    return totalScore;
}

void RelayRaceGame::waitForTurn() {}
void RelayRaceGame::playMyTurn() {
    fillLEDs(COLOR_GREEN);
    beep(200);
    totalScore = 500;
}
void RelayRaceGame::passTurn() {}

SyncShakeGame::SyncShakeGame(WiFiSync* wifiSync, uint8_t puckID) {
    wifi = wifiSync;
    myPuckID = puckID;
    targetIntensity = 20.0;
    myIntensity = 0;
    syncAchieved = false;
}

uint32_t SyncShakeGame::play() {
    Serial.println("\n🎮 MULTIPLAYER GAME: SYNCHRONIZED SHAKE");
    Serial.println("(Simplified version - full sync coming soon)");

    // Simple placeholder
    for (int i = 0; i < 10; i++) {
        fillLEDs(COLOR_GREEN);
        delay(1000);
    }

    return 1000;
}

void SyncShakeGame::showSyncProgress() {}
