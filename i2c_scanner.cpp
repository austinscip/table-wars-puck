#include <Arduino.h>
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n========================================");
  Serial.println("  I2C Scanner for ESP32");
  Serial.println("========================================\n");

  Wire.begin(21, 22); // SDA=21, SCL=22

  Serial.println("Scanning I2C bus...\n");

  byte count = 0;

  for (byte i = 1; i < 127; i++) {
    Wire.beginTransmission(i);
    byte error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("✅ I2C device found at address 0x");
      if (i < 16) Serial.print("0");
      Serial.print(i, HEX);

      // Identify common devices
      if (i == 0x68) Serial.print(" (MPU6050 default)");
      if (i == 0x69) Serial.print(" (MPU6050 alternate)");

      Serial.println();
      count++;
    }
  }

  Serial.println("\n========================================");
  if (count == 0) {
    Serial.println("❌ No I2C devices found!");
    Serial.println("\nTroubleshooting:");
    Serial.println("- Check wiring (SDA=21, SCL=22)");
    Serial.println("- Verify VCC is 3.3V (NOT 5V!)");
    Serial.println("- Check GND connection");
  } else {
    Serial.print("✅ Found ");
    Serial.print(count);
    Serial.println(" device(s)");
  }
  Serial.println("========================================\n");
}

void loop() {
  // Re-scan every 5 seconds
  delay(5000);
  Serial.println("Scanning again...");
  setup();
}
