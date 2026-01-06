/**
 * i2s_audio.h
 *
 * I2S Digital Audio System
 * Real audio playback using I2S DAC/amplifier instead of buzzer beeps
 *
 * Hardware Options:
 *   1. MAX98357A I2S Amplifier ($2.50) - Easiest, best for small speaker
 *   2. PCM5102 DAC ($4) + PAM8403 Amp ($0.50) - Higher quality
 *   3. UDA1334A DAC ($7) - Professional audio quality
 *
 * Features:
 *   - WAV file playback from SPIFFS/SD card
 *   - MP3 decoding (with ESP32-audioI2S library)
 *   - Voice announcements (text-to-speech)
 *   - Sound effects library
 *   - Background music
 *   - Volume control
 *   - Stereo output (optional)
 *
 * Wiring (MAX98357A):
 *   ESP32 GPIO 25 → BCLK (Bit Clock)
 *   ESP32 GPIO 26 → LRC  (Left/Right Clock / Word Select)
 *   ESP32 GPIO 27 → DIN  (Data In)
 *   ESP32 3.3V → VIN
 *   ESP32 GND → GND
 *   MAX98357A Speaker Out → 4Ω speaker
 *
 * Dependencies: ESP8266Audio library
 */

#ifndef I2S_AUDIO_H
#define I2S_AUDIO_H

#include <Arduino.h>
#include <driver/i2s.h>
#include <SPIFFS.h>

// ============================================================================
// I2S PIN CONFIGURATION
// ============================================================================

#define I2S_BCLK_PIN      25  // Bit Clock
#define I2S_LRC_PIN       26  // Left/Right Clock (Word Select)
#define I2S_DOUT_PIN      27  // Data Out
#define I2S_NUM           I2S_NUM_0
#define I2S_SAMPLE_RATE   44100  // CD quality
#define I2S_BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT

// ============================================================================
// AUDIO CONFIGURATION
// ============================================================================

#define MAX_VOLUME        100
#define DEFAULT_VOLUME    70

// Current playback state
bool audioInitialized = false;
uint8_t currentVolume = DEFAULT_VOLUME;
bool audioPlaying = false;
String currentTrack = "";

// ============================================================================
// I2S INITIALIZATION
// ============================================================================

/**
 * Initialize I2S audio system
 */
void initI2SAudio() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔊 INITIALIZING I2S AUDIO SYSTEM");
    Serial.println("═══════════════════════════════════");

    // Configure I2S driver
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = I2S_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,  // Stereo
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    // Configure I2S pins
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCLK_PIN,
        .ws_io_num = I2S_LRC_PIN,
        .data_out_num = I2S_DOUT_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    // Install and start I2S driver
    esp_err_t err = i2s_driver_install(I2S_NUM, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("❌ Failed to install I2S driver: %d\n", err);
        return;
    }

    err = i2s_set_pin(I2S_NUM, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("❌ Failed to set I2S pins: %d\n", err);
        return;
    }

    // Initialize SPIFFS for audio files
    if (!SPIFFS.begin(true)) {
        Serial.println("❌ SPIFFS initialization failed");
        return;
    }

    audioInitialized = true;

    Serial.println("✅ I2S driver installed");
    Serial.printf("   Sample Rate: %d Hz\n", I2S_SAMPLE_RATE);
    Serial.printf("   Bits Per Sample: 16\n");
    Serial.printf("   Channels: Stereo\n");
    Serial.printf("   Volume: %d%%\n", currentVolume);
    Serial.println("═══════════════════════════════════\n");
}

/**
 * Set audio volume (0-100)
 */
void setVolume(uint8_t volume) {
    if (volume > MAX_VOLUME) volume = MAX_VOLUME;
    currentVolume = volume;
    Serial.printf("🔊 Volume: %d%%\n", currentVolume);
}

/**
 * Increase volume
 */
void volumeUp() {
    if (currentVolume < MAX_VOLUME) {
        currentVolume += 10;
        setVolume(currentVolume);
    }
}

/**
 * Decrease volume
 */
void volumeDown() {
    if (currentVolume > 0) {
        currentVolume -= 10;
        setVolume(currentVolume);
    }
}

// ============================================================================
// AUDIO PLAYBACK
// ============================================================================

