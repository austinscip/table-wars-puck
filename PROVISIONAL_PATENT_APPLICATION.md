# PROVISIONAL PATENT APPLICATION
## Interactive Multi-Device Competitive Gaming System

**Applicant:** Austin Scipione
**Filing Date:** December 28, 2025
**Application Type:** Provisional (37 CFR 1.53(c))

---

## TITLE OF INVENTION

Interactive Multi-Device Competitive Gaming System for Venue Entertainment

---

## FIELD OF THE INVENTION

This invention relates to networked gaming systems, specifically to portable motion-sensing controller devices that enable competitive physical challenges with real-time scoring, visual display systems, and multi-user coordination across social venues, healthcare facilities, fitness centers, and event environments.

---

## BACKGROUND OF THE INVENTION

### Problems with Existing Systems:

1. **Limited Venue Entertainment Options**
   - Traditional bar games (darts, pool, trivia) lack real-time competitive tracking
   - No automated scoring or live leaderboards
   - Difficulty scaling across multiple tables/groups simultaneously

2. **Fixed Gaming Installations**
   - Arcade systems require permanent installation and significant infrastructure
   - High capital costs ($5,000-50,000 per installation)
   - Cannot be moved or reconfigured for different venues or events

3. **Motion Gaming Limitations**
   - Existing motion controllers (Wii, PlayStation Move) require dedicated console and TV per user
   - Cannot coordinate multiple independent users for venue-wide competition
   - Designed for home use, not commercial environments

4. **Senior Living Engagement**
   - Limited technology for cognitive assessment and therapeutic activities
   - Existing solutions (tablets, exercise programs) lack objective measurement
   - No engaging multi-user competitive systems for elderly populations

5. **Data Tracking Gaps**
   - No objective measurement of physical/cognitive performance in entertainment contexts
   - Inability to track user engagement across sessions
   - No integration with healthcare or wellness monitoring

### Need for New Solution:

There exists a need for a portable, battery-powered interactive gaming system that:
- Enables multi-user competitive physical challenges
- Operates independently without requiring individual displays per user
- Aggregates performance data from multiple devices to a central server
- Displays real-time competitive rankings on shared venue displays
- Works across diverse markets (entertainment, healthcare, fitness, corporate events)
- Provides objective measurement data for therapeutic and wellness applications

---

## SUMMARY OF THE INVENTION

The present invention provides a networked system of portable interactive controller devices ("pucks") that detect physical interactions via motion sensors, transmit performance data wirelessly to a central server, and enable real-time competitive gaming with visual feedback on shared display systems.

### Key Innovations:

1. **Dual-Wireless Architecture**: Each portable device contains two independent wireless radios operating simultaneously:
   - First radio (Bluetooth Low Energy): Receives game commands from mobile control devices
   - Second radio (WiFi): Transmits performance data directly to server infrastructure
   - Separation of control plane and data plane enables scalable venue-wide coordination

2. **Multi-Device Competitive Coordination**: Multiple independent portable devices operate simultaneously within a venue, with centralized server aggregating performance data and broadcasting comparative rankings to shared display systems in real-time.

3. **Motion-Based Performance Quantification**: Algorithms convert accelerometer and gyroscope data into quantified performance metrics for competitive activities:
   - Shake intensity measurement (peak acceleration, sustained force, frequency analysis)
   - Tap speed and frequency detection
   - Movement pattern recognition
   - Reaction time measurement

4. **Hybrid Input/Display Architecture**: Portable devices serve as input controllers with minimal local feedback (LED patterns, audio cues), while comprehensive visual game graphics, animations, and competitive rankings are rendered on centralized display systems (venue TVs, projectors, monitors).

5. **Cross-Market Platform**: System architecture supports diverse applications:
   - Entertainment venues (bars, restaurants, arcades)
   - Healthcare facilities (senior living, rehabilitation, therapy)
   - Fitness centers (competitive training, gamification)
   - Corporate events (team building, conferences)
   - Educational institutions (STEM learning, physical education)

---

## DETAILED DESCRIPTION OF THE INVENTION

### I. SYSTEM OVERVIEW

The invention comprises four primary components that work in coordination:

#### A. Portable Controller Device ("Puck")

**Physical Configuration:**
- Circular housing (80-120mm diameter, 30-40mm height)
- Ergonomic form factor designed to be held in one hand or placed on surface
- Durable construction suitable for commercial use and repeated handling

**Electronic Components:**

1. **Motion Sensing Subsystem:**
   - 6-axis inertial measurement unit (IMU) combining:
     - 3-axis accelerometer (measures linear acceleration in X, Y, Z axes)
     - 3-axis gyroscope (measures rotational velocity around X, Y, Z axes)
   - Sampling rate: 100-1000 Hz for accurate motion capture
   - Sensitivity range: ±2G to ±16G acceleration, ±250°/s to ±2000°/s rotation

2. **Visual Feedback System:**
   - Addressable RGB LED array (12-20 LEDs arranged in circular ring pattern)
   - Individual control of color (16.7M colors) and brightness (256 levels) per LED
   - Pattern generation: radial fills, chases, pulses, color waves
   - Purpose: Provide immediate local feedback, countdowns, status indication

3. **Audio Feedback System:**
   - Piezoelectric buzzer or small speaker
   - Frequency range: 2-8 kHz
   - Programmable tones, melodies, sound effects

