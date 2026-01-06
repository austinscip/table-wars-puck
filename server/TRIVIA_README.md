# TRIVIA WARS - YDKJ-Style Trivia System

Complete implementation of a You Don't Know Jack inspired trivia game system for TABLE WARS pucks.

## 🎮 What's Included

### Database Schema
- **trivia_categories** - 10 absurd categories (Ways to Die Stupidly, Florida Man, etc.)
- **trivia_questions** - 30+ YDKJ-style questions with setup text, answers, and snarky commentary
- **trivia_game_types** - 10 different game modes with unique mechanics
- **trivia_sessions** - Track active game sessions
- **trivia_answers** - Record player answers and scores

### Game Engines (7/10 Complete)
1. ✅ **Category Royale** - Players shake to pick category
2. ✅ **Multiplier Madness** - Spin puck for risk/reward multipliers
3. ✅ **Screw Your Neighbor** - Pay points to force opponents to answer
4. ✅ **Speed Pyramid** - Speed-based scoring tiers
5. ✅ **Trivia Gauntlet** - Elimination mode (3 strikes you're out)
6. ✅ **Fact or Crap** - True/False with tilt controls
7. ✅ **Hostage Trivia** - One player vs everyone (reversed scoring)
8. ⏸️ Chaos Round - Random modifiers (TODO)
9. ⏸️ All or Nothing - Final question bet (TODO)
10. ⏸️ Shake Attack - Rapid-fire Jack Attack style (TODO)

### Web Interfaces
- **TV Display** (`/trivia/tv/<session_code>`) - Large screen display for bars
- **Admin Dashboard** (`/admin` > Trivia Questions) - Manage questions and categories

## 🚀 Setup

### 1. Start the Server
```bash
cd server
python app.py
```

The server will automatically:
- Initialize trivia database tables
- Seed game types and categories
- Load 30+ sample questions (if database is empty)
- Start Flask server on port 5001

### 2. Access Admin Dashboard
```
http://localhost:5001/admin
```

Navigate to **🎭 Trivia Questions** section to:
- View all questions
- Filter by category/difficulty
- Add new questions
- See category stats

## 📝 Adding Questions

### Via Admin Dashboard
1. Go to `http://localhost:5001/admin`
2. Click "🎭 Trivia Questions"
3. Click "+ Add Question"
4. Fill in the form:
   - **Category** - Select from dropdown
   - **Setup Text** - Optional narrative setup
   - **Question Text** - The actual question
   - **4 Answers** (A, B, C, D)
   - **Correct Answer** - Which letter is right
   - **Difficulty** - Easy/Medium/Hard
   - **Time Limit** - Seconds (default 15)
   - **Explanation** - Why that answer is correct
   - **Commentary (Correct)** - Snarky host response
   - **Commentary (Wrong)** - Snarky host response
5. Click "Create Question"

### Via Code
Add questions to `trivia_questions_seed.py`:

```python
{
    'category': 'Ways to Die Stupidly',
    'setup': "Chuck thought it'd be hilarious to...",
    'question': "What actually happened?",
    'answers': {
        'A': "Turkey exploded",
        'B': "It was delicious",
        'C': "Turkey attacked him",
        'D': "Nothing happened"
    },
    'correct': 'A',
    'explanation': "Water + hot oil = boom",
    'commentary_correct': "Correct! Physics is a bitch.",
    'commentary_wrong': "Wrong! It's ALWAYS the explosion.",
    'difficulty': 'easy',
    'time_limit': 15
}
```

Then run:
```bash
python trivia_questions_seed.py
```

## 🎯 API Endpoints

### Session Management
```
POST /api/trivia/start
  - Start new trivia session
  - Returns: session_code, tv_url

GET /api/trivia/session/<session_code>
  - Get current session state

GET /api/trivia/question/<session_code>
  - Load next question

POST /api/trivia/answer
  - Submit player answer
  - Returns: is_correct, points, commentary

GET /api/trivia/results/<session_code>
  - Get round results
```

### Admin
```
GET /api/trivia/categories
  - List all categories

GET /api/trivia/game-types
  - List all game types

GET /api/trivia/admin/questions
  - List all questions (with category names)

POST /api/trivia/admin/questions
  - Create new question
```

## 🎮 Game Flow Example

### 1. Start Session
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
```

Response:
```json
{
  "success": true,
  "session_code": "ABC123",
  "tv_url": "/trivia/tv/ABC123"
}
```

### 2. Open TV Display
Navigate to: `http://localhost:5001/trivia/tv/ABC123`

### 3. Load Question
```bash
curl http://localhost:5001/api/trivia/question/ABC123
```

### 4. Submit Answer
```bash
curl -X POST http://localhost:5001/api/trivia/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_code": "ABC123",
    "puck_id": 1,
    "answer": "A",
    "response_time_ms": 3500
  }'
```

## 📊 Database Schema

### Key Tables
```sql
trivia_categories
  - id, name, emoji, description, difficulty

trivia_questions
  - id, category_id, question_text, setup_text
  - answer_a, answer_b, answer_c, answer_d
  - correct_answer, explanation
  - host_commentary_correct, host_commentary_wrong
  - difficulty, time_limit

trivia_sessions
  - id, bar_id, table_number, game_type_id
  - session_code, status, current_round

trivia_answers
  - id, session_id, question_id, puck_id
  - answer_given, is_correct, response_time_ms
  - points_earned, multiplier_used
```

## 🎨 YDKJ Style Guidelines

When writing questions, follow these patterns:

### 1. Absurd Setup + Real Outcome
```
Setup: "A man in Russia decided to play chicken with his friends."
Question: "What did he use instead of a car?"
Answer: "A hand grenade"
```

### 2. Dark Humor Darwin Awards
```
Category: Ways to Die Stupidly
Focus: Natural selection fails, physics lessons, common sense violations
```

### 3. Snarky Commentary
```
Correct: "Correct! Chuck learned that frozen + 350°F oil = insurance claim!"
Wrong: "Wrong! It's ALWAYS the explosion. Rule #1: thaw first, blow up never."
```

### 4. Real-World Absurdity
- Florida Man headlines
- Banned inventions/products
- Historical stupidity
- Criminal masterminds (who got caught immediately)

## 🔧 Troubleshooting

### Questions Not Loading
```bash
# Check if questions exist
sqlite3 tablewars.db "SELECT COUNT(*) FROM trivia_questions;"

# Re-seed if empty
python trivia_questions_seed.py
```

### Categories Not Showing
```bash
# Check categories
sqlite3 tablewars.db "SELECT * FROM trivia_categories;"

# Re-initialize
python trivia_database.py
```

### Port Already in Use
Edit `app.py` line 637:
```python
socketio.run(app, host='0.0.0.0', port=5002, debug=True)
```

## 📁 File Structure

```
server/
├── app.py                      # Main Flask app (trivia integrated)
├── trivia_routes.py           # API endpoints
├── trivia_database.py         # Database schema
├── trivia_game_engines.py     # Game logic (7 engines)
├── trivia_questions_seed.py   # 30+ sample questions
├── templates/
│   ├── admin_dashboard.html   # Admin UI (trivia section added)
│   └── trivia_tv.html         # TV display
└── tablewars.db               # SQLite database
```

## 🚧 TODO - Remaining Work

### 3 Game Engines
- Chaos Round (random modifiers)
- All or Nothing (final question bet)
- Shake Attack (rapid-fire Jack Attack)

### Features
- Delete question endpoint
- Edit question UI
- Category management (add/edit categories)
- Question statistics (correct %, avg response time)
- WebSocket real-time updates
- Voice commentary generation (ElevenLabs integration)

## 📞 Testing

```bash
# 1. Start server
python app.py

# 2. Open admin dashboard
open http://localhost:5001/admin

# 3. Click "Trivia Questions" - should see 30+ questions

# 4. Test adding a question
# 5. Test starting a session via API
# 6. Open TV display URL
```

## 🎉 Next Steps

1. **Complete remaining 3 game engines**
2. **Add more questions** (need 200-500 for production)
3. **Integrate with ESP32 puck firmware**
4. **Set up WebSocket for real-time updates**
5. **Add voice commentary generation**
6. **Test with actual hardware**

---

Built with Flask, SQLite, and absurd humor. 🎭
