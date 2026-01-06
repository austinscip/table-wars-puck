# TABLE WARS - Complete Business Overview

*For AI Evaluation & Investor Review*

---

## 🎯 THE CORE IDEA

**Tagline:** "Jackbox Party Pack meets physical gaming pucks for bars, airports, and social venues"

**Elevator Pitch:**
Table Wars creates interactive entertainment experiences using ESP32-powered gaming pucks. Players compete in 92+ games spanning trivia (YDKJ-style) and skill challenges, with results displayed on venue TVs. Think arcade games meets social trivia, but the controller is a glowing hockey puck you shake, tilt, and spin.

---

## 🎮 THE PRODUCT

### Hardware: Gaming Puck Specs

**Physical Device:**
- Form factor: Hockey puck sized (3" diameter × 1" thick)
- Weight: ~150g with battery
- Cost to build: $42-58 per unit (at scale)
- Retail value: $150-200 per puck
- Lifespan: 500+ charge cycles, 3-5 years

**Core Components:**
- **ESP32-DevKitC-32** - Main microcontroller (WiFi + Bluetooth)
- **GY-521 MPU6050** - 6-axis motion sensor (accelerometer + gyroscope)
- **WS2812B LED Ring** - 16 individually addressable RGB LEDs
- **3.7V LiPo Battery** - 2000mAh (4-6 hours playtime)
- **Tactile Button** - Primary input
- **Piezo Buzzer** - Audio feedback (beeps/tones only, no voice)
- **Vibration Motor** - Haptic feedback
- **TP4057 USB-C Charger** - Built-in charging circuit
- **MT3608 Boost Converter** - 5V power for bright LEDs

**Input Methods (The Magic):**
- **SHAKE** - Accelerometer detects shake intensity
- **TILT** - 4-directional tilt (left/right/forward/back) for A/B/C/D answers
- **SPIN** - Gyroscope measures rotation speed (RPM)
- **TAP** - Button press to confirm selections
- **HOLD** - Hold button for special actions (screw opponent, double down, etc.)

**Output:**
- **LED Ring** - Player colors, animations, feedback
- **Buzzer** - Correct beeps, wrong buzzes, alerts
- **Vibration** - Wrong answer punishment, warnings
- **WiFi** - Sends game data to server, receives commands

**Durability:**
- Bar-safe design (spill resistant, drop tested)
- No exposed circuits
- Replaceable batteries
- (Future: 3D printed enclosures, silicone coating)

---

## 🎲 THE GAMES

### Total: 92 Games

#### 51 Skill Games (ESP32 Firmware - ALREADY CODED)
Physical challenges using puck hardware:
- Speed Tap Battle - Tap as fast as possible
- Shake Duel - Shake faster than opponent
- Red Light Green Light - Freeze when red LED
- LED Chase Race - Track moving LED
- Simon Says LED - Memory pattern matching
- Hot Potato - Don't be holding when timer stops
- Spin Master - Spin speed competition
- Balance Master - Hold perfectly still
- Reaction Chain - Sequential tap timing
- *...42 more coded and ready*

**Categories:**
- Speed games (reaction time)
- Physical games (shake, spin)
- Skill games (timing, precision)
- Gambling games (roulette, risk-taking)
- Social games (hot potato, dare roulette)

#### 41 YDKJ-Style Trivia Games (SERVER-BASED - IN PROGRESS)
Inspired by Jackbox Party Packs, adapted for puck controls:

**Core Trivia Games (10):**
1. Trivia Murder Party - Horror trivia + "Killing Floor" mini-games
2. Category Royale - Shake to claim categories
3. Speed Pyramid - Fast answers = more points
4. Fact or Crap - Tilt left/right for true/false
5. You Don't Know Jack: Puck Edition - Classic with screw mechanics
6. Multiplier Madness - Spin for 0.5x-3x multipliers
7. Trivia Gauntlet - 3 strikes elimination
8. Wheel of Enormous Proportions - Trivia + wheel spinning
9. Guesspionage - Guess survey percentages
10. Timejinx - Guess historical years

