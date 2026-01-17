/*
 * TABLE WARS - Buzzer Tune Library & Test
 *
 * Press button to cycle through different game sound effects!
 *
 * Wiring:
 * - Buzzer + (red) → GPIO 15
 * - Buzzer - (black) → GND
 * - Button → GPIO 27 (with internal pullup)
 */

#include <Arduino.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// MPU6050 sensor
Adafruit_MPU6050 mpu;
sensors_event_t accel_event, gyro_event, temp_event;

// Computed sensor values
float shake_intensity = 0;
bool shake_detected = false;
float tilt_x = 0;
float tilt_y = 0;
float gyro_z_raw = 0;
float spin_speed = 0;
const char* spin_direction = "NONE";

// Sprint 0B: Rate limiting for ESP-NOW broadcasts
unsigned long last_send = 0;
const unsigned long SEND_INTERVAL_MS = 200;  // 5 Hz default send rate

// Pin definitions
#define BUZZER_PIN    15
#define BUTTON_PIN    27

// Note frequencies (Hz)
#define NOTE_C4  262
#define NOTE_CS4 277
#define NOTE_D4  294
#define NOTE_DS4 311
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_FS4 370
#define NOTE_G4  392
#define NOTE_GS4 415
#define NOTE_A4  440
#define NOTE_AS4 466
#define NOTE_B4  494
#define NOTE_C5  523
#define NOTE_CS5 554
#define NOTE_D5  587
#define NOTE_DS5 622
#define NOTE_E5  659
#define NOTE_F5  698
#define NOTE_FS5 740
#define NOTE_G5  784
#define NOTE_GS5 831
#define NOTE_A5  880
#define NOTE_AS5 932
#define NOTE_B5  988
#define NOTE_C6  1047
#define NOTE_D6  1175
#define NOTE_E6  1319
#define NOTE_F6  1397
#define NOTE_G6  1568
#define NOTE_A6  1760
#define NOTE_B6  1976
#define NOTE_C7  2093
#define NOTE_D7  2349
#define NOTE_E7  2637
#define REST     0

// Helper function to play a note
void playNote(int frequency, int duration) {
  if (frequency == REST) {
    delay(duration);
  } else {
    tone(BUZZER_PIN, frequency, duration);
    delay(duration * 1.05); // Slight gap between notes
  }
}

// ============================================================================
// 🎮 GAME SOUND EFFECTS
// ============================================================================

// 1. POWER-UP SEQUENCE (Mario-style)
void tune_PowerUp() {
  Serial.println("🔊 Playing: POWER-UP");
  playNote(NOTE_G4, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_G5, 100);
  playNote(NOTE_C6, 100);
  playNote(NOTE_G5, 200);
  playNote(NOTE_C6, 400);
}

// 2. BUTTON PRESS (Short blip)
void tune_ButtonPress() {
  Serial.println("🔊 Playing: BUTTON PRESS");
  playNote(NOTE_E5, 50);
  playNote(NOTE_A5, 50);
}

// 3. BOMB COUNTDOWN (Escalating tension)
void tune_BombTick() {
  Serial.println("🔊 Playing: BOMB TICK");
  playNote(NOTE_C5, 100);
  delay(100);
  playNote(NOTE_C5, 100);
  delay(100);
  playNote(NOTE_C5, 80);
  delay(80);
  playNote(NOTE_C5, 80);
  delay(60);
  playNote(NOTE_C5, 60);
  delay(60);
  playNote(NOTE_C5, 60);
}

// 4. EXPLOSION (Bomb explodes!)
void tune_Explosion() {
  Serial.println("🔊 Playing: EXPLOSION 💥");
  playNote(NOTE_G5, 50);
  playNote(NOTE_F5, 50);
  playNote(NOTE_E5, 50);
  playNote(NOTE_D5, 50);
  playNote(NOTE_C5, 50);
  playNote(NOTE_B4, 50);
  playNote(NOTE_A4, 50);
  playNote(NOTE_G4, 100);
  playNote(NOTE_F4, 100);
  playNote(NOTE_E4, 150);
  playNote(NOTE_D4, 200);
  playNote(NOTE_C4, 300);
}