4. **User Input Mechanism:**
   - Tactile switch (physical button) on top surface
   - Debounced input with 10-50ms response time
   - Rated for 100,000+ actuations

5. **Dual Wireless Communication:**

   **First Radio (Control Plane):**
   - Protocol: Bluetooth Low Energy (BLE) 4.2 or 5.0
   - Range: 10-30 meters
   - Power consumption: 10-50mW during active connection
   - Purpose: Receive game commands, configuration from mobile app
   - Services exposed: Battery level, device status, command reception

   **Second Radio (Data Plane):**
   - Protocol: WiFi (802.11 b/g/n/ac, 2.4GHz and/or 5GHz)
   - Range: 30-100 meters (venue coverage)
   - Power consumption: 100-500mW during transmission
   - Purpose: Transmit performance data to central server
   - Connection: Direct to venue WiFi access point

6. **Power Management:**
   - Rechargeable lithium-polymer (LiPo) battery (300-1000mAh)
   - Battery management system with charge controller
   - USB charging interface (USB-C or micro-USB)
   - Runtime: 4-12 hours continuous use
   - Standby time: 24-72 hours

7. **Processing Unit:**
   - Microcontroller with dual-core processor
   - Clock speed: 80-240 MHz
   - RAM: 256KB-512KB
   - Flash storage: 2-16MB
   - Capable of:
     - Real-time motion data processing
     - Game logic execution
     - Wireless protocol management
     - LED/audio control

#### B. Central Server System

**Software Architecture:**

1. **Game Logic Engine:**
   - Receives performance data from multiple pucks
   - Executes game rules and scoring algorithms
   - Manages game state (countdown timers, round progression, win conditions)
   - Validates data integrity (anti-cheat, anomaly detection)

2. **Multi-User Coordination:**
   - Synchronizes game start/stop across multiple devices
   - Maintains participant roster per game session
   - Handles joins/drops mid-game
   - Manages game lobbies and matchmaking

3. **Performance Data Processing:**
   - Aggregates sensor data from devices
   - Calculates comparative rankings in real-time
   - Maintains historical performance records
   - Generates analytics and trend analysis

4. **Rendering Engine:**
   - Generates visual game graphics for display systems
   - Animations: Character movements, progress bars, visual effects
   - UI elements: Scoreboards, leaderboards, countdown timers
   - Branding: Customizable themes for different venues

5. **Broadcasting System:**
   - Streams rendered graphics to display endpoints
   - Supports multiple simultaneous displays
   - Low-latency updates (< 100ms from input to display)
   - Protocols: HTTP, WebSocket, HDMI/DisplayPort

6. **Data Storage:**
   - Database: Stores user profiles, game history, venue configuration
   - Schemas: Users, Games, Scores, Devices, Venues, Analytics
   - Backup and recovery systems

**Hardware Configuration:**
- Server deployment options:
  - On-premises: Computer/mini-PC at venue
  - Cloud-hosted: AWS, Google Cloud, Azure
  - Hybrid: Local processing + cloud backup
- Minimum specs: Quad-core CPU, 8GB RAM, 100GB storage
- Network: Gigabit ethernet, WiFi access point

#### C. Display System

**Display Endpoints:**

1. **Primary Venue Displays:**
   - Large screens: TVs (40-80 inches), projectors, video walls
   - Placement: Visible to all participants (mounted high, central locations)
   - Resolution: 1080p minimum, 4K preferred
   - Connection: HDMI, DisplayPort, wireless casting (Chromecast, AirPlay)

2. **Secondary Displays:**
   - Tablet/monitor at host station (for venue staff)
   - Mobile app views (for individual participants)
   - Web dashboard (for remote monitoring)

**Display Content Types:**

1. **Game Graphics:**
   - Full-screen animated game visuals
   - Examples:
     - Greyhound race: 3D animated dogs racing on track with betting odds
     - Claw machine: 3D claw and prize bin with physics simulation
     - Duck hunt: Animated ducks flying across screen with crosshairs
     - Stack boxes: Animated boxes stacking with physics
   - High-quality graphics (game-engine rendered or pre-rendered animations)

2. **Leaderboards:**
   - Real-time rankings during active games
   - All-time high scores
   - Daily/weekly/monthly leaders
   - Tournament brackets

3. **Status Information:**
   - Active games and participants
   - Upcoming scheduled games
   - Device availability (which pucks are in use)

4. **Venue Branding:**
   - Custom logos, color schemes
   - Promotional content between games
   - Sponsor advertisements

#### D. Mobile Control Application

**Platform Support:**
- iOS (iPhone, iPad)
- Android (phones, tablets)

**Core Functions:**

1. **Device Pairing:**
   - BLE discovery and connection to nearby pucks
   - QR code scanning for quick pairing
   - Multi-device management (pair/unpair multiple pucks)

2. **Game Control:**
   - Browse available game modes
   - Start/stop games
   - Configure game parameters (duration, difficulty, teams)
   - Vote on game selection (multi-user consensus)

3. **User Interface:**
   - Simple, intuitive controls (large buttons, minimal text)
   - Accessibility options (high contrast, voice control)
   - Multiple language support

4. **Monitoring:**
   - Battery level of connected pucks
   - Connection status
   - Game progress (optional mini-view)

5. **Social Features:**
   - User profiles and avatars
   - Friend lists and challenges
   - Share results to social media

---

### II. GAME MECHANICS & ALGORITHMS

The system supports diverse game types based on physical interaction patterns. Below are representative examples demonstrating the range of capabilities.

