# Patent Search Brief - Table Wars System

**Prepared for:** Patent Attorney Review
**Date:** December 22, 2025
**Inventor:** [Your Name]
**Product Name:** Table Wars / Interactive Gaming Puck System

---

## 1. PRODUCT OVERVIEW (30-Second Pitch)

**Table Wars** is a **wireless, interactive drinking game puck** that combines motion sensing, LED feedback, and smartphone connectivity to create competitive physical games at bars and social venues. Players interact with physical pucks that track their performance in real-time and wirelessly communicate scores to a central server for live leaderboards displayed on venue TVs.

**Think:** "Topgolf or Dave & Buster's gamification, but for bar games - turning simple drinking challenges into tracked, competitive experiences."

---

## 2. CORE INVENTION COMPONENTS

### **A. Hardware Device (The "Puck")**

**Physical Description:**
- Circular handheld device (96mm diameter × 35mm height)
- Similar size to hockey puck or bar coaster
- Self-contained electronic gaming device

**Key Components:**
1. **Motion Sensor** (MPU-6050 6-axis accelerometer/gyroscope)
   - Detects shaking, tapping, movement patterns
   - Tracks speed and intensity of physical actions

2. **Physical Button** (Tactile switch)
   - User input for game interactions
   - Speed/reflex testing

3. **LED Ring** (16× addressable RGB LEDs - WS2812B)
   - Visual feedback and game status
   - Countdown timers, color-coded challenges
   - Win/lose animations

4. **Audio Feedback** (Piezo buzzer)
   - Sound effects for game events
   - Audible countdowns and alerts

5. **Dual Wireless Communication:**
   - **Bluetooth Low Energy (BLE)** - Direct mobile app control
   - **WiFi** - Server communication for scoring/leaderboards

6. **Rechargeable Battery System**
   - USB-C charging
   - Onboard power management (LiPo charger + voltage regulation)

7. **Microcontroller** (ESP32)
   - Dual-core processor
   - Manages sensors, connectivity, game logic

---

### **B. Software/Server System**

1. **Game Logic Engine**
   - 10+ competitive game modes
   - Real-time scoring algorithms
   - Difficulty scaling

2. **Central Server Backend**
   - Score aggregation and validation
   - Player/table management
   - Live leaderboard generation
   - Multi-venue support

3. **Mobile App Integration**
   - Remote game launching via BLE
   - Game mode selection
   - Battery monitoring
   - Device pairing

4. **Venue Display System**
   - TV dashboard showing live scores
   - Multi-table competition tracking
   - Bar-specific branding

---

## 3. NOVEL FEATURES & INNOVATIONS

### **Primary Novelty Claims:**

#### **1. Networked Physical Gaming Pucks for Bars/Venues**
- **What's Novel:** Combination of physical interaction device + wireless networking + venue-wide leaderboard system specifically designed for bar/restaurant environments
- **Prior Art Concern:** Arcade games, Topgolf tracking, electronic darts
- **Our Differentiation:** Portable, battery-powered, works across multiple tables, tracks individual player performance across sessions

#### **2. Motion-Based Drinking Game Automation**
- **What's Novel:** Automated scoring and timing for physical drinking challenges using motion sensors
- **Examples:**
  - Shake detection with intensity measurement
  - Tap speed/count tracking
  - Reaction time measurement
  - Pass-the-puck timing (hot potato style)
- **Prior Art Concern:** Fitness trackers, game controllers (Wii, etc.)
- **Our Differentiation:** Specifically designed for bar game scenarios with social/competitive context

#### **3. Dual-Mode Wireless Communication Architecture**
- **What's Novel:** BLE for local control + WiFi for cloud scoring in a battery-powered device
- **Why It Matters:**
  - BLE: Player's phone directly controls puck (no app server needed)
  - WiFi: Puck independently reports scores to venue server
  - Separation of control plane and data plane
- **Prior Art Concern:** IoT devices with dual radios
- **Our Differentiation:** Specific implementation for real-time gaming with both local control and centralized scoring

#### **4. Multi-Table Competitive Gaming System**
- **What's Novel:** Multiple independent pucks networked to create venue-wide competition
- **Features:**
  - Simultaneous multi-table gameplay
  - Cross-table scoring and rankings
  - Real-time leaderboard updates
  - Tournament/bracket support
- **Prior Art Concern:** Multiplayer arcade systems, bowling alleys
- **Our Differentiation:** Portable devices (not fixed installations), works in existing bars without infrastructure

#### **5. Specific Game Mechanics (Examples):**

