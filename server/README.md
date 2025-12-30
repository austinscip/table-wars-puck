# TABLE WARS - Scoreboard Server

Flask + WebSocket server for real-time leaderboard and score tracking.

## Features

- ✅ REST API for score submission
- ✅ SQLite database for persistence
- ✅ Real-time WebSocket updates
- ✅ Beautiful web-based leaderboard
- ✅ Player statistics tracking
- ✅ Session management

## Quick Start

### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Run Server

```bash
python app.py
```

### 3. Access Leaderboard

Open browser to: **http://localhost:5000**

---

## API Endpoints

### Register Puck

```bash
POST /api/register
Content-Type: application/json

{
  "puck_id": 1,
  "name": "Puck_1",
  "table_number": 1,
  "battery_level": 85
}
```

### Submit Score

```bash
POST /api/score
Content-Type: application/json

{
  "puck_id": 1,
  "game_type": "Speed Tap Battle",
  "score": 470,
  "session_id": "optional"
}
```

### Get Leaderboard

```bash
GET /api/leaderboard?limit=10
```

Response:
```json
[
  {
    "id": 1,
    "name": "Puck_1",
    "table_number": 1,
    "games_played": 25,
    "total_score": 15430,
    "avg_score": 617,
    "high_score": 980
  }
]
```

### Get Recent Games

```bash
GET /api/recent?limit=20
```

### Get Stats

```bash
GET /api/stats
```

Response:
```json
{
  "total_pucks": 6,
  "total_games": 142,
  "total_score": 87340
}
```

---

## ESP32 Integration

Add this to your puck firmware to submit scores:

```cpp
#include <HTTPClient.h>

void submitScore(uint8_t puckID, const char* gameType, uint32_t score) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;

        http.begin("http://YOUR_SERVER_IP:5000/api/score");
        http.addHeader("Content-Type", "application/json");

        String payload = "{";
        payload += "\"puck_id\":" + String(puckID) + ",";
        payload += "\"game_type\":\"" + String(gameType) + "\",";
        payload += "\"score\":" + String(score);
        payload += "}";

        int httpCode = http.POST(payload);

        if (httpCode == 200) {
            Serial.println("✅ Score submitted");
        } else {
            Serial.printf("❌ Submit failed: %d\n", httpCode);
        }

        http.end();
    }
}
```

---

## WebSocket Events

### Client → Server

- `connect` - Establish connection
- `request_leaderboard` - Request leaderboard update

### Server → Client

- `connected` - Connection established
- `score_update` - New score posted
  ```json
  {
    "puck_id": 1,
    "game_type": "Speed Tap Battle",
    "score": 470,
    "timestamp": "2024-01-15T10:30:00"
  }
  ```
- `puck_online` - New puck registered
  ```json
  {
    "puck_id": 1,
    "name": "Puck_1",
    "table_number": 1
  }
  ```
- `leaderboard_update` - Full leaderboard data

---

## Deployment

### Run on Raspberry Pi (at bar)

1. **Install Python 3**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

2. **Clone and setup**
   ```bash
   git clone <your-repo>
   cd table-wars-puck/server
   pip3 install -r requirements.txt
   ```

3. **Run as service**
   Create `/etc/systemd/system/tablewars.service`:
   ```ini
   [Unit]
   Description=TABLE WARS Scoreboard Server
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/table-wars-puck/server
   ExecStart=/usr/bin/python3 app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and start**
   ```bash
   sudo systemctl enable tablewars
   sudo systemctl start tablewars
   ```

5. **Access from bar WiFi**
   - Find Pi's IP: `hostname -I`
   - Access: `http://<pi-ip>:5000`

### Display on Bar TV

**Option 1: Raspberry Pi + HDMI**
- Connect Pi to bar TV via HDMI
- Set Chromium to kiosk mode:
  ```bash
  chromium-browser --kiosk --app=http://localhost:5000
  ```

**Option 2: Any device with browser**
- iPad/tablet in kiosk stand
- Open browser to server URL
- Enable auto-refresh

---

## Database Schema

### `pucks` Table
```sql
id                 INTEGER PRIMARY KEY
name               TEXT NOT NULL
table_number       INTEGER
battery_level      INTEGER
is_online          BOOLEAN
last_seen          TIMESTAMP
total_games_played INTEGER
```

### `games` Table
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
puck_id     INTEGER (FK to pucks)
game_type   TEXT
score       INTEGER
timestamp   TIMESTAMP
session_id  TEXT
```

### `sessions` Table
```sql
id          TEXT PRIMARY KEY
table_number INTEGER
start_time   TIMESTAMP
end_time     TIMESTAMP
total_pucks  INTEGER
is_active    BOOLEAN
```

---

## Troubleshooting

**Port already in use:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>
```

**Database locked:**
```bash
# Reset database
rm tablewars.db
python app.py  # Will recreate
```

**WebSocket not connecting:**
- Check firewall allows port 5000
- Verify server IP is accessible from client
- Check browser console for errors

---

## Future Enhancements

- [ ] Bar vs Bar leaderboards
- [ ] Player profiles with avatars
- [ ] Achievement system
- [ ] Tournament brackets
- [ ] Historical analytics
- [ ] Mobile app integration
- [ ] Social media sharing
- [ ] Prize/reward system

---

**Questions? Issues?**
Open an issue on GitHub or check the main README.md
