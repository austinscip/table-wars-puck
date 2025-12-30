# Complete Deployment Checklist

## 🎯 Goal

Deploy upgraded firmware to all 6 pucks with all FREE features enabled.

**Time**: 3 hours total
**Cost**: $0.50 (copper tape)
**Result**: Professional multiplayer gaming system

---

## ✅ Pre-Deployment Checklist

### Software Requirements:

- [ ] PlatformIO installed (`pio --version`)
- [ ] Python 3 installed (`python3 --version`)
- [ ] Git installed (for version control)
- [ ] Text editor (VS Code, Cursor, etc.)

### Hardware Requirements:

- [ ] 6× ESP32 pucks (working condition)
- [ ] USB-C cables (for initial upload)
- [ ] Copper tape roll (for capacitive touch)
- [ ] Soldering iron + solder
- [ ] 22 AWG wire

### Network Requirements:

- [ ] WiFi network name & password
- [ ] All devices on same network
- [ ] Firewall allows port 3232 (for OTA)
- [ ] Router assigns static IPs (recommended)

---

## 📋 Part 1: Test on Single Puck (1 hour)

### Step 1: Backup Current Code

```bash
cd /Users/austinscipione/table-wars-puck

# Backup current firmware
cp src/main.cpp src/main_backup.cpp
cp src/main_tablewars.h src/main_tablewars_backup.h

# Create git commit
git add .
git commit -m "Backup before upgrade"
```

**Verify**:
- [ ] Backup files created
- [ ] Git commit successful

---

### Step 2: Upload Test Code

```bash
# Upload test firmware to Puck 1 via USB
pio run -e puck1 -t upload
```

**Expected output**:
```
Configuring upload protocol...
Uploading .pio/build/puck1/firmware.bin
Writing at 0x00010000... (100 %)
Wrote 1234567 bytes (789012 compressed) at 0x00010000
Hash of data verified.

Leaving...
Hard resetting via RTS pin...
```

**Verify**:
- [ ] Upload successful (no errors)
- [ ] Puck restarts automatically

---

### Step 3: Open Serial Monitor

```bash
pio device monitor --baud 115200
```

**Expected output**:
```
╔══════════════════════════════════╗
║                                  ║
║   TESTING ALL ESP32 FEATURES     ║
║                                  ║
║  🔄 OTA Updates                  ║
║  👆 Capacitive Touch             ║
║  📡 ESP-NOW                      ║
║  🧲 Hall Sensor                  ║
║  🌡️  Temperature                 ║
║  💤 Deep Sleep                   ║
║  📳 Shake Detection              ║
║  🔘 Button Input                 ║
║                                  ║
╚══════════════════════════════════╝

📡 Connecting to WiFi....... ✅ Connected!
IP Address: 192.168.1.101
✅ MPU6050 connected
✅ Hardware initialized!

Starting tests in 3 seconds...
```

**Verify**:
- [ ] WiFi connected
- [ ] IP address assigned
- [ ] MPU6050 detected
- [ ] No error messages

---

### Step 4: Test Each Feature

The test code runs automatically. Watch for these results:

#### Test 1: OTA Updates
```
═══════════════════════════════════
TEST 1: OTA FIRMWARE UPDATES
═══════════════════════════════════
✅ Arduino OTA initialized
✅ OTA hostname: TableWarsPuck
✅ OTA port: 3232
✅ OTA password: ********
✅ OTA Test Complete
```

**Verify**:
- [ ] OTA initialized
- [ ] No errors

#### Test 2: Button Input
```
═══════════════════════════════════
TEST 8: BUTTON INPUT
═══════════════════════════════════
Press button 5 times...
✓ Button press 1/5
✓ Button press 2/5
✓ Button press 3/5
✓ Button press 4/5
✓ Button press 5/5
✅ Button Input Test Complete
```

**Verify**:
- [ ] Button presses detected (press button 5 times)
- [ ] LEDs flash green on each press

#### Test 3: Shake Detection
```
═══════════════════════════════════
TEST 7: SHAKE DETECTION
═══════════════════════════════════
Shake the puck for 10 seconds...
📳 Shake 1 detected!
📳 Shake 2 detected!
📳 Shake 3 detected!
✅ Shake Detection Test Complete (3 shakes)
```