**Speed Tap Battle:**
- Accelerometer measures tap frequency and force
- LED countdown timer
- Fastest tapper wins
- **Novel element:** Using accelerometer + LED ring for competitive tapping game

**Shake Duel:**
- Gyroscope measures shake intensity
- Real-time visual feedback of shake power
- Threshold-based win condition
- **Novel element:** Quantifying "shake intensity" for drinking game context

**Hot Potato Pass:**
- Accelerometer detects "passes" between players
- Timed countdown with LED/audio cues
- Last person holding when timer expires loses
- **Novel element:** Motion-based pass detection in timed passing game

---

## 4. TECHNICAL IMPLEMENTATION

### **System Architecture:**

```
[Player's Phone] <--BLE--> [Puck] <--WiFi--> [Venue Server] --> [TV Display]
                              ↓
                      [Motion Sensors]
                      [LED Ring]
                      [Button]
                      [Buzzer]
```

### **Data Flow:**
1. Player opens mobile app, connects to puck via BLE
2. Player selects game mode, sends command to puck
3. Puck runs game locally (sensors, LEDs, timing)
4. Puck calculates score based on sensor data
5. Puck transmits score to venue server via WiFi
6. Server updates leaderboard
7. TV displays live rankings

### **Key Technical Features:**
- **Edge computing:** Game logic runs on puck (no latency)
- **Offline capable:** Games work without server (scores cached)
- **Battery efficient:** BLE for low-power phone communication
- **Scalable:** Each puck operates independently
- **Secure:** Score validation on server prevents cheating

---

## 5. USE CASES & MARKET APPLICATION

### **Primary Market:**
- Bars, nightclubs, restaurants
- College bars and social venues
- Corporate team-building events
- Party entertainment

### **Business Model:**
- Venues purchase/lease puck sets (5-20 pucks per location)
- Increases customer engagement and "dwell time"
- Drives beverage sales through gamification
- Optional revenue share on game plays

### **User Experience:**
1. Customer asks bartender for "Table Wars puck"
2. Bartender hands them a puck (like getting a pool cue)
3. Player uses their phone to select game
4. Competes against friends or other tables
5. Scores appear on bar's TV
6. Winner gets bragging rights (or free drink)

---

## 6. PRIOR ART SEARCH AREAS

### **Search These Technology Domains:**

#### **A. Electronic Gaming Devices:**
- Handheld electronic games
- Motion-controlled gaming devices (Wii, PlayStation Move)
- Interactive toys with motion sensors
- Electronic dice, spinners, game pieces

#### **B. Bar/Venue Entertainment Systems:**
- Electronic dartboards (Arachnid, Viper)
- Topgolf ball tracking system
- Bowling alley scoring systems
- Arcade game networks
- Jukebox networked systems (TouchTunes)

#### **C. Drinking Game Related:**
- Electronic drinking game devices
- Automated bartending/pouring systems
- Party game systems
- Breathalyzer games

#### **D. IoT/Wireless Communication:**
- Battery-powered BLE + WiFi devices
- Mesh networked gaming systems
- Multi-device coordination systems

#### **E. Motion Sensing Applications:**
- Fitness trackers (Fitbit, Apple Watch)
- Smart sports equipment (connected basketballs, golf clubs)
- Gesture recognition devices
- Shake-to-activate devices

### **Specific Patent Classifications to Search:**

**US Patent Classes:**
- **A63F 13/00** - Video games
- **A63F 9/00** - Games not otherwise provided for
- **G06F 3/01** - Input arrangements using sensors (motion)
- **H04W 4/80** - Services using short range communication (BLE)
- **A63F 13/42** - Wireless gaming devices
- **G06F 19/00** - Digital computing for recreation
- **H04L 67/00** - Network arrangements for gaming

**International (IPC) Classes:**
- **A63F** - Card, board, or roulette games
- **H04W** - Wireless communication networks
- **G06F** - Electric digital data processing

---

## 7. COMPETITIVE/SIMILAR PRODUCTS

### **Direct Competitors (if any exist):**
[Search for these - none currently known to us]

### **Adjacent Products:**
1. **Bop It / Simon** - Electronic handheld games (no networking)
2. **Topgolf** - Physical game tracking (fixed installation)
3. **Electronic dartboards** - Networked scoring (wall-mounted)
4. **TouchTunes jukebox** - Venue networking (different domain)
5. **Dave & Buster's PowerCard** - Venue gaming system (arcade focused)
6. **Buzztime trivia** - Bar entertainment (tablets, no physical interaction)

### **Why We're Different:**
- **Portable** (not fixed like darts/arcade)
- **Physical interaction** (not just digital like trivia)
- **Multi-table networking** (not isolated like Bop It)
- **Bar-optimized** (battery-powered, drink-proof, social)

