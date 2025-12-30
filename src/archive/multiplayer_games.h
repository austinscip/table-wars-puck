/*
 * TABLE WARS - Multiplayer Games
 *
 * Games that require 2+ pucks with WiFi sync
 */

#ifndef MULTIPLAYER_GAMES_H
#define MULTIPLAYER_GAMES_H

#include "wifi_sync.h"

// NOTE: This file is meant to be included from main_tablewars.h
// It relies on hardware objects and functions defined there

// ============================================================================
// MULTIPLAYER GAME 1: PASS THE BOMB
// ============================================================================

class PassTheBombGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    bool hasBomb;
    unsigned long bombStartTime;
    unsigned long bombDuration;
    unsigned long bombReceivedTime;
    uint8_t passCount;
    bool gameOver;

    void explodeBomb();
    void showBombCountdown();

public:
    PassTheBombGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};

// ============================================================================
// MULTIPLAYER GAME 2: TEAM BATTLE
// ============================================================================

class TeamBattleGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    uint8_t myTeam;          // 0 = Red, 1 = Blue
    uint32_t myTeamColor;
    uint32_t teamScores[2];
    uint8_t roundsPlayed;

    void assignTeams();
    void syncTeamColors();
    void playRound();
    void showTeamScores();

public:
    TeamBattleGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};

// ============================================================================
// MULTIPLAYER GAME 3: KING OF THE HILL
// ============================================================================

class KingOfTheHillGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    uint8_t currentKing;
    uint32_t myScore;
    unsigned long kingStartTime;
    uint32_t kingColor;

    void challengeForKing();
    void showKingStatus();
    void syncScores();

public:
    KingOfTheHillGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};

// ============================================================================
// MULTIPLAYER GAME 4: RELAY RACE
// ============================================================================

class RelayRaceGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    uint8_t turnOrder[MAX_PUCKS];
    uint8_t currentTurn;
    bool myTurnActive;
    uint32_t totalScore;
    unsigned long turnStartTime;

    void waitForTurn();
    void playMyTurn();
    void passTurn();

public:
    RelayRaceGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};

// ============================================================================
// MULTIPLAYER GAME 5: SYNCHRONIZED SHAKE
// ============================================================================

class SyncShakeGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    float targetIntensity;
    float myIntensity;
    bool syncAchieved;

    void waitForSync();
    void showSyncProgress();

public:
    SyncShakeGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};

// Include implementation
#include "multiplayer_games_impl.h"

#endif // MULTIPLAYER_GAMES_H