**Lie Detection & Deception (7):**
11. Fibbage: Puck Lies - Create lies, vote for truth
12. Survive the Internet - Twist quotes out of context
13. Split the Room - Create divisive scenarios
14. Hypnotorious - Find the outlier player
15. Suspectives - Murder mystery deduction
16. Fakin' It: Puck Edition - One player fakes actions
17. Weapons Drawn - Social deduction murder game

**Word & Creativity (8):**
18. Quiplash: Puck Wars - Funniest answer wins
19. Mad Verse City: Rap Battle - Fill-in rap lyrics
20. Joke Boat - Complete joke setups
21. Dictionarium - Define fake words
22. FixyText - Chaotic autocorrect
23. Word Spud - Word association chain
24. Blather 'Round - Describe with limited vocabulary
25. Nonsensory - Rate descriptions 1-10

**Gambling & Risk (5):**
26. All or Nothing - Bet all points on final question
27. Russian Roulette Trivia - Progressive penalties
28. Double or Nothing - Bet to double points
29. Bracketeering - Tournament bracket voting
30. Lucky Streak - Consecutive answer multipliers

**Physical & Skill Hybrid (7):**
31. Shake Attack - Jack Attack rapid-fire matching
32. Screw Your Neighbor - Force opponent to answer
33. Hostage Trivia - One vs everyone
34. Chaos Round - Random modifiers each question
35. Perfect Timing - Tap at exact moment
36. Balance Master - Answer while balancing
37. Spin Zone - Answer speed + spin combo

**Team & Cooperative (4):**
38. The Poll Mine - Team poll ranking guessing
39. Devils and the Details - Cooperative chores + selfish tasks
40. Push the Button - Find the alien impostor
41. Legends of Trivia - Cooperative RPG trivia

**Question Style - YDKJ Absurdity:**
Example: "Your dad stepped on a rusty nail 3 days ago. Now his leg is turning black and smells like death. The doctor says it's gangrene. What's your move?"
- A: Cut off his foot before it spreads ✅
- B: Let nature take its course
- C: Rub essential oils on it
- D: Google "gangrene home remedies"

Commentary: "Correct! Gangrene spreads fast. Cut off the foot, save the leg. Brutal but necessary."

---

## 💻 TECH STACK

### Hardware Layer
- **ESP32** - Dual-core 240MHz, WiFi, Bluetooth, 520KB RAM
- **Arduino Framework** - C++ firmware with PlatformIO
- **Custom libraries:** FastLED (LEDs), MPU6050 (motion), WiFi, HTTPClient

### Server/Backend
- **Language:** Python 3.12
- **Framework:** Flask + Flask-SocketIO
- **Database:** SQLite (dev) → PostgreSQL (production)
- **WebSockets:** Real-time game state sync
- **REST API:** Score submission, game management

**Key Server Components:**
- `app.py` - Main Flask server
- `trivia_routes.py` - Trivia game API endpoints
- `trivia_game_engines.py` - Game logic for 41 trivia types
- `trivia_session_manager.py` - 20-min curated session flow
- `database.py` - SQLite/PostgreSQL abstraction layer

### Frontend/Display
- **Customer Dashboard:** HTML/CSS/JavaScript (vanilla)
- **TV Display:** Large screen interface for spectators
- **Admin Dashboard:** Venue management, question editor
- **Rendering:** Jinja2 templates, real-time WebSocket updates

### Database Schema
**Tables:**
- `pucks` - Device registration, battery status
- `games` - Game sessions, scores
- `bars` - Venue information
- `trivia_questions` - 500+ YDKJ questions (34 created so far)
- `trivia_sessions` - Active trivia games
- `trivia_answers` - Player responses, scoring
- `trivia_categories` - 11 question categories
- `trivia_game_types` - 41 game type definitions
- `trivia_skill_breaks` - Skill game integration

