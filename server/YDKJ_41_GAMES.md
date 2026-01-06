# 41 YDKJ-STYLE TRIVIA GAMES FOR TABLE WARS PUCKS

Inspired by Jackbox Party Pack games, adapted for ESP32 puck hardware (shake, tilt, spin, tap, hold).

---

## CORE TRIVIA GAMES (Traditional Question-Based)

### 1. **Trivia Murder Party**
- **Concept:** Horror-themed trivia with "Killing Floor" mini-games
- **Puck Mechanics:**
  - Answer questions via TILT (A=left, B=right, C=forward, D=back)
  - Wrong answer = mini-game (SHAKE to escape, SPIN for roulette, TAP timing)
  - Last survivor wins
- **Example:** "Your grandma's on fire. What chemical compound is making her smell like bacon?" Wrong answer = SHAKE to extinguish flames or die
- **Difficulty:** Hard

### 2. **Category Royale** (EXISTING)
- **Concept:** Players SHAKE to claim categories first
- **Example:** First to SHAKE picks "Ways to Die Stupidly" vs "Florida Man"

### 3. **Speed Pyramid** (EXISTING)
- **Concept:** Answer speed determines point tiers (Gold/Silver/Bronze)
- **Puck Mechanics:** TILT answer + TAP to lock in
- **Example:** "What gas kills you at 78% concentration?" First 3 sec = 1000pts

### 4. **Fact or Crap**
- **Concept:** True/False with absurd scenarios
- **Puck Mechanics:** TILT LEFT = Fact, TILT RIGHT = Crap, HOLD = Double Down
- **Example:** "Florida Man arrested for teaching alligators to breakdance. Fact or Crap?"

### 5. **You Don't Know Jack: Puck Edition**
- **Concept:** Classic YDKJ with puck screws
- **Puck Mechanics:** SHAKE + HOLD to screw opponent, forcing them to answer
- **Example:** Standard YDKJ absurdity with gangrene-style questions

### 6. **Multiplier Madness** (EXISTING)
- **Concept:** SPIN puck before each question for risk/reward multiplier
- **Fast spin = 5x points or -5x penalty**

### 7. **The Wheel of Enormous Proportions**
- **Concept:** Trivia + physical wheel spinning for bonus points
- **Puck Mechanics:** Answer trivia, then SPIN puck to land on point zones
- **Example:** Correct answer = unlock wheel, fastest SPIN = biggest multiplier

### 8. **Guesspionage**
- **Concept:** Guess percentages of survey results
- **Puck Mechanics:** TILT to adjust percentage (0-100), TAP to lock in
- **Example:** "What % of people have texted while driving?" Closest guess wins

### 9. **Trivia Gauntlet** (EXISTING)
- **Concept:** 3 strikes elimination mode
- **Last puck standing wins**

### 10. **Timejinx**
- **Concept:** Guess the year events happened
- **Puck Mechanics:** TILT to adjust year (1900-2025), TAP to submit
- **Example:** "When did Hitler shoot himself?" (Closest to 1945 wins)

---

## LIE DETECTION & DECEPTION GAMES

### 11. **Fibbage: Puck Lies**
- **Concept:** Players create lies, vote for truth (adapted from Fibbage)
- **Puck Mechanics:**
  - Pre-game: Use TV display to enter text lies on phone
  - In-game: TILT through options, TAP to vote
- **Example:** "What did the Austrian army use to kill 10,000 of their own men?" (Players submit fake answers, vote for real one)

### 12. **Survive the Internet**
- **Concept:** Twist other players' quotes out of context
- **Puck Mechanics:** Players speak quotes into puck mic, others SPIN to select twist category
- **Example:** P1 says "I love animals" → P2 twists to "...as food" → TAP to vote

### 13. **Split the Room**
- **Concept:** Create divisive scenarios to split votes evenly
- **Puck Mechanics:** TILT LEFT or RIGHT to vote, points for even split
- **Example:** "You can fly but every time you fart, a puppy dies. Accept?" (Want 50/50 split)

### 14. **Hypnotorious**
- **Concept:** Find the "Outlier" whose answers don't match the secret category
- **Puck Mechanics:** Answer questions, then SHAKE to accuse outlier
- **Example:** Category = "Things at a wedding" but one player has "Things at a funeral"

### 15. **Suspectives**
- **Concept:** Social deduction - find the guilty player based on evidence
- **Puck Mechanics:** TILT through suspects, SHAKE to accuse
- **Example:** Survey says "Who double-dips chips?" Evidence points to guilty player

### 16. **Fakin' It: Puck Edition**
- **Concept:** One player is Faker, must blend in with physical actions
- **Puck Mechanics:**
  - Players get "SHAKE 3 times" but Faker gets different instruction
  - Other players TILT to vote who's fake
- **Example:** "Tap your puck to the beat" - Faker has to guess the beat

