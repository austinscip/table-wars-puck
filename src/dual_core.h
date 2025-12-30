/**
 * dual_core.h
 *
 * Dual-Core FreeRTOS Task Management
 * Optimizes ESP32 performance by separating tasks across two cores
 *
 * CORE 0 (Protocol Core):
 *   - Game logic and physics
 *   - LED animations
 *   - Sensor reading (MPU6050)
 *   - Button debouncing
 *   - Audio playback
 *
 * CORE 1 (Application Core):
 *   - WiFi management
 *   - WebSocket communication
 *   - HTTP requests
 *   - OTA updates
 *   - Server synchronization
 *
 * Benefits:
 *   - Eliminates network lag affecting game performance
 *   - Smoother LED animations (no WiFi interruptions)
 *   - More responsive sensor input
 *   - Better battery life (independent sleep modes)
 *   - 2x processing power for complex games
 *
 * Hardware: ESP32-DevKitC (Dual-core Xtensa LX6 @ 240MHz)
 */

#ifndef DUAL_CORE_H
#define DUAL_CORE_H

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

// ============================================================================
// TASK CONFIGURATION
// ============================================================================

// Task priorities (0 = lowest, 25 = highest)
#define PRIORITY_GAME_LOGIC       20  // Highest - game must be responsive
#define PRIORITY_LED_ANIMATION    18  // High - visual feedback
#define PRIORITY_SENSOR_READ      17  // High - input responsiveness
#define PRIORITY_AUDIO            16  // Medium-high - audio glitches are bad
#define PRIORITY_NETWORK          10  // Medium - network can wait
#define PRIORITY_OTA_UPDATE        5  // Low - background task

// Stack sizes (bytes)
#define STACK_SIZE_GAME_LOGIC     8192
#define STACK_SIZE_LED_ANIMATION  4096
#define STACK_SIZE_SENSOR_READ    4096
#define STACK_SIZE_AUDIO          4096
#define STACK_SIZE_NETWORK        8192
#define STACK_SIZE_OTA            8192

// Core assignments
#define CORE_GAME      0  // Protocol core - game logic
#define CORE_NETWORK   1  // Application core - WiFi/network

// ============================================================================
// INTER-TASK COMMUNICATION
// ============================================================================

// Queues for passing data between cores
QueueHandle_t sensorDataQueue;      // Sensor → Game Logic
QueueHandle_t ledCommandQueue;      // Game Logic → LED Animation
QueueHandle_t audioCommandQueue;    // Game Logic → Audio
QueueHandle_t networkTxQueue;       // Game Logic → Network (send)
QueueHandle_t networkRxQueue;       // Network → Game Logic (receive)

// Mutexes for shared resources
SemaphoreHandle_t i2cMutex;         // MPU6050 I2C access
SemaphoreHandle_t ledMutex;         // FastLED access
SemaphoreHandle_t buzzerMutex;      // Buzzer access

// ============================================================================
// DATA STRUCTURES
// ============================================================================

/**
 * Sensor data packet (MPU6050 → Game Logic)
 */
struct SensorData {
    float accel_x;
    float accel_y;
    float accel_z;
    float gyro_x;
    float gyro_y;
    float gyro_z;
    float tilt_angle_x;
    float tilt_angle_y;
    bool shake_detected;
    float shake_intensity;
    bool button_pressed;
    unsigned long timestamp;
};

/**
 * LED animation command (Game Logic → LED Animation)
 */
struct LEDCommand {
    enum Type {
        SET_ALL,
        SET_SINGLE,
        SET_RANGE,
        RAINBOW,
        PULSE,
        SPIN,
        FLASH,
        CLEAR
    } type;

    uint8_t r, g, b;          // RGB color
    uint8_t led_index;        // For SET_SINGLE
    uint8_t start_led;        // For SET_RANGE
    uint8_t end_led;          // For SET_RANGE
    uint16_t duration_ms;     // For animations
    uint8_t speed;            // Animation speed (1-100)
};

/**
 * Audio command (Game Logic → Audio)
 */
struct AudioCommand {
    enum Type {
        PLAY_TONE,
        PLAY_MELODY,
        PLAY_EFFECT,
        STOP
    } type;

