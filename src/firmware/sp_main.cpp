// Speed Pyramid v1 — firmware entry point.
//
// Build with the platformio env `puck1_speed_pyramid` (see platformio.ini).
// Defaults: PUCK_ID=1, Rev A pin map. For Rev B pucks, set
// -D PUCK_REV_B in build_flags.
//
// On boot:
//   1. Initialize sensors + LED ring + buzzer + motor.
//   2. Connect to WiFi.
//   3. Drop into the Speed Pyramid pair-mode state machine
//      (g_speed_pyramid.h). Hold the button 1s to start dialing.

#include <Arduino.h>
#include "../games/g_speed_pyramid.h"

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("============================================");
  Serial.println(" TABLE WARS - Speed Pyramid v1");
  Serial.print(" PUCK_ID = ");
  Serial.println(PUCK_ID);
#if defined(PUCK_REV_B)
  Serial.println(" Hardware: Rev B");
#else
  Serial.println(" Hardware: Rev A");
#endif
  Serial.println("============================================");

  sp_game::begin();

  if (sp_net::is_connected()) {
    Serial.print(" WiFi: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" WiFi: NOT CONNECTED -- check SSID/PASS");
  }

  Serial.println(" Ready. Hold button 1s to enter pair mode.");
}

void loop() {
  sp_game::pair_mode_loop();
  delay(8);  // ~125 Hz poll
}