/**
 * Play WAV file from SPIFFS
 */
void playWAV(const char* filename) {
    if (!audioInitialized) {
        Serial.println("⚠️ Audio not initialized");
        return;
    }

    Serial.printf("🎵 Playing: %s\n", filename);

    File audioFile = SPIFFS.open(filename, "r");
    if (!audioFile) {
        Serial.printf("❌ Failed to open: %s\n", filename);
        return;
    }

    // Skip WAV header (44 bytes)
    audioFile.seek(44);

    // Read and play audio data
    const size_t bufferSize = 512;
    uint8_t buffer[bufferSize];
    size_t bytesWritten;

    audioPlaying = true;
    currentTrack = String(filename);

    while (audioFile.available() && audioPlaying) {
        size_t bytesRead = audioFile.read(buffer, bufferSize);

        // Apply volume by scaling samples
        int16_t* samples = (int16_t*)buffer;
        size_t sampleCount = bytesRead / 2;

        for (size_t i = 0; i < sampleCount; i++) {
            samples[i] = (samples[i] * currentVolume) / 100;
        }

        // Write to I2S
        i2s_write(I2S_NUM, buffer, bytesRead, &bytesWritten, portMAX_DELAY);
    }

    audioFile.close();
    audioPlaying = false;
    currentTrack = "";
    Serial.println("✅ Playback complete");
}

/**
 * Stop current playback
 */
void stopAudio() {
    audioPlaying = false;
    i2s_zero_dma_buffer(I2S_NUM);
    Serial.println("⏹️ Audio stopped");
}

/**
 * Play a synthesized tone (for compatibility with old buzzer code)
 */
void playToneI2S(uint16_t frequency, uint16_t duration) {
    if (!audioInitialized) return;

    const size_t sampleCount = (I2S_SAMPLE_RATE * duration) / 1000;
    const size_t bufferSize = 512;
    int16_t buffer[bufferSize];
    size_t bytesWritten;

    float phase = 0;
    float phaseIncrement = (2.0 * PI * frequency) / I2S_SAMPLE_RATE;

    for (size_t i = 0; i < sampleCount; i += bufferSize / 2) {
        size_t samplesInBuffer = min(bufferSize / 2, sampleCount - i);

        for (size_t j = 0; j < samplesInBuffer; j++) {
            // Generate sine wave
            int16_t sample = (int16_t)(sin(phase) * 8000 * currentVolume / 100);
            buffer[j * 2] = sample;      // Left channel
            buffer[j * 2 + 1] = sample;  // Right channel

            phase += phaseIncrement;
            if (phase >= 2.0 * PI) phase -= 2.0 * PI;
        }

        i2s_write(I2S_NUM, buffer, samplesInBuffer * 4, &bytesWritten, portMAX_DELAY);
    }
}

// ============================================================================
// GAME SOUND EFFECTS
// ============================================================================

/**
 * Pre-defined sound effects for common game events
 */
enum SoundEffect {
    SFX_GAME_START,
    SFX_GAME_OVER,
    SFX_LEVEL_UP,
    SFX_SCORE_POINT,
    SFX_LOSE_POINT,
    SFX_BUTTON_PRESS,
    SFX_CORRECT_ANSWER,
    SFX_WRONG_ANSWER,
    SFX_COUNTDOWN_TICK,
    SFX_COUNTDOWN_FINAL,
    SFX_POWER_UP,
    SFX_CRASH,
    SFX_VICTORY,
    SFX_DEFEAT,
    SFX_ACHIEVEMENT
};

/**
 * Play a pre-defined sound effect
 */