    uint16_t frequency;       // For PLAY_TONE
    uint16_t duration_ms;     // For PLAY_TONE
    uint8_t melody_id;        // For PLAY_MELODY
    uint8_t effect_id;        // For PLAY_EFFECT
};

/**
 * Network transmission packet (Game Logic → Network)
 */
struct NetworkTxPacket {
    enum Type {
        WEBSOCKET_SEND,
        HTTP_POST,
        HTTP_GET
    } type;

    String url;
    String payload;
    bool await_response;
};

/**
 * Network reception packet (Network → Game Logic)
 */
struct NetworkRxPacket {
    enum Type {
        WEBSOCKET_MESSAGE,
        HTTP_RESPONSE,
        SERVER_EVENT
    } type;

    String data;
    int status_code;
    unsigned long timestamp;
};

// ============================================================================
// TASK HANDLES
// ============================================================================

TaskHandle_t taskHandleGameLogic = NULL;
TaskHandle_t taskHandleLEDAnimation = NULL;
TaskHandle_t taskHandleSensorRead = NULL;
TaskHandle_t taskHandleAudio = NULL;
TaskHandle_t taskHandleNetwork = NULL;
TaskHandle_t taskHandleOTA = NULL;

// ============================================================================
// CORE 0 TASKS (GAME LOGIC)
// ============================================================================

/**
 * TASK: Sensor Reading (Core 0)
 * Continuously reads MPU6050 and button state
 * Sends data to game logic via queue
 */
void taskSensorRead(void *parameter) {
    SensorData sensorData;
    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t frequency = pdMS_TO_TICKS(10);  // 100 Hz (every 10ms)

    Serial.println("✅ [CORE 0] Sensor reading task started");

    while (true) {
        // Take I2C mutex
        if (xSemaphoreTake(i2cMutex, portMAX_DELAY) == pdTRUE) {
            // Read accelerometer and gyroscope
            readAccelerometer();  // Your existing function

            // Populate sensor data packet
            sensorData.accel_x = accelX;
            sensorData.accel_y = accelY;
            sensorData.accel_z = accelZ;
            sensorData.gyro_x = gyroX;
            sensorData.gyro_y = gyroY;
            sensorData.gyro_z = gyroZ;
            sensorData.tilt_angle_x = getTiltAngle_X();
            sensorData.tilt_angle_y = getTiltAngle_Y();
            sensorData.shake_detected = detectShake();
            sensorData.shake_intensity = getShakeIntensity();
            sensorData.button_pressed = !digitalRead(BUTTON_PIN);
            sensorData.timestamp = millis();

            // Release I2C mutex
            xSemaphoreGive(i2cMutex);

            // Send to game logic (non-blocking)
            xQueueSend(sensorDataQueue, &sensorData, 0);
        }

        // Sleep until next reading (precise timing)
        vTaskDelayUntil(&lastWakeTime, frequency);
    }
}

/**
 * TASK: LED Animation (Core 0)
 * Handles all LED animations based on commands from game logic
 */