**Verify**:
- [ ] Shake detected (shake puck vigorously)
- [ ] LEDs flash yellow
- [ ] Buzzer beeps

#### Test 4: Capacitive Touch
```
═══════════════════════════════════
TEST 2: CAPACITIVE TOUCH
═══════════════════════════════════
Touch the puck surface for 10 seconds...
✓ Tap 1 detected!
✓ Tap 2 detected!
◀️ Swipe Left!
▶️ Swipe Right!
✅ Capacitive Touch Test Complete (4 taps detected)
```

**Verify** (if copper tape installed):
- [ ] Tap detected
- [ ] Swipe left/right detected
- [ ] LEDs respond to touch

**If no copper tape yet**:
- [ ] Skip this test for now

#### Test 5: ESP-NOW
```
═══════════════════════════════════
TEST 3: ESP-NOW MULTIPLAYER
═══════════════════════════════════
✅ ESP-NOW initialized
✅ Broadcast peer added
Discovering nearby pucks...
📡 Broadcasting test message...
✅ ESP-NOW Test Complete
```

**Verify**:
- [ ] ESP-NOW initialized
- [ ] No errors

#### Test 6: Hall Sensor
```
═══════════════════════════════════
TEST 4: HALL SENSOR
═══════════════════════════════════
Wave a magnet near the ESP32 for 10 seconds...
🧲 Magnet detected! Value: 120
🧲 Magnet detected! Value: 95
✅ Hall Sensor Test Complete (2 detections)
```

**Verify** (if you have a magnet):
- [ ] Magnet detected
- [ ] LEDs flash magenta
- [ ] Serial shows hall values