// 5. VICTORY FANFARE (You won!)
void tune_Victory() {
  Serial.println("🔊 Playing: VICTORY 🏆");
  playNote(NOTE_G4, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_G5, 300);
  playNote(REST, 50);
  playNote(NOTE_E5, 100);
  playNote(NOTE_G5, 400);
  playNote(REST, 100);
  playNote(NOTE_C6, 100);
  playNote(NOTE_G5, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_C5, 400);
}

// 6. DEFEAT (Game over)
void tune_Defeat() {
  Serial.println("🔊 Playing: DEFEAT 💀");
  playNote(NOTE_C5, 200);
  playNote(NOTE_G4, 200);
  playNote(NOTE_E4, 200);
  playNote(NOTE_A4, 300);
  playNote(NOTE_B4, 300);
  playNote(NOTE_A4, 300);
  playNote(NOTE_GS4, 300);
  playNote(NOTE_AS4, 300);
  playNote(NOTE_GS4, 500);
}

// 7. LEVEL UP (Achievement unlocked!)
void tune_LevelUp() {
  Serial.println("🔊 Playing: LEVEL UP ⭐");
  playNote(NOTE_E5, 150);
  playNote(NOTE_G5, 150);
  playNote(NOTE_E6, 150);
  playNote(NOTE_C6, 150);
  playNote(NOTE_D6, 150);
  playNote(NOTE_G6, 400);
}

// 8. PUCK DISCOVERED (Found another puck!)
void tune_PuckFound() {
  Serial.println("🔊 Playing: PUCK DISCOVERED 📡");
  playNote(NOTE_C5, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_G5, 200);
}

// 9. TEAM ASSIGNED (Red team vs Blue team)
void tune_TeamAssigned() {
  Serial.println("🔊 Playing: TEAM ASSIGNED 🎯");
  playNote(NOTE_A4, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_A5, 300);
}

// 10. COIN COLLECT (Score point)
void tune_CoinCollect() {
  Serial.println("🔊 Playing: COIN COLLECT 💰");
  playNote(NOTE_B5, 100);
  playNote(NOTE_E6, 400);
}

// 11. ZELDA SECRET (Easter egg!)
void tune_Secret() {
  Serial.println("🔊 Playing: SECRET FOUND 🎁");
  playNote(NOTE_G5, 100);
  playNote(NOTE_FS5, 100);
  playNote(NOTE_DS5, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_GS4, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_GS5, 100);
  playNote(NOTE_C6, 400);
}

// 12. ALARM (Warning!)
void tune_Alarm() {
  Serial.println("🔊 Playing: ALARM ⚠️");
  for (int i = 0; i < 3; i++) {
    playNote(NOTE_A5, 100);
    playNote(NOTE_C5, 100);
  }
}

// 13. SUPER MARIO BROS THEME (First 8 notes)
void tune_MarioTheme() {
  Serial.println("🔊 Playing: MARIO THEME 🍄");
  playNote(NOTE_E5, 150);
  playNote(NOTE_E5, 150);
  playNote(REST, 150);
  playNote(NOTE_E5, 150);
  playNote(REST, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_E5, 150);
  playNote(REST, 150);
  playNote(NOTE_G5, 300);
  playNote(REST, 300);
  playNote(NOTE_G4, 300);
}

// 14. TETRIS THEME (Simplified)
void tune_Tetris() {
  Serial.println("🔊 Playing: TETRIS 📦");
  playNote(NOTE_E5, 200);
  playNote(NOTE_B4, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_D5, 200);
  playNote(NOTE_C5, 100);
  playNote(NOTE_B4, 100);
  playNote(NOTE_A4, 200);
  playNote(NOTE_A4, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_E5, 200);
  playNote(NOTE_D5, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_B4, 300);
}

