/**
 * bluetooth_audio.h
 *
 * Bluetooth A2DP Audio Streaming
 * Stream music and sound effects to Bluetooth speakers/headphones
 *
 * ESP32 Bluetooth Features:
 *   - Bluetooth Classic v4.2
 *   - Bluetooth Low Energy (BLE)
 *   - A2DP (Advanced Audio Distribution Profile)
 *   - AVRCP (Audio/Video Remote Control Profile)
 *   - HFP (Hands-Free Profile)
 *   - SPP (Serial Port Profile)
 *
 * Use Cases:
 *   1. Stream game audio to bar's sound system via Bluetooth
 *   2. Wireless headphones for quiet play
 *   3. Voice announcements through venue speakers
 *   4. Multi-puck audio sync (all pucks play same music)
 *   5. Audio output without adding speaker hardware to puck
 *
 * Benefits:
 *   - No speaker weight in puck (better for throwing games)
 *   - Better audio quality (use venue's speakers)
 *   - Cheaper (no speaker hardware needed)
 *   - Wireless (no audio cables)
 *   - Multi-device support
 *
 * Dependencies: ESP32-A2DP library
 *   Install: Arduino Library Manager → "ESP32-A2DP"
 */

#ifndef BLUETOOTH_AUDIO_H
#define BLUETOOTH_AUDIO_H

#include <Arduino.h>
#include <BluetoothA2DPSource.h>  // For streaming TO speakers
#include <BluetoothA2DPSink.h>    // For receiving FROM phone

// ============================================================================
// BLUETOOTH CONFIGURATION
// ============================================================================

#define BT_DEVICE_NAME    "TableWarsPuck"
#define BT_PIN_CODE       "1234"

// Audio sample rate
#define BT_SAMPLE_RATE    44100
#define BT_CHANNELS       2  // Stereo

// ============================================================================
// BLUETOOTH OBJECTS
// ============================================================================

BluetoothA2DPSource btSource;  // Stream audio TO Bluetooth speaker
BluetoothA2DPSink   btSink;    // Receive audio FROM phone/tablet

bool bluetoothInitialized = false;
bool bluetoothConnected = false;
String connectedDevice = "";

enum BluetoothMode {
    BT_MODE_SOURCE,  // Puck streams audio to speaker
    BT_MODE_SINK,    // Puck receives audio from phone
    BT_MODE_OFF
};

BluetoothMode currentBTMode = BT_MODE_OFF;

// ============================================================================
// AUDIO GENERATION FOR STREAMING
// ============================================================================

// Tone generator state
struct ToneGenerator {
    float frequency;
    float amplitude;
    float phase;
    bool active;
};

ToneGenerator toneGen = {440.0, 0.5, 0.0, false};

/**
 * Generate audio samples for Bluetooth streaming
 * Called automatically by A2DP library
 */
int32_t bt_audio_data_callback(Frame *frame, int32_t frame_count) {
    if (!toneGen.active) {
        // Silence
        for (int i = 0; i < frame_count; i++) {
            frame[i].channel1 = 0;
            frame[i].channel2 = 0;
        }
        return frame_count;
    }

    // Generate sine wave
    float phaseIncrement = (2.0 * PI * toneGen.frequency) / BT_SAMPLE_RATE;

    for (int i = 0; i < frame_count; i++) {
        int16_t sample = (int16_t)(sin(toneGen.phase) * toneGen.amplitude * 32767);

        frame[i].channel1 = sample;  // Left
        frame[i].channel2 = sample;  // Right

        toneGen.phase += phaseIncrement;
        if (toneGen.phase >= 2.0 * PI) {
            toneGen.phase -= 2.0 * PI;
        }
    }

    return frame_count;
}

// ============================================================================
// BLUETOOTH SOURCE MODE (PUCK → SPEAKER)
// ============================================================================

/**
 * Initialize Bluetooth as audio source (stream TO speaker)
 */
