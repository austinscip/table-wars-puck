/*
 * TABLE WARS - Game Framework
 *
 * Base classes and types for the mini-game system
 */

#ifndef GAME_FRAMEWORK_H
#define GAME_FRAMEWORK_H

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_MPU6050.h>

// ============================================================================
// GAME TYPES & CONSTANTS
// ============================================================================

enum GameType {
    GAME_SPEED_TAP,           // Mash button as fast as possible
    GAME_SHAKE_DUEL,          // Shake puck violently
    GAME_FREEZE_ROUND,        // Don't move when red light shows
    GAME_PASS_THE_BOMB,       // Hot potato with pucks
    GAME_TRIVIA_RACE,         // First to buzz wins
    GAME_SYNC_TAP,            // All players tap in sync
    GAME_CHAOS_MODE,          // Random mini-games rapid fire
    GAME_STEALTH_MODE,        // Ninja mode - don't get detected
    GAME_LED_CHASE,           // Hit the target LED
    GAME_COLOR_WARS,          // Team color domination
    GAME_RAINBOW_ROULETTE,    // Stop on the right color
    GAME_VISUAL_BOMB,         // Bomb with visual countdown
    GAME_SIMON_SAYS,          // LED pattern memory
    GAME_LIGHTNING_ROUND,     // Random table activation
    GAME_RED_LIGHT_GREEN,     // Squid Game style
    GAME_COUNT                // Total number of games
};

enum GameState {
    STATE_IDLE,
    STATE_WAITING,            // Waiting for game to start
    STATE_COUNTDOWN,          // 3...2...1... countdown
    STATE_PLAYING,            // Game in progress
    STATE_SCORING,            // Calculating results
    STATE_RESULTS             // Showing results
};

enum TeamColor {
    COLOR_TEAM_RED,
    COLOR_TEAM_BLUE,
    COLOR_TEAM_GREEN,
    COLOR_TEAM_YELLOW,
    COLOR_TEAM_PURPLE,
    COLOR_TEAM_CYAN,
    COLOR_TEAM_ORANGE,
    COLOR_TEAM_WHITE
};

// ============================================================================
// GAME RESULT STRUCTURE
// ============================================================================

struct GameResult {
    uint32_t score;           // Final score for this round
    uint32_t time;            // Time taken (ms)
    uint32_t accuracy;        // Accuracy percentage (0-100)
    bool completed;           // Did player complete the game?
    String message;           // Result message
};

// ============================================================================
// PUCK INFO STRUCTURE
// ============================================================================

struct PuckInfo {
    uint8_t puckId;           // Unique puck ID (1-255)
    uint8_t tableNumber;      // Table assignment
    TeamColor teamColor;      // Team color
    String playerName;        // Optional player name
    uint32_t totalScore;      // Session total score
    bool isActive;            // Is puck active in game?
};

// ============================================================================
// BASE GAME CLASS
// ============================================================================

class MiniGame {
public:
    virtual void setup() = 0;                           // Initialize game
    virtual void start() = 0;                           // Start game
    virtual void update() = 0;                          // Called every loop
    virtual GameResult getResult() = 0;                 // Get final result
    virtual String getName() = 0;                       // Game name
    virtual String getInstructions() = 0;               // How to play
    virtual uint32_t getDuration() = 0;                 // Game duration (ms)
    virtual bool isComplete() = 0;                      // Is game finished?

    virtual ~MiniGame() {}                              // Virtual destructor
};

// ============================================================================
// GAME MANAGER CLASS
// ============================================================================

class GameManager {
private:
    GameState currentState;
    GameType currentGame;
    MiniGame* activeGame;
    unsigned long stateStartTime;
    unsigned long gameStartTime;
    PuckInfo puckInfo;

public:
    GameManager();

    void init(uint8_t puckId, uint8_t tableNum);
    void update();
    void startGame(GameType game);
    void endGame();

    GameState getState() { return currentState; }
    GameType getCurrentGame() { return currentGame; }
    PuckInfo& getPuckInfo() { return puckInfo; }

    void setState(GameState newState);
    void setTeamColor(TeamColor color);
};

// ============================================================================
// HARDWARE ABSTRACTION
// ============================================================================

class HardwareInterface {
public:
    Adafruit_NeoPixel* leds;
    Adafruit_MPU6050* mpu;

    uint8_t pinButton;
    uint8_t pinBuzzer;
    uint8_t pinMotor;

    bool buttonPressed();
    bool buttonReleased();
    float getShakeIntensity();
    float getAcceleration();
    void beep(uint16_t duration, uint16_t frequency = 2000);
    void vibrate(uint16_t duration);
    void setLEDs(uint32_t color);
    void setLED(uint8_t index, uint32_t color);
    void updateLEDs();
    void clearLEDs();

    // LED effects
    void flashLEDs(uint32_t color, uint8_t count, uint16_t delayMs);
    void breatheLEDs(uint32_t color, uint16_t periodMs);
    void rainbowCycle(uint8_t wait);
    void theaterChase(uint32_t color, uint8_t wait);
    void pulse(uint32_t color, uint8_t pulseCount);
    void countdown(uint8_t seconds, uint32_t color);

private:
    bool lastButtonState;
    unsigned long lastDebounceTime;
    const unsigned long debounceDelay = 50;
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

namespace GameUtils {
    uint32_t teamColorToRGB(TeamColor color);
    String gameTypeToString(GameType game);
    String formatTime(uint32_t ms);
    uint32_t calculateScore(uint32_t rawScore, uint32_t time, uint32_t maxTime);
}

#endif // GAME_FRAMEWORK_H