// 15. RICK ROLL (You've been rickrolled!)
void tune_RickRoll() {
  Serial.println("🔊 Playing: NEVER GONNA GIVE YOU UP 🎤");
  playNote(NOTE_D5, 200);
  playNote(NOTE_E5, 200);
  playNote(NOTE_FS5, 200);
  playNote(NOTE_D5, 200);
  playNote(NOTE_E5, 200);
  playNote(NOTE_FS5, 200);
  playNote(NOTE_E5, 200);
  playNote(NOTE_A4, 400);
  playNote(NOTE_A4, 200);
  playNote(NOTE_B4, 200);
  playNote(NOTE_D5, 200);
  playNote(NOTE_B4, 200);
  playNote(NOTE_FS5, 200);
  playNote(NOTE_E5, 600);
}

// 16. STAR WARS THEME (Imperial March!)
void tune_StarWars() {
  Serial.println("🔊 Playing: IMPERIAL MARCH ⭐");
  playNote(NOTE_A4, 500);
  playNote(NOTE_A4, 500);
  playNote(NOTE_A4, 500);
  playNote(NOTE_F4, 350);
  playNote(NOTE_C5, 150);
  playNote(NOTE_A4, 500);
  playNote(NOTE_F4, 350);
  playNote(NOTE_C5, 150);
  playNote(NOTE_A4, 1000);
}

// 17. PAC-MAN DEATH (Waka waka waa waa)
void tune_PacManDeath() {
  Serial.println("🔊 Playing: PAC-MAN DEATH 👻");
  playNote(NOTE_B4, 100);
  playNote(NOTE_F5, 100);
  playNote(NOTE_B4, 100);
  playNote(NOTE_FS4, 100);
  playNote(NOTE_E4, 100);
  playNote(NOTE_B4, 100);
  playNote(NOTE_E4, 100);
  playNote(NOTE_FS4, 100);
  playNote(NOTE_DS4, 100);
  playNote(NOTE_E4, 100);
  playNote(NOTE_D4, 100);
  playNote(NOTE_CS4, 100);
  playNote(NOTE_C4, 200);
}

// 18. SONIC RING COLLECT
void tune_SonicRing() {
  Serial.println("🔊 Playing: SONIC RING 💎");
  playNote(NOTE_E6, 100);
  playNote(NOTE_G6, 100);
  playNote(NOTE_E7, 200);
}

// 19. ZELDA ITEM GET (Da da da daaaa!)
void tune_ZeldaItem() {
  Serial.println("🔊 Playing: ZELDA ITEM GET 🗡️");
  playNote(NOTE_G5, 150);
  playNote(NOTE_A5, 150);
  playNote(NOTE_B5, 150);
  playNote(NOTE_C6, 400);
  playNote(REST, 100);
  playNote(NOTE_C6, 400);
  playNote(REST, 100);
  playNote(NOTE_C6, 400);
  playNote(NOTE_B5, 150);
  playNote(NOTE_C6, 600);
}

// 20. POKEMON BATTLE START
void tune_PokemonBattle() {
  Serial.println("🔊 Playing: POKEMON BATTLE ⚔️");
  playNote(NOTE_E5, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_E5, 100);
  playNote(REST, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_E5, 100);
  playNote(REST, 100);
  playNote(NOTE_G5, 200);
  playNote(REST, 200);
  playNote(NOTE_G4, 200);
}

// 21. COFFIN DANCE MEME
void tune_CoffinDance() {
  Serial.println("🔊 Playing: COFFIN DANCE ⚰️");
  playNote(NOTE_D5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_A4, 300);
  playNote(NOTE_D5, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_D5, 300);
  playNote(NOTE_D5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_G5, 300);
}

