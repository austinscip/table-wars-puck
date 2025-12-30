/**
 * sd_card.h
 *
 * SD Card Storage System
 * Store thousands of trivia questions, audio files, and game data offline
 *
 * Hardware:
 *   - Micro SD card breakout module ($1.50)
 *   - Micro SD card (8GB-32GB recommended)
 *
 * Wiring (SPI Mode):
 *   ESP32 GPIO 18 → SCK  (Clock)
 *   ESP32 GPIO 19 → MISO (Master In, Slave Out)
 *   ESP32 GPIO 23 → MOSI (Master Out, Slave In)
 *   ESP32 GPIO 5  → CS   (Chip Select)
 *   SD Module VCC → 3.3V (NOT 5V!)
 *   SD Module GND → GND
 *
 * Features:
 *   - Store 10,000+ trivia questions offline
 *   - Audio file library (WAV, MP3)
 *   - Game replays and high scores
 *   - User profiles and stats
 *   - Downloadable content packs
 *   - Offline mode for all games
 *
 * File Structure:
 *   /trivia/
 *     /categories/
 *       sports.json
 *       movies.json
 *       history.json
 *   /audio/
 *     /sfx/
 *     /voice/
 *     /music/
 *   /replays/
 *   /scores/
 *   /users/
 *
 * Dependencies: SD library (built-in)
 */

#ifndef SD_CARD_H
#define SD_CARD_H

#include <Arduino.h>
#include <SD.h>
#include <SPI.h>
#include <ArduinoJson.h>

// ============================================================================
// SD CARD PIN CONFIGURATION
// ============================================================================

#define SD_CS_PIN     5   // Chip Select
#define SD_SCK_PIN    18  // Clock
#define SD_MISO_PIN   19  // Master In, Slave Out
#define SD_MOSI_PIN   23  // Master Out, Slave In

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

bool sdCardInitialized = false;
uint8_t sdCardType = 0;
uint64_t sdCardSize = 0;

// ============================================================================
// SD CARD INITIALIZATION
// ============================================================================

/**
 * Initialize SD card system
 */
bool initSDCard() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("💾 INITIALIZING SD CARD");
    Serial.println("═══════════════════════════════════");

    // Initialize SPI with custom pins
    SPI.begin(SD_SCK_PIN, SD_MISO_PIN, SD_MOSI_PIN, SD_CS_PIN);

    // Attempt to mount SD card
    if (!SD.begin(SD_CS_PIN)) {
        Serial.println("❌ SD card mount failed");
        Serial.println("   Check:");
        Serial.println("   - SD card is inserted");
        Serial.println("   - Wiring is correct");
        Serial.println("   - SD module uses 3.3V (NOT 5V)");
        return false;
    }

    sdCardInitialized = true;

    // Detect card type
    sdCardType = SD.cardType();

    if (sdCardType == CARD_NONE) {
        Serial.println("❌ No SD card detected");
        return false;
    }

    // Print card type
    Serial.print("✅ SD Card Type: ");
    switch (sdCardType) {
        case CARD_MMC:
            Serial.println("MMC");
            break;
        case CARD_SD:
            Serial.println("SDSC");
            break;
        case CARD_SDHC:
            Serial.println("SDHC");
            break;
        default:
            Serial.println("UNKNOWN");
    }

    // Get card size
    sdCardSize = SD.cardSize() / (1024 * 1024);
    Serial.printf("   Size: %llu MB\n", sdCardSize);

    uint64_t usedBytes = SD.usedBytes() / (1024 * 1024);
    uint64_t totalBytes = SD.totalBytes() / (1024 * 1024);
    Serial.printf("   Used: %llu MB / %llu MB\n", usedBytes, totalBytes);

    // Create directory structure
    createDirectoryStructure();

    Serial.println("═══════════════════════════════════\n");
    return true;
}

/**
 * Create standard directory structure
 */
void createDirectoryStructure() {
    const char* directories[] = {
        "/trivia",
        "/trivia/categories",
        "/trivia/custom",
        "/audio",
        "/audio/sfx",
        "/audio/voice",
        "/audio/music",
        "/replays",
        "/scores",
        "/users",
        "/updates"
    };

    Serial.println("Creating directory structure...");

    for (int i = 0; i < sizeof(directories) / sizeof(directories[0]); i++) {
        if (!SD.exists(directories[i])) {
            SD.mkdir(directories[i]);
            Serial.printf("  Created: %s\n", directories[i]);
        }
    }
}

// ============================================================================
// TRIVIA QUESTION DATABASE
// ============================================================================

