# TABLE WARS - Week 1 Action Plan

**Goal**: Contact 50 bars, book 10 demos, close 5 paid pilots in 30 days.

**This week's focus**: Customer discovery + build demo materials

---

## 📅 MONDAY

### Morning (9am-12pm): Competitor Research

- [ ] **Create spreadsheet**: Competitor Analysis
  - Columns: Company, Product, Pricing, Customer Reviews, Your Advantage
- [ ] **Research 5 competitors**:
  - [ ] Buzztime (buzztime.com) - pricing model?
  - [ ] NTN Trivia - why are they declining?
  - [ ] Pour Taproom - how do they monetize games?
  - [ ] TouchTunes/AMI Jukeboxes - lease model?
  - [ ] Arachnid dartboards - purchase vs lease?

### Afternoon (1pm-5pm): Customer Interviews

- [ ] **Call 3 bars that use Buzztime**
  - Google "bars with trivia near me"
  - Ask: "What do you pay? What do you love/hate?"
- [ ] **Build target bar list** (start with 20 bars)
  - Sports bars, college bars, craft beer bars
  - Within 30 min drive of your location
  - Get: Name, address, phone, owner/manager name

**Evening**: Review notes, identify patterns

---

## 📅 TUESDAY

### Morning (9am-12pm): Build Sales Materials

- [ ] **Create 1-page pitch deck** (Google Slides or Keynote)
  - Slide 1: Problem (bars lose money on slow nights)
  - Slide 2: Solution (TABLE WARS interactive pucks)
  - Slide 3: How it works (6 pucks, 8 games, TV scoreboard)
  - Slide 4: Pricing ($99/month or $599 purchase)
  - Slide 5: Next steps (2-week free trial)

- [ ] **Draft email template**:
```
Subject: Quick question about [Bar Name]'s slow nights

Hi [Manager Name],

I'm [Your Name], and I help bars increase weeknight sales
with interactive game tech. Quick question:

What's your biggest challenge with Tuesday/Wednesday slow nights?

I've built something that's helping bars like [Local Bar] see
30-40% sales lifts on game nights, and I'd love to get your
feedback.

Can I swing by for 5 minutes this week to show you? I'll bring
coffee. Tuesday at 2pm?

Thanks,
[Your Name]
[Phone]

PS - Here's a 60-sec video if you're curious: [link]
```

### Afternoon (1pm-5pm): Create Demo Video

- [ ] **Record 90-second demo video** (iPhone is fine)
  - 0-15 sec: Hook ("What if every table was a game?")
  - 15-60 sec: Show pucks lighting up, gameplay
  - 60-90 sec: Business value ("Customers stay longer = more drinks")
- [ ] **Upload to YouTube** (unlisted)
- [ ] **Test sending to 2 friends** - does it make sense?

**Evening**: Finalize pitch materials

---

## 📅 WEDNESDAY

### Morning (9am-12pm): Build Landing Page

- [ ] **Buy domain**: tablewars.io or tablewars.bar ($12)
- [ ] **Create 1-page site** (Carrd.co - $19/year)
  - Hero: "Turn Tables Into Multiplayer Battle Arenas"
  - How it works (3 steps)
  - Embed demo video
  - Pricing: "$99/month for 6 pucks"
  - Email capture: "Request Free Trial"
- [ ] **Set up email capture** (Airtable form - free)
- [ ] **Test on mobile** (most bar owners will view on phone)

### Afternoon (1pm-5pm): In-Person Bar Visits

**Target**: 5 bars, 2-4pm (slow time, manager available)

**What to bring**:
- [ ] 1 charged puck (for demo)
- [ ] Business cards (or just phone number on paper)
- [ ] Notebook (take notes)

**Script**:
> "Hi! I'm [Name], I build game tech for bars. Do you have 2 minutes?
> I want to show you something that's helping bars boost slow night sales."
>
> [Pull out puck, light it up]
>
> "This is TABLE WARS - interactive game pucks. Customers compete,
> scores show on your TV. Bars using this see 30-40% sales lifts
> on Tuesdays/Wednesdays."
>
> "Mind if I leave you my number? I'd love to demo the full system
> later this week."

**Track**:
- [ ] Bar name, manager name, phone
- [ ] Interested? (Yes/Maybe/No)
- [ ] Follow-up date

**Goal**: 2 demos booked for next week

**Evening**: Follow up with anyone who seemed interested

---

## 📅 THURSDAY

### Morning (9am-12pm): Cold Calling Blitz

**Target**: 20 calls

**Script**:
> "Hi, is [Manager Name] available? This is [Your Name] from TABLE WARS.
> We make interactive game pucks that help bars increase weeknight sales.
>
> I'd love to drop by for 5 minutes to show you how it works - are you
> free tomorrow around 2pm? I'll bring coffee."

**Objections**:
- "Not interested" → "Can I ask what you currently do for entertainment?"
- "Too busy" → "I'll make it 3 minutes. Tuesday at 2?"
- "Email me" → "Sure - [email] - but trust me, you gotta see the LEDs in person"

**Track in spreadsheet**:
- [ ] Bar name, phone, manager
- [ ] Response (interested/not interested/callback)
- [ ] Demo booked? (date/time)

**Goal**: Book 3 demos for next week

### Afternoon (1pm-5pm): More In-Person Visits

- [ ] Visit 5 more bars (same as Wednesday)
- [ ] Goal: Book 2 more demos