// 22. NYAN CAT
void tune_NyanCat() {
  Serial.println("🔊 Playing: NYAN CAT 🐱🌈");
  playNote(NOTE_FS5, 150);
  playNote(NOTE_GS5, 150);
  playNote(NOTE_CS5, 150);
  playNote(NOTE_DS5, 150);
  playNote(NOTE_B4, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_CS5, 150);
  playNote(NOTE_B4, 150);
  playNote(NOTE_B4, 150);
  playNote(NOTE_CS5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_CS5, 150);
  playNote(NOTE_B4, 150);
  playNote(NOTE_CS5, 150);
  playNote(NOTE_DS5, 150);
}

// 23. WINDOWS XP STARTUP
void tune_WindowsXP() {
  Serial.println("🔊 Playing: WINDOWS XP 🪟");
  playNote(NOTE_E5, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_E4, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_C5, 200);
}

// 24. AMONG US KILL
void tune_AmongUs() {
  Serial.println("🔊 Playing: AMONG US 🔪");
  playNote(NOTE_C5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_C5, 300);
  playNote(REST, 100);
  playNote(NOTE_G4, 600);
}

// 25. SPONGEBOB THEME
void tune_Spongebob() {
  Serial.println("🔊 Playing: SPONGEBOB 🧽");
  playNote(NOTE_D5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_A5, 300);
  playNote(NOTE_G5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_D5, 300);
}

// 26. PINK PANTHER
void tune_PinkPanther() {
  Serial.println("🔊 Playing: PINK PANTHER 🐆");
  playNote(REST, 100);
  playNote(NOTE_DS5, 150);
  playNote(NOTE_E5, 150);
  playNote(REST, 100);
  playNote(NOTE_FS5, 150);
  playNote(NOTE_G5, 150);
  playNote(REST, 100);
  playNote(NOTE_DS5, 150);
  playNote(NOTE_E5, 150);
  playNote(REST, 100);
  playNote(NOTE_FS5, 150);
  playNote(NOTE_G5, 150);
  playNote(NOTE_C6, 150);
  playNote(NOTE_B5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_G5, 150);
  playNote(NOTE_B5, 150);
  playNote(NOTE_AS5, 200);
  playNote(NOTE_A5, 150);
  playNote(NOTE_G5, 300);
}

// 27. CAN CAN DANCE
void tune_CanCan() {
  Serial.println("🔊 Playing: CAN CAN 💃");
  playNote(NOTE_G5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_G5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_G5, 300);
}

// 28. JEOPARDY THINKING MUSIC
void tune_Jeopardy() {
  Serial.println("🔊 Playing: JEOPARDY ❓");
  playNote(NOTE_G5, 200);
  playNote(NOTE_C6, 200);
  playNote(NOTE_G5, 200);
  playNote(NOTE_C5, 200);
  playNote(NOTE_G5, 200);
  playNote(NOTE_C6, 400);
  playNote(NOTE_G5, 400);
}

// 29. MORTAL KOMBAT
void tune_MortalKombat() {
  Serial.println("🔊 Playing: MORTAL KOMBAT 🥊");
  playNote(NOTE_A4, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_D5, 100);
  playNote(NOTE_A4, 100);
  playNote(NOTE_E5, 100);
  playNote(NOTE_D5, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_C5, 100);
  playNote(NOTE_A4, 200);
}

// 30. MEGALOVANIA (Undertale Sans)
void tune_Megalovania() {
  Serial.println("🔊 Playing: MEGALOVANIA 💀");
  playNote(NOTE_D5, 100);
  playNote(NOTE_D5, 100);
  playNote(NOTE_D6, 200);
  playNote(NOTE_A5, 200);
  playNote(REST, 100);
  playNote(NOTE_GS5, 150);
  playNote(REST, 100);
  playNote(NOTE_G5, 150);
  playNote(REST, 100);
  playNote(NOTE_F5, 150);
  playNote(NOTE_D5, 100);
  playNote(NOTE_F5, 100);
  playNote(NOTE_G5, 100);
}