### Cloud Infrastructure (Future)
- **Hosting:** AWS/DigitalOcean VPS
- **CDN:** Cloudflare (static assets, DDoS protection)
- **Voice Generation:** ElevenLabs API (host commentary)
- **Analytics:** Mixpanel or custom dashboard

### Development Tools
- **IDE:** VS Code + PlatformIO
- **Version Control:** Git + GitHub
- **Prototyping:** Breadboards → Custom PCB (future)
- **3D Modeling:** (Future enclosure design)

---

## 🏢 BUSINESS MODEL

### Revenue Streams

**1. Hardware Sales (Primary - B2B)**
- **Puck 6-Pack:** $900-1,200 per set
- **Cost:** $250-350 to build 6 pucks
- **Margin:** 65-75% gross margin
- **Target:** Bars, breweries, entertainment venues

**2. Subscription SaaS (Recurring - B2B)**
- **Per-Venue License:** $99-199/month
- **Includes:**
  - Cloud-hosted server
  - Question database (500+ expanding)
  - Admin dashboard access
  - Analytics & leaderboards
  - Regular game updates
  - Bar vs Bar competitions
- **Margin:** 85-90% after hosting costs

**3. Premium Content (Future - B2B2C)**
- **Themed Question Packs:** $29-49 per pack
  - Sports trivia pack
  - Movie/TV pack
  - Local history pack (custom per city)
  - Seasonal packs (Halloween, Christmas, etc.)
- **Custom Branding:** Brewery-specific questions, logos

**4. Tournament Revenue (Future - B2C)**
- **Entry Fees:** $5-10 per player
- **Bar partnerships:** Venue takes door, we take digital entry
- **Prize pools:** Sponsored by beer brands

**5. Data Analytics (Future - B2B)**
- **Anonymized Insights:** Sell to alcohol brands
  - Peak bar hours
  - Game popularity by demographic
  - Engagement metrics
- **Advertising:** In-game sponsored questions (non-intrusive)

### Unit Economics (Per Venue)

**Initial Sale:**
- 6 pucks @ $1,000 = $1,000 revenue
- Cost: $300 = $700 profit (70% margin)

**Recurring (Annual):**
- Subscription: $150/mo × 12 = $1,800/year
- Server costs: $20/mo × 12 = $240/year
- **Net:** $1,560/year per venue (87% margin)

**Lifetime Value (3 years):**
- Initial: $700
- Recurring: $1,560 × 3 = $4,680
- **LTV:** $5,380 per venue

**Customer Acquisition Cost:**
- Direct sales: $200 (demo unit, travel)
- **Payback:** 1.5 months

---

## 🎯 TARGET MARKETS

### Primary: Bars & Breweries
- **TAM:** 60,000+ bars in US
- **Serviceable:** 15,000 (modern, tech-forward venues)
- **Target Year 1:** 100 venues

**Why Bars Win:**
- Extended dwell time = more drink sales
- Competitive social atmosphere
- Existing TVs for display
- Willing to pay for customer engagement tools
- Repeat customers (regulars)

**Sales Pitch:**
"Increase average ticket by 30% and dwell time by 45 minutes. Customers stay for 'one more round' to finish the game."

### Secondary Markets

**2. Airport Lounges**
- **Value Prop:** Time-killer entertainment for travelers
- **Adaptation:** Quick 5-10 min games, luggage-safe design
- **Target:** Premium lounges (Amex Centurion, Delta Sky Club)
- **Pricing:** Higher margin ($2,000+ per lounge)

**3. Senior Living Centers**
- **Value Prop:** Cognitive stimulation, social engagement
- **Adaptation:** Slower pace, 60s-80s nostalgia trivia, health tracking
- **Target:** 15,000+ senior communities
- **Pricing:** B2B healthcare model ($5,000+ annual contracts)

**4. College Campuses**
- **Value Prop:** Dorm/rec room entertainment
- **Adaptation:** Student-focused trivia, party games
- **Target:** Student unions, Greek life
- **Pricing:** Edu discount ($600 per 6-pack)

