/*
 * TABLE WARS - Game Framework Implementation
 */

#include "GameFramework.h"

// ============================================================================
// GAME MANAGER IMPLEMENTATION
// ============================================================================

GameManager::GameManager() {
    currentState = STATE_IDLE;
    currentGame = GAME_SPEED_TAP;
    activeGame = nullptr;
    stateStartTime = 0;
    gameStartTime = 0;
}

void GameManager::init(uint8_t puckId, uint8_t tableNum) {
    puckInfo.puckId = puckId;
    puckInfo.tableNumber = tableNum;
    puckInfo.teamColor = COLOR_TEAM_CYAN;
    puckInfo.totalScore = 0;
    puckInfo.isActive = true;
}

void GameManager::setState(GameState newState) {
    currentState = newState;
    stateStartTime = millis();
}

void GameManager::setTeamColor(TeamColor color) {
    puckInfo.teamColor = color;
}

// ============================================================================
// HARDWARE INTERFACE IMPLEMENTATION
// ============================================================================

bool HardwareInterface::buttonPressed() {
    bool reading = !digitalRead(pinButton); // Active LOW
    bool pressed = false;

    if (reading != lastButtonState) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > debounceDelay) {
        if (reading && !lastButtonState) {
            pressed = true;
        }
        lastButtonState = reading;
    }

    return pressed;
}

bool HardwareInterface::buttonReleased() {
    bool reading = !digitalRead(pinButton);
    bool released = false;

    if (reading != lastButtonState) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > debounceDelay) {
        if (!reading && lastButtonState) {
            released = true;
        }
        lastButtonState = reading;
    }

    return released;
}

float HardwareInterface::getShakeIntensity() {
    sensors_event_t accel, gyro, temp;
    mpu->getEvent(&accel, &gyro, &temp);

    // Calculate total acceleration magnitude
    float ax = accel.acceleration.x;
    float ay = accel.acceleration.y;
    float az = accel.acceleration.z;

    float magnitude = sqrt(ax*ax + ay*ay + az*az);
    return abs(magnitude - 9.81); // Remove gravity baseline
}

float HardwareInterface::getAcceleration() {
    sensors_event_t accel, gyro, temp;
    mpu->getEvent(&accel, &gyro, &temp);

    float ax = accel.acceleration.x;
    float ay = accel.acceleration.y;
    float az = accel.acceleration.z;

    return sqrt(ax*ax + ay*ay + az*az);
}

void HardwareInterface::beep(uint16_t duration, uint16_t frequency) {
    digitalWrite(pinBuzzer, HIGH);
    delay(duration);
    digitalWrite(pinBuzzer, LOW);
}

void HardwareInterface::vibrate(uint16_t duration) {
    digitalWrite(pinMotor, HIGH);
    delay(duration);
    digitalWrite(pinMotor, LOW);
}

void HardwareInterface::setLEDs(uint32_t color) {
    for (int i = 0; i < leds->numPixels(); i++) {
        leds->setPixelColor(i, color);
    }
}

void HardwareInterface::setLED(uint8_t index, uint32_t color) {
    leds->setPixelColor(index, color);
}

void HardwareInterface::updateLEDs() {
    leds->show();
}

void HardwareInterface::clearLEDs() {
    leds->clear();
    leds->show();
}

void HardwareInterface::flashLEDs(uint32_t color, uint8_t count, uint16_t delayMs) {
    for (uint8_t i = 0; i < count; i++) {
        setLEDs(color);
        updateLEDs();
        delay(delayMs);
        clearLEDs();
        if (i < count - 1) delay(delayMs);
    }
}

void HardwareInterface::breatheLEDs(uint32_t color, uint16_t periodMs) {
    float phase = (millis() % periodMs) / (float)periodMs;
    float brightness = (sin(phase * 2 * PI - PI/2) + 1.0) / 2.0;

    uint8_t r = ((color >> 16) & 0xFF) * brightness;
    uint8_t g = ((color >> 8) & 0xFF) * brightness;
    uint8_t b = (color & 0xFF) * brightness;

    setLEDs(leds->Color(r, g, b));
    updateLEDs();
}

void HardwareInterface::rainbowCycle(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    static uint16_t hue = 0;

    if (millis() - lastUpdate >= wait) {
        for (int i = 0; i < leds->numPixels(); i++) {
            int pixelHue = hue + (i * 65536L / leds->numPixels());
            leds->setPixelColor(i, leds->gamma32(leds->ColorHSV(pixelHue)));
        }
        leds->show();
        hue += 256;
        lastUpdate = millis();
    }
}