// 31. PUNCH-OUT!! TRAINING THEME (Little Mac!)
void tune_PunchOut() {
  Serial.println("🔊 Playing: PUNCH-OUT!! 🥊");
  playNote(NOTE_E5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_E5, 300);
  playNote(NOTE_G5, 300);
  playNote(REST, 300);
  playNote(NOTE_C5, 150);
  playNote(NOTE_G4, 150);
  playNote(REST, 150);
  playNote(NOTE_E4, 300);
  playNote(NOTE_A4, 150);
  playNote(NOTE_B4, 150);
  playNote(NOTE_AS4, 150);
  playNote(NOTE_A4, 300);
  playNote(NOTE_G4, 200);
  playNote(NOTE_E5, 200);
  playNote(NOTE_G5, 200);
  playNote(NOTE_A5, 150);
  playNote(NOTE_F5, 150);
  playNote(NOTE_G5, 150);
  playNote(REST, 150);
  playNote(NOTE_E5, 150);
  playNote(NOTE_C5, 150);
  playNote(NOTE_D5, 150);
  playNote(NOTE_B4, 300);
}

// 32. BOHEMIAN RHAPSODY (Opening 20 seconds - Demo of complexity!)
void tune_BohemianRhapsody() {
  Serial.println("🔊 Playing: BOHEMIAN RHAPSODY (Intro) 👑");

  // Opening piano melody
  playNote(NOTE_AS4, 400);
  playNote(NOTE_F5, 400);
  playNote(NOTE_AS4, 400);
  playNote(NOTE_F5, 400);
  playNote(NOTE_AS4, 200);
  playNote(NOTE_F5, 200);
  playNote(NOTE_AS4, 400);

  playNote(NOTE_GS4, 400);
  playNote(NOTE_DS5, 400);
  playNote(NOTE_GS4, 400);
  playNote(NOTE_DS5, 400);
  playNote(NOTE_GS4, 200);
  playNote(NOTE_DS5, 200);
  playNote(NOTE_GS4, 400);

  playNote(NOTE_G4, 400);
  playNote(NOTE_D5, 400);
  playNote(NOTE_G4, 400);
  playNote(NOTE_D5, 400);
  playNote(NOTE_G4, 200);
  playNote(NOTE_D5, 200);
  playNote(NOTE_G4, 400);

  playNote(NOTE_FS4, 400);
  playNote(NOTE_CS5, 400);
  playNote(NOTE_FS4, 400);
  playNote(NOTE_CS5, 400);

  // "Is this the real life..." melody
  playNote(NOTE_AS4, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_D5, 300);
  playNote(NOTE_DS5, 300);
  playNote(NOTE_D5, 600);
  playNote(REST, 200);

  playNote(NOTE_AS4, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_D5, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_AS4, 600);
  playNote(REST, 200);

  playNote(NOTE_GS4, 300);
  playNote(NOTE_AS4, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_D5, 300);
  playNote(NOTE_C5, 600);
  playNote(REST, 200);

  playNote(NOTE_AS4, 300);
  playNote(NOTE_GS4, 300);
  playNote(NOTE_G4, 300);
  playNote(NOTE_FS4, 300);
  playNote(NOTE_G4, 800);
  playNote(REST, 300);

  // Continues with more melodic variation
  playNote(NOTE_D5, 300);
  playNote(NOTE_DS5, 300);
  playNote(NOTE_D5, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_AS4, 600);
  playNote(REST, 200);

  playNote(NOTE_AS4, 300);
  playNote(NOTE_C5, 300);
  playNote(NOTE_D5, 300);
  playNote(NOTE_DS5, 600);
  playNote(NOTE_D5, 300);
  playNote(NOTE_C5, 800);
}

// ============================================================================
// SETUP & LOOP
// ============================================================================