**5. Corporate Events**
- **Value Prop:** Team building, ice breakers
- **Adaptation:** Professional trivia, leadership scenarios
- **Target:** Companies with 100+ employees
- **Pricing:** Event rental ($500/day) or purchase

**6. Cruise Ships**
- **Value Prop:** Daily passenger entertainment
- **Target:** Major cruise lines (Carnival, Royal Caribbean)
- **Pricing:** Fleet deals ($50,000+ annual)

**7. Sports Bars (Halftime Entertainment)**
- **Value Prop:** Fill dead air during commercials/halftime
- **Adaptation:** Sports trivia, fast rounds
- **Pricing:** Premium tier $1,500 for 6 pucks

**8. Hotel Lobbies**
- **Value Prop:** Guest engagement, lobby activation
- **Target:** Boutique hotels, resorts
- **Pricing:** $1,200 per set

**9. Waiting Rooms (Medical/Dental)**
- **Value Prop:** Anxiety reduction, time passes faster
- **Target:** High-end practices
- **Pricing:** $800 per set (smaller venues)

**10. Food Courts / Malls**
- **Value Prop:** Keep families entertained while eating
- **Target:** Modern food halls
- **Pricing:** $1,500 per zone

---

## 📊 COMPETITIVE LANDSCAPE

### Direct Competitors

**1. Buzztime / NTN (Bar Trivia Tablets)**
- **Weakness:** Outdated UI, individual tablets (not social), expensive
- **Our Advantage:** Physical pucks more engaging, group play, modern games

**2. Jackbox Party Packs**
- **Weakness:** Requires everyone to have phones, no physical component
- **Our Advantage:** Dedicated hardware, better for bars (no phone distractions)

**3. Traditional Bar Trivia (Host-Based)**
- **Weakness:** Requires hiring trivia host, once per week, not interactive
- **Our Advantage:** 24/7 availability, automated, multiple game types

**4. Bar Arcade Games (Golden Tee, etc.)**
- **Weakness:** $5,000+ per unit, single-player, takes up floor space
- **Our Advantage:** $1,000 for 4+ players, table-top, 92 games in one

### Indirect Competitors

**5. Phones (The Real Enemy)**
- **Weakness:** People stare at their own screens, anti-social
- **Our Advantage:** Forces social interaction, shared experience

**6. Darts / Pool Tables**
- **Weakness:** Requires skill, excludes casual players, takes space
- **Our Advantage:** Everyone can play trivia, instant pickup

---

## 🚀 GO-TO-MARKET STRATEGY

### Phase 1: Local Pilot (Months 1-3)
- **Target:** 5 bars in home city
- **Offer:** Free hardware, $50/mo subscription (beta pricing)
- **Goal:** Prove concept, gather feedback, video testimonials

**Metrics:**
- Average session length
- Repeat play rate
- Revenue impact on bar sales
- NPS from bar owners + customers

### Phase 2: Regional Expansion (Months 4-8)
- **Target:** 50 bars across 3 major cities
- **Pricing:** Full price ($1,000 hardware + $150/mo)
- **Channel:** Direct sales (in-person demos)
- **Marketing:** Case studies from Phase 1 venues

### Phase 3: National Scale (Months 9-18)
- **Target:** 500 venues nationwide
- **Channel:** Inside sales team (3-5 reps)
- **Partnerships:** Bar equipment distributors
- **Marketing:** Trade shows (Nightclub & Bar Show), digital ads

### Phase 4: Adjacent Markets (Year 2+)
- Airport lounges (premium margin)
- Senior living (healthcare channel)
- Corporate events (B2B sales)

---

## 💰 FINANCIAL PROJECTIONS (5-Year)

### Year 1
- **Venues:** 100
- **Hardware Revenue:** $100,000 (100 × $1,000)
- **Subscription Revenue:** $180,000 (100 × $150/mo × 12)
- **Total Revenue:** $280,000
- **Costs:** $150,000 (COGS, hosting, salaries)
- **Profit:** $130,000 (46% margin)