**Evening**: Update spreadsheet, plan Week 2

---

## 📅 FRIDAY

### Morning (9am-12pm): Instagram DM Outreach

**Target**: 10 bars with active Instagram

**Message**:
> "Hey [Bar Name]! 👋 Love your vibe. I'm building interactive
> game pucks (think glowing LED bar games) and looking for a
> few local bars to pilot them. Mind if I DM you a 60-sec demo
> video? No sales pitch - just want feedback."

[If they respond]
> [Send demo video link]
>
> "Would you ever try something like this for a slow Tuesday/
> Wednesday? I'm offering 2-week free trials to 5 local spots."

**Track**:
- [ ] Bar name, Instagram handle
- [ ] Responded? (Yes/No)
- [ ] Demo booked?

### Afternoon (1pm-5pm): Build Pilot Inventory

**Order components for 12 pucks** (2 pilot sets):
- [ ] 2× ESP32 DevKitC-32
- [ ] 2× WS2812B LED rings
- [ ] 2× MPU6050 accelerometers
- [ ] 2× TP4057 charging modules
- [ ] 2× 2000mAh LiPo batteries
- [ ] 2× Vibration motors
- [ ] 2× Piezo buzzers
- [ ] Wire, resistors, etc. (see PARTS_LIST.md)

**Estimated cost**: $360 ($180 per set)

**Evening**: Review week, plan Week 2 demos

---

## 📅 WEEKEND

### Saturday: Assemble Pilot Sets

- [ ] **Build 12 pucks** (2 sets of 6)
  - Follow BUILD_CHECKLIST.md
  - Test each puck thoroughly
  - Charge to 100%

- [ ] **Prepare pilot kits**:
  - [ ] 6 pucks in portable case
  - [ ] Raspberry Pi + scoreboard server
  - [ ] HDMI cable
  - [ ] Quick start guide (print from docs)
  - [ ] "How to Play" table tents (design + print)

### Sunday: Prep for Week 2

- [ ] **Review Week 1 metrics**:
  - Bars contacted: ___ / 50
  - Demos booked: ___ / 10
  - Interested bars: ___ / 20

- [ ] **Create Week 2 schedule**:
  - List all booked demos (date/time)
  - Plan demo logistics (who, where, when)
  - Rehearse demo script

- [ ] **Draft pilot agreement** (see BUSINESS_PLAYBOOK.md)

---

## 📊 WEEK 1 SUCCESS METRICS

**Minimum**:
- [ ] 20 bars contacted
- [ ] 5 demos booked for Week 2-3
- [ ] 2 pilot sets built and ready

**Target**:
- [ ] 50 bars contacted
- [ ] 10 demos booked
- [ ] 3 "yes, I'd try it for free" responses

**Stretch**:
- [ ] 100 bars contacted
- [ ] 15 demos booked
- [ ] 1 bar ready to do paid pilot immediately

---

## 🚨 RED FLAGS (Stop and Reassess)

If by end of Week 1:
- **<10 bars contacted** → You're not executing, need more urgency
- **<2 demos booked** → Your pitch isn't working, iterate
- **Everyone says "no thanks"** → Price too high? Product not compelling? Wrong customer segment?

**Action**: Review BUSINESS_PLAYBOOK.md Section "Scenario 1: Low Demand"

---

## ✅ WEEK 1 CHECKLIST (Print This)

### Monday
- [ ] Research 5 competitors
- [ ] Call 3 bars with Buzztime
- [ ] Build target bar list (20 bars)

### Tuesday
- [ ] Create 1-page pitch deck
- [ ] Draft email template
- [ ] Record demo video

### Wednesday
- [ ] Build landing page
- [ ] Visit 5 bars in person
- [ ] Book 2 demos

### Thursday
- [ ] Make 20 cold calls
- [ ] Visit 5 more bars
- [ ] Book 3 more demos

### Friday
- [ ] Send 10 Instagram DMs
- [ ] Order pilot components
- [ ] Review week, plan Week 2

### Saturday
- [ ] Assemble 2 pilot sets (12 pucks)
- [ ] Prepare pilot kits

### Sunday
- [ ] Review metrics
- [ ] Plan Week 2 demos
- [ ] Rehearse pitch

---

## 💡 TIPS FOR SUCCESS

**Do**:
✅ Move fast (velocity matters)
✅ Listen to bar owners (they know their business)
✅ Track everything in spreadsheet
✅ Follow up within 24 hours
✅ Be persistent but respectful

**Don't**:
❌ Overthink - just start calling bars
❌ Give up after 5 "no's" (expect 50)
❌ Skip tracking data (you need metrics)
❌ Wait until "everything is perfect"
❌ Forget to charge your demo puck 😅

---

## 📞 WEEK 2 PREVIEW

**Focus**: Run 10 demos, close 5 paid pilots

**Monday-Wednesday**: Demo days
- Run 3-4 demos with bars from Week 1 outreach
- Bring pilot kit, full demo setup
- Pitch pricing: "$99/month or $599 purchase"

**Thursday-Friday**: Follow-up + close
- Call all demo'd bars
- Address objections
- Close 2-3 paid pilots (goal: 5 total by end of Week 4)

---

**Ready? Start Monday. No excuses.**

Questions? See BUSINESS_PLAYBOOK.md for full details.

You've got this! 🚀