void HardwareInterface::theaterChase(uint32_t color, uint8_t wait) {
    static unsigned long lastUpdate = 0;
    static uint8_t offset = 0;

    if (millis() - lastUpdate >= wait) {
        clearLEDs();
        for (int i = 0; i < leds->numPixels(); i += 3) {
            leds->setPixelColor(i + offset, color);
        }
        leds->show();
        offset = (offset + 1) % 3;
        lastUpdate = millis();
    }
}

void HardwareInterface::pulse(uint32_t color, uint8_t pulseCount) {
    for (uint8_t i = 0; i < pulseCount; i++) {
        for (uint8_t brightness = 0; brightness < 255; brightness += 5) {
            uint8_t r = ((color >> 16) & 0xFF) * brightness / 255;
            uint8_t g = ((color >> 8) & 0xFF) * brightness / 255;
            uint8_t b = (color & 0xFF) * brightness / 255;
            setLEDs(leds->Color(r, g, b));
            updateLEDs();
            delay(5);
        }
        for (uint8_t brightness = 255; brightness > 0; brightness -= 5) {
            uint8_t r = ((color >> 16) & 0xFF) * brightness / 255;
            uint8_t g = ((color >> 8) & 0xFF) * brightness / 255;
            uint8_t b = (color & 0xFF) * brightness / 255;
            setLEDs(leds->Color(r, g, b));
            updateLEDs();
            delay(5);
        }
    }
}

void HardwareInterface::countdown(uint8_t seconds, uint32_t color) {
    for (uint8_t i = seconds; i > 0; i--) {
        setLEDs(color);
        updateLEDs();
        beep(200);
        delay(800);
        clearLEDs();
        delay(200);
    }
    // Final GO! beep
    setLEDs(leds->Color(0, 255, 0));
    updateLEDs();
    beep(500);
    delay(500);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

namespace GameUtils {

uint32_t teamColorToRGB(TeamColor color) {
    switch (color) {
        case COLOR_TEAM_RED:    return 0xFF0000;
        case COLOR_TEAM_BLUE:   return 0x0000FF;
        case COLOR_TEAM_GREEN:  return 0x00FF00;
        case COLOR_TEAM_YELLOW: return 0xFFFF00;
        case COLOR_TEAM_PURPLE: return 0x800080;
        case COLOR_TEAM_CYAN:   return 0x00FFFF;
        case COLOR_TEAM_ORANGE: return 0xFF6600;
        case COLOR_TEAM_WHITE:  return 0xFFFFFF;
        default:                return 0x00FFFF;
    }
}

String gameTypeToString(GameType game) {
    switch (game) {
        case GAME_SPEED_TAP:        return "Speed Tap Battle";
        case GAME_SHAKE_DUEL:       return "Shake Duel";
        case GAME_FREEZE_ROUND:     return "Freeze Round";
        case GAME_PASS_THE_BOMB:    return "Pass The Bomb";
        case GAME_TRIVIA_RACE:      return "Trivia Race";
        case GAME_SYNC_TAP:         return "Sync Tap";
        case GAME_CHAOS_MODE:       return "Chaos Mode";
        case GAME_STEALTH_MODE:     return "Stealth Mode";
        case GAME_LED_CHASE:        return "LED Chase Race";
        case GAME_COLOR_WARS:       return "Color Wars";
        case GAME_RAINBOW_ROULETTE: return "Rainbow Roulette";
        case GAME_VISUAL_BOMB:      return "Visual Bomb";
        case GAME_SIMON_SAYS:       return "Simon Says LED";
        case GAME_LIGHTNING_ROUND:  return "Lightning Round";
        case GAME_RED_LIGHT_GREEN:  return "Red Light Green Light";
        default:                    return "Unknown Game";
    }
}

String formatTime(uint32_t ms) {
    uint32_t seconds = ms / 1000;
    uint32_t millis = ms % 1000;
    char buffer[16];
    sprintf(buffer, "%lu.%03lu s", seconds, millis);
    return String(buffer);
}

uint32_t calculateScore(uint32_t rawScore, uint32_t time, uint32_t maxTime) {
    // Score formula: rawScore * (1 + timeBonus)
    // Faster completion = higher bonus
    float timeBonus = (float)(maxTime - time) / maxTime * 0.5; // Up to 50% bonus
    if (timeBonus < 0) timeBonus = 0;

    return rawScore * (1.0 + timeBonus);
}

} // namespace GameUtils
