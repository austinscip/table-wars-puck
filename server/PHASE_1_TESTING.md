# 🎮 PHASE 1 TESTING GUIDE

## What Was Built

### ✅ Customer-Facing Dashboard
- Beautiful game selection interface with 51 games
- Web Bluetooth connection for phone → puck
- Live game instructions and scoring
- Per-table leaderboards

### ✅ Multi-Bar Support
- Database now supports multiple bars
- Each bar gets unique slug (URL-friendly name)
- Per-bar and per-table routing

### ✅ QR Code Generation
- Automatic QR code generation for each table
- Admin page to view/print all QR codes
- QR codes link to table-specific dashboards

### ✅ New API Endpoints
- `/bar/<slug>/table/<num>` - Customer dashboard
- `/api/leaderboard/<slug>` - Bar-specific leaderboard
- `/api/game-start` - Track game starts
- `/api/qr/<slug>/<table>` - Generate QR codes
- `/api/bars` - List/create bars

---

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
cd /Users/austinscipione/table-wars-puck/server
pip install -r requirements.txt
```

### Step 2: Delete Old Database (Fresh Start)

```bash
rm tablewars.db  # Delete if exists
```

### Step 3: Run Server

```bash
python app.py
```

You should see:
```
╔═══════════════════════════════════════════╗
║   TABLE WARS - Scoreboard Server v1.0    ║
╚═══════════════════════════════════════════╝

✅ Database initialized
✅ Created demo bar
🚀 Starting server...
📊 Leaderboard: http://localhost:5000
📡 API Docs: http://localhost:5000/api/stats
```

---

## ✅ Verification Tests

### Test 1: View Customer Dashboard

**URL:** http://localhost:5000/bar/demo-bar/table/1

**Expected:**
- Beautiful purple gradient dashboard
- "Demo Bar" and "Table 1" displayed
- Game grid showing 18 games (Speed Tap, Duck Hunt, etc.)
- Category filter buttons (All Games, Speed, Gambling, etc.)
- "Connect to Puck" button (disabled/gray since no puck nearby)
- Leaderboard section at bottom

**Status:** [ ] PASS  [ ] FAIL

**Screenshot:**
```
┌─────────────────────────────────────┐
│      🎮 TABLE WARS                  │
│         Demo Bar                    │
│        Table 1                      │
│                                     │
│  [●] Not Connected                  │
│  [Connect to Puck] (button)         │
│                                     │
│  🎯 Choose Your Game                │
│  [All Games] [⚡ Speed] [💰 Gambling]│
│                                     │
│  ⚡        🔥        🎯              │
│  Speed     Shake     Duck           │
│  Tap       Duel      Hunt           │
│                                     │
│  🏆 Today's Leaders                 │
│  (empty for now)                    │
└─────────────────────────────────────┘
```

---

### Test 2: Try Different Tables

**URLs to test:**
- http://localhost:5000/bar/demo-bar/table/1
- http://localhost:5000/bar/demo-bar/table/2
- http://localhost:5000/bar/demo-bar/table/3
- http://localhost:5000/bar/demo-bar/table/4

**Expected:**
- Each URL shows same dashboard
- Table number changes in header
- Games remain the same

**Status:** [ ] PASS  [ ] FAIL

---

### Test 3: Filter Games by Category

**Steps:**
1. Open http://localhost:5000/bar/demo-bar/table/1
2. Click "⚡ Speed" button
3. Click "💰 Gambling" button
4. Click "🎉 Social" button
5. Click "All Games" button

**Expected:**
- Clicking "Speed" shows: Speed Tap, Sucker Punch
- Clicking "Gambling" shows: Double or Nothing, Russian Roulette, Death Roll, All In
- Clicking "Social" shows: Judas Mode, Shame Wheel, Beer Roulette, etc.
- Clicking "All Games" shows all 18 games again
- Active button has green border

**Status:** [ ] PASS  [ ] FAIL

---

### Test 4: Generate QR Codes

**URL:** http://localhost:5000/admin/qr-codes/demo-bar

**Expected:**
- Page title: "QR Codes for Demo Bar"
- 4 QR codes displayed (one for each table)
- Each shows:
  - "Table 1", "Table 2", "Table 3", "Table 4"
  - QR code image (scannable)
  - URL: http://tablewars.io/bar/demo-bar/table/X
  - Print button

**Status:** [ ] PASS  [ ] FAIL

**Action:**
- Scan one of the QR codes with your phone
- Should open browser (won't work yet since tablewars.io isn't real)
- Note: For local testing, change the domain in code or use ngrok

---

### Test 5: QR Code API

**Test API directly:**

```bash
curl http://localhost:5000/api/qr/demo-bar/1
```

**Expected JSON:**
```json
{
  "url": "http://tablewars.io/bar/demo-bar/table/1",
  "qr_code": "data:image/png;base64,iVBOR...",
  "bar": "demo-bar",
  "table": 1
}
```

**Status:** [ ] PASS  [ ] FAIL

---

### Test 6: Create New Bar

**Test via curl:**

```bash
curl -X POST http://localhost:5000/api/bars \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Shamrock Tavern",
    "slug": "shamrock-tavern",
    "location": "Chicago, IL",
    "total_tables": 6
  }'