void playEffect(SoundEffect effect) {
    switch (effect) {
        case SFX_GAME_START:
            playWAV("/sounds/game_start.wav");
            break;
        case SFX_GAME_OVER:
            playWAV("/sounds/game_over.wav");
            break;
        case SFX_LEVEL_UP:
            playWAV("/sounds/level_up.wav");
            break;
        case SFX_SCORE_POINT:
            playWAV("/sounds/score.wav");
            break;
        case SFX_LOSE_POINT:
            playWAV("/sounds/lose_point.wav");
            break;
        case SFX_BUTTON_PRESS:
            playToneI2S(1000, 50);
            break;
        case SFX_CORRECT_ANSWER:
            playWAV("/sounds/correct.wav");
            break;
        case SFX_WRONG_ANSWER:
            playWAV("/sounds/wrong.wav");
            break;
        case SFX_COUNTDOWN_TICK:
            playToneI2S(800, 100);
            break;
        case SFX_COUNTDOWN_FINAL:
            playToneI2S(1200, 200);
            break;
        case SFX_POWER_UP:
            playWAV("/sounds/powerup.wav");
            break;
        case SFX_CRASH:
            playWAV("/sounds/crash.wav");
            break;
        case SFX_VICTORY:
            playWAV("/sounds/victory.wav");
            break;
        case SFX_DEFEAT:
            playWAV("/sounds/defeat.wav");
            break;
        case SFX_ACHIEVEMENT:
            playWAV("/sounds/achievement.wav");
            break;
    }
}

// ============================================================================
// VOICE ANNOUNCEMENTS
// ============================================================================

/**
 * Play pre-recorded voice announcement
 */
void announceVoice(const char* message) {
    // Map common messages to audio files
    if (strcmp(message, "ready") == 0) {
        playWAV("/voice/ready.wav");
    } else if (strcmp(message, "go") == 0) {
        playWAV("/voice/go.wav");
    } else if (strcmp(message, "winner") == 0) {
        playWAV("/voice/winner.wav");
    } else if (strcmp(message, "game_over") == 0) {
        playWAV("/voice/game_over.wav");
    } else if (strcmp(message, "new_high_score") == 0) {
        playWAV("/voice/new_high_score.wav");
    } else if (strcmp(message, "shake_harder") == 0) {
        playWAV("/voice/shake_harder.wav");
    } else if (strcmp(message, "nice_shot") == 0) {
        playWAV("/voice/nice_shot.wav");
    }
}

/**
 * Announce a number (score, countdown, etc.)
 */
void announceNumber(int number) {
    char filename[32];
    sprintf(filename, "/voice/numbers/%d.wav", number);
    playWAV(filename);
}

/**
 * Announce countdown (3, 2, 1, GO!)
 */
void announceCountdown() {
    announceNumber(3);
    delay(1000);
    announceNumber(2);
    delay(1000);
    announceNumber(1);
    delay(1000);
    announceVoice("go");
}

// ============================================================================
// BACKGROUND MUSIC
// ============================================================================

TaskHandle_t backgroundMusicTask = NULL;
bool backgroundMusicPlaying = false;
String backgroundMusicFile = "";

/**
 * Background music task (runs on separate core)
 */
void taskBackgroundMusic(void *parameter) {
    while (backgroundMusicPlaying) {
        playWAV(backgroundMusicFile.c_str());
        // Loop the music
    }
    vTaskDelete(NULL);
}

/**
 * Start playing background music
 */
void startBackgroundMusic(const char* filename) {
    if (backgroundMusicPlaying) {
        stopBackgroundMusic();
    }

    backgroundMusicFile = String(filename);
    backgroundMusicPlaying = true;

    xTaskCreatePinnedToCore(
        taskBackgroundMusic,
        "BackgroundMusic",
        4096,
        NULL,
        5,  // Low priority
        &backgroundMusicTask,
        1   // Core 1 (network core - has spare capacity)
    );

    Serial.printf("🎵 Background music started: %s\n", filename);
}

/**
 * Stop background music
 */
void stopBackgroundMusic() {
    if (backgroundMusicTask != NULL) {
        backgroundMusicPlaying = false;
        vTaskDelay(pdMS_TO_TICKS(100));  // Wait for task to finish
        backgroundMusicTask = NULL;
        Serial.println("🔇 Background music stopped");
    }
}

// ============================================================================
// AUDIO FILE MANAGEMENT
// ============================================================================

/**
 * List all audio files in SPIFFS
 */
