// ============================================================================
// GAME 40: JUDAS MODE (Betrayal Game)
// ============================================================================

uint32_t game_JudasMode() {
    Serial.println("\n🎮 GAME: JUDAS MODE");
    Serial.println("Everyone shakes to contribute. One player is JUDAS...");
    Serial.println("Judas can STEAL by holding button for 3 seconds");
    Serial.println("Others can ACCUSE by tapping during countdown");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint32_t pot = 0;

    // Randomly become Judas (20% chance)
    bool isJudas = (random(100) < 20);

    if (isJudas) {
        Serial.println("🗡️ YOU ARE JUDAS! 🗡️");
        fillLEDs(COLOR_RED);
        vibrate(500);
        delay(2000);
    } else {
        Serial.println("👼 You are INNOCENT");
        fillLEDs(COLOR_GREEN);
        delay(2000);
    }

    // Everyone "contributes" by shaking
    Serial.println("\nShake to contribute to the pot!");
    fillLEDs(COLOR_CYAN);

    unsigned long phaseStart = millis();
    while (millis() - phaseStart < 5000) {
        float shake = getShakeIntensity();
        if (shake > 5.0) {
            pot += 10;
            beep(30);
            // Show pot filling
            int litLEDs = min((int)NUM_LEDS, (int)(pot / 50));
            clearLEDs();
            for (int i = 0; i < litLEDs; i++) {
                strip.setPixelColor(i, COLOR_YELLOW);
            }
            strip.show();
            delay(50);
        }
    }

    Serial.printf("💰 Total pot: %lu points\n", pot);
    delay(1000);

    // Judas decision phase
    if (isJudas) {
        Serial.println("\n🗡️ HOLD button for 3s to STEAL THE POT!");
        fillLEDs(COLOR_RED);

        unsigned long stealWindow = millis();
        bool stole = false;
        unsigned long holdStart = 0;
        bool holding = false;

        while (millis() - stealWindow < 8000 && !stole) {
            if (!digitalRead(PIN_BUTTON) && !holding) {
                holdStart = millis();
                holding = true;
                Serial.println("⏱️ Stealing...");
            }

            if (holding && digitalRead(PIN_BUTTON)) {
                holding = false;
                Serial.println("❌ Released too early!");
            }

            if (holding && (millis() - holdStart > 3000)) {
                stole = true;
                Serial.println("💰 YOU STOLE THE POT!");
                score = pot * 2; // Double points for successful betrayal
                fillLEDs(COLOR_MAGENTA);
                for (int i = 0; i < 5; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
            }

            delay(10);
        }

        if (!stole) {
            Serial.println("😇 You remained innocent...");
            score = pot / 2; // Half pot for not betraying
            fillLEDs(COLOR_GREEN);
            beep(200);
        }
    } else {
        // Innocent players wait
        Serial.println("\n⏱️ Waiting for betrayal...");
        fillLEDs(COLOR_BLUE);

        // Simulate suspense
        for (int i = 0; i < 8; i++) {
            beep(100);
            delay(1000);
        }

        // Random outcome for solo mode
        if (random(100) < 30) {
            Serial.println("😱 Someone STOLE the pot!");
            fillLEDs(COLOR_RED);
            beep(500);
            score = 0; // Lost the pot
        } else {
            Serial.println("😌 No betrayal! You get your share!");
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 3; i++) {
                beep(100);
                delay(150);
            }
            score = pot / 2;
        }
    }

    delay(2000);
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 41: DRUNK DUCK HUNT
// ============================================================================

uint32_t game_DrunkDuckHunt() {
    Serial.println("\n🎮 GAME: DRUNK DUCK HUNT");
    Serial.println("SLAP when you hear QUACK!");
    Serial.println("But DON'T hit the GOOSE!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 12;
    uint8_t hits = 0;
    uint8_t misses = 0;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/12\n", round + 1);

        fillLEDs(COLOR_CYAN);
        delay(random(1000, 3000)); // Random wait

        // 80% duck, 20% goose
        bool isDuck = (random(100) < 80);

        if (isDuck) {
            Serial.println("🦆 QUACK!");
            fillLEDs(COLOR_GREEN);
        } else {
            Serial.println("🦢 HONK! (GOOSE)");
            fillLEDs(COLOR_RED);
        }

        // Play sound
        for (int i = 0; i < 3; i++) {
            beep(isDuck ? 150 : 300);
            delay(isDuck ? 100 : 200);
        }

        // Wait for slap (300ms window)
        unsigned long windowStart = millis();
        bool slapped = false;

        while (millis() - windowStart < 300) {
            if (getShakeIntensity() > 15.0) {
                slapped = true;
                break;
            }
            delay(10);
        }

        if (slapped && isDuck) {
            Serial.println("✅ HIT!");
            fillLEDs(COLOR_YELLOW);
            vibrate(100);
            beep(200);
            score += 100;
            hits++;
        } else if (slapped && !isDuck) {
            Serial.println("❌ YOU HIT THE GOOSE! -200");
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
            score = (score >= 200) ? score - 200 : 0;
            misses++;
        } else if (!slapped && isDuck) {
            Serial.println("💔 MISSED!");
            fillLEDs(COLOR_ORANGE);
            beep(300);
            misses++;
        } else {
            Serial.println("😌 Good restraint!");
            fillLEDs(COLOR_BLUE);
            beep(100);
            score += 50;
        }

        delay(1500);
        clearLEDs();
        delay(500);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎯 Hits: %d\n", hits);
    Serial.printf("💔 Misses: %d\n", misses);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 42: SUCKER PUNCH (Reaction Duel)
// ============================================================================

uint32_t game_SuckerPunch() {
    Serial.println("\n🎮 GAME: SUCKER PUNCH");
    Serial.println("Hands ready... GRAB the puck when it flashes GREEN!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/5\n", round + 1);
        Serial.println("Get ready...");

        // Suspense phase
        fillLEDs(COLOR_YELLOW);
        delay(2000);

        Serial.println("Steady...");
        fillLEDs(COLOR_ORANGE);
        delay(random(1000, 4000)); // Random delay = unpredictable

        // GO!
        Serial.println("GRAB NOW!");
        fillLEDs(COLOR_GREEN);
        beep(300);

        unsigned long flashTime = millis();
        bool grabbed = false;
        unsigned long reactionTime = 0;

        // Wait for grab (shake + button)
        while (millis() - flashTime < 2000 && !grabbed) {
            if (getShakeIntensity() > 10.0 || !digitalRead(PIN_BUTTON)) {
                reactionTime = millis() - flashTime;
                grabbed = true;
            }
            delay(5);
        }

        if (grabbed) {
            Serial.printf("⚡ Reaction: %lu ms\n", reactionTime);

            uint32_t roundScore = 0;

            if (reactionTime < 100) {
                Serial.println("🏆 LIGHTNING FAST!");
                fillLEDs(COLOR_MAGENTA);
                for (int i = 0; i < 5; i++) {
                    beep(80);
                    vibrate(80);
                    delay(80);
                }
                roundScore = 500;
            } else if (reactionTime < 200) {
                Serial.println("🎯 EXCELLENT!");
                fillLEDs(COLOR_YELLOW);
                beep(200);
                vibrate(200);
                roundScore = 300;
            } else if (reactionTime < 400) {
                Serial.println("✅ GOOD!");
                fillLEDs(COLOR_GREEN);
                beep(150);
                vibrate(150);
                roundScore = 150;
            } else {
                Serial.println("😐 SLOW...");
                fillLEDs(COLOR_BLUE);
                beep(100);
                roundScore = 50;
            }

            score += roundScore;
            Serial.printf("+%lu points\n", roundScore);
        } else {
            Serial.println("❌ TOO SLOW!");
            fillLEDs(COLOR_RED);
            beep(500);
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 43: DEATH ROLL (Gambling Game)
// ============================================================================

uint32_t game_DeathRoll() {
    Serial.println("\n🎮 GAME: DEATH ROLL");
    Serial.println("Roll random numbers down to 1 = YOU LOSE!");

    beep(200);
    delay(1000);

    uint32_t currentMax = 100;
    uint32_t rollNumber = 1;

    Serial.println("Starting at 100...");
    fillLEDs(COLOR_GREEN);
    delay(2000);

    while (currentMax > 1) {
        Serial.printf("\n🎲 Roll #%lu (1-%lu)\n", rollNumber, currentMax);
        Serial.println("SHAKE to roll!");

        fillLEDs(COLOR_YELLOW);

        // Wait for shake
        while (getShakeIntensity() < 8.0) {
            delay(50);
        }

        // Rolling animation
        for (int i = 0; i < 20; i++) {
            clearLEDs();
            strip.setPixelColor(random(NUM_LEDS), COLOR_CYAN);
            strip.show();
            beep(50);
            delay(50);
        }

        // Roll result
        uint32_t roll = random(1, currentMax + 1);
        currentMax = roll;

        Serial.printf("📊 Rolled: %lu\n", roll);

        if (roll == 1) {
            // DEATH!
            Serial.println("\n💀 YOU ROLLED 1! DEATH! 💀");
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 10; i++) {
                beep(100);
                vibrate(100);
                delay(100);
                clearLEDs();
                delay(100);
                fillLEDs(COLOR_RED);
            }
            break;
        } else {
            // Show progress (closer to death = more red)
            float progress = 1.0 - (roll / 100.0);
            uint8_t red = progress * 255;
            uint8_t green = (1.0 - progress) * 255;

            int litLEDs = map(roll, 1, 100, 1, NUM_LEDS);
            clearLEDs();
            for (int i = 0; i < litLEDs; i++) {
                strip.setPixelColor(i, strip.Color(red, green, 0));
            }
            strip.show();

            beep(200);
            vibrate(100);
            delay(2000);
        }

        rollNumber++;
    }

    // Score = how many rolls survived
    uint32_t score = (rollNumber - 1) * 100;

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎲 Survived %lu rolls\n", rollNumber - 1);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);

    delay(2000);
    return score;
}

// ============================================================================
// GAME 44: SHAME WHEEL (Humiliation Roulette)
// ============================================================================

uint32_t game_ShameWheel() {
    Serial.println("\n🎮 GAME: SHAME WHEEL");
    Serial.println("Spin for your punishment level!");

    beep(200);
    delay(1000);

    uint32_t score = 1000; // Start with points, lose them via shame
    uint8_t rounds = 3;

    const char* shameLevel1[] = {"Tell a dad joke", "Dance for 5 seconds", "Compliment someone"};
    const char* shameLevel2[] = {"Truth question", "Funny voice for 30s", "Do 10 pushups"};
    const char* shameLevel3[] = {"Embarrassing story", "Sing out loud", "Take a shot"};
    const char* shameLevel4[] = {"Group chooses dare", "Social media post", "Ultimate embarrassment"};

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/3\n", round + 1);
        Serial.println("SHAKE to spin the wheel!");

        fillLEDs(COLOR_CYAN);

        // Wait for big shake
        while (getShakeIntensity() < 10.0) {
            delay(50);
        }

        // Spinning animation
        Serial.println("🎡 Spinning...");
        for (int i = 0; i < 40; i++) {
            clearLEDs();
            strip.setPixelColor(i % NUM_LEDS, COLOR_MAGENTA);
            strip.show();
            beep(50);
            delay(50 + (i * 3)); // Slow down
        }

        // Determine shame level (1-4)
        uint8_t level = random(1, 17); // 16 LEDs total

        if (level <= 6) level = 1;        // Mild (1-6 LEDs)
        else if (level <= 11) level = 2;  // Medium (7-11)
        else if (level <= 15) level = 3;  // Spicy (12-15)
        else level = 4;                    // NUCLEAR (16)

        // Show result
        clearLEDs();
        for (int i = 0; i < level * 4; i++) {
            if (level == 1) strip.setPixelColor(i, COLOR_GREEN);
            else if (level == 2) strip.setPixelColor(i, COLOR_YELLOW);
            else if (level == 3) strip.setPixelColor(i, COLOR_ORANGE);
            else strip.setPixelColor(i, COLOR_RED);
        }
        strip.show();

        Serial.printf("\n🎪 SHAME LEVEL: %d\n", level);

        // Display punishment
        if (level == 1) {
            Serial.printf("😊 MILD: %s\n", shameLevel1[random(3)]);
            beep(200);
            score -= 100;
        } else if (level == 2) {
            Serial.printf("😬 MEDIUM: %s\n", shameLevel2[random(3)]);
            beep(300);
            vibrate(200);
            score -= 200;
        } else if (level == 3) {
            Serial.printf("😱 SPICY: %s\n", shameLevel3[random(3)]);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score -= 400;
        } else {
            Serial.printf("💀 NUCLEAR: %s\n", shameLevel4[random(3)]);
            for (int i = 0; i < 5; i++) {
                fillLEDs(i % 2 ? COLOR_RED : COLOR_MAGENTA);
                beep(150);
                vibrate(150);
                delay(150);
            }
            score -= 600;
        }

        Serial.printf("Points remaining: %lu\n", score);
        delay(3000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 45: ALL IN (Degenerate Gambling)
// ============================================================================

uint32_t game_AllIn() {
    Serial.println("\n🎮 GAME: ALL IN");
    Serial.println("Bet everything on a coin flip!");

    beep(200);
    delay(1000);

    uint32_t bankroll = 1000;
    uint8_t flips = 0;

    Serial.printf("💰 Starting bankroll: %lu\n", bankroll);
    delay(1500);

    while (bankroll > 0 && flips < 5) {
        flips++;
        Serial.printf("\n🎰 Flip #%d\n", flips);
        Serial.printf("💰 Current bankroll: %lu\n", bankroll);

        Serial.println("\nTAP to bet it all!");
        Serial.println("HOLD for 3s to walk away");

        fillLEDs(COLOR_YELLOW);

        unsigned long decisionStart = millis();
        bool betPlaced = false;
        bool walkedAway = false;
        unsigned long holdStart = 0;
        bool holding = false;

        while (millis() - decisionStart < 10000 && !betPlaced && !walkedAway) {
            if (!digitalRead(PIN_BUTTON) && !holding) {
                holdStart = millis();
                holding = true;
                fillLEDs(COLOR_BLUE);
            }

            if (holding && digitalRead(PIN_BUTTON)) {
                // Released - check if tap or cancelled hold
                unsigned long holdDuration = millis() - holdStart;
                if (holdDuration < 500) {
                    // Quick tap = BET
                    betPlaced = true;
                    Serial.println("\n💎 ALL IN!");
                } else {
                    // Was holding but released early
                    fillLEDs(COLOR_YELLOW);
                }
                holding = false;
            }

            if (holding && (millis() - holdStart > 3000)) {
                // Held for 3s = WALK AWAY
                walkedAway = true;
                Serial.println("\n🚶 Walking away...");
            }

            delay(10);
        }

        if (walkedAway) {
            Serial.println("😌 You kept your money!");
            fillLEDs(COLOR_GREEN);
            beep(300);
            delay(2000);
            break;
        }

        if (!betPlaced) {
            Serial.println("⏰ Timeout! Forced to bet!");
            betPlaced = true;
        }

        // Coin flip animation
        Serial.println("\n🪙 Flipping...");
        for (int i = 0; i < 20; i++) {
            fillLEDs(i % 2 ? COLOR_GREEN : COLOR_RED);
            beep(50);
            delay(100);
        }

        // Result
        bool won = random(2);

        if (won) {
            Serial.println("✅ WIN! DOUBLED!");
            bankroll *= 2;
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
        } else {
            Serial.println("❌ LOSE! BUSTED!");
            bankroll = 0;
            fillLEDs(COLOR_RED);
            for (int i = 0; i < 10; i++) {
                beep(100);
                vibrate(100);
                delay(100);
            }
            break;
        }

        Serial.printf("💰 New bankroll: %lu\n", bankroll);
        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("\n🎰 Flips survived: %d\n", flips);
    Serial.printf("💯 FINAL SCORE: %lu\n", bankroll);

    delay(2000);
    return bankroll;
}

// ============================================================================
// GAME 46: COPYCAT CHAOS (Dance/Movement Copy)
// ============================================================================

uint32_t game_CopycatChaos() {
    Serial.println("\n🎮 GAME: COPYCAT CHAOS");
    Serial.println("Copy the movement patterns!");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 5;

    const char* moves[] = {"SHAKE HARD", "SPIN 360°", "JUMP", "FREEZE", "TAP RAPIDLY"};

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/5\n", round + 1);

        // Show the move
        int moveIndex = random(5);
        Serial.printf("🎭 DO THIS: %s\n", moves[moveIndex]);

        // Visual cue
        fillLEDs(COLOR_CYAN);
        beep(200);
        delay(2000);

        // GO!
        Serial.println("GO!");
        fillLEDs(COLOR_GREEN);
        beep(300);

        unsigned long moveStart = millis();
        bool success = false;

        // Check for correct move (3 second window)
        while (millis() - moveStart < 3000 && !success) {
            if (moveIndex == 0) { // SHAKE HARD
                if (getShakeIntensity() > 15.0) {
                    success = true;
                }
            } else if (moveIndex == 1) { // SPIN
                if (getShakeIntensity() > 10.0) {
                    success = true; // Simplified for single puck
                }
            } else if (moveIndex == 2) { // JUMP
                if (getShakeIntensity() > 20.0) {
                    success = true;
                }
            } else if (moveIndex == 3) { // FREEZE
                if (getShakeIntensity() < 1.0) {
                    success = true;
                }
            } else if (moveIndex == 4) { // TAP RAPIDLY
                static int taps = 0;
                if (readButton()) {
                    taps++;
                    if (taps >= 5) {
                        success = true;
                        taps = 0;
                    }
                }
            }
            delay(10);
        }

        if (success) {
            Serial.println("✅ PERFECT!");
            fillLEDs(COLOR_YELLOW);
            for (int i = 0; i < 3; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score += 200;
        } else {
            Serial.println("❌ FAILED!");
            fillLEDs(COLOR_RED);
            beep(300);
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 47: BEER ROULETTE (Russian Roulette - Drink Edition)
// ============================================================================

uint32_t game_BeerRoulette() {
    Serial.println("\n🎮 GAME: BEER ROULETTE");
    Serial.println("6 drinks. 1 is 'loaded'. Don't pick it!");

    beep(200);
    delay(1000);

    uint32_t score = 0;

    // Pick the "loaded" drink (1-6)
    uint8_t loadedDrink = random(1, 7);
    Serial.printf("🎰 The loaded drink is... (hidden)\n");

    fillLEDs(COLOR_YELLOW);
    delay(2000);

    for (int round = 1; round <= 6; round++) {
        Serial.printf("\nDrink %d/6\n", round);
        Serial.println("SHAKE to select this drink");
        Serial.println("or wait 5 seconds to skip");

        fillLEDs(COLOR_CYAN);

        unsigned long decisionStart = millis();
        bool selected = false;

        while (millis() - decisionStart < 5000 && !selected) {
            if (getShakeIntensity() > 8.0) {
                selected = true;
            }
            delay(50);
        }

        if (selected) {
            Serial.printf("🍺 You picked drink #%d\n", round);

            // Suspense
            for (int i = 0; i < 10; i++) {
                fillLEDs(i % 2 ? COLOR_YELLOW : COLOR_OFF);
                beep(100);
                delay(200);
            }

            if (round == loadedDrink) {
                Serial.println("\n💀 LOADED! YOU LOSE!");
                fillLEDs(COLOR_RED);
                for (int i = 0; i < 10; i++) {
                    beep(100);
                    vibrate(100);
                    delay(100);
                }
                score = 0;
                break;
            } else {
                Serial.println("✅ SAFE!");
                fillLEDs(COLOR_GREEN);
                for (int i = 0; i < 3; i++) {
                    beep(100);
                    vibrate(100);
                    delay(150);
                }
                score += 200;
            }
        } else {
            Serial.println("😌 Skipped this one");
            fillLEDs(COLOR_BLUE);
            beep(100);
            delay(1000);
        }

        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 48: NEVER HAVE I EVER (Digital Version)
// ============================================================================

uint32_t game_NeverHaveIEver() {
    Serial.println("\n🎮 GAME: NEVER HAVE I EVER");
    Serial.println("TAP if you HAVE done it");
    Serial.println("FREEZE if you HAVEN'T");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t rounds = 8;

    const char* statements[] = {
        "Been skydiving",
        "Cheated on a test",
        "Broken a bone",
        "Met a celebrity",
        "Been arrested",
        "Traveled abroad",
        "Been in a fight",
        "Lied to a cop"
    };

    for (int round = 0; round < rounds; round++) {
        Serial.printf("\nRound %d/8\n", round + 1);
        Serial.printf("Never have I ever... %s\n", statements[round]);

        fillLEDs(COLOR_CYAN);
        delay(2000);

        Serial.println("TAP = YES, FREEZE = NO");
        fillLEDs(COLOR_YELLOW);
        beep(200);

        unsigned long answerWindow = millis();
        bool answered = false;
        bool answer = false;

        while (millis() - answerWindow < 3000 && !answered) {
            if (readButton()) {
                answer = true;
                answered = true;
                Serial.println("👆 You HAVE!");
                fillLEDs(COLOR_GREEN);
                beep(100);
            } else if (getShakeIntensity() < 0.5) {
                // They're frozen
                if (millis() - answerWindow > 1000) {
                    answer = false;
                    answered = true;
                    Serial.println("🧊 You HAVEN'T");
                    fillLEDs(COLOR_BLUE);
                    beep(100);
                }
            }
            delay(10);
        }

        if (!answered) {
            Serial.println("⏰ No answer = skip");
            fillLEDs(COLOR_ORANGE);
            beep(200);
        } else {
            score += 100;
        }

        delay(2000);
        clearLEDs();
        delay(1000);
    }

    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 49: ACCENT ROULETTE
// ============================================================================

uint32_t game_AccentRoulette() {
    Serial.println("\n🎮 GAME: ACCENT ROULETTE");
    Serial.println("Speak in the assigned accent for 60 seconds!");

    beep(200);
    delay(1000);

    uint32_t score = 0;

    const char* accents[] = {"RUSSIAN", "IRISH", "FRENCH", "SOUTHERN", "PIRATE", "VALLEY GIRL"};
    uint32_t accentColors[] = {COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, COLOR_PURPLE, COLOR_CYAN};

    // Spin for accent
    Serial.println("SHAKE to spin for your accent!");
    fillLEDs(COLOR_CYAN);

    while (getShakeIntensity() < 8.0) {
        delay(50);
    }

    // Spinning
    Serial.println("🎡 Spinning...");
    for (int i = 0; i < 30; i++) {
        clearLEDs();
        strip.setPixelColor(i % NUM_LEDS, COLOR_MAGENTA);
        strip.show();
        beep(50);
        delay(80);
    }

    // Select accent
    int accentIndex = random(6);

    Serial.printf("\n🎭 YOUR ACCENT: %s\n", accents[accentIndex]);
    fillLEDs(accentColors[accentIndex]);
    for (int i = 0; i < 3; i++) {
        beep(200);
        delay(300);
    }

    Serial.println("\nSpeak in this accent for 60 seconds!");
    Serial.println("Group will vote: TAP if good, SHAKE if bad");

    // Countdown with LED ring
    for (int seconds = 60; seconds > 0; seconds--) {
        int litLEDs = map(seconds, 0, 60, 0, NUM_LEDS);
        clearLEDs();
        for (int i = 0; i < litLEDs; i++) {
            strip.setPixelColor(i, accentColors[accentIndex]);
        }
        strip.show();

        if (seconds % 10 == 0) {
            Serial.printf("%d seconds remaining...\n", seconds);
            beep(100);
        }

        delay(1000);
    }

    // Time's up!
    Serial.println("\n⏰ TIME'S UP!");
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    // Simulated voting (random for single player)
    Serial.println("\nVoting...");
    delay(2000);

    bool approved = random(2);
    if (approved) {
        Serial.println("✅ APPROVED!");
        fillLEDs(COLOR_GREEN);
        for (int i = 0; i < 5; i++) {
            beep(100);
            vibrate(100);
            delay(150);
        }
        score = 1000;
    } else {
        Serial.println("❌ REJECTED!");
        fillLEDs(COLOR_RED);
        beep(500);
        score = 0;
    }

    delay(2000);

    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    delay(2000);
    return score;
}

// ============================================================================
// GAME 50: TRIVIA SPINNER (LED Answer Selection)
// ============================================================================

uint32_t game_TriviaSpinner() {
    Serial.println("\n🎮 GAME: TRIVIA SPINNER");
    Serial.println("Stop the spinner on your answer (A/B/C/D)");

    beep(200);
    delay(1000);

    uint32_t score = 0;
    uint8_t questions = 5;

    // Sample trivia questions (in real deployment, from server/app)
    const char* questionText[] = {
        "What is 2+2?",
        "Capital of France?",
        "Largest planet?",
        "H2O is?",
        "First US President?"
    };

    const char* answerA[] = {"3", "London", "Earth", "Oxygen", "Jefferson"};
    const char* answerB[] = {"4", "Paris", "Jupiter", "Water", "Washington"};
    const char* answerC[] = {"5", "Berlin", "Saturn", "Hydrogen", "Adams"};
    const char* answerD[] = {"6", "Madrid", "Neptune", "Helium", "Lincoln"};

    const char correctAnswers[] = {'B', 'B', 'B', 'B', 'B'}; // All B for demo

    for (int q = 0; q < questions; q++) {
        Serial.printf("\n━━━━━ QUESTION %d/5 ━━━━━\n", q + 1);
        Serial.println(questionText[q]);
        Serial.printf("A: %s\n", answerA[q]);
        Serial.printf("B: %s\n", answerB[q]);
        Serial.printf("C: %s\n", answerC[q]);
        Serial.printf("D: %s\n", answerD[q]);

        Serial.println("\n🎯 TAP to STOP the spinner on your answer!");
        delay(2000);

        // LED ring divided into 4 quadrants
        // LEDs 0-3 = A (RED)
        // LEDs 4-7 = B (GREEN)
        // LEDs 8-11 = C (BLUE)
        // LEDs 12-15 = D (YELLOW)

        // Spinner animation
        Serial.println("🎡 Spinner active...");

        int spinnerPos = 0;
        unsigned long spinStart = millis();
        bool stopped = false;
        int finalPos = 0;

        // Spin for up to 10 seconds or until stopped
        while (millis() - spinStart < 10000 && !stopped) {
            // Clear and show spinner
            clearLEDs();
            strip.setPixelColor(spinnerPos, COLOR_WHITE);
            strip.show();

            // Check for button press
            if (readButton()) {
                stopped = true;
                finalPos = spinnerPos;
                Serial.println("🛑 STOPPED!");

                // Flash the selected LED
                for (int i = 0; i < 5; i++) {
                    strip.setPixelColor(finalPos, i % 2 ? COLOR_WHITE : COLOR_OFF);
                    strip.show();
                    beep(100);
                    delay(150);
                }
            }

            // Move spinner (slower than other games for accuracy)
            spinnerPos = (spinnerPos + 1) % NUM_LEDS;
            beep(30);
            delay(120); // SLOWER spin = easier to target

            // Slightly randomize delay for unpredictability
            delay(random(0, 30));
        }

        if (!stopped) {
            Serial.println("⏰ Timeout! Random answer selected");
            finalPos = random(NUM_LEDS);
        }

        // Determine selected answer from LED position
        char selectedAnswer;
        uint32_t answerColor;

        if (finalPos < 4) {
            selectedAnswer = 'A';
            answerColor = COLOR_RED;
        } else if (finalPos < 8) {
            selectedAnswer = 'B';
            answerColor = COLOR_GREEN;
        } else if (finalPos < 12) {
            selectedAnswer = 'C';
            answerColor = COLOR_BLUE;
        } else {
            selectedAnswer = 'D';
            answerColor = COLOR_YELLOW;
        }

        Serial.printf("\n📍 You selected: %c\n", selectedAnswer);

        // Show selected answer quadrant
        clearLEDs();
        int startLED = (selectedAnswer - 'A') * 4;
        for (int i = 0; i < 4; i++) {
            strip.setPixelColor(startLED + i, answerColor);
        }
        strip.show();

        delay(2000);

        // Reveal answer
        Serial.println("\n🎓 Correct answer is...");
        delay(1500);

        for (int i = 0; i < 3; i++) {
            clearLEDs();
            delay(200);
            int correctStartLED = (correctAnswers[q] - 'A') * 4;
            for (int j = 0; j < 4; j++) {
                if (correctAnswers[q] == 'A') strip.setPixelColor(correctStartLED + j, COLOR_RED);
                else if (correctAnswers[q] == 'B') strip.setPixelColor(correctStartLED + j, COLOR_GREEN);
                else if (correctAnswers[q] == 'C') strip.setPixelColor(correctStartLED + j, COLOR_BLUE);
                else strip.setPixelColor(correctStartLED + j, COLOR_YELLOW);
            }
            strip.show();
            beep(100);
            delay(200);
        }

        Serial.printf("%c!\n", correctAnswers[q]);

        // Check if correct
        if (selectedAnswer == correctAnswers[q]) {
            Serial.println("\n✅ CORRECT!");
            fillLEDs(COLOR_GREEN);
            for (int i = 0; i < 5; i++) {
                beep(100);
                vibrate(100);
                delay(150);
            }
            score += 200;
        } else {
            Serial.println("\n❌ WRONG!");
            fillLEDs(COLOR_RED);
            beep(500);
            vibrate(500);
        }

        delay(2000);
        clearLEDs();

        if (q < questions - 1) {
            Serial.println("\nNext question in 3 seconds...");
            delay(3000);
        }
    }

    // Final results
    fillLEDs(COLOR_MAGENTA);
    beep(500);

    Serial.println("\n━━━━━━━━━━━━━━━━━━━");
    Serial.printf("📊 Correct answers: %lu/5\n", score / 200);
    Serial.printf("💯 FINAL SCORE: %lu\n", score);
    Serial.println("━━━━━━━━━━━━━━━━━━━");

    delay(3000);
    return score;
}