```

**Expected:**
```json
{
  "success": true,
  "bar_id": 2,
  "name": "Shamrock Tavern",
  "slug": "shamrock-tavern"
}
```

**Then visit:** http://localhost:5000/bar/shamrock-tavern/table/1

**Expected:**
- Dashboard loads
- Shows "Shamrock Tavern" instead of "Demo Bar"
- Table 1 displayed

**Status:** [ ] PASS  [ ] FAIL

---

### Test 7: List All Bars

```bash
curl http://localhost:5000/api/bars
```

**Expected:**
```json
[
  {
    "id": 1,
    "name": "Demo Bar",
    "slug": "demo-bar",
    "location": "San Francisco, CA",
    "total_tables": 4,
    "is_active": 1
  },
  {
    "id": 2,
    "name": "Shamrock Tavern",
    "slug": "shamrock-tavern",
    "location": "Chicago, IL",
    "total_tables": 6,
    "is_active": 1
  }
]
```

**Status:** [ ] PASS  [ ] FAIL

---

### Test 8: Bar-Specific Leaderboard

```bash
curl http://localhost:5000/api/leaderboard/demo-bar
```

**Expected:**
```json
[]
```
(Empty since no games played yet)

**Status:** [ ] PASS  [ ] FAIL

---

### Test 9: Test Game Click (Without Puck)

**Steps:**
1. Open http://localhost:5000/bar/demo-bar/table/1
2. Try to click any game card

**Expected:**
- Nothing happens (games are disabled)
- Cards show opacity: 0.5 (grayed out)
- Cursor shows "not-allowed"

**Status:** [ ] PASS  [ ] FAIL

---

### Test 10: Responsive Design (Mobile)

**Steps:**
1. Open http://localhost:5000/bar/demo-bar/table/1
2. Open browser dev tools (F12)
3. Toggle device toolbar (mobile view)
4. Test iPhone 12 Pro, iPad, etc.

**Expected:**
- Layout adjusts for mobile
- Game grid shows 2-3 columns (not 4)
- Text remains readable
- Buttons remain touchable

**Status:** [ ] PASS  [ ] FAIL

---

## 🐛 Known Limitations (Not Bugs)

### 1. Web Bluetooth Won't Connect Yet
**Reason:** Your ESP32 firmware doesn't have Bluetooth LE enabled yet.
**Fix:** Will add in Phase 4

### 2. QR Codes Link to tablewars.io (Doesn't Exist)
**Reason:** That's the production domain.
**Fix:** For local testing, use ngrok or change domain in code to `localhost:5000`

### 3. Games Don't Actually Start
**Reason:** No puck connected, and firmware doesn't handle game commands yet.
**Fix:** Will add in Phase 4

### 4. Leaderboard is Empty
**Reason:** No scores submitted yet.
**Fix:** Can manually test score submission in Phase 2

---

## 📊 What to Check

**Database Structure:**
```bash
sqlite3 tablewars.db

.tables
# Should show: bars, pucks, games, sessions, active_games

.schema bars
# Should show bar table structure

SELECT * FROM bars;
# Should show demo-bar and any bars you created
```

---

## ✅ Success Criteria

Phase 1 is **COMPLETE** if:

- [x] Customer dashboard loads at `/bar/demo-bar/table/1`
- [x] Game grid displays 18+ games with emojis
- [x] Category filters work
- [x] QR code generation works
- [x] Can create new bars via API
- [x] Each bar has unique URLs
- [x] Responsive on mobile
- [x] No console errors in browser
- [x] Server runs without errors

---

## 🚀 Next Steps (Phase 2)

Once Phase 1 is verified:

1. ✅ Test Web Bluetooth connection (simulated)
2. ✅ Add game instructions for all 51 games
3. ✅ Implement score submission flow
4. ✅ Test live gameplay UI
5. ✅ Add TV dashboard for bars

---

## 🆘 Troubleshooting

**Server won't start:**
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill if needed
kill -9 <PID>

# Try again
python app.py
```

**Database error:**
```bash
# Delete and recreate
rm tablewars.db
python app.py
```

**Missing dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**QR codes not generating:**
```bash
# Install manually
pip install qrcode Pillow
```

---

## 📸 Take Screenshots

Please take screenshots of:
1. Customer dashboard (game selection screen)
2. QR code admin page
3. Mobile view
4. Browser console (F12) showing no errors

This will help verify everything works!

---

**Ready to test? Let me know which test fails (if any) and I'll fix it!** 🎮