bool initBluetoothSource(const char* deviceName = BT_DEVICE_NAME) {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔵 INITIALIZING BLUETOOTH SOURCE");
    Serial.println("═══════════════════════════════════");

    // Disconnect if already connected in different mode
    if (currentBTMode != BT_MODE_OFF) {
        stopBluetooth();
    }

    btSource.set_auto_reconnect(true);
    btSource.set_ssid_callback(bt_audio_data_callback);

    if (btSource.start(deviceName)) {
        bluetoothInitialized = true;
        currentBTMode = BT_MODE_SOURCE;

        Serial.println("✅ Bluetooth source started");
        Serial.printf("   Device name: %s\n", deviceName);
        Serial.println("   Waiting for speaker connection...");
        Serial.println("   (Pair from speaker's Bluetooth menu)");
        Serial.println("═══════════════════════════════════\n");

        return true;
    } else {
        Serial.println("❌ Failed to start Bluetooth source");
        Serial.println("═══════════════════════════════════\n");
        return false;
    }
}

/**
 * Connect to a specific Bluetooth speaker
 */
bool connectToSpeaker(const char* speakerAddress) {
    if (currentBTMode != BT_MODE_SOURCE) {
        Serial.println("⚠️ Not in source mode");
        return false;
    }

    Serial.printf("🔗 Connecting to speaker: %s\n", speakerAddress);

    if (btSource.connect_to(speakerAddress)) {
        bluetoothConnected = true;
        connectedDevice = String(speakerAddress);
        Serial.println("✅ Connected to speaker");
        return true;
    } else {
        Serial.println("❌ Failed to connect");
        return false;
    }
}

/**
 * Play a tone through Bluetooth speaker
 */
void playBluetoothTone(float frequency, float duration_ms, float amplitude = 0.5) {
    if (!bluetoothConnected || currentBTMode != BT_MODE_SOURCE) {
        Serial.println("⚠️ Bluetooth not connected");
        return;
    }

    Serial.printf("🎵 Playing %d Hz for %d ms\n", (int)frequency, (int)duration_ms);

    toneGen.frequency = frequency;
    toneGen.amplitude = amplitude;
    toneGen.phase = 0;
    toneGen.active = true;

    delay(duration_ms);

    toneGen.active = false;
}

/**
 * Play a melody through Bluetooth
 */
void playBluetoothMelody(int* frequencies, int* durations, int noteCount) {
    for (int i = 0; i < noteCount; i++) {
        playBluetoothTone(frequencies[i], durations[i]);
        delay(50);  // Small gap between notes
    }
}

// ============================================================================
// BLUETOOTH SINK MODE (PHONE → PUCK)
// ============================================================================

/**
 * Audio data received callback (when puck receives audio from phone)
 */
void bt_audio_received(const uint8_t *data, uint32_t length) {
    // Forward received audio to I2S speaker (if connected)
    // Or process audio for visualization on LEDs

    // Example: Visualize audio level on LEDs
    int16_t* samples = (int16_t*)data;
    int sampleCount = length / 2;

    // Calculate average amplitude
    int32_t sum = 0;
    for (int i = 0; i < sampleCount; i++) {
        sum += abs(samples[i]);
    }
    int32_t avgAmplitude = sum / sampleCount;

    // Map to LED brightness
    int brightness = map(avgAmplitude, 0, 32767, 0, 255);

    // Show on LED ring
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CRGB(0, brightness, brightness);
    }
    FastLED.show();
}

/**
 * Initialize Bluetooth as audio sink (receive FROM phone)
 */
bool initBluetoothSink(const char* deviceName = BT_DEVICE_NAME) {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔵 INITIALIZING BLUETOOTH SINK");
    Serial.println("═══════════════════════════════════");

    // Disconnect if already connected in different mode
    if (currentBTMode != BT_MODE_OFF) {
        stopBluetooth();
    }

    btSink.set_auto_reconnect(true);
    btSink.set_stream_reader(bt_audio_received, false);

    if (btSink.start(deviceName)) {
        bluetoothInitialized = true;
        currentBTMode = BT_MODE_SINK;

        Serial.println("✅ Bluetooth sink started");
        Serial.printf("   Device name: %s\n", deviceName);
        Serial.println("   Waiting for phone connection...");
        Serial.println("   (Connect from phone's Bluetooth menu)");
        Serial.println("═══════════════════════════════════\n");

        return true;
    } else {
        Serial.println("❌ Failed to start Bluetooth sink");
        Serial.println("═══════════════════════════════════\n");
        return false;
    }
}

// ============================================================================
// BLUETOOTH CONTROL
// ============================================================================

/**
 * Stop Bluetooth
 */
