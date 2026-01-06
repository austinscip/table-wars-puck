# TRIVIA WARS - Curated Session System

## 📊 Current Status

**Server Running:** http://localhost:5001
**Total Questions:** 34 (14 easy, 16 medium, 4 hard)
**Game Types:** 10 different trivia game modes
**Categories:** 11 question categories
**Session Structure:** 3 rounds of trivia with 2 skill game breaks

---

## ❓ Answering Your Questions

### 1. What was the "41 trivia games"?

There are **10 trivia game types**, not 41:
1. Shake Attack
2. Category Royale
3. Multiplier Madness
4. Screw Your Neighbor
5. Fact or Crap
6. Hostage Trivia
7. Speed Pyramid
8. Trivia Gauntlet
9. Chaos Round
10. All or Nothing

Combined with **51 skill games** from ESP32 firmware = **61 total games** in the system.

### 2. Category vs Game Type - What's the Difference?

**Categories (11 total)** = WHAT questions are ABOUT:
- Ways to Die Stupidly
- Florida Man Headlines
- Medical Malpractice
- Historical Dumbassery
- Things That Got Banned
- General Knowledge
- Rejected Inventions
- Terrible Life Advice
- When Animals Attack
- Criminal Masterminds
- Weird Laws

**Game Types (10 total)** = HOW the game is PLAYED:
- Category Royale: Shake to pick category
- Multiplier Madness: Spin for point multipliers
- Speed Pyramid: Fast answers = more points
- Trivia Gauntlet: 3 strikes elimination
- Etc.

**Example:** A "Medical Malpractice" question (category) can be played in "Speed Pyramid" (game type) where answering fast = more points.

### 3. Question Volume

✅ **Current:** 34 questions for demo
📈 **Future:** 200-500+ questions for production
🎯 **Right now:** Good enough to demo the curated session flow

### 4. Question Balance

✅ **Fixed:** No longer all absurd and hard
✅ **Distribution:**
  - 14 easy (41%)
  - 16 medium (47%)
  - 4 hard (12%)

✅ **Style Mix:**
  - Some absurd scenarios (gangrene, Darwin Awards)
  - Some straightforward (Mars = Red Planet)
  - Some educational scenarios (scuba diving decompression)
  - ALL have clear correct answers

---

## 🎮 Curated 20-Minute Session Structure

```
START
  ↓
ROUND 1: 5 Trivia Questions (Easy → Medium → Medium → Easy → Medium)
  ↓
SKILL BREAK 1: Pick from 51 games, winner gets +500 points
  ↓
ROUND 2: 5 Trivia Questions (Medium → Hard → Easy → Medium → Medium)
  ↓
SKILL BREAK 2: Pick from 51 games, winner gets +500 points
  ↓
ROUND 3: 5 Trivia Questions (Easy → Medium → Medium → Hard → Medium)
  ↓
FINAL RESULTS: Leaderboard with podium, skill break winners, stats
```

**Total Time:** ~20 minutes
- 15 trivia questions @ 30 sec each = 7.5 min
- 2 skill breaks @ 2 min each = 4 min
- Results/transitions = 2 min
- Buffer = 6.5 min

---

## 🚀 How to Play (Demo)

### 1. Open Customer Dashboard
```
http://localhost:5001/bar/demo-bar/table/1
```

### 2. Select "TRIVIA WARS" Mode

### 3. Pick a Game Type
- Try "Category Royale" or "Speed Pyramid" for starters

### 4. Play Through Session
- **Round 1:** Answer 5 questions
- **Skill Break:** Simulated 5-second skill game
- **Round 2:** Answer 5 questions
- **Skill Break:** Simulated 5-second skill game
- **Round 3:** Answer 5 questions
- **Results:** View final podium and stats

### 5. View Results Page
Shows:
- 🥇🥈🥉 Podium with top 3 players
- Accuracy percentages
- Skill break winners
- Total stats

---

## 📁 New Files Created

### Core Session Manager
- **trivia_session_manager.py** - Handles curated session flow
  - Tracks current phase (trivia/skill break/results)
  - Auto-selects difficulty mix (40% easy, 40% medium, 20% hard)
  - Manages skill break integration
  - Calculates final results

### Updated Routes
- **trivia_routes.py** - Extended with new endpoints:
  - `GET /api/trivia/session/<code>` - Get current phase
  - `GET /api/trivia/question/<code>` - Load next question (auto difficulty)
  - `POST /api/trivia/answer` - Submit with phase checking
  - `POST /api/trivia/skill-break/start` - Start skill game
  - `POST /api/trivia/skill-break/complete` - Record winner
  - `GET /api/trivia/results/<code>` - Final stats

### Templates
- **customer_dashboard_v2.html** - Updated gameplay:
  - Mode selection (Trivia vs Free Play)
  - Progress indicator (Round X • Question Y/5)
  - Phase-aware question loading
  - Skill break integration
  - Auto-redirect to results

- **trivia_results.html** - Results page:
  - Podium display (🥇🥈🥉)
  - Player stats (score, accuracy, avg time)
  - Skill break winners
  - Play Again button

### Questions
- **trivia_questions_balanced.py** - 10 balanced questions:
  - 3 easy (straightforward)
  - 5 medium (mix of absurd and educational)
  - 2 hard (obscure but real facts)

---

## 🎯 API Flow Example