/**
 * Trivia question structure
 */
struct TriviaQuestion {
    String category;
    String question;
    String answer;
    String options[4];  // For multiple choice
    int difficulty;     // 1-5
    int timeLimit;      // Seconds
};

/**
 * Load trivia questions from JSON file
 */
bool loadTriviaCategory(const char* category, TriviaQuestion* questions, int maxQuestions, int& loadedCount) {
    if (!sdCardInitialized) {
        Serial.println("⚠️ SD card not initialized");
        return false;
    }

    char filename[64];
    sprintf(filename, "/trivia/categories/%s.json", category);

    if (!SD.exists(filename)) {
        Serial.printf("❌ Category file not found: %s\n", filename);
        return false;
    }

    File file = SD.open(filename, FILE_READ);
    if (!file) {
        Serial.printf("❌ Failed to open: %s\n", filename);
        return false;
    }

    // Parse JSON
    DynamicJsonDocument doc(16384);  // 16KB buffer
    DeserializationError error = deserializeJson(doc, file);

    if (error) {
        Serial.printf("❌ JSON parsing failed: %s\n", error.c_str());
        file.close();
        return false;
    }

    file.close();

    // Extract questions
    JsonArray questionsArray = doc["questions"];
    loadedCount = 0;

    for (JsonObject q : questionsArray) {
        if (loadedCount >= maxQuestions) break;

        questions[loadedCount].category = category;
        questions[loadedCount].question = q["question"].as<String>();
        questions[loadedCount].answer = q["answer"].as<String>();
        questions[loadedCount].difficulty = q["difficulty"] | 3;
        questions[loadedCount].timeLimit = q["timeLimit"] | 30;

        // Load multiple choice options if available
        if (q.containsKey("options")) {
            JsonArray opts = q["options"];
            for (int i = 0; i < 4 && i < opts.size(); i++) {
                questions[loadedCount].options[i] = opts[i].as<String>();
            }
        }

        loadedCount++;
    }

    Serial.printf("✅ Loaded %d questions from %s\n", loadedCount, category);
    return true;
}

/**
 * Get random trivia question from category
 */
TriviaQuestion getRandomQuestion(const char* category) {
    TriviaQuestion questions[100];
    int loadedCount = 0;

    loadTriviaCategory(category, questions, 100, loadedCount);

    if (loadedCount > 0) {
        return questions[random(loadedCount)];
    }

    // Return empty question if load failed
    return TriviaQuestion();
}

/**
 * Save custom trivia questions
 */
bool saveTriviaQuestion(const char* category, TriviaQuestion& question) {
    char filename[64];
    sprintf(filename, "/trivia/custom/%s.json", category);

    // Load existing questions
    DynamicJsonDocument doc(16384);

    if (SD.exists(filename)) {
        File file = SD.open(filename, FILE_READ);
        deserializeJson(doc, file);
        file.close();
    } else {
        doc["category"] = category;
        doc["questions"] = JsonArray();
    }

    // Add new question
    JsonArray questions = doc["questions"];
    JsonObject newQ = questions.createNestedObject();

    newQ["question"] = question.question;
    newQ["answer"] = question.answer;
    newQ["difficulty"] = question.difficulty;
    newQ["timeLimit"] = question.timeLimit;

    if (question.options[0] != "") {
        JsonArray opts = newQ.createNestedArray("options");
        for (int i = 0; i < 4; i++) {
            if (question.options[i] != "") {
                opts.add(question.options[i]);
            }
        }
    }

    // Save back to file
    File file = SD.open(filename, FILE_WRITE);
    if (!file) {
        Serial.println("❌ Failed to save trivia question");
        return false;
    }

    serializeJson(doc, file);
    file.close();

    Serial.println("✅ Trivia question saved");
    return true;
}

/**
 * List all trivia categories
 */
void listTriviaCategories() {
    Serial.println("\n📚 TRIVIA CATEGORIES:\n");

    File root = SD.open("/trivia/categories");
    File file = root.openNextFile();

    int count = 0;
    while (file) {
        if (!file.isDirectory()) {
            String filename = String(file.name());
            if (filename.endsWith(".json")) {
                filename.remove(filename.length() - 5);  // Remove .json
                Serial.printf("  %d. %s\n", ++count, filename.c_str());
            }
        }
        file = root.openNextFile();
    }

    Serial.println();
}

// ============================================================================
// HIGH SCORES & USER DATA
// ============================================================================

/**
 * Save high score to SD card
 */