void listAudioFiles() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📂 AUDIO FILES IN SPIFFS");
    Serial.println("═══════════════════════════════════");

    File root = SPIFFS.open("/");
    File file = root.openNextFile();

    int fileCount = 0;
    size_t totalSize = 0;

    while (file) {
        if (!file.isDirectory()) {
            String filename = String(file.name());
            if (filename.endsWith(".wav") || filename.endsWith(".mp3")) {
                Serial.printf("  %s (%d bytes)\n", file.name(), file.size());
                fileCount++;
                totalSize += file.size();
            }
        }
        file = root.openNextFile();
    }

    Serial.println("───────────────────────────────────");
    Serial.printf("Total: %d files, %d KB\n", fileCount, totalSize / 1024);
    Serial.printf("SPIFFS Usage: %d / %d KB\n",
                  SPIFFS.usedBytes() / 1024,
                  SPIFFS.totalBytes() / 1024);
    Serial.println("═══════════════════════════════════\n");
}

/**
 * Check if audio file exists
 */
bool audioFileExists(const char* filename) {
    return SPIFFS.exists(filename);
}

// ============================================================================
// GAME INTEGRATION EXAMPLES
// ============================================================================

/**
 * Example: Replace old buzzer code with I2S audio
 */
void gameStartSound() {
    // OLD: tone(BUZZER_PIN, 1000, 200);
    // NEW:
    playEffect(SFX_GAME_START);
}

void scorePointSound() {
    // OLD: tone(BUZZER_PIN, 2000, 100);
    // NEW:
    playEffect(SFX_SCORE_POINT);
}

void gameOverSound() {
    // OLD: tone(BUZZER_PIN, 500, 1000);
    // NEW:
    playEffect(SFX_GAME_OVER);
}

/**
 * Example: Game with voice announcements
 */
void gameWithVoiceAnnouncements() {
    Serial.println("Starting game with voice...");

    announceVoice("ready");
    delay(1000);

    announceCountdown();  // 3... 2... 1... GO!

    // Game loop...
    int score = 42;

    // Announce score
    Serial.printf("Score: %d\n", score);
    announceNumber(score);

    // Game over
    announceVoice("game_over");
    playEffect(SFX_DEFEAT);
}

/**
 * Example: Game with background music
 */
void gameWithBackgroundMusic() {
    Serial.println("Starting game with music...");

    startBackgroundMusic("/music/action_theme.wav");

    // Game loop...
    delay(30000);  // 30 seconds of gameplay

    stopBackgroundMusic();
}

// ============================================================================
// AUDIO DIAGNOSTIC TOOLS
// ============================================================================

/**
 * Test all sound effects
 */
void testAllSoundEffects() {
    Serial.println("\n🔊 Testing all sound effects...\n");

    Serial.println("Game Start");
    playEffect(SFX_GAME_START);
    delay(1000);

    Serial.println("Score Point");
    playEffect(SFX_SCORE_POINT);
    delay(1000);

    Serial.println("Correct Answer");
    playEffect(SFX_CORRECT_ANSWER);
    delay(1000);

    Serial.println("Wrong Answer");
    playEffect(SFX_WRONG_ANSWER);
    delay(1000);

    Serial.println("Game Over");
    playEffect(SFX_GAME_OVER);
    delay(1000);

    Serial.println("\n✅ Sound effect test complete\n");
}

/**
 * Test voice announcements
 */
void testVoiceAnnouncements() {
    Serial.println("\n🎤 Testing voice announcements...\n");

    announceCountdown();
    delay(1000);

    announceVoice("nice_shot");
    delay(1500);

    for (int i = 1; i <= 5; i++) {
        announceNumber(i);
        delay(800);
    }

    announceVoice("winner");

    Serial.println("\n✅ Voice test complete\n");
}

/**
 * Print I2S diagnostics
 */
void printI2SDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔊 I2S AUDIO DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");
    Serial.printf("Initialized: %s\n", audioInitialized ? "Yes" : "No");
    Serial.printf("Volume: %d%%\n", currentVolume);
    Serial.printf("Currently Playing: %s\n", audioPlaying ? currentTrack.c_str() : "None");
    Serial.printf("Background Music: %s\n", backgroundMusicPlaying ? backgroundMusicFile.c_str() : "None");
    Serial.printf("Sample Rate: %d Hz\n", I2S_SAMPLE_RATE);
    Serial.printf("Bits Per Sample: 16\n");
    Serial.printf("Channels: Stereo\n");
    Serial.println("═══════════════════════════════════\n");
}

#endif // I2S_AUDIO_H