---

## 8. POTENTIAL PATENT CLAIMS (High-Level)

### **Device Claims:**

**Claim 1 (Apparatus):**
A portable interactive gaming device comprising:
- A housing adapted to be held in one hand
- A motion sensor detecting at least three axes of movement
- A visual feedback system comprising a plurality of LEDs arranged in a ring
- A wireless communication module supporting at least two protocols
- A button for user input
- A rechargeable battery
- A processor executing game logic based on motion sensor data

**Claim 2 (Specific Configuration):**
The device of Claim 1, wherein the wireless communication comprises:
- A first wireless protocol (BLE) for receiving game commands from a mobile device
- A second wireless protocol (WiFi) for transmitting game results to a remote server

### **System Claims:**

**Claim 3 (System):**
A networked gaming system for venues comprising:
- A plurality of portable interactive gaming devices
- A central server receiving score data from said devices
- A display system showing aggregated scores from multiple devices
- A mobile application for controlling individual devices

### **Method Claims:**

**Claim 4 (Method):**
A method of conducting a competitive game comprising:
- Receiving a game initiation command via Bluetooth
- Measuring physical interaction via motion sensors
- Calculating a score based on sensor data
- Transmitting said score to a remote server via WiFi
- Displaying said score on a venue display with scores from other devices

### **Design Claims:**
- Specific ornamental design of circular puck with LED ring
- Button placement and form factor
- Case design with specific proportions

---

## 9. PATENTABILITY ANALYSIS (Initial Thoughts)

### **Strong Points:**

✅ **Combination is Novel:** While individual components exist (accelerometers, BLE, LEDs), the specific combination for bar gaming might be new

✅ **Specific Application:** Using motion sensors + dual wireless for drinking game automation is likely unpatented

✅ **System Architecture:** Multi-puck venue system with centralized scoring may be novel

✅ **Business Method:** Revenue model around gamifying bar experiences could have method patent potential

### **Weak Points:**

⚠️ **Obvious Combination?** Could be argued that combining existing tech is "obvious to one skilled in the art"

⚠️ **Prior Art Risk:** Wii controllers, fitness trackers, electronic games may be cited

⚠️ **Software Patents:** Game logic alone may not be patentable

### **Recommendations for Stronger Patent:**

1. **Focus on system-level claims** (multi-device + server + display)
2. **Emphasize specific algorithms** (shake intensity calculation, tap detection)
3. **Highlight dual-wireless architecture** (BLE + WiFi separation)
4. **Document specific game mechanics** (unique interaction patterns)
5. **Consider design patent** for puck form factor

---

## 10. TRADEMARK CONSIDERATIONS

### **Brand Names to Protect:**
- **"Table Wars"** - Primary brand
- Potential taglines or slogans
- Specific game names (if unique)

### **Logo/Trade Dress:**
- Circular puck design with LED ring
- App interface design
- TV dashboard layout

---

## 11. SEARCH OBJECTIVES

### **What We Need to Know:**

1. **Does anything like this exist?**
   - Portable, battery-powered gaming pucks
   - Networked drinking game systems
   - Motion-based bar entertainment

2. **What's the closest prior art?**
   - Electronic games with motion sensing
   - Networked arcade/bar systems
   - Portable gaming devices with LEDs

3. **Where are the white spaces?**
   - What aspects are NOT covered by existing patents?
   - What claims would be strongest?
   - What modifications would improve patentability?

4. **Who are the competitors?**
   - Existing patents in this space
   - Companies with similar tech
   - Recent patent applications (last 5 years)

5. **International considerations?**
   - Is this patented elsewhere? (EU, Asia)
   - Should we file internationally?

---

## 12. BUSINESS CONTEXT

### **Why This Matters:**

**Investment Potential:**
- Seeking investment/funding
- Patent protection increases valuation
- Defensible IP attracts investors

**Manufacturing:**
- About to order prototypes (~$300)
- Planning production run (50-500 units)
- Want to protect before going to market

**Timeline:**
- Prototypes arriving: 3-4 weeks
- Potential launch: 3-6 months
- Need to file before public disclosure

**Market Size:**
- ~65,000 bars in US
- ~$30B bar/nightclub industry
- Entertainment tech in hospitality growing

---

## 13. QUESTIONS FOR PATENT ATTORNEY

1. **Patentability Opinion:**
   - Is this patentable as described?
   - What claims would be strongest?
   - Utility patent, design patent, or both?

2. **Prior Art Risk:**
   - What's the closest existing technology?
   - Any blocking patents?
   - Freedom to operate concerns?