// ============================================================================
// SETUP & LOOP - AUTO-PLAY MODE (NO BUTTON NEEDED!)
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n========================================");
  Serial.println("  🎵 TABLE WARS - EPIC TUNE LIBRARY 🎵");
  Serial.println("  ✨ 31 ICONIC TUNES - AUTO-PLAY MODE!");
  Serial.println("========================================");

  // Initialize I2C and MPU6050
  Wire.begin();
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) { delay(10); }
  }
  Serial.println("MPU6050 Found!");

  // Configure sensor ranges
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  Serial.println();
  Serial.println("Wiring:");
  Serial.println("  Buzzer + (red)  → GPIO 15");
  Serial.println("  Buzzer - (black) → GND");
  Serial.println();
  Serial.println("🔥 Playing ALL 31 tunes in sequence...");
  Serial.println("   Star Wars | Pac-Man | Sonic | Zelda");
  Serial.println("   Pokemon | Coffin Dance | Nyan Cat");
  Serial.println("   Among Us | Spongebob | Pink Panther");
  Serial.println("   Mortal Kombat | Megalovania");
  Serial.println("   🥊 PUNCH-OUT!! & MORE!");
  Serial.println("========================================\n");

  pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
  // Read MPU6050 sensor data
  mpu.getEvent(&accel_event, &gyro_event, &temp_event);

  // Compute shake_intensity (magnitude of acceleration vector)
  shake_intensity = sqrt(
    accel_event.acceleration.x * accel_event.acceleration.x +
    accel_event.acceleration.y * accel_event.acceleration.y +
    accel_event.acceleration.z * accel_event.acceleration.z
  );

  // Detect shake when intensity exceeds threshold (above gravity ~9.8)
  shake_detected = (shake_intensity > 12.0);

  // Compute tilt angles from accelerometer
  tilt_x = atan2(accel_event.acceleration.y, accel_event.acceleration.z) * 180.0 / PI;
  tilt_y = atan2(-accel_event.acceleration.x,
    sqrt(accel_event.acceleration.y * accel_event.acceleration.y +
         accel_event.acceleration.z * accel_event.acceleration.z)) * 180.0 / PI;

  // Compute spin speed from gyroscope Z axis
  gyro_z_raw = gyro_event.gyro.z;
  spin_speed = abs(gyro_z_raw) * 57.2958; // rad/s to deg/s
  spin_direction = (gyro_z_raw > 0.1) ? "CW" : (gyro_z_raw < -0.1) ? "CCW" : "NONE";

  // Sprint 0B: Rate-limited sensor data broadcast (for ESP-NOW integration)
  // Sends at SEND_INTERVAL_MS rate, or immediately if shake detected
  if (millis() - last_send > SEND_INTERVAL_MS || shake_detected) {
    // Debug output - shows sensor values that would be sent
    Serial.print("TX: tilt_x="); Serial.print(tilt_x, 1);
    Serial.print(" tilt_y="); Serial.print(tilt_y, 1);
    Serial.print(" gyro_z="); Serial.print(gyro_z_raw, 4);
    Serial.print(" spin="); Serial.print(spin_speed, 1);
    Serial.print(" shake="); Serial.println(shake_detected ? "YES" : "no");

    /* ESP-NOW send pattern (uncomment when ESP-NOW enabled):
    PuckMessage msg;
    msg.senderPuckId = PUCK_ID;
    msg.tilt_x = tilt_x;
    msg.tilt_y = tilt_y;
    msg.shake_intensity = shake_intensity;
    msg.spin_speed = spin_speed;
    msg.gyro_z = gyro_z_raw;
    msg.shake_detected = shake_detected;
    esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(msg));
    */

    last_send = millis();
  }

  Serial.println("\n👑 Playing BOHEMIAN RHAPSODY snippet...\n");
  Serial.println("   (20-second intro showing complexity)\n");

  tune_BohemianRhapsody();

  Serial.println("\n✅ Done! That was ~70 notes in 20 seconds!");
  Serial.println("   Playing again in 5 seconds...\n");
  delay(5000);
}