#### A. Shake Intensity Challenge

**Objective:** Achieve highest shake intensity within time limit

**Puck Behavior:**
1. **Pre-Game:** LED ring pulses slowly (blue) - ready state
2. **Game Start:** Buzzer sounds, LEDs flash green - "GO!"
3. **During Game:**
   - LEDs show intensity meter (more LEDs lit = higher current shake)
   - Color gradient: green (low) → yellow (medium) → red (high)
   - Buzzer chirps on intensity milestones
4. **Game End:** Buzzer sounds, LEDs freeze at final intensity
5. **Result Transmission:** Final score sent to server via WiFi

**Server Processing:**
1. Receive raw accelerometer data stream (X, Y, Z values at 100Hz)
2. Calculate metrics:
   - Peak acceleration: Maximum G-force during period
   - Sustained intensity: Average acceleration over rolling windows
   - Frequency analysis: Shakes per second
3. Compute composite score: `Score = (peak × 40%) + (sustained × 40%) + (frequency × 20%)`
4. Rank all participants
5. Update leaderboard display

**TV Display:**
1. Show all participants' avatars/names
2. Animated intensity bars showing real-time shake levels
3. Visual effects (screen shake effect, particle bursts)
4. Countdown timer
5. Winner announcement with celebration animation

**Algorithm Detail - Shake Intensity Calculation:**

```
Input: Accelerometer data (Ax, Ay, Az) sampled at 100 Hz for duration T seconds

Step 1: Calculate magnitude of acceleration vector at each sample
  For each sample i:
    magnitude[i] = sqrt(Ax[i]² + Ay[i]² + Az[i]²)

Step 2: Remove gravity component (device at rest = 1G)
  For each sample i:
    shake_accel[i] = |magnitude[i] - 1.0|

Step 3: Calculate peak intensity
  peak_intensity = max(shake_accel[])

Step 4: Calculate sustained intensity (average over rolling 1-second windows)
  For each 1-second window w:
    window_avg[w] = mean(shake_accel[w...w+100])
  sustained_intensity = mean(window_avg[])

Step 5: Calculate shake frequency
  Apply high-pass filter to detect direction changes
  Count zero-crossings in filtered signal
  frequency = zero_crossings / (T * 2)  // Divide by 2 (one shake = 2 crossings)

Step 6: Composite score
  score = (peak_intensity × 0.4) + (sustained_intensity × 0.4) + (frequency × 0.2)

Output: Numerical score (typically 0-100 range after normalization)
```

This algorithm quantifies "shakiness" objectively, enabling fair comparison across participants.

#### B. Speed Tap Battle

**Objective:** Press button as many times as possible within time limit (10 seconds)

**Puck Behavior:**
1. **Countdown:** LEDs chase around ring (3-2-1) with buzzer beeps
2. **Game Active:**
   - Each button press: LED flashes white, short beep
   - Progress: More LEDs light up as taps accumulate
3. **Time Running Out:** LEDs pulse red when < 3 seconds remain
4. **Finish:** All LEDs flash current count color-coded

**Server Processing:**
1. Receive button press timestamps
2. Count presses within valid window
3. Detect and discard invalid presses (debounce errors, double-counts)
4. Rank by tap count
5. Calculate taps-per-second rate

**TV Display:**
1. Animated counter for each participant (numbers spinning upward)
2. Visual representation (e.g., "hits" on target, filling progress bar)
3. Leader indicator (crown icon on current leader)
4. Final results with taps/sec stat

#### C. Reaction Time Test

**Objective:** Press button as quickly as possible after LED/buzzer cue

**Puck Behavior:**
1. **Ready State:** All LEDs off, silence
2. **Random Delay:** Wait 2-5 seconds (randomized)
3. **GO Cue:** All LEDs flash bright white + loud buzzer tone
4. **Response:** Measure time until button press
5. **Feedback:**
   - Fast (< 250ms): Green flash
   - Medium (250-400ms): Yellow flash
   - Slow (> 400ms): Red flash

**Server Processing:**
1. Record reaction time in milliseconds
2. Multiple rounds (e.g., 5 trials per participant)
3. Calculate statistics: mean, median, best, worst
4. Rank by best average reaction time

**TV Display:**
1. Visual cues synchronized with pucks (screen flash)
2. Stopwatch display showing reaction times
3. Histogram of all participants' times
4. Ranking with millisecond precision

#### D. Hot Potato (Pass the Puck)

**Objective:** Don't be holding puck when timer expires

**Puck Behavior:**
1. **Active Puck:**
   - LEDs pulse red with increasing speed (timer visualization)
   - Buzzer beeps faster as time runs out
2. **Pass Detection:**
   - Accelerometer detects rapid change (thrown/handed off)
   - LEDs turn green briefly (pass registered)
   - Becomes inactive
3. **Received Puck:**
   - New accelerometer activity detected (caught/grabbed)
   - LEDs turn red (now "hot")
   - Becomes active
4. **Explosion:**
   - Timer expires: All LEDs flash red rapidly, loud alarm buzzer
   - Holder loses round

**Server Processing:**
1. Track current holder of "hot potato"
2. Manage countdown timer
3. Detect pass events (transfer of activity between pucks)
4. Declare loser when timer expires

**TV Display:**
1. Animated potato graphic bouncing between player avatars
2. Countdown timer (visual + numeric)
3. Highlight current holder
4. Explosion animation when timer expires
5. Elimination bracket (if multi-round tournament)