3. **Filing Strategy:**
   - Provisional first, then utility?
   - Design patent in parallel?
   - Trademark simultaneously?

4. **International:**
   - Should we file PCT (international)?
   - Which countries matter? (US, EU, China?)
   - Timing and costs?

5. **Trade Secret vs. Patent:**
   - Should any aspects be kept as trade secrets?
   - Software algorithms patentable or keep closed-source?

6. **Timeline:**
   - How long until we can say "patent pending"?
   - When must we file by? (public disclosure deadline)
   - Cost estimates for provisional vs. full utility?

7. **Defensive Strategy:**
   - Should we file even if not planning to enforce?
   - Value for fundraising vs. actual protection?

---

## 14. SUPPORTING MATERIALS

### **Available for Review:**

✅ **Firmware Source Code** - Complete game logic implementation
✅ **Server Source Code** - Backend scoring system
✅ **PCB Design** - Hardware schematics (Altium files)
✅ **3D Case Models** - Physical design (STL files)
✅ **BLE Protocol Specification** - Communication protocol
✅ **Game Mechanics Documentation** - 10 game mode descriptions
✅ **System Architecture Diagrams** - Network/data flow
✅ **Video Demonstration** - Working prototype with BLE control (if you record one)

---

## 15. BUDGET & TIMELINE

### **Patent Budget:**
- **Provisional Patent:** $2,000 - $5,000
- **Full Utility Patent:** $10,000 - $15,000
- **Design Patent:** $2,000 - $4,000
- **Trademark:** $1,500 - $3,000
- **Patent Search:** $1,000 - $3,000

### **Timeline Needs:**
- **Prototype testing:** 4 weeks (starting now)
- **Soft launch:** 3-6 months
- **Need "patent pending" status before:** Public demos, investor pitches
- **Public disclosure deadline:** Before posting to Kickstarter/social media

---

## 16. SIMPLIFIED ONE-PARAGRAPH DESCRIPTION

**For quick searches:**

"A battery-powered, handheld circular electronic gaming device (96mm diameter puck) containing a 6-axis motion sensor, 16 RGB LEDs, physical button, and dual wireless radios (Bluetooth + WiFi), designed for competitive drinking games at bars. The device detects physical actions (shaking, tapping, passing) via accelerometer, provides visual/audio feedback via LEDs and buzzer, receives game commands from a mobile app via Bluetooth, and wirelessly transmits scores to a venue server via WiFi for display on TVs. Multiple pucks network together to create venue-wide competitive leaderboards across tables, gamifying traditional bar activities with real-time scoring and tracking."

---

## 17. KEY SEARCH TERMS FOR ATTORNEY

**Technology Terms:**
- Interactive gaming puck
- Motion-sensing drinking game
- Networked bar entertainment
- Portable gaming device with dual wireless
- Accelerometer-based game controller
- BLE + WiFi gaming device
- Multi-device competitive gaming system
- Venue entertainment network

**Functional Terms:**
- Shake detection gaming
- Tap speed measurement device
- LED ring feedback system
- Battery-powered game puck
- Handheld motion game controller

**Industry Terms:**
- Bar gaming system
- Drinking game automation
- Hospitality entertainment technology
- Social venue gaming network

---

## 18. INVENTOR'S DECLARATION

**I hereby declare that:**

1. I am the original inventor of this system
2. This has not been publicly disclosed prior to [date]
3. This is not currently being sold or offered for sale
4. No prior patent applications have been filed
5. I have not assigned rights to any other party

**Inventor Information:**
- Name: [Your Name]
- Contact: [Your Email/Phone]
- Date of Invention: [When you started - maybe mid-2024?]
- First Working Prototype: December 2025

---

## SUMMARY FOR ATTORNEY

**Bottom Line:**

We've built a **networked physical gaming system for bars** combining:
- Portable pucks with motion sensors + LEDs
- Dual wireless (BLE control + WiFi scoring)
- Venue-wide competitive leaderboards
- 10+ interactive drinking games

**We need to know:**
1. Is this patentable?
2. What's the prior art?
3. What claims would be strongest?
4. Should we file provisional ASAP?
5. What's the budget and timeline?

**We're ready to provide:**
- Full source code
- Hardware designs
- Working prototype demo
- Business plan and market analysis

**Timeline pressure:**
- Prototypes arriving in 3-4 weeks
- Want "patent pending" before showing to investors/venues
- Planning soft launch in 3-6 months

---

**Contact for Questions:**
[Your Name]
[Your Email]
[Your Phone]

**Date Prepared:** December 22, 2025
