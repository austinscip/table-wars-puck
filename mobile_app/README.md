# TABLE WARS - Mobile Control App

Flutter app for bar staff to control TABLE WARS pucks via Bluetooth LE.

## Features

- ✅ Scan for nearby pucks
- ✅ View puck status (battery, signal strength)
- ✅ Connect to pucks via BLE
- ✅ Start/stop games remotely
- ✅ Monitor multiple pucks
- ⏳ View live scores (coming soon)
- ⏳ OTA firmware updates (coming soon)

---

## Screenshots

*(Add screenshots here after building UI)*

---

## Setup

### Prerequisites

- Flutter SDK 3.0+
- Android Studio / Xcode
- Physical device (BLE doesn't work well in emulators)

### 1. Install Flutter

```bash
# macOS
brew install flutter

# Or download from: https://flutter.dev/docs/get-started/install
```

### 2. Install Dependencies

```bash
cd mobile_app
flutter pub get
```

### 3. Run on Device

**Android:**
```bash
flutter run
```

**iOS:**
```bash
cd ios
pod install
cd ..
flutter run
```

---

## Configuration

### Set Server URL

Edit `lib/puck_controller.dart`:

```dart
String _serverUrl = 'http://YOUR_SERVER_IP:5000';
```

Replace with your Flask server IP address.

### Permissions

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.BLUETOOTH"/>
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN"/>
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"/>
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>NSBluetoothAlwaysUsageDescription</key>
<string>This app needs Bluetooth to control TABLE WARS pucks</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Location is required for Bluetooth scanning</string>
```

---

## Usage

### 1. Scan for Pucks

- Open the app
- Tap the "Scan Pucks" button
- Wait for pucks to appear in the list

### 2. Connect to a Puck

- Tap the menu icon (⋮) on a puck card
- Select "Connect"
- Wait for connection confirmation

### 3. Start a Game

- Tap the menu icon on a connected puck
- Select "Start Game"
- Choose game from the list
- Game will start on the puck

### 4. Monitor Status

- View battery level
- Check signal strength (RSSI)
- See online/offline status

---

## BLE Service UUIDs

To enable full control, the ESP32 firmware must expose these BLE services:

### Game Control Service
```
Service UUID: 0x1800
Characteristic: Game Command (0x2A00)
  - Write: Start game (1 byte game ID)
  - Read: Current game state
```

### Status Service
```
Service UUID: 0x180F
Characteristic: Battery Level (0x2A19)
  - Read/Notify: Battery percentage (1 byte)
```

### Configuration Service
```
Service UUID: 0x1801
Characteristic: Puck ID (0x2A01)
  - Read: Puck ID (1 byte)
Characteristic: Firmware Version (0x2A02)
  - Read: Version string
```

---

## Adding BLE to ESP32 Firmware

Add this to your puck firmware:

```cpp
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Service UUIDs
#define SERVICE_UUID        "0000180f-0000-1000-8000-00805f9b34fb"
#define BATTERY_CHAR_UUID   "00002a19-0000-1000-8000-00805f9b34fb"
#define GAME_SERVICE_UUID   "00001800-0000-1000-8000-00805f9b34fb"
#define GAME_CHAR_UUID      "00002a00-0000-1000-8000-00805f9b34fb"

BLEServer* pServer = nullptr;
BLECharacteristic* pBatteryChar = nullptr;
BLECharacteristic* pGameChar = nullptr;

class GameCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string value = pCharacteristic->getValue();

        if (value.length() > 0) {
            uint8_t gameId = value[0];
            Serial.printf("Starting game: %d\n", gameId);

            // Start the requested game
            // gameId: 1=Speed Tap, 2=Shake Duel, etc.
        }
    }
};

void setupBLE() {
    BLEDevice::init("Puck_1");

    pServer = BLEDevice::createServer();

    // Battery Service
    BLEService *pBatteryService = pServer->createService(SERVICE_UUID);
    pBatteryChar = pBatteryService->createCharacteristic(
        BATTERY_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pBatteryChar->addDescriptor(new BLE2902());

    // Game Control Service
    BLEService *pGameService = pServer->createService(GAME_SERVICE_UUID);
    pGameChar = pGameService->createCharacteristic(
        GAME_CHAR_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    pGameChar->setCallbacks(new GameCallbacks());

    pBatteryService->start();
    pGameService->start();

    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->addServiceUUID(GAME_SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();

    Serial.println("✅ BLE advertising started");
}

void updateBattery(uint8_t level) {
    if (pBatteryChar) {
        pBatteryChar->setValue(&level, 1);
        pBatteryChar->notify();
    }
}
```

---

## Building for Production

### Android APK

```bash
flutter build apk --release
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

### iOS IPA

```bash
flutter build ios --release
```

Then archive and export via Xcode.

---

## Troubleshooting

**BLE not working:**
- Ensure location permissions granted (Android)
- Check Bluetooth is enabled
- Try on a physical device (not emulator)
- Verify pucks are advertising

**Can't connect to puck:**
- Move closer to puck (< 10m)
- Check puck is powered on
- Restart puck
- Re-scan

**Games don't start:**
- Verify BLE characteristic UUIDs match
- Check firmware has BLE service implemented
- View logs: `flutter logs`

---

## Future Features

- [ ] Real-time score display
- [ ] Tournament management
- [ ] Puck grouping (by table)
- [ ] Firmware OTA updates
- [ ] Historical game data
- [ ] Custom game creation
- [ ] Multiple bar management
- [ ] Staff accounts

---

**Questions?**
See main project README or open an issue on GitHub.