#### E. Claw Machine Prize Game

**Objective:** Position virtual claw and grab prize

**Puck Behavior:**
1. **Movement Control:** Tilting puck moves claw (gyroscope-based 2D positioning)
   - Tilt forward: Claw moves up
   - Tilt back: Claw moves down
   - Tilt left/right: Claw moves horizontally
2. **Visual Feedback:** LED ring shows claw position
   - Top LED lit = claw at top
   - Lights rotate to indicate position
3. **Grab Action:** Press button to drop claw and attempt grab
4. **Result:**
   - Success: Green flash, success tone
   - Fail: Red flash, buzzer

**Server Processing:**
1. Receive tilt data (orientation angles)
2. Map to 2D coordinate system (claw position in prize bin)
3. Physics simulation:
   - Collision detection (did claw touch prize?)
   - Grab probability (based on precision, prize type)
   - Prize pickup mechanics
4. Determine success/failure

**TV Display:**
1. 3D rendered claw machine
   - Transparent bin filled with prizes
   - Animated claw moving in real-time based on puck tilt
2. Participant's camera view (claw perspective)
3. Prize inventory (what you've won)
4. Physics effects (prizes shifting when claw moves)

#### F. Stack the Boxes

**Objective:** Stack virtual boxes as high as possible

**Puck Behavior:**
1. **Box Incoming:** LEDs chase (showing box moving across)
2. **Timing:** Press button when LED reaches top (perfect timing = box stacks)
3. **Miss:** LEDs flash red, stack collapses (game over)
4. **Stack Height:** Number of lit LEDs = current stack height

**Server Processing:**
1. Measure button press timing relative to optimal window
2. Precision scoring: Perfect (±10ms) > Good (±50ms) > Okay (±100ms) > Miss
3. Track stack height
4. Speed increases with each successful stack (difficulty scaling)

**TV Display:**
1. Animated boxes moving on conveyor
2. Stack building upward with each successful press
3. Physics simulation (wobble, collapse animation)
4. Height counter
5. Comparison to other players' current stacks

#### G. Duck Hunt

**Objective:** Aim and shoot flying ducks

**Puck Behavior:**
1. **Aiming:** Point puck at TV (accelerometer measures orientation)
2. **Crosshair Feedback:** LED indicates aim quality
   - Center LED lit = aimed at target
   - Side LEDs = off-target (directional hint)
3. **Shoot:** Press button to fire
4. **Hit/Miss:** Green flash (hit) or red (miss) with corresponding sound

**Server Processing:**
1. Receive puck orientation data (pitch, roll, yaw)
2. Calculate aim point on screen (ray casting from puck to TV)
3. Collision detection: Does aim intersect duck hitbox?
4. Score hits, track accuracy percentage

**TV Display:**
1. Classic duck hunt visuals:
   - Ducks flying across screen (varied speeds, patterns)
   - Background scenery
2. Crosshair showing each participant's aim point
3. Score counter (hits / shots fired)
4. Bonus ducks (rare, high points)

#### H. Correlation Word Game

**Objective:** Identify correlated terms quickly

**Puck Behavior:**
1. **Waiting:** LEDs off
2. **Match Appears:** LEDs flash specific color when correlated term shows on TV
3. **Response:** Press button when you see correlation
4. **Scoring:** Faster response = more points, wrong answers = penalty

**Server Processing:**
1. Present primary term on TV (e.g., "VITAMINS")
2. Show series of words (e.g., "WATER", "B12", "IRON", "COFFEE")
3. Track button press timing relative to correlated term appearance
4. Score: `points = max(0, 1000 - (reaction_time_ms × 2))`
5. Deduct points for incorrect presses

**TV Display:**
1. Primary term displayed prominently
2. Scrolling list of potential matches
3. Highlight when someone presses button
4. Correct/incorrect indicator
5. Running score tally

#### I. Greyhound Racing (Virtual Betting)

**Objective:** Bet on winning virtual greyhound

**Puck Behavior:**
1. **Betting Phase:**
   - LEDs show 6 different colors (representing 6 dogs)
   - Press button to cycle through dog selections
   - Shake to confirm bet
2. **Race Phase:**
   - Assigned dog's color pulses on LED ring
   - Cheer mechanic: Shake puck to "encourage" your dog (slight speed boost)
3. **Results:**
   - Win: LEDs flash winning color, victory tune
   - Lose: LEDs dim, sad buzzer

**Server Processing:**
1. Collect all bets
2. Run race simulation:
   - Each dog has base speed + randomness
   - Player "cheering" (shake intensity) adds small speed modifier
   - Calculate race outcome
3. Determine winners
4. Award points based on betting odds

**TV Display:**
1. 3D animated race track with 6 lanes
2. Greyhounds running (smooth animations)
3. Betting board showing odds
4. Real-time race with photo finish
5. Winner celebration
6. Payout animation (confetti for winners)

---

### III. SYSTEM ARCHITECTURE

#### A. Data Flow

**Typical Game Session:**

1. **Initiation:**
   - User opens mobile app
   - App scans for nearby pucks via BLE
   - User selects puck, app connects (BLE pairing)
   - App retrieves puck status (battery, firmware version)

2. **Game Selection:**
   - User browses game menu in app
   - User selects game mode (e.g., "Greyhound Racing")
   - App sends game command to puck via BLE: `{command: "START_GAME", gameID: 9, duration: 60}`

3. **Local Game Execution:**
   - Puck receives command, acknowledges via BLE
   - Puck begins game logic execution locally (LEDs, buzzer, sensor monitoring)
   - Puck simultaneously connects to venue WiFi
   - Puck sends game start notification to server via WiFi: `POST /api/game/start {puckID, gameID, timestamp}`

4. **Real-Time Performance Transmission:**
   - During game, puck samples sensors (100 Hz)
   - Puck performs local processing (algorithm execution)
   - Puck transmits performance updates to server via WiFi (every 100-500ms):
     - `POST /api/game/update {puckID, gameID, currentScore, rawData}`
   - Server receives data from all participating pucks
   - Server aggregates, processes, ranks

5. **Display Rendering:**
   - Server generates game graphics (current race positions, intensity meters, etc.)
   - Server broadcasts to display endpoints via WebSocket or HTTP streaming
   - TVs update in near-real-time (< 100ms latency)

6. **Game Completion:**
   - Puck detects game end condition (timer expires, win condition met)
   - Puck performs final calculations
   - Puck sends final score to server: `POST /api/game/complete {puckID, gameID, finalScore, stats}`
   - Server updates leaderboard, broadcasts results to displays
   - Puck shows local feedback (winner/loser animation)
   - Puck remains connected, ready for next game

7. **Post-Game:**
   - Server stores game record in database
   - Results available in app, web dashboard
   - Historical stats updated

**Key Insight:** Puck operates autonomously for game execution, reducing latency. Server is authoritative for scoring and display, preventing cheating.

#### B. Network Architecture

**Topology:**

```
[Mobile App] <--BLE--> [Puck 1] <--WiFi--> [Venue WiFi AP] <--Ethernet--> [Server]
                                                                               |
                                                                               |
                       [Puck 2] <--WiFi--> [Venue WiFi AP] <--Ethernet--> [Server] <--HDMI--> [TV Display]
                                                                               |
                       [Puck 3] <--WiFi--> [Venue WiFi AP] <--Ethernet--> [Server] <--WebSocket--> [Web Dashboard]
                          ...
                       [Puck N]
```

**Communication Protocols:**

1. **BLE (Puck ↔ Mobile App):**
   - Connection: 1-to-1 (one app controls one puck at a time)
   - Data: Commands, status queries
   - Frequency: On-demand (button presses, queries)
   - Power: Low (enables long battery life)

2. **WiFi (Puck ↔ Server):**
   - Connection: Many-to-1 (all pucks connect to same server)
   - Protocol: HTTPS REST API or WebSocket
   - Data: Game data, scores, raw sensor readings
   - Frequency: Continuous during active game (1-10 Hz updates)

3. **Display Protocol (Server ↔ TVs):**
   - Options:
     - HDMI (direct wired connection)
     - Wireless casting (Chromecast, AirPlay)
     - Web browser (TV runs browser in kiosk mode)
   - Data: Rendered graphics, HTML/CSS/JS or video stream

**Scalability:**

- System supports 2-100+ simultaneous pucks in single venue
- Venue WiFi must support concurrent connections
- Server scales with participant count:
  - Small venue (2-10 pucks): Raspberry Pi or mini-PC
  - Medium venue (10-50 pucks): Standard server or cloud instance
  - Large venue/multiple locations (50+ pucks): Cloud-hosted with load balancing

#### C. Security & Anti-Cheat

**Threat Model:**

1. **Cheating:** Player manipulates puck or data to achieve unfair advantage
2. **Impersonation:** Unauthorized puck connects to system
3. **Data Integrity:** Transmission errors or intentional corruption

**Mitigations:**

1. **Device Authentication:**
   - Each puck has unique identifier (burned into firmware)
   - Server maintains whitelist of authorized puck IDs
   - TLS/SSL encryption for WiFi communication

2. **Data Validation:**
   - Server performs sanity checks on received data:
     - Is shake intensity within physical limits? (< 20G for human shaking)
     - Is button press rate plausible? (< 20 presses/second)
     - Are timestamps sequential and reasonable?
   - Anomalous data flagged, scores invalidated

3. **Redundancy:**
   - Puck calculates score locally (for immediate feedback)
   - Server recalculates score from raw data (authoritative)
   - Discrepancies trigger alert

4. **Physical Security:**
   - Pucks have tamper-evident seals
   - Firmware updates require authentication

---

### IV. APPLICATIONS & USE CASES

The system's versatility enables deployment across diverse markets. Below are representative use cases demonstrating commercial viability.

#### A. Bar & Restaurant Entertainment

**Deployment:**
- Venue purchases 10-20 pucks
- Server installed on local network
- Primary TV displays game graphics and leaderboards

**Workflow:**
1. Customer requests puck from bartender
2. Customer uses personal phone to select game via app
3. Competes against friends at same table or other tables
4. Live leaderboard shown on bar's TVs
5. Winner gets recognition (bragging rights, possible drink discount)

**Value Proposition:**
- Increases customer engagement and dwell time
- Drives beverage sales through gamification
- Differentiates venue from competitors
- Minimal staff involvement (automated system)

**Revenue Model:**
- One-time hardware sale: $2,000-4,000 per venue (10-20 pucks)
- Optional subscription: $200-500/month for software updates, cloud features

#### B. Senior Living Facilities

**Deployment:**
- Facility purchases 15-30 pucks (1-2 per resident in activities program)
- Server connects to facility's activity monitoring system
- Large display in common area shows game graphics

**Workflow:**
1. Activities director schedules game sessions
2. Residents receive pucks
3. Play cognitive/physical games (reaction tests, memory challenges)
4. Performance data logged for therapeutic records
5. Family members can view progress via web dashboard

**Value Proposition:**
- Cognitive stimulation and assessment (dementia screening)
- Physical therapy (motor skills, reaction time)
- Social engagement (group activities, reduces isolation)
- Data-driven care (objective metrics for medical records)
- Regulatory compliance (documented resident activities)

**Revenue Model:**
- Hardware sale: $3,000-6,000 per facility
- Software subscription: $300-600/month (includes data analytics, family portal)
- Medicare billing potential (therapeutic device reimbursement)

#### C. Corporate Team Building

**Deployment:**
- Event planner rents 50-100 pucks for conference or corporate event
- Temporary server setup at event venue
- Multiple large screens for game displays

**Workflow:**
1. Event begins, attendees receive pucks
2. Icebreaker games throughout day (short 2-5 minute games)
3. Leaderboards displayed on screens
4. Final tournament with prizes for top performers

**Value Proposition:**
- Engaging alternative to traditional icebreakers
- Measurable participation (data on engagement levels)
- Scalable (works for 10 or 1,000 attendees)
- Memorable experience (social media shareable)

**Revenue Model:**
- Rental: $50-100 per puck per event
- Event package: $5,000-20,000 for 100-puck setup including setup/teardown

#### D. Fitness & Wellness

**Deployment:**
- Gym purchases 20-30 pucks
- Integration with gym's member management system
- Display screens throughout facility

**Workflow:**
1. Gym member checks out puck at front desk
2. Personal trainer sets up workout challenges
3. Member competes in reaction drills, coordination exercises
4. Performance tracked over weeks/months
5. Progress reports generated

**Value Proposition:**
- Gamifies fitness (increases engagement and retention)
- Objective performance tracking (vs. subjective assessments)
- Competitive element (members challenge each other)
- Personalized programming (data-driven workout adjustments)

**Revenue Model:**
- Hardware sale: $2,000-5,000 per gym
- Subscription: $200-400/month (software, analytics platform)
- Per-member fee: $5-10/month added to membership

#### E. Education & STEM Learning

**Deployment:**
- School purchases 30-60 pucks (one per student in class)
- Integration with classroom display (projector/smartboard)

**Workflow:**
1. Teacher launches lesson (e.g., "Physics of Motion")
2. Students receive pucks
3. Experiments: Measure acceleration, calculate force, observe motion patterns
4. Data collected and analyzed in real-time
5. Results displayed on classroom screen

**Value Proposition:**
- Hands-on STEM learning (kinesthetic engagement)
- Real sensor data (introduces students to IoT, data science)
- Inclusive (all students participate simultaneously)
- Assessment tool (teacher sees all students' results in real-time)

**Revenue Model:**
- Bulk education pricing: $1,500-3,000 for class set (30 pucks)
- Curriculum subscription: $500-1,000/year (lesson plans, teacher resources)

---

### V. ALTERNATIVE EMBODIMENTS

The invention is not limited to the specific configurations described above. Various modifications and alternative implementations are within the scope of the invention.

#### A. Hardware Variations

1. **Form Factor:**
   - Alternative shapes: Square, hexagonal, wearable (wristband)
   - Size variations: Mini version (50mm diameter), large version (150mm)
   - Materials: Soft silicone coating, ruggedized waterproof housing

2. **Sensors:**
   - Additional sensors: Heart rate monitor (for fitness applications), temperature sensor
   - Higher precision IMU (16-bit vs. 12-bit ADC)
   - Magnetometer (compass for orientation-based games)

3. **Feedback Mechanisms:**
   - Haptic feedback: Vibration motor for tactile cues
   - Display: Small OLED screen (32x32 pixels) for score display
   - Advanced audio: Small speaker for voice prompts or music

4. **Wireless:**
   - Alternative to WiFi: Cellular (LTE/5G) for outdoor/mobile use
   - Mesh networking: Pucks communicate peer-to-peer
   - NFC: Tap-to-pair functionality

5. **Power:**
   - Solar charging: Small solar panel for outdoor use
   - Wireless charging: Qi-compatible charging pad
   - Replaceable batteries: AA/AAA instead of LiPo

#### B. Software Variations

1. **Game Modes:**
   - Hundreds of potential game variations not explicitly described
   - User-generated content: Allow venues to create custom games
   - Adaptive difficulty: AI adjusts challenge level based on player skill

2. **Scoring Algorithms:**
   - Alternative metrics for shake intensity (e.g., total energy, peak-to-peak amplitude)
   - Machine learning: Train models to detect specific movement patterns (e.g., "spinning motion")
   - Handicapping: Adjust scores to level playing field (age, ability-based)

3. **Display Rendering:**
   - VR/AR: Use virtual reality or augmented reality for immersive graphics
   - Holographic displays: Project 3D images
   - Mobile-only mode: No TV required, all graphics on personal phones

#### C. System Architecture Variations

1. **Peer-to-Peer Mode:**
   - Pucks communicate directly without server
   - Useful for small groups (2-4 players) without venue infrastructure
   - One puck acts as coordinator

2. **Cloud-First Architecture:**
   - All processing in cloud (no local server)
   - Pucks connect directly to internet via cellular or venue WiFi
   - Enables cross-venue competitions (compete against players in other cities)

3. **Hybrid Local/Cloud:**
   - Local server for low-latency gaming
   - Cloud sync for long-term data storage and analytics
   - Failover: If local server fails, cloud takes over

#### D. Market-Specific Variations

1. **Kids Version:**
   - Larger buttons, softer materials
   - Simplified games (colors, shapes, counting)
   - Parental controls via app

2. **Medical Device Version:**
   - FDA-approved sensors for clinical use
   - HIPAA-compliant data storage
   - Integration with electronic health records (EHR)
   - Prescription-based deployment (physician orders device for patient)

3. **Industrial Training:**
   - Durable enclosure for workshop environments
   - Training simulations (assembly line speed tests, quality control reactions)
   - Integration with workforce management systems

---

### VI. ADVANTAGES OVER PRIOR ART

The present invention provides significant improvements over existing systems:

1. **Portability:**
   - Unlike fixed arcade systems, pucks are handheld and battery-powered
   - Enables flexible deployment (move between tables, take home, outdoor events)
   - Lower infrastructure costs (no permanent installation)

2. **Scalability:**
   - Supports 2-100+ simultaneous users without requiring individual displays
   - Shared display architecture reduces cost-per-user
   - Modular expansion (add more pucks as needed)

3. **Dual-Wireless Architecture:**
   - Separation of control and data planes enables independent operation
   - BLE for low-power mobile app communication
   - WiFi for high-bandwidth performance data transmission
   - Puck continues functioning even if mobile app disconnects

4. **Multi-Market Platform:**
   - Single hardware design serves entertainment, healthcare, fitness, education
   - Software-defined functionality (same puck, different games via updates)
   - Broad market appeal increases commercial viability

5. **Objective Performance Measurement:**
   - Quantifies physical/cognitive performance (vs. subjective assessment)
   - Enables longitudinal tracking (progress over time)
   - Applicable to therapeutic/medical contexts (not just entertainment)

6. **Real-Time Competitive Coordination:**
   - Centralized server aggregates data from all participants
   - Live leaderboards create social competition
   - Synchronized game start/stop across multiple devices

7. **Low Barrier to Entry:**
   - Users only need personal smartphone (no special app purchase)
   - Venue provides pucks (like pool cues or bowling shoes)
   - Simple UX (minimal learning curve)

---

### VII. CLAIMS (Informal - For Provisional)

The following claims outline the scope of protection sought. Formal claims will be refined for utility patent filing.

**Claim 1 (Apparatus - Broadest):**

A portable interactive gaming device comprising:
- A housing adapted to be held or manipulated by a user;
- A motion sensor detecting movement in at least two axes;
- A first wireless communication module operating on a first protocol for receiving command data;
- A second wireless communication module operating on a second protocol distinct from said first protocol for transmitting performance data;
- A user input mechanism;
- A visual feedback system comprising a plurality of light-emitting elements;
- An audio output device;
- A rechargeable power source;
- A processor configured to:
  - Execute game logic based on detected motion and user input,
  - Control said visual feedback system and audio output device,
  - Communicate via said first wireless module with a mobile control device,
  - Transmit performance metrics via said second wireless module to a remote server.

**Claim 2 (System - Multi-Device):**

A competitive gaming system comprising:
- A plurality of portable interactive devices as in Claim 1;
- A central server configured to:
  - Receive performance data from said plurality of devices via wireless communication,
  - Aggregate and process said performance data to generate comparative rankings,
  - Render graphical content depicting competitive status;
- A display system configured to present said graphical content to multiple users simultaneously;
- Wherein said devices operate independently and concurrently, with said server coordinating competitive activities.

**Claim 3 (Method - Game Execution):**

A method of conducting a multi-user competitive physical challenge comprising:
- Distributing portable devices to a plurality of participants, each device containing motion sensors and wireless transceivers;
- Receiving at each device a game initiation command via a first wireless protocol from a mobile application;
- Measuring physical interactions via said motion sensors during a defined time period;
- Calculating performance metrics at each device based on sensor data;
- Transmitting said performance metrics from each device to a central server via a second wireless protocol;
- Aggregating performance metrics from said plurality of devices at said server;
- Generating comparative rankings;
- Displaying said rankings on a shared display system accessible to all participants.

**Claim 4 (Specific - Dual Wireless):**

The device of Claim 1, wherein:
- Said first wireless module operates using Bluetooth Low Energy protocol;
- Said second wireless module operates using WiFi (IEEE 802.11) protocol;
- Said first and second modules operate simultaneously and independently;
- Said first module receives game parameters without relaying performance data; and
- Said second module transmits performance data without receiving commands.

**Claim 5 (Specific - Motion Algorithm):**

The device of Claim 1, wherein said processor is further configured to:
- Sample accelerometer data at a frequency of at least 50 Hz;
- Calculate a magnitude of acceleration vector for each sample;
- Remove gravitational component to isolate motion-induced acceleration;
- Determine peak acceleration value over measurement period;
- Calculate average acceleration over rolling time windows;
- Derive frequency of oscillatory motion from directional changes in acceleration;
- Compute composite performance score as weighted combination of peak, average, and frequency metrics.

**Claim 6 (Application - Healthcare):**

The system of Claim 2, further comprising:
- A therapeutic assessment mode wherein said games measure cognitive or physical parameters relevant to healthcare;
- Data storage configured to maintain longitudinal records of user performance;
- Analytics module configured to detect trends or deviations in performance over time;
- Reporting interface providing performance data in medical record format.

**Claim 7 (Display Architecture):**

The system of Claim 2, wherein:
- Said portable devices provide minimal visual feedback via light-emitting elements;
- Said display system renders comprehensive graphical representations including animations, avatars, and environmental graphics;
- Game visuals are partitioned such that input feedback occurs on said devices and game world visualization occurs on said display system.

**Claim 8 (Design - Ornamental):**

The ornamental design of a circular handheld gaming controller as shown and described, comprising:
- A circular body with diameter approximately three times its height;
- A ring of addressable LEDs visible on top surface;
- A tactile button centered on top surface;
- A contoured edge for ergonomic gripping.

---

### VIII. DRAWINGS

[Note: For provisional patent, drawings can be informal but must show invention clearly. Below are descriptions of figures to be included.]

**Figure 1: System Overview**
- Block diagram showing: Multiple pucks, mobile apps, venue WiFi, server, database, TV displays
- Arrows indicating data flow (BLE, WiFi, HDMI/streaming)

**Figure 2: Puck Hardware Architecture**
- Cross-section view of puck showing:
  - PCB with ESP32 microcontroller
  - MPU-6050 IMU sensor
  - WS2812B LED ring
  - Button, buzzer
  - Battery, charging circuit
  - WiFi/BLE antenna

**Figure 3: Puck External Views**
- Top view (showing LED ring, button)
- Side view (showing circular profile, USB port)
- Bottom view (showing label, charging contacts)

**Figure 4: Data Flow Diagram**
- Sequence diagram showing:
  1. Mobile app connects to puck (BLE)
  2. App sends game command
  3. Puck executes game, samples sensors
  4. Puck sends data to server (WiFi)
  5. Server renders graphics
  6. TV displays results

**Figure 5: Game Example - Shake Intensity**
- Timeline showing:
  - T0: Game start (LEDs green, buzzer beep)
  - T1: User shaking (LEDs showing intensity meter)
  - T2: Game end (LEDs freeze, final score)
- Graph showing accelerometer data over time

**Figure 6: TV Display Screenshots**
- Greyhound race display (3D race track with dogs)
- Leaderboard display (rankings, scores, player names)
- Claw machine display (3D claw and prizes)

**Figure 7: Mobile App Wireframes**
- Home screen (device pairing)
- Game selection screen (grid of game modes)
- Active game screen (minimal controls, status)

**Figure 8: Server Architecture**
- Diagram showing server components:
  - API layer (REST endpoints)
  - Game engine (logic processing)
  - Database (user data, scores)
  - Rendering engine (graphics generation)
  - Broadcasting (WebSocket to displays)

**Figure 9: Alternative Embodiment - Wearable**
- Wristband form factor with same core components

**Figure 10: Use Case - Bar Environment**
- Photo/rendering showing:
  - Multiple patrons holding pucks
  - TV on wall displaying game graphics
  - Bartender observing

---

### IX. ABSTRACT

An interactive multi-user competitive gaming system comprising portable controller devices (pucks) with motion sensors, dual wireless radios (Bluetooth and WiFi), LED feedback, and audio output. Users manipulate pucks through physical actions (shaking, tapping, tilting) while game graphics and competitive rankings are displayed on centralized screens. Each puck operates autonomously, receiving commands via Bluetooth from mobile apps and transmitting performance data via WiFi to a server that coordinates multi-device gameplay. Applications include entertainment venues, senior living facilities, fitness centers, corporate events, and education. The system quantifies physical/cognitive performance objectively, enabling competitive gaming, therapeutic assessment, and engagement tracking across diverse user populations.

---

## CONCLUSION

This provisional patent application describes a novel networked gaming system that combines portable motion-sensing controllers, dual wireless communication, centralized graphics rendering, and multi-user competitive coordination. The system addresses unmet needs across entertainment, healthcare, fitness, and education markets.

The invention's key innovations include:
1. Dual-wireless architecture separating control and data planes
2. Hybrid input/display partitioning (pucks as controllers, TVs as displays)
3. Scalable multi-device competitive coordination
4. Objective physical/cognitive performance quantification
5. Platform approach serving diverse markets with single hardware design

**This provisional application establishes priority for the described invention and its variations. Full utility patent application will be filed within 12 months.**

---

**Prepared by:** Austin Scipione
**Date:** December 28, 2025
**Signature:** ________________________

---

## APPENDIX A: Source Code Excerpts

[Include key algorithm implementations from firmware - shake detection, tap counting, motion processing]

## APPENDIX B: Hardware Schematics

[Include PCB schematics showing component connections]

## APPENDIX C: BOM (Bill of Materials)

[Include complete component list with part numbers]

---

**END OF PROVISIONAL PATENT APPLICATION**

**File Size:** Approximately 30 pages (within typical provisional range)
**Word Count:** ~10,000 words (comprehensive coverage)

**Next Steps:**
1. Review this document thoroughly
2. Add any missing details or variations you've thought of
3. Prepare figures/drawings (can be hand-drawn sketches for provisional)
4. Fill out USPTO Form SB/16 (cover sheet)
5. Submit electronically via USPTO EFS-Web
6. Pay $75 filing fee (micro entity)
7. Receive filing receipt with serial number and date
8. YOU NOW HAVE "PATENT PENDING" STATUS! 🎉