void stopBluetooth() {
    Serial.println("🔴 Stopping Bluetooth...");

    if (currentBTMode == BT_MODE_SOURCE) {
        btSource.disconnect();
        btSource.end();
    } else if (currentBTMode == BT_MODE_SINK) {
        btSink.disconnect();
        btSink.end();
    }

    bluetoothConnected = false;
    bluetoothInitialized = false;
    currentBTMode = BT_MODE_OFF;
    connectedDevice = "";

    Serial.println("✅ Bluetooth stopped");
}

/**
 * Check if Bluetooth is connected
 */
bool isBluetoothConnected() {
    if (currentBTMode == BT_MODE_SOURCE) {
        return btSource.is_connected();
    } else if (currentBTMode == BT_MODE_SINK) {
        return btSink.is_connected();
    }
    return false;
}

/**
 * Get connection status string
 */
String getBluetoothStatus() {
    if (!bluetoothInitialized) {
        return "Bluetooth OFF";
    }

    String mode = (currentBTMode == BT_MODE_SOURCE) ? "Source" : "Sink";

    if (isBluetoothConnected()) {
        return "Connected (" + mode + ")";
    } else {
        return "Waiting for connection (" + mode + ")";
    }
}

// ============================================================================
// BLUETOOTH DEVICE DISCOVERY
// ============================================================================

/**
 * Scan for nearby Bluetooth devices
 */
void scanBluetoothDevices() {
    Serial.println("\n🔍 SCANNING FOR BLUETOOTH DEVICES");
    Serial.println("═══════════════════════════════════");

    // Note: ESP32 Bluetooth Classic doesn't support scanning while A2DP is active
    // Would need to use BLE scan or stop A2DP first

    Serial.println("To discover devices:");
    Serial.println("1. Put speaker in pairing mode");
    Serial.println("2. Look for 'TableWarsPuck' in speaker's menu");
    Serial.println("3. Or use connectToSpeaker() with known address");
    Serial.println("═══════════════════════════════════\n");
}

// ============================================================================
// GAME INTEGRATION
// ============================================================================

/**
 * Play game start sound via Bluetooth
 */
void bluetoothGameStart() {
    int frequencies[] = {523, 659, 784};  // C, E, G
    int durations[] = {200, 200, 400};
    playBluetoothMelody(frequencies, durations, 3);
}

/**
 * Play game over sound via Bluetooth
 */
void bluetoothGameOver() {
    int frequencies[] = {784, 659, 523, 392};  // G, E, C, A
    int durations[] = {200, 200, 200, 600};
    playBluetoothMelody(frequencies, durations, 4);
}

/**
 * Play score sound via Bluetooth
 */
void bluetoothScorePoint() {
    playBluetoothTone(1000, 100);
}

/**
 * Example: Music visualizer mode
 * Phone plays music → Puck receives → LEDs react to beat
 */
void musicVisualizerMode() {
    Serial.println("🎵 MUSIC VISUALIZER MODE");
    Serial.println("Connect your phone and play music!");

    initBluetoothSink("PuckVisualizer");

    while (true) {
        // Audio visualization happens in bt_audio_received callback
        // LEDs will react to music automatically
        delay(10);

        // Exit on button press
        if (digitalRead(BUTTON_PIN) == LOW) {
            break;
        }
    }

    stopBluetooth();
}

/**
 * Example: Wireless speaker mode for games
 */
void wirelessSpeakerGameMode() {
    Serial.println("🔊 WIRELESS SPEAKER MODE");

    // Connect to bar's Bluetooth speaker
    initBluetoothSource("TableWarsPuck_Game");

    Serial.println("Waiting for speaker connection...");
    while (!isBluetoothConnected()) {
        delay(100);
    }

    Serial.println("✅ Connected! Starting game...");

    // Play game with Bluetooth audio
    bluetoothGameStart();

    // Game loop
    for (int i = 0; i < 10; i++) {
        Serial.printf("Round %d\n", i + 1);
        delay(2000);
        bluetoothScorePoint();
    }

    bluetoothGameOver();
    stopBluetooth();
}

// ============================================================================
// MULTI-PUCK AUDIO SYNC
// ============================================================================

/**
 * Synchronize audio playback across multiple pucks
 * All pucks connect to same speaker and play coordinated sounds
 */