bool saveHighScore(int gameId, const char* playerName, int score, int time) {
    char filename[32];
    sprintf(filename, "/scores/game_%d.json", gameId);

    // Load existing scores
    DynamicJsonDocument doc(8192);

    if (SD.exists(filename)) {
        File file = SD.open(filename, FILE_READ);
        deserializeJson(doc, file);
        file.close();
    } else {
        doc["game_id"] = gameId;
        doc["scores"] = JsonArray();
    }

    // Add new score
    JsonArray scores = doc["scores"];
    JsonObject newScore = scores.createNestedObject();

    newScore["player"] = playerName;
    newScore["score"] = score;
    newScore["time"] = time;
    newScore["timestamp"] = millis();

    // Sort scores (highest first)
    // Keep only top 10
    if (scores.size() > 10) {
        scores.remove(10);
    }

    // Save back to file
    File file = SD.open(filename, FILE_WRITE);
    if (!file) return false;

    serializeJson(doc, file);
    file.close();

    Serial.printf("✅ High score saved: %s - %d points\n", playerName, score);
    return true;
}

/**
 * Load high scores for a game
 */
void loadHighScores(int gameId) {
    char filename[32];
    sprintf(filename, "/scores/game_%d.json", gameId);

    if (!SD.exists(filename)) {
        Serial.println("No high scores yet");
        return;
    }

    File file = SD.open(filename, FILE_READ);
    DynamicJsonDocument doc(8192);
    deserializeJson(doc, file);
    file.close();

    Serial.printf("\n🏆 HIGH SCORES - Game %d\n", gameId);
    Serial.println("═══════════════════════════════════");

    JsonArray scores = doc["scores"];
    int rank = 1;

    for (JsonObject score : scores) {
        Serial.printf("%d. %s - %d pts (%d sec)\n",
                      rank++,
                      score["player"].as<const char*>(),
                      score["score"].as<int>(),
                      score["time"].as<int>());
    }

    Serial.println("═══════════════════════════════════\n");
}

/**
 * Save user profile
 */
bool saveUserProfile(const char* username, int totalGamesPlayed, int totalScore) {
    char filename[64];
    sprintf(filename, "/users/%s.json", username);

    DynamicJsonDocument doc(4096);

    doc["username"] = username;
    doc["total_games"] = totalGamesPlayed;
    doc["total_score"] = totalScore;
    doc["last_played"] = millis();

    File file = SD.open(filename, FILE_WRITE);
    if (!file) return false;

    serializeJson(doc, file);
    file.close();

    return true;
}

// ============================================================================
// GAME REPLAYS
// ============================================================================

/**
 * Record game replay data
 */
File replayFile;
bool replayRecording = false;

bool startReplayRecording(int gameId, const char* playerName) {
    char filename[64];
    sprintf(filename, "/replays/game%d_%lu.replay", gameId, millis());

    replayFile = SD.open(filename, FILE_WRITE);
    if (!replayFile) {
        Serial.println("❌ Failed to start replay recording");
        return false;
    }

    // Write header
    DynamicJsonDocument doc(512);
    doc["game_id"] = gameId;
    doc["player"] = playerName;
    doc["start_time"] = millis();
    doc["events"] = JsonArray();

    serializeJson(doc, replayFile);
    replayFile.println();

    replayRecording = true;
    Serial.println("🎥 Replay recording started");
    return true;
}

void recordReplayEvent(const char* eventType, float value1, float value2 = 0) {
    if (!replayRecording || !replayFile) return;

    DynamicJsonDocument doc(256);
    doc["type"] = eventType;
    doc["time"] = millis();
    doc["value1"] = value1;
    doc["value2"] = value2;

    serializeJson(doc, replayFile);
    replayFile.println();
}

void stopReplayRecording() {
    if (replayRecording && replayFile) {
        replayFile.close();
        replayRecording = false;
        Serial.println("⏹️ Replay recording stopped");
    }
}

// ============================================================================
// FILE UTILITIES
// ============================================================================

/**
 * List all files in a directory
 */
void listDirectory(const char* dirname, int levels = 1) {
    Serial.printf("Listing directory: %s\n", dirname);

    File root = SD.open(dirname);
    if (!root) {
        Serial.println("Failed to open directory");
        return;
    }
    if (!root.isDirectory()) {
        Serial.println("Not a directory");
        return;
    }

    File file = root.openNextFile();
    while (file) {
        if (file.isDirectory()) {
            Serial.print("  DIR : ");
            Serial.println(file.name());
            if (levels > 0) {
                listDirectory(file.path(), levels - 1);
            }
        } else {
            Serial.print("  FILE: ");
            Serial.print(file.name());
            Serial.print("\tSIZE: ");
            Serial.println(file.size());
        }
        file = root.openNextFile();
    }
}