### Year 2
- **Venues:** 500 (400 new)
- **Hardware Revenue:** $400,000
- **Subscription Revenue:** $900,000 (500 × $150 × 12)
- **Total Revenue:** $1,300,000
- **Costs:** $550,000
- **Profit:** $750,000 (58% margin)

### Year 3
- **Venues:** 1,500 (1,000 new)
- **Hardware Revenue:** $1,000,000
- **Subscription Revenue:** $2,700,000 (1,500 × $150 × 12)
- **Premium Content:** $150,000
- **Total Revenue:** $3,850,000
- **Costs:** $1,500,000
- **Profit:** $2,350,000 (61% margin)

### Year 5 Target
- **Venues:** 5,000+
- **Annual Revenue:** $10M+
- **Recurring Revenue:** 85%+
- **Valuation:** $50-75M (5-7x revenue multiple for SaaS)

---

## ✅ WHAT'S BUILT (Current Status)

### Hardware (COMPLETE - 90%)
- ✅ 6 working prototypes built on breadboards
- ✅ All components sourced and tested
- ✅ Motion controls working (shake, tilt, spin)
- ✅ LED animations functional
- ✅ WiFi connectivity stable
- ⏳ Custom enclosure design (pending)
- ⏳ PCB design for manufacturing scale (pending)

### Firmware (COMPLETE - 100%)
- ✅ All 51 skill games coded and tested
- ✅ BLE communication working
- ✅ Battery management implemented
- ✅ Game state machine complete

### Server Backend (COMPLETE - 70%)
- ✅ Flask server running
- ✅ SQLite database schema complete
- ✅ WebSocket real-time updates working
- ✅ REST API for score submission
- ✅ Admin dashboard operational
- ✅ 7 of 41 trivia game engines coded
- ✅ 34 YDKJ-style questions written
- ⏳ Remaining 34 trivia game engines
- ⏳ 500+ question database (need 466 more)
- ⏳ Voice commentary generation (ElevenLabs)

### Frontend (COMPLETE - 80%)
- ✅ Customer dashboard (mode selection, gameplay)
- ✅ TV display interface
- ✅ Admin question editor
- ✅ Leaderboard system
- ✅ Results/podium display
- ⏳ Polished UI/UX design
- ⏳ Animated transitions

---

## ❌ WHAT'S STILL NEEDED

### Technical
1. **34 more trivia game engines** (Category Royale, etc. need full implementation)
2. **466 more YDKJ questions** (have 34, need 500 total)
3. **Voice commentary** (ElevenLabs integration for host voice)
4. **Custom puck enclosures** (3D printed or injection molded)
5. **PCB design** for manufacturing (move from breadboards)
6. **Production firmware** (over-the-air updates, diagnostics)
7. **Cloud infrastructure** (AWS deployment, not just localhost)

### Business
1. **Legal entity** (LLC formation)
2. **Patents/IP protection** (provisional patent on puck design)
3. **Insurance** (product liability)
4. **Manufacturing partner** (contract manufacturer for 100+ units)
5. **Sales team** (1 sales rep to start)
6. **Marketing materials** (demo videos, sales deck)
7. **Pilot venue agreements** (5 beta locations)

### Financial
1. **Seed funding** ($50-100K to complete buildout)
2. **Inventory financing** (first 50 units = $15K)
3. **Working capital** (runway for sales cycle)

---

## 🎯 KEY METRICS TO TRACK

### Product Metrics
- Session length (target: 20 min average)
- Repeat play rate (target: 60%+ return within 7 days)
- Game completion rate (target: 85%+ finish all 3 rounds)
- Favorite game types (data-driven content roadmap)
- Puck uptime/reliability (target: 99%+)

### Business Metrics
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)
- LTV:CAC ratio (target: 3:1 minimum)
- Monthly Recurring Revenue (MRR)
- Churn rate (target: <5% monthly)
- Net Promoter Score (NPS) - venues + end users
- Revenue per venue
- Gross margin (target: 70%+)

