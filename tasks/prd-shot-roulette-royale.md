# PRD: SHOT ROULETTE ROYALE Game

## Introduction
SHOT ROULETTE ROYALE is a physical skill + gambling game where players spin their
puck to spin a virtual roulette wheel. Light spin = safe zone, hard spin = risk of
CHUG or BOMB, but also chance at CHAMPION. Physical spin technique creates mastery.

## Goals
1. Create compelling "one more spin" addiction through physical skill mastery
2. Support 2-8 simultaneous players (brewery group size)
3. Demonstrate screen-centric architecture with physical puck as precision input
4. Establish spin-detection patterns reusable across other games

## User Stories

### US-001: Roulette Wheel Display
As a player watching the bar screen,
I want to see a massive 3D wheel with clear prize zones,
So that I can plan my spin intensity and feel the tension.

**Acceptance Criteria:**
- [ ] 3D wheel renders with 8 zones: CHAMPION, DRINK ONE, DRINK TWO, CHUG, SPIN AGAIN, IMMUNITY, CHALLENGE, BOMB
- [ ] Each zone has distinct color and icon
- [ ] Wheel animates smoothly at 60fps
- [ ] Current spinner's name highlighted
- [ ] Zone sizes reflect probability (CHAMPION small, DRINK ONE large)
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-002: Puck Spin Detection
As a player holding my puck,
I want to physically spin my puck and have the wheel spin proportionally,
So that my physical technique affects my outcome.

**Acceptance Criteria:**
- [ ] Gyroscope Z-axis detects spin velocity (degrees/second)
- [ ] Light spin (<100 deg/s) = wheel travels 1-2 zones
- [ ] Medium spin (100-300 deg/s) = wheel travels 3-5 zones
- [ ] Hard spin (>300 deg/s) = wheel travels 6-8 zones (risky!)
- [ ] Spin data sent via WebSocket within 50ms
- [ ] LED ring shows spin intensity (blue->yellow->red gradient)
- [ ] Typecheck passes

### US-003: Wheel Physics and Resolution
As a game system,
I want realistic wheel physics with anticipation and resolution,
So that every spin feels dramatic and uncertain.

**Acceptance Criteria:**
- [ ] Wheel accelerates based on spin intensity
- [ ] Wheel decelerates with realistic friction curve
- [ ] Final 2 seconds play in slow motion for tension
- [ ] Clicking sound as wheel passes each zone
- [ ] Final zone highlighted with celebration/doom animation
- [ ] "SO CLOSE!" indicator when within 5% of adjacent zone
- [ ] Typecheck passes

### US-004: Prize Zone Effects
As a player landing on a zone,
I want immediate visual and audio feedback with clear consequences,
So that outcomes are dramatic and memorable.

**Acceptance Criteria:**
- [ ] CHAMPION: Crown animation, winner picks someone to drink
- [ ] DRINK ONE/TWO: Beer pour animation, player drinks
- [ ] CHUG: Skull animation, dramatic music, player chugs
- [ ] SPIN AGAIN: Arrows animation, immediate respin
- [ ] IMMUNITY: Shield animation, skip next penalty
- [ ] CHALLENGE: Swords animation, 1v1 mini-game prompt
- [ ] BOMB: Explosion, EVERYONE drinks (groans from crowd)
- [ ] Haptic feedback on puck matches outcome
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Multiplayer Turn Management
As a group at the bar,
I want clear turn order and scoreboard,
So that everyone stays engaged and knows who's winning.

**Acceptance Criteria:**
- [ ] Player queue displayed (who's next)
- [ ] Current player highlighted with countdown (10 sec to spin)
- [ ] Scoreboard: drinks taken, immunities held, challenges won
- [ ] 5 rounds per game by default (configurable)
- [ ] Final results screen with champion declaration
- [ ] "Play Again" shuffles turn order
- [ ] Typecheck passes

### US-006: Controlled Spin Tutorial
As a new player,
I want a practice mode that teaches optimal spin technique,
So that I develop skill and feel confident competing.

**Acceptance Criteria:**
- [ ] "Training Mode" option before joining game
- [ ] Target zones displayed with spin intensity required
- [ ] Real-time feedback: "Too light! Spin harder"
- [ ] Progress tracker: spins completed, accuracy %
- [ ] Unlock "Certified Spinner" badge after 10 accurate spins
- [ ] Tutorial completable in under 2 minutes
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

## Functional Requirements
- FR-1: Game server must run on Flask backend at port 5001
- FR-2: WebSocket connection on /game/shot-roulette namespace
- FR-3: Puck firmware sends events: spin_data {velocity, duration}, connected, heartbeat
- FR-4: Game state includes: players[], currentSpinner, scores{}, round, phase
- FR-5: Round duration: spin phase (10s) + wheel resolution (5s) + celebration (5s)

## Non-Goals
- Real money betting (drinking stakes only)
- Age verification (venue responsibility)
- Persistent leaderboards (single-session only for v1)
- Custom wheel configuration (fixed zones for v1)

## Technical Considerations
- MPU6050 gyroscope for spin detection (use DPS setting for max accuracy)
- Canvas 2D or Three.js for wheel rendering
- Web Audio API for click sounds and celebrations
- Consider "anti-cheat": detect if puck set down vs genuinely spun