void multiPuckAudioSync() {
    Serial.println("🎮 MULTI-PUCK AUDIO SYNC MODE");

    // Each puck gets a unique channel ID
    int puckChannel = PUCK_ID % 8;

    initBluetoothSource("TableWarsPuck_Multi");

    // Wait for all pucks to connect
    while (!isBluetoothConnected()) {
        delay(100);
    }

    // Synchronized countdown
    for (int i = 3; i > 0; i--) {
        playBluetoothTone(800 + (i * 200), 500);
        delay(1000);
    }

    playBluetoothTone(1500, 1000);  // GO!

    stopBluetooth();
}

// ============================================================================
// DIAGNOSTICS
// ============================================================================

/**
 * Print Bluetooth diagnostics
 */
void printBluetoothDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🔵 BLUETOOTH DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");

    Serial.printf("Initialized: %s\n", bluetoothInitialized ? "Yes" : "No");
    Serial.printf("Mode: ");
    switch (currentBTMode) {
        case BT_MODE_SOURCE: Serial.println("Source (Puck → Speaker)"); break;
        case BT_MODE_SINK:   Serial.println("Sink (Phone → Puck)"); break;
        case BT_MODE_OFF:    Serial.println("OFF"); break;
    }

    Serial.printf("Connected: %s\n", isBluetoothConnected() ? "Yes" : "No");

    if (connectedDevice != "") {
        Serial.printf("Device: %s\n", connectedDevice.c_str());
    }

    Serial.printf("Device Name: %s\n", BT_DEVICE_NAME);
    Serial.printf("Sample Rate: %d Hz\n", BT_SAMPLE_RATE);
    Serial.printf("Channels: %d (Stereo)\n", BT_CHANNELS);

    Serial.println("═══════════════════════════════════\n");
}

/**
 * Test Bluetooth audio with scale
 */
void testBluetoothAudio() {
    Serial.println("\n🎵 BLUETOOTH AUDIO TEST\n");

    if (!bluetoothInitialized) {
        initBluetoothSource();
    }

    Serial.println("Waiting for connection...");
    while (!isBluetoothConnected()) {
        delay(100);
    }

    Serial.println("✅ Connected! Playing musical scale...\n");

    // C major scale
    int frequencies[] = {261, 293, 329, 349, 392, 440, 493, 523};
    const char* notes[] = {"C", "D", "E", "F", "G", "A", "B", "C"};

    for (int i = 0; i < 8; i++) {
        Serial.printf("Note: %s (%d Hz)\n", notes[i], frequencies[i]);
        playBluetoothTone(frequencies[i], 500);
        delay(100);
    }

    Serial.println("\n✅ Test complete\n");
}

// ============================================================================
// POWER MANAGEMENT
// ============================================================================

/**
 * Bluetooth power consumption notes:
 *
 * Bluetooth Classic (A2DP):
 *   - Active streaming: ~100-120 mA
 *   - Connected idle: ~20-30 mA
 *   - Discoverable: ~80-100 mA
 *
 * Bluetooth Low Energy (BLE):
 *   - Active: ~15-20 mA
 *   - Advertising: ~10-15 mA
 *   - Connected idle: ~5-10 mA
 *
 * Power Saving Tips:
 *   1. Use BLE instead of Classic when possible
 *   2. Disconnect when not in use
 *   3. Reduce transmission power if range permits
 *   4. Use WiFi OR Bluetooth, not both (saves 50+ mA)
 */

/**
 * Set Bluetooth transmission power
 * Lower power = less range, but better battery life
 */
void setBluetoothPower(int power) {
    // ESP_PWR_LVL_N12 = -12 dBm (lowest, ~1m range)
    // ESP_PWR_LVL_P9  = +9 dBm (highest, ~10m range)

    // Typical values:
    // ESP_PWR_LVL_N12, ESP_PWR_LVL_N9, ESP_PWR_LVL_N6, ESP_PWR_LVL_N3,
    // ESP_PWR_LVL_N0, ESP_PWR_LVL_P3, ESP_PWR_LVL_P6, ESP_PWR_LVL_P9

    Serial.printf("🔋 Setting Bluetooth power level: %d dBm\n", power);
    esp_bredr_tx_power_set(ESP_PWR_LVL_N0, ESP_PWR_LVL_P9);
}

#endif // BLUETOOTH_AUDIO_H