### Bar Impact Metrics (The Selling Point)
- Average ticket increase (target: +30%)
- Dwell time increase (target: +45 min)
- Return visit rate
- Table occupancy rate
- Social media mentions/UGC

---

## 🚧 BIGGEST RISKS & MITIGATION

### Risk 1: Hardware Failure in Bar Environment
- **Mitigation:** Ruggedized design, warranty program, rapid replacement
- **Cost:** 10% buffer for warranty replacements

### Risk 2: Bars Don't Want to Pay Subscription
- **Mitigation:** Free trial period, performance guarantees (increase sales or money back)
- **Backup:** One-time purchase option (higher upfront cost)

### Risk 3: Content Gets Stale (Question Fatigue)
- **Mitigation:** Monthly question pack releases, user-generated content, seasonal updates
- **Investment:** Hire part-time writers ($2K/mo)

### Risk 4: Can't Compete with Phones
- **Mitigation:** Enforce "no phones" during games, gamify social engagement
- **Data:** Bars report 40% less phone usage during active games

### Risk 5: Manufacturing Delays/Quality Issues
- **Mitigation:** Start with small batches (10 units), local assembly, quality testing protocol
- **Partner:** Work with US-based contract manufacturer

### Risk 6: Licensing/Legal (Jackbox Similarities)
- **Mitigation:** Original game mechanics, different hardware platform, consult IP attorney
- **Cost:** $10K legal budget

---

## 💡 UNFAIR ADVANTAGES

1. **Physical Hardware Moat** - Harder to copy than pure software
2. **Captive Audience** - Bars control the environment (can't just download an app)
3. **Network Effects** - Bar vs Bar competitions create stickiness
4. **Data Flywheel** - More venues = more gameplay data = better game design
5. **Content Library** - 500+ questions becomes valuable IP over time
6. **First Mover** - No direct competitor in "gaming puck for bars" space

---

## 🎨 BRAND IDENTITY

**Name:** TABLE WARS
**Tagline:** "Battle at Your Table"
**Voice:** Irreverent, competitive, bar-friendly (like YDKJ meets ESPN)
**Design:** Bold colors, neon aesthetics, retro arcade vibes
**Mascot:** (TBD - possibly an angry hockey puck character)

---

## 📞 ASK FOR EVALUATOR

**Please analyze and provide feedback on:**

1. **Business Model Viability** - Is the B2B SaaS + hardware model sound?
2. **Market Sizing** - Are we targeting the right venues? What are we missing?
3. **Pricing** - Is $1,000/6-pack + $150/mo subscription realistic?
4. **Tech Stack** - Any red flags in our architecture?
5. **Competitive Position** - How do we truly differentiate from Buzztime/Jackbox?
6. **Go-to-Market** - Is the pilot → regional → national plan feasible?
7. **Biggest Risks** - What are we not seeing?
8. **Funding Needs** - How much capital to reach profitability?
9. **Unit Economics** - Do our margins make sense?
10. **Product-Market Fit** - Will bars actually pay for this?

**Specific Questions:**
- Should we focus on bars exclusively or diversify early?
- Is hardware sale + subscription the right model, or go pure SaaS?
- How do we prevent bars from buying hardware then canceling subscription?
- What's a realistic Year 1 venue target? (We said 100)
- Should we build in-house or outsource manufacturing?

---

## 📎 SUPPORTING MATERIALS

**Files to Reference:**
- `YDKJ_41_GAMES.md` - Full game descriptions
- `CURATED_SESSION_GUIDE.md` - Session flow documentation
- `PARTS_LIST.md` - Hardware BOM and costs
- Database: 34 questions already created (see examples above)

**Demo Available:**
- Working breadboard prototypes (6 units)
- Local Flask server running all current features
- Can demo in-person or via video

---

**Document Version:** 1.0
**Last Updated:** December 2024
**Contact:** [Your info here]
**Website:** (Coming soon)

---

*End of Business Overview*