### 17. **Weapons Drawn**
- **Concept:** Murder mystery - deduce who killed who
- **Puck Mechanics:** SPIN creates murder "signature", players TILT to accuse
- **Example:** Each puck has unique LED flash pattern = murder weapon

---

## WORD & CREATIVITY GAMES (Adapted for Pucks)

### 18. **Quiplash: Puck Wars**
- **Concept:** Funniest answer wins (text via phone, vote via puck)
- **Puck Mechanics:** TILT LEFT/RIGHT to vote between two quips
- **Example:** "What's in Trump's wig?" Vote for funniest answer

### 19. **Mad Verse City: Rap Battle**
- **Concept:** Fill-in-the-blank rap lyrics
- **Puck Mechanics:** Pre-written lyrics, TAP to pick rhyme from options
- **Example:** "Yo mama's so fat, she ____" (A: broke the scale, B: ate the moon, etc.)

### 20. **Joke Boat**
- **Concept:** Complete joke setups
- **Puck Mechanics:** Phone for text entry, TILT to vote on jokes
- **Example:** "A man walks into a bar and ____" (Funniest completion wins)

### 21. **Dictionarium**
- **Concept:** Define fake words
- **Puck Mechanics:** Phone for definitions, TILT to vote
- **Example:** "What does 'Blorgenschmidt' mean?" (Funniest definition wins)

### 22. **FixyText**
- **Concept:** Create chaotic autocorrect fails
- **Puck Mechanics:** TILT to inject words into text template
- **Example:** "Sorry I'm late, I was ____" (Random word injection)

### 23. **Word Spud**
- **Concept:** Word association chain
- **Puck Mechanics:** TILT through word bank, TAP to select association
- **Example:** "Pizza" → Player picks "Italy" → Next picks "Rome" → etc.

### 24. **Blather 'Round**
- **Concept:** Describe things with limited vocabulary
- **Puck Mechanics:** Pre-selected phrase templates, others guess via TILT
- **Example:** "It's a thing... with four legs... you sleep on it..." (Bed)

### 25. **Nonsensory**
- **Concept:** Rate how well descriptions match prompts (1-10 scale)
- **Puck Mechanics:** TILT to adjust rating 1-10, TAP to submit
- **Example:** "How metal is 'cutting off your dad's gangrenous foot'?" (1-10)

---

## GAMBLING & RISK GAMES

### 26. **All or Nothing**
- **Concept:** Bet all your points on one final question
- **Puck Mechanics:** TILT to adjust bet amount, SHAKE to go all-in
- **Example:** "Final question: What % of your brain is water?" (Bet 0-100% of points)

### 27. **Russian Roulette Trivia**
- **Concept:** Wrong answer = progressive punishment
- **Puck Mechanics:** SPIN determines penalty severity (1x-6x point loss)
- **Example:** Each wrong answer, SPIN the puck - land on skull = lose all points

### 28. **Double or Nothing**
- **Concept:** After each correct answer, bet to double points
- **Puck Mechanics:** SHAKE to double down, HOLD to keep current points
- **Example:** Got 1000pts? SHAKE to risk for 2000 or lose it all

### 29. **Bracketeering: Trivia Tournament**
- **Concept:** Answers compete in tournament bracket
- **Puck Mechanics:** TILT to vote in head-to-head matchups
- **Example:** "Best way to die?" A vs B, C vs D → Winners face off

### 30. **Lucky Streak**
- **Concept:** Consecutive correct answers multiply points
- **Puck Mechanics:** Streak counter, miss one = reset to 1x
- **Example:** 3 in a row = 3x multiplier, 5 = 5x, etc.

---

## PHYSICAL & SKILL HYBRID GAMES

### 31. **Shake Attack** (Jack Attack style)
- **Concept:** Rapid-fire category matching
- **Puck Mechanics:** TV shows word, SHAKE when it matches category
- **Example:** Category = "Florida Man headlines" → "Arrested for riding alligator" → SHAKE!

### 32. **Screw Your Neighbor** (EXISTING)
- **Concept:** Pay points to force opponent to answer hard questions
- **Puck Mechanics:** SHAKE + HOLD to activate screw

### 33. **Hostage Trivia** (EXISTING)
- **Concept:** One player vs everyone, reversed scoring
- **Example:** If hostage answers correctly, everyone ELSE loses points

### 34. **Chaos Round**
- **Concept:** Random modifiers each question
- **Puck Mechanics:** SPIN before question to determine rule (Opposite Day, Swap Scores, etc.)
- **Example:** Landed on "Opposite Day" = wrong answer = points

### 35. **Perfect Timing**
- **Concept:** TAP puck at exact moment
- **Puck Mechanics:** TV countdown, TAP at zero for bonus points
- **Example:** "When did WWII end?" + TAP timing challenge = double points

