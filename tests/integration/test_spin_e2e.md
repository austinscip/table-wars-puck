# End-to-End Test: Puck Spin to Browser Display

## Sprint 0D Acceptance Criteria
Physical puck spin -> gateway receives -> server receives -> browser displays gyro_z within 500ms

## Test Setup

### Prerequisites
1. Server running: `cd server && python app.py`
2. Browser open to any TV game with debug panel OR the puck simulator

### Using Puck Simulator (Recommended for Testing Without Hardware)

1. Navigate to: http://localhost:5001/test/puck-simulator
2. Use the simulator controls to send sensor data
3. Open a second browser tab to any TV game (e.g., http://localhost:5001/tv/puck-racer/1)
4. Verify the debug panel updates in real-time

### Using Physical Hardware

1. Upload firmware to ESP32 puck: `pio run -e puck1 -t upload`
2. Monitor serial output: `pio device monitor --baud 115200`
3. Verify serial shows: `TX: tilt_x=X.X tilt_y=X.X gyro_z=X.XXXX spin=X.X shake=no`
4. Gateway ESP32 should forward data to server via WebSocket
5. Browser debug panel should update in real-time

## Test Cases

### TC-001: Gyro Z Display Update
**Steps:**
1. Start server
2. Open browser to TV game with debug panel
3. Use puck simulator to send gyro_z = 0.5
4. Observe debug panel

**Expected:**
- Gyro Z value shows "0.5000"
- Update occurs within 500ms of send

### TC-002: Spin Speed Display
**Steps:**
1. Use puck simulator to send spin_speed = 150
2. Observe debug panel

**Expected:**
- Spin shows "150.0 deg/s"
- "FAST" indicator appears in red

### TC-003: Shake Detection
**Steps:**
1. Use puck simulator to send shake_detected = true, shake_intensity = 15
2. Observe debug panel

**Expected:**
- Shake shows "15.0 m/s^2"
- "SHAKING!" indicator appears in red

### TC-004: Tilt Values
**Steps:**
1. Use puck simulator to send tilt_x = 45, tilt_y = -30
2. Observe debug panel

**Expected:**
- Tilt X shows "45.0 deg"
- Tilt Y shows "-30.0 deg"

## Sprint 0 Complete When
- [ ] All test cases pass
- [ ] Latency from simulator send to browser display < 500ms
- [ ] Debug panel shows all sensor fields correctly

## Notes
- Gateway hardware not yet implemented - using direct WebSocket for testing
- For production, gateway ESP32 will bridge ESP-NOW to WebSocket