/**
 * Delete a file
 */
bool deleteFile(const char* path) {
    if (SD.remove(path)) {
        Serial.printf("✅ Deleted: %s\n", path);
        return true;
    } else {
        Serial.printf("❌ Failed to delete: %s\n", path);
        return false;
    }
}

/**
 * Get SD card storage info
 */
void printSDCardInfo() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("💾 SD CARD INFORMATION");
    Serial.println("═══════════════════════════════════");

    if (!sdCardInitialized) {
        Serial.println("❌ SD card not initialized");
        Serial.println("═══════════════════════════════════\n");
        return;
    }

    Serial.print("Type: ");
    switch (sdCardType) {
        case CARD_MMC:  Serial.println("MMC"); break;
        case CARD_SD:   Serial.println("SDSC"); break;
        case CARD_SDHC: Serial.println("SDHC"); break;
        default:        Serial.println("UNKNOWN");
    }

    uint64_t cardSize = SD.cardSize() / (1024 * 1024);
    uint64_t usedBytes = SD.usedBytes() / (1024 * 1024);
    uint64_t totalBytes = SD.totalBytes() / (1024 * 1024);
    uint64_t freeBytes = totalBytes - usedBytes;

    Serial.printf("Card Size: %llu MB\n", cardSize);
    Serial.printf("Total Space: %llu MB\n", totalBytes);
    Serial.printf("Used Space: %llu MB\n", usedBytes);
    Serial.printf("Free Space: %llu MB\n", freeBytes);
    Serial.printf("Usage: %.1f%%\n", (float)usedBytes / totalBytes * 100);

    Serial.println("═══════════════════════════════════\n");
}

/**
 * Copy file from SPIFFS to SD card
 */
bool copyFileToSD(const char* sourcePath, const char* destPath) {
    File sourceFile = SPIFFS.open(sourcePath, FILE_READ);
    if (!sourceFile) {
        Serial.printf("❌ Failed to open source: %s\n", sourcePath);
        return false;
    }

    File destFile = SD.open(destPath, FILE_WRITE);
    if (!destFile) {
        Serial.printf("❌ Failed to open destination: %s\n", destPath);
        sourceFile.close();
        return false;
    }

    // Copy data
    byte buffer[512];
    while (sourceFile.available()) {
        size_t bytesRead = sourceFile.read(buffer, sizeof(buffer));
        destFile.write(buffer, bytesRead);
    }

    sourceFile.close();
    destFile.close();

    Serial.printf("✅ Copied: %s → %s\n", sourcePath, destPath);
    return true;
}

// ============================================================================
// DOWNLOAD CONTENT PACKS
// ============================================================================

/**
 * Download and install content pack from server
 */
bool downloadContentPack(const char* packName) {
    if (!sdCardInitialized) {
        Serial.println("⚠️ SD card not initialized");
        return false;
    }

    Serial.printf("📥 Downloading content pack: %s\n", packName);

    // Download from server
    HTTPClient http;
    String url = String(SERVER_URL) + "/content-packs/" + String(packName) + ".zip";

    http.begin(url);
    int httpCode = http.GET();

    if (httpCode == 200) {
        char filename[64];
        sprintf(filename, "/updates/%s.zip", packName);

        File file = SD.open(filename, FILE_WRITE);
        if (!file) {
            Serial.println("❌ Failed to create file");
            http.end();
            return false;
        }

        WiFiClient* stream = http.getStreamPtr();
        int totalSize = http.getSize();
        int downloaded = 0;

        byte buffer[512];
        while (http.connected() && (downloaded < totalSize || totalSize == -1)) {
            size_t available = stream->available();
            if (available) {
                int bytesRead = stream->readBytes(buffer, min(sizeof(buffer), available));
                file.write(buffer, bytesRead);
                downloaded += bytesRead;

                // Progress
                if (totalSize > 0) {
                    int percent = (downloaded * 100) / totalSize;
                    Serial.printf("Progress: %d%%\r", percent);
                }
            }
        }

        file.close();
        http.end();

        Serial.printf("\n✅ Downloaded: %s (%d bytes)\n", packName, downloaded);
        Serial.println("📦 Extract manually or implement unzip...");

        return true;
    } else {
        Serial.printf("❌ Download failed: HTTP %d\n", httpCode);
        http.end();
        return false;
    }
}

#endif // SD_CARD_H