### 36. **Balance Master**
- **Concept:** Hold puck perfectly still while answering
- **Puck Mechanics:** Accelerometer detects movement, shake = penalty
- **Example:** Answer trivia while balancing puck on forehead

### 37. **Spin Zone**
- **Concept:** Answer speed + spin speed combined score
- **Puck Mechanics:** TILT to answer, then SPIN for multiplier
- **Example:** Fast correct answer + fast spin = max points

---

## TEAM & COOPERATIVE GAMES

### 38. **The Poll Mine**
- **Concept:** Teams guess poll rankings cooperatively
- **Puck Mechanics:** TILT to select answer, team must agree or lose torch
- **Example:** "Rank: Ways to die" → Pick #1 most popular → Wrong = lose torch

### 39. **Devils and the Details**
- **Concept:** Complete family chores cooperatively but compete for selfish tasks
- **Puck Mechanics:** SHAKE for chores, HOLD for selfish tasks (builds meter)
- **Example:** "Do dishes" (team) vs "Eat all the cookies" (selfish)

### 40. **Push the Button**
- **Concept:** Find the alien impostor among crew
- **Puck Mechanics:** Aliens get different prompts, SHAKE to accuse
- **Example:** Humans see "Shake 3 times" but alien sees "Shake 5 times"

### 41. **Legends of Trivia**
- **Concept:** Cooperative RPG trivia - fight monsters together
- **Puck Mechanics:** Answer trivia to deal damage, SHAKE for power-ups
- **Example:** "What's gangrene?" = 100 damage to monster, 10 questions = boss dead

---

## DEPLOYMENT SCENARIOS

### Target Venues:
1. **Bars & Breweries** (primary) - Competitive drinking games
2. **Airport Lounges** - Time-killer for travelers
3. **Senior Living Centers** - Cognitive stimulation games
4. **College Campuses** - Dorm/frat party entertainment
5. **Corporate Events** - Team building exercises
6. **Cruise Ships** - Passenger entertainment
7. **Sports Bars** - Halftime trivia competitions
8. **Hotel Lobbies** - Guest engagement
9. **Waiting Rooms** - Medical/dental entertainment
10. **Food Courts** - Mall entertainment zones

### Venue-Specific Adaptations:
- **Senior Centers:** Slower pace, 60s-80s trivia, cognitive health tracking
- **Airports:** Quick 5-min games, luggage-safe puck design
- **Bars:** Drinking game integration, shot roulette modes
- **Corporate:** Professional questions, leadership scenarios

---

## GAME DIFFICULTY DISTRIBUTION
- **Easy (10 games):** #1, 2, 4, 8, 18, 23, 25, 30, 35, 41
- **Medium (20 games):** #3, 5, 7, 9, 11, 12, 13, 16, 19, 20, 21, 22, 24, 26, 28, 29, 31, 33, 36, 38
- **Hard (11 games):** #6, 10, 14, 15, 17, 27, 32, 34, 37, 39, 40

## SESSION STRUCTURE (20-min Curated)
```
Round 1: Pick 1 of 41 games → 5 questions
   ↓
Skill Break 1: Pick from 51 ESP32 games → +500 bonus
   ↓
Round 2: Pick different game → 5 questions
   ↓
Skill Break 2: Pick from 51 ESP32 games → +500 bonus
   ↓
Round 3: Pick different game → 5 questions
   ↓
Final Results: Podium + stats
```

## PUCK MECHANICS REFERENCE
| Action | Hardware | Use Case |
|--------|----------|----------|
| **SHAKE** | Accelerometer | Category select, rapid-fire, accusations |
| **TILT** | Accelerometer | Answer A/B/C/D, vote, adjust values |
| **SPIN** | Gyroscope | Multipliers, roulette, risk mechanics |
| **TAP** | Button | Lock in, confirm, timing challenges |
| **HOLD** | Button | Double down, screw neighbor, activate power |
| **LED Flash** | NeoPixel | Visual feedback, player ID, murder weapon |
| **Vibrate** | Motor | Wrong answer, timer warning, alerts |
| **Sound** | Piezo Buzzer | Beeps, tones, alerts (no voice) |

---

**Total Games:** 41 YDKJ-style trivia games + 51 skill games = **92 total games**

**Audio Limitations:**
- Pucks have **piezo buzzers** (not speakers)
- Can only play: beeps, tones, alerts, simple melodies
- **NO voice playback on pucks**
- Host commentary must come from TV/speakers via server

**Next Steps:**
1. Implement all 41 game engines (currently have 7)
2. Create 500+ YDKJ-style questions across all categories
3. Build TV display interfaces for each game type
4. Host commentary plays through TV speakers (ElevenLabs voice generation)
5. Puck buzzer for feedback only (correct beep, wrong buzz, timing alerts)
6. Test with real puck hardware
7. Deploy to first bar venue