**If no magnet**:
- [ ] Shows "0 detections" (that's OK)

#### Test 7: Temperature
```
═══════════════════════════════════
TEST 5: TEMPERATURE SENSOR
═══════════════════════════════════
🌡️  Temperature: 28.5°C
🌡️  Temperature: 28.7°C
🌡️  Temperature: 28.9°C
🌡️  Temperature: 29.1°C
🌡️  Temperature: 29.3°C
✅ Temperature Test Complete
```

**Verify**:
- [ ] Temperature values reasonable (25-35°C room temp)
- [ ] LEDs change color based on temp

#### Final Test Results
```
╔══════════════════════════════════╗
║                                  ║
║   🎉 ALL TESTS COMPLETE! 🎉      ║
║                                  ║
╚══════════════════════════════════╝

✅ All features working!
Type 'help' for interactive commands
```

**Verify**:
- [ ] All tests passed
- [ ] Rainbow animation played
- [ ] Ready for interactive mode

---

### Step 5: Interactive Testing

Type commands in serial monitor:

```bash
help    # Show available commands
```

**Expected output**:
```
📖 COMMANDS:
  help   - Show this help
  ota    - Test OTA
  touch  - Test touch
  espnow - Test ESP-NOW
  hall   - Test hall sensor
  temp   - Test temperature
  shake  - Test shake
  sleep  - Test deep sleep
  all    - Run all tests
```

**Test each command**:

```bash
ota      # Test OTA
```
- [ ] OTA ready message

```bash
shake    # Test shake (shake puck for 10 sec)
```
- [ ] Shake detection working

```bash
temp     # Test temperature
```
- [ ] Temperature readings shown

---

### Step 6: Test OTA Upload

**Important**: This is the last time you'll use USB!

```bash
# Exit serial monitor (Ctrl+C)

# Upload via OTA (WiFi)
pio run -e puck1_ota -t upload
```

**Expected output**:
```
Configuring upload protocol...
Looking for upload port...
Auto-detected: 192.168.1.101
Uploading .pio/build/puck1_ota/firmware.bin
Sending invitation to 192.168.1.101
192.168.1.101 accepted
Sending: [############] 100%
Done!
```

**Verify**:
- [ ] OTA upload successful
- [ ] Puck restarted
- [ ] No USB cable needed!

---

## 📋 Part 2: Add Capacitive Touch (30 minutes)

**Only if you have copper tape!**

### Step 1: Prepare Materials

- [ ] Cut 4 pieces of copper tape (see CAPACITIVE_TOUCH_WIRING_GUIDE.md)
- [ ] Strip 4 wires (15cm each)
- [ ] Heat up soldering iron

### Step 2: Apply Copper Tape

**Inside the case**:

- [ ] Clean surface with rubbing alcohol
- [ ] Stick Top pad (5cm × 3cm) to GPIO 4 area
- [ ] Stick Left pad (3cm × 3cm) to GPIO 2 area
- [ ] Stick Right pad (3cm × 3cm) to GPIO 14 area
- [ ] Stick Bottom pad (4cm × 2cm) to GPIO 13 area
- [ ] Press firmly, remove air bubbles

### Step 3: Solder Wires

- [ ] Solder red wire to Top pad → Connect to GPIO 4
- [ ] Solder yellow wire to Left pad → Connect to GPIO 2
- [ ] Solder green wire to Right pad → Connect to GPIO 14
- [ ] Solder blue wire to Bottom pad → Connect to GPIO 13

### Step 4: Test Touch

```bash
# Open serial monitor
pio device monitor --baud 115200

# Type 'touch' command
touch
```

**Expected output**:
```
═══════════════════════════════════
TEST 2: CAPACITIVE TOUCH
═══════════════════════════════════
Touch the puck surface for 10 seconds...
```

**Test each pad**:

- [ ] Touch top → LEDs light up, "Tap detected!"
- [ ] Touch left → LEDs red, "Swipe Left!"
- [ ] Touch right → LEDs blue, "Swipe Right!"
- [ ] Hold bottom → "Long press!"

**If not working**:
- Check CAPACITIVE_TOUCH_WIRING_GUIDE.md troubleshooting section
- Verify solder connections
- Adjust `TOUCH_THRESHOLD` in code

---

## 📋 Part 3: Deploy to All 6 Pucks (90 minutes)

### Preparation

```bash
# Update WiFi credentials in platformio_UPGRADED.ini
# Set your WiFi SSID and password

# Verify IP addresses for each puck
# Default:
# Puck 1: 192.168.1.101
# Puck 2: 192.168.1.102
# Puck 3: 192.168.1.103
# Puck 4: 192.168.1.104
# Puck 5: 192.168.1.105
# Puck 6: 192.168.1.106
```

**Update platformio_UPGRADED.ini if needed**:
- [ ] WiFi SSID correct
- [ ] WiFi password correct
- [ ] IP addresses match your network

---

### Initial USB Upload (Only Once!)

Connect each puck via USB and upload:

```bash
# Puck 1
pio run -e puck1 -t upload

# Puck 2
pio run -e puck2 -t upload

# Puck 3
pio run -e puck3 -t upload

# Puck 4
pio run -e puck4 -t upload

# Puck 5
pio run -e puck5 -t upload

# Puck 6
pio run -e puck6 -t upload
```

**Checklist**:
- [ ] Puck 1 uploaded, WiFi connected, OTA ready
- [ ] Puck 2 uploaded, WiFi connected, OTA ready
- [ ] Puck 3 uploaded, WiFi connected, OTA ready
- [ ] Puck 4 uploaded, WiFi connected, OTA ready
- [ ] Puck 5 uploaded, WiFi connected, OTA ready
- [ ] Puck 6 uploaded, WiFi connected, OTA ready

---

### Test Multiplayer Communication

Power on at least 2 pucks. On each:

```bash
pio device monitor --baud 115200
```

Type:
```bash
espnow
```

**Expected output on both pucks**:
```
═══════════════════════════════════
TEST 3: ESP-NOW MULTIPLAYER
═══════════════════════════════════
✅ ESP-NOW initialized
✅ Broadcast peer added
Discovering nearby pucks...
📡 Found Puck 2!
📡 Found Puck 3!
📡 Broadcasting test message...
✅ Received message from Puck 2!
✅ ESP-NOW Test Complete
```

**Verify**:
- [ ] Pucks discover each other
- [ ] Messages sent/received
- [ ] No errors

---

### Wireless OTA Updates (Forever!)

From now on, update all pucks wirelessly:

```bash
# Use the deployment script
./deploy_all_pucks.sh
```

**Or manually**:

```bash
pio run -e puck1_ota -t upload && \
pio run -e puck2_ota -t upload && \
pio run -e puck3_ota -t upload && \
pio run -e puck4_ota -t upload && \
pio run -e puck5_ota -t upload && \
pio run -e puck6_ota -t upload
```

**Expected output**:
```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           TABLE WARS PUCK - OTA DEPLOYMENT               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

✅ PlatformIO found
Mode: ota
Deploying to pucks: 1 2 3 4 5 6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Deploying to Puck 1...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[...]
✅ Puck 1 deployed successfully!

[... repeat for all pucks ...]

╔══════════════════════════════════════════════════════════╗
║                   DEPLOYMENT SUMMARY                     ║
╚══════════════════════════════════════════════════════════╝

✅ Successful: 6
❌ Failed: 0

🎮 All pucks deployed! Start the server:
   cd server && python app.py
```

**Verify**:
- [ ] All 6 pucks updated via WiFi
- [ ] No USB cables needed
- [ ] All pucks restarted automatically

---

## 📋 Part 4: Start Server (5 minutes)

### Install Python Dependencies

```bash
cd server
pip3 install flask flask-socketio python-socketio
```

### Start Server

```bash
python3 app.py
```

**Expected output**:
```
🎮 TABLE WARS SERVER STARTING...

✅ Server initialized
✅ WebSocket enabled
✅ Static files: /static
✅ Templates: /templates

🌐 Server running on:
   http://localhost:5001
   http://192.168.1.100:5001

🎮 Game Dashboard: http://localhost:5001/
🏆 Leaderboard: http://localhost:5001/leaderboard
🔧 Firmware Dashboard: http://localhost:5001/firmware/dashboard

Press Ctrl+C to stop
```

**Verify**:
- [ ] Server started
- [ ] No errors

### Test Dashboards

**Open in browser**:

1. **Game Dashboard**: http://localhost:5001/
   - [ ] Shows all 6 pucks
   - [ ] Real-time status updates

2. **Leaderboard**: http://localhost:5001/leaderboard
   - [ ] Shows top scores

3. **Firmware Dashboard**: http://localhost:5001/firmware/dashboard
   - [ ] Shows all puck versions
   - [ ] Shows online status

---

## 📋 Part 5: Test Games (30 minutes)

### Test Solo Games

On any puck, type game number:

```bash
1    # Shake Race
```

**Verify**:
- [ ] Game starts
- [ ] LEDs animate
- [ ] Shake detection works
- [ ] Score sent to server

Try a few more:
```bash
2    # Button Masher
5    # Reaction Time
10   # Memory Lights
```

**Verify**:
- [ ] All games load
- [ ] Controls responsive
- [ ] Scores tracked

---

### Test Multiplayer Games

Power on at least 2 pucks. On all pucks, type:

```bash
52   # Puck Wars
```

**Expected**:
```
🎮 PUCK WARS - Battle Royale!

3... 2... 1... GO!

Health: ████████████████ 100%
```

**Shake one puck to attack another**:
- [ ] Attack registered
- [ ] Target puck takes damage
- [ ] Health bars update
- [ ] Victory when one eliminated

Try other multiplayer games:
```bash
53   # Hot Potato Relay
54   # Sync Shake Challenge
55   # Boss Battle
56   # King of the Hill
```

**Verify**:
- [ ] Pucks communicate
- [ ] Game mechanics work
- [ ] Scores tracked

---

## 📋 Part 6: Production Testing (15 minutes)

### Power Test

- [ ] Charge all pucks to 100%
- [ ] Run games for 1 hour
- [ ] Check battery levels
- [ ] Verify deep sleep activates after 5 min idle

### Range Test

- [ ] Place 2 pucks 10m apart
- [ ] Test ESP-NOW communication
- [ ] Increase distance until fails
- [ ] Verify range > 50m indoors

### Reliability Test

- [ ] Run 10 games back-to-back
- [ ] Check for crashes
- [ ] Verify no memory leaks
- [ ] Monitor temperature

### Stress Test

- [ ] All 6 pucks active simultaneously
- [ ] Start Boss Battle (all vs boss)
- [ ] Continuous activity for 10 minutes
- [ ] Check for disconnections

---

## 🎉 Final Checklist

### Hardware
- [ ] All 6 pucks working
- [ ] Capacitive touch installed (optional)
- [ ] Cases closed securely
- [ ] Batteries charged

### Software
- [ ] Firmware version matches across all pucks
- [ ] WiFi credentials correct
- [ ] OTA updates working
- [ ] All features tested

### Server
- [ ] Flask server running
- [ ] All dashboards accessible
- [ ] WebSocket connections stable
- [ ] Scores saving correctly

### Games
- [ ] Solo games work
- [ ] Multiplayer games work
- [ ] Touch controls work (if installed)
- [ ] All 56 games tested

---

## 🚀 You're Done!

**Congratulations!** Your pucks now have:

✅ Wireless OTA updates
✅ Dual-core performance
✅ Touch controls (if copper tape installed)
✅ Multiplayer communication
✅ Deep sleep battery management
✅ Hall sensor games
✅ Temperature sensing
✅ 56 total games

**What's next?**

### This Week:
- Play all 56 games
- Test with friends
- Fine-tune touch sensitivity

### Next Week:
- Order I2S audio ($27 for 6 pucks)
- Add real voice/music/effects

### Next Month:
- Order SD cards ($15 for 6 pucks)
- Load 10,000 trivia questions
- Add high score persistence

### Later:
- Order ESP32-CAM ($36 for 6 pucks)
- Add AR games
- QR scavenger hunts

---

## 🐛 Troubleshooting

### Puck Won't Connect to WiFi

**Check**:
- [ ] SSID/password correct in code
- [ ] Router is 2.4 GHz (ESP32 doesn't support 5 GHz)
- [ ] MAC filtering disabled on router

**Fix**:
```cpp
// Update WiFi credentials
const char* WIFI_SSID = "YOUR_NETWORK_NAME";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Re-upload
pio run -e puck1 -t upload
```

---

### OTA Upload Fails

**Check**:
- [ ] Puck connected to WiFi
- [ ] Laptop on same network
- [ ] Firewall allows port 3232
- [ ] Ping puck IP: `ping 192.168.1.101`

**Fix**:
```bash
# Use IP address instead of hostname
pio run -e puck1_ota -t upload --upload-port 192.168.1.101
```

---

### ESP-NOW Messages Not Received

**Check**:
- [ ] Both pucks initialized ESP-NOW
- [ ] Both on same WiFi channel
- [ ] Within 100m range

**Debug**:
```bash
# Type in serial monitor
espnow    # Test ESP-NOW

# Watch for:
# ✅ ESP-NOW initialized
# ✅ Found Puck X
```

---

### Touch Sensors Not Working

**Check**:
- [ ] Wires connected to correct GPIO pins
- [ ] Copper tape making good contact
- [ ] Calibration ran: `calibrateTouchSensors()`

**Debug**:
```bash
# Type in serial monitor
touch

# Watch for raw values:
# T0 (GPIO 4): 12  ← Low = touching
# T2 (GPIO 2): 45  ← High = not touching
```

**Adjust sensitivity**:
```cpp
// In capacitive_touch.h
#define TOUCH_THRESHOLD 40  // Lower = more sensitive
```

---

### Server Won't Start

**Check**:
- [ ] Python 3 installed
- [ ] Flask installed: `pip3 install flask`
- [ ] Port 5001 not in use

**Fix**:
```bash
# Kill process on port 5001
lsof -ti:5001 | xargs kill -9

# Restart server
python3 app.py
```

---

## 📞 Support

**Documentation**:
- QUICK_START_GUIDE.md
- FEATURES_REALITY_CHECK.md
- CAPACITIVE_TOUCH_WIRING_GUIDE.md
- MULTIPLAYER_GAMES_EXAMPLES.md
- FEATURE_IMPACT_GUIDE.md

**Issues**:
Check serial monitor output for error messages.

---

**You did it! Enjoy your upgraded pucks!** 🎮✨