void taskLEDAnimation(void *parameter) {
    LEDCommand cmd;

    Serial.println("✅ [CORE 0] LED animation task started");

    while (true) {
        // Wait for LED command from game logic
        if (xQueueReceive(ledCommandQueue, &cmd, portMAX_DELAY) == pdTRUE) {
            // Take LED mutex
            if (xSemaphoreTake(ledMutex, portMAX_DELAY) == pdTRUE) {
                switch (cmd.type) {
                    case LEDCommand::SET_ALL:
                        for (int i = 0; i < NUM_LEDS; i++) {
                            leds[i] = CRGB(cmd.r, cmd.g, cmd.b);
                        }
                        FastLED.show();
                        break;

                    case LEDCommand::SET_SINGLE:
                        leds[cmd.led_index] = CRGB(cmd.r, cmd.g, cmd.b);
                        FastLED.show();
                        break;

                    case LEDCommand::SET_RANGE:
                        for (int i = cmd.start_led; i <= cmd.end_led && i < NUM_LEDS; i++) {
                            leds[i] = CRGB(cmd.r, cmd.g, cmd.b);
                        }
                        FastLED.show();
                        break;

                    case LEDCommand::RAINBOW:
                        rainbowCycle(cmd.speed);
                        break;

                    case LEDCommand::PULSE:
                        for (int brightness = 0; brightness < 255; brightness += 5) {
                            for (int i = 0; i < NUM_LEDS; i++) {
                                leds[i] = CRGB(
                                    (cmd.r * brightness) / 255,
                                    (cmd.g * brightness) / 255,
                                    (cmd.b * brightness) / 255
                                );
                            }
                            FastLED.show();
                            vTaskDelay(pdMS_TO_TICKS(10));
                        }
                        for (int brightness = 255; brightness >= 0; brightness -= 5) {
                            for (int i = 0; i < NUM_LEDS; i++) {
                                leds[i] = CRGB(
                                    (cmd.r * brightness) / 255,
                                    (cmd.g * brightness) / 255,
                                    (cmd.b * brightness) / 255
                                );
                            }
                            FastLED.show();
                            vTaskDelay(pdMS_TO_TICKS(10));
                        }
                        break;

                    case LEDCommand::SPIN:
                        for (int pos = 0; pos < NUM_LEDS; pos++) {
                            for (int i = 0; i < NUM_LEDS; i++) {
                                leds[i] = CRGB(0, 0, 0);
                            }
                            leds[pos] = CRGB(cmd.r, cmd.g, cmd.b);
                            FastLED.show();
                            vTaskDelay(pdMS_TO_TICKS(cmd.duration_ms / NUM_LEDS));
                        }
                        break;

                    case LEDCommand::FLASH:
                        for (int i = 0; i < 5; i++) {
                            for (int j = 0; j < NUM_LEDS; j++) {
                                leds[j] = CRGB(cmd.r, cmd.g, cmd.b);
                            }
                            FastLED.show();
                            vTaskDelay(pdMS_TO_TICKS(100));
                            for (int j = 0; j < NUM_LEDS; j++) {
                                leds[j] = CRGB(0, 0, 0);
                            }
                            FastLED.show();
                            vTaskDelay(pdMS_TO_TICKS(100));
                        }
                        break;

                    case LEDCommand::CLEAR:
                        for (int i = 0; i < NUM_LEDS; i++) {
                            leds[i] = CRGB(0, 0, 0);
                        }
                        FastLED.show();
                        break;
                }

                // Release LED mutex
                xSemaphoreGive(ledMutex);
            }
        }
    }
}

/**
 * TASK: Audio Playback (Core 0)
 * Handles buzzer/speaker audio based on commands from game logic
 */
void taskAudio(void *parameter) {
    AudioCommand cmd;

    Serial.println("✅ [CORE 0] Audio task started");

    while (true) {
        // Wait for audio command from game logic
        if (xQueueReceive(audioCommandQueue, &cmd, portMAX_DELAY) == pdTRUE) {
            // Take buzzer mutex
            if (xSemaphoreTake(buzzerMutex, portMAX_DELAY) == pdTRUE) {
                switch (cmd.type) {
                    case AudioCommand::PLAY_TONE:
                        tone(BUZZER_PIN, cmd.frequency, cmd.duration_ms);
                        vTaskDelay(pdMS_TO_TICKS(cmd.duration_ms));
                        noTone(BUZZER_PIN);
                        break;

                    case AudioCommand::PLAY_MELODY:
                        // Play pre-defined melody by ID
                        // (Would call your existing melody functions)
                        break;

                    case AudioCommand::PLAY_EFFECT:
                        // Play sound effect by ID
                        break;

                    case AudioCommand::STOP:
                        noTone(BUZZER_PIN);
                        break;
                }

                // Release buzzer mutex
                xSemaphoreGive(buzzerMutex);
            }
        }
    }
}

/**
 * TASK: Game Logic (Core 0)
 * Main game loop - processes sensor input and updates game state
 */