### Start Session
```bash
curl -X POST http://localhost:5001/api/trivia/start \
  -H "Content-Type: application/json" \
  -d '{
    "bar_slug": "demo-bar",
    "table_number": 1,
    "game_type": "category_royale",
    "players": [
      {"puck_id": 1, "player_name": "Player 1"},
      {"puck_id": 2, "player_name": "Player 2"}
    ]
  }'

Response: {"success": true, "session_code": "ABC123", ...}
```

### Check Session State
```bash
curl http://localhost:5001/api/trivia/session/ABC123

Response:
{
  "phase": "trivia_round",  // or "skill_break" or "final_results"
  "round": 1,
  "questions_completed": 2,
  "total_questions": 15,
  "skill_breaks_completed": 0,
  "time_remaining": 1080
}
```

### Load Question (Auto Difficulty)
```bash
curl http://localhost:5001/api/trivia/question/ABC123

Response:
{
  "success": true,
  "question": {
    "id": 5,
    "setup": "Your dad stepped on a rusty nail...",
    "question": "What's your move?",
    "answers": {"A": "Cut off foot", "B": "Essential oils", ...},
    "difficulty": "medium",
    "category": "Medical Malpractice"
  },
  "round": 1,
  "question_number": 3  // 3 of 5
}
```

### Submit Answer
```bash
curl -X POST http://localhost:5001/api/trivia/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_code": "ABC123",
    "puck_id": 1,
    "question_id": 5,
    "answer": "A",
    "response_time_ms": 3500
  }'

Response:
{
  "success": true,
  "is_correct": true,
  "points": 1000,
  "commentary": "Correct! Gangrene spreads fast...",
  "next_phase": "next_question"  // or "skill_break_needed" or "session_complete"
}
```

### Start Skill Break
```bash
curl -X POST http://localhost:5001/api/trivia/skill-break/start \
  -H "Content-Type: application/json" \
  -d '{"session_code": "ABC123"}'

Response:
{
  "success": true,
  "skill_game": {"id": 3, "name": "Spin Champion"},
  "message": "Get ready to play Spin Champion!"
}
```

### Complete Skill Break
```bash
curl -X POST http://localhost:5001/api/trivia/skill-break/complete \
  -H "Content-Type: application/json" \
  -d '{
    "session_code": "ABC123",
    "winner_puck_id": 1,
    "bonus_points": 500
  }'

Response:
{
  "success": true,
  "message": "Skill break complete! +500 bonus points awarded",
  "next_phase": "trivia_round"
}
```

---

## 🎨 Question Style Guidelines

### ✅ GOOD Examples

**Easy + Straightforward:**
```
Q: Which planet is known as the Red Planet?
A: Mars
```

**Medium + Scenario:**
```
Setup: "You're scuba diving and rush to the surface."
Q: "What's the biggest danger?"
A: The bends (nitrogen bubbles in blood)
```

**Hard + Absurd but Real:**
```
Q: "In 1788, the Austrian army killed 10,000 of their own soldiers. What caused it?"
A: They got drunk and started a brawl
```

### ❌ BAD Examples

**Too obscure, no clear answer:**
```
Q: "Grandma is on fire. What do you do?"
A: ??? (no objectively correct answer)
```

**All absurd, no variety:**
```
Every question: "Florida Man does something crazy..."
```

---

## 🔧 Next Steps

### Immediate
- ✅ Curated session structure implemented
- ✅ Skill game breaks integrated
- ✅ Question balance fixed (mix of easy/medium/hard)
- ✅ Results page with podium

### Short Term (1-2 weeks)
- [ ] Add 50+ more questions for variety
- [ ] Integrate with ESP32 puck firmware for real skill games
- [ ] WebSocket real-time updates
- [ ] TV display updates during gameplay

### Long Term (Production)
- [ ] 200-500+ questions across all categories
- [ ] Voice commentary (ElevenLabs integration)
- [ ] Advanced scoring algorithms (speed bonuses, streaks)
- [ ] Tournament mode
- [ ] Question statistics and analytics

---

## 📞 Testing the System

### Quick Test Flow
```bash
# 1. Server running
http://localhost:5001

# 2. Open customer dashboard
http://localhost:5001/bar/demo-bar/table/1

# 3. Click "TRIVIA WARS"
# 4. Pick any game type
# 5. Play through:
#    - 5 questions
#    - Skill break (5 sec simulation)
#    - 5 questions
#    - Skill break (5 sec simulation)
#    - 5 questions
#    - Results page

# 6. Should see:
#    - Podium with player scores
#    - Skill break winners
#    - Stats (15 questions answered)
```

### Admin Dashboard
```bash
# View all questions
http://localhost:5001/admin
# Click "🎭 Trivia Questions"
# Should see 34 questions
# Filter by difficulty to verify mix
```

---

## 🎉 Summary

**What Changed:**
1. Built curated 20-minute session system (not endless trivia)
2. Integrated skill game breaks between rounds
3. Added 10 balanced questions (mix of easy/medium/hard, absurd/educational)
4. Created results page with podium
5. Clarified architecture (10 game types + 51 skill games = 61 total)
6. Explained category vs game type distinction

**Current State:**
- ✅ 34 questions (good for demo)
- ✅ 10 game types
- ✅ 11 categories
- ✅ Curated session flow working
- ✅ Skill breaks integrated
- ✅ Results page complete

**Ready For:**
- Demo gameplay
- Testing with real puck hardware
- Adding more questions
- Production deployment prep