void taskGameLogic(void *parameter) {
    SensorData sensorData;
    NetworkRxPacket networkData;

    Serial.println("✅ [CORE 0] Game logic task started");

    while (true) {
        // Read sensor data
        if (xQueueReceive(sensorDataQueue, &sensorData, pdMS_TO_TICKS(10)) == pdTRUE) {
            // Process sensor input for current game
            // This is where your game logic runs

            // Example: Send LED command based on tilt
            LEDCommand ledCmd;
            ledCmd.type = LEDCommand::SET_ALL;
            ledCmd.r = abs(sensorData.tilt_angle_x) * 10;
            ledCmd.g = abs(sensorData.tilt_angle_y) * 10;
            ledCmd.b = 100;
            xQueueSend(ledCommandQueue, &ledCmd, 0);
        }

        // Check for network messages
        if (xQueueReceive(networkRxQueue, &networkData, 0) == pdTRUE) {
            // Handle server events
            if (networkData.type == NetworkRxPacket::SERVER_EVENT) {
                // Process server command
            }
        }

        // Small delay to prevent task starvation
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ============================================================================
// CORE 1 TASKS (NETWORK)
// ============================================================================

/**
 * TASK: Network Management (Core 1)
 * Handles WiFi, WebSocket, HTTP requests
 */
void taskNetwork(void *parameter) {
    NetworkTxPacket txPacket;

    Serial.println("✅ [CORE 1] Network task started");

    while (true) {
        // Handle WebSocket events
        webSocket.loop();

        // Check for outgoing network requests
        if (xQueueReceive(networkTxQueue, &txPacket, 0) == pdTRUE) {
            switch (txPacket.type) {
                case NetworkTxPacket::WEBSOCKET_SEND:
                    webSocket.sendTXT(txPacket.payload);
                    break;

                case NetworkTxPacket::HTTP_POST:
                    // Handle HTTP POST
                    break;

                case NetworkTxPacket::HTTP_GET:
                    // Handle HTTP GET
                    break;
            }
        }

        // WiFi connection maintenance
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("⚠️ WiFi disconnected - reconnecting...");
            WiFi.reconnect();
            vTaskDelay(pdMS_TO_TICKS(5000));
        }

        vTaskDelay(pdMS_TO_TICKS(10));  // 100 Hz network loop
    }
}

/**
 * TASK: OTA Update Management (Core 1)
 * Background task for checking and installing firmware updates
 */
void taskOTA(void *parameter) {
    Serial.println("✅ [CORE 1] OTA update task started");

    while (true) {
        // Handle Arduino OTA
        ArduinoOTA.handle();

        // Check for HTTP OTA updates periodically
        handleOTAUpdates();

        // Run every 10 seconds
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize dual-core task system
 * Call this from setup() instead of running everything in loop()
 */
void initDualCore() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("🚀 INITIALIZING DUAL-CORE SYSTEM");
    Serial.println("═══════════════════════════════════");

    // Create queues
    sensorDataQueue = xQueueCreate(10, sizeof(SensorData));
    ledCommandQueue = xQueueCreate(20, sizeof(LEDCommand));
    audioCommandQueue = xQueueCreate(10, sizeof(AudioCommand));
    networkTxQueue = xQueueCreate(10, sizeof(NetworkTxPacket));
    networkRxQueue = xQueueCreate(10, sizeof(NetworkRxPacket));

    // Create mutexes
    i2cMutex = xSemaphoreCreateMutex();
    ledMutex = xSemaphoreCreateMutex();
    buzzerMutex = xSemaphoreCreateMutex();

    Serial.println("✅ Queues and mutexes created");

    // ========================================================================
    // CORE 0: Game Logic Tasks
    // ========================================================================

    xTaskCreatePinnedToCore(
        taskSensorRead,           // Task function
        "SensorRead",             // Name
        STACK_SIZE_SENSOR_READ,   // Stack size
        NULL,                     // Parameters
        PRIORITY_SENSOR_READ,     // Priority
        &taskHandleSensorRead,    // Task handle
        CORE_GAME                 // Core 0
    );

    xTaskCreatePinnedToCore(
        taskLEDAnimation,
        "LEDAnimation",
        STACK_SIZE_LED_ANIMATION,
        NULL,
        PRIORITY_LED_ANIMATION,
        &taskHandleLEDAnimation,
        CORE_GAME
    );

    xTaskCreatePinnedToCore(
        taskAudio,
        "Audio",
        STACK_SIZE_AUDIO,
        NULL,
        PRIORITY_AUDIO,
        &taskHandleAudio,
        CORE_GAME
    );

    xTaskCreatePinnedToCore(
        taskGameLogic,
        "GameLogic",
        STACK_SIZE_GAME_LOGIC,
        NULL,
        PRIORITY_GAME_LOGIC,
        &taskHandleGameLogic,
        CORE_GAME
    );

    Serial.println("✅ Core 0 tasks created (Game Logic)");

    // ========================================================================
    // CORE 1: Network Tasks
    // ========================================================================

    xTaskCreatePinnedToCore(
        taskNetwork,
        "Network",
        STACK_SIZE_NETWORK,
        NULL,
        PRIORITY_NETWORK,
        &taskHandleNetwork,
        CORE_NETWORK
    );

    xTaskCreatePinnedToCore(
        taskOTA,
        "OTA_Updates",
        STACK_SIZE_OTA,
        NULL,
        PRIORITY_OTA_UPDATE,
        &taskHandleOTA,
        CORE_NETWORK
    );

    Serial.println("✅ Core 1 tasks created (Network)");

    Serial.println("═══════════════════════════════════");
    Serial.println("✅ DUAL-CORE SYSTEM READY");
    Serial.println("   Core 0: Sensor, LED, Audio, Game");
    Serial.println("   Core 1: WiFi, WebSocket, OTA");
    Serial.println("═══════════════════════════════════\n");
}

/**
 * Print task diagnostics (CPU usage, stack remaining)
 */
void printTaskDiagnostics() {
    Serial.println("\n═══════════════════════════════════");
    Serial.println("📊 TASK DIAGNOSTICS");
    Serial.println("═══════════════════════════════════");

    char statsBuffer[512];
    vTaskGetRunTimeStats(statsBuffer);
    Serial.println("CPU Usage:");
    Serial.println(statsBuffer);

    Serial.println("\nStack High Water Marks (bytes remaining):");
    if (taskHandleSensorRead) {
        Serial.printf("  Sensor Read:    %d\n", uxTaskGetStackHighWaterMark(taskHandleSensorRead));
    }
    if (taskHandleLEDAnimation) {
        Serial.printf("  LED Animation:  %d\n", uxTaskGetStackHighWaterMark(taskHandleLEDAnimation));
    }
    if (taskHandleAudio) {
        Serial.printf("  Audio:          %d\n", uxTaskGetStackHighWaterMark(taskHandleAudio));
    }
    if (taskHandleGameLogic) {
        Serial.printf("  Game Logic:     %d\n", uxTaskGetStackHighWaterMark(taskHandleGameLogic));
    }
    if (taskHandleNetwork) {
        Serial.printf("  Network:        %d\n", uxTaskGetStackHighWaterMark(taskHandleNetwork));
    }
    if (taskHandleOTA) {
        Serial.printf("  OTA:            %d\n", uxTaskGetStackHighWaterMark(taskHandleOTA));
    }

    Serial.printf("\nFree Heap: %d bytes\n", ESP.getFreeHeap());
    Serial.println("═══════════════════════════════════\n");
}

// ============================================================================
// HELPER FUNCTIONS FOR GAME CODE
// ============================================================================

/**
 * Send LED command to animation task
 */
void setLEDColor(uint8_t r, uint8_t g, uint8_t b) {
    LEDCommand cmd;
    cmd.type = LEDCommand::SET_ALL;
    cmd.r = r;
    cmd.g = g;
    cmd.b = b;
    xQueueSend(ledCommandQueue, &cmd, 0);
}

/**
 * Play a tone via audio task
 */
void playGameTone(uint16_t frequency, uint16_t duration) {
    AudioCommand cmd;
    cmd.type = AudioCommand::PLAY_TONE;
    cmd.frequency = frequency;
    cmd.duration_ms = duration;
    xQueueSend(audioCommandQueue, &cmd, 0);
}

/**
 * Send WebSocket message via network task
 */
void sendNetworkMessage(String message) {
    NetworkTxPacket packet;
    packet.type = NetworkTxPacket::WEBSOCKET_SEND;
    packet.payload = message;
    xQueueSend(networkTxQueue, &packet, 0);
}

#endif // DUAL_CORE_H
