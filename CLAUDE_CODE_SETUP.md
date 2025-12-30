# 🚀 TABLE WARS - CLAUDE CODE WORKFLOW GUIDE

**Your new superpower development setup**

---

## 🎯 WHAT YOU JUST GOT

You now have a **professional AI-assisted development workflow** with:
- ✅ Custom slash commands (shortcuts for common tasks)
- ✅ Agents (autonomous multi-step task execution)
- ✅ Persistent context (no more multiple terminal windows)
- ✅ Optimized for YOUR specific project

---

## 📱 HOW TO USE THIS (SIMPLE VERSION)

### **OLD WAY (What you were doing):**
```bash
# Terminal 1
claude
> "Add new game to firmware"

# Terminal 2
claude
> "Now test the compilation"

# Terminal 3
claude
> "Update the patent with new game"
```
**Problem:** Multiple windows, repeating context, inefficient

### **NEW WAY (What you do now):**
```bash
# ONE terminal, ONE session
cd table-wars-puck
claude

# Use slash commands
/add-game "Claw Machine Prize Game"
# Agent autonomously: adds game ID, creates files, updates code, tests compilation

/patent-update
# Updates patent application with new game details

/status
# Shows complete project status
```

**Result:** 10x faster, no repeated work, flawless execution

---

## 🎮 YOUR CUSTOM SLASH COMMANDS

You have 6 custom commands. Here's what they do:

### `/add-game [game name]`
**What it does:** Adds a complete new game mode to your system
**Example:** `/add-game "Duck Hunt"`
**What happens:**
1. Adds game ID to Config.h
2. Creates new game header file
3. Updates main firmware
4. Updates server to handle new game
5. Tests compilation
6. Documents the game

**When to use:** Every time you want to add a new game

---

### `/test-firmware`
**What it does:** Compiles and optionally uploads firmware to ESP32
**Example:** `/test-firmware`
**What happens:**
1. Checks PlatformIO installation
2. Compiles firmware
3. Reports any errors (with fixes suggested)
4. Offers to upload to connected ESP32
5. Offers to monitor serial output

**When to use:** After making firmware changes, before testing

---

### `/server-start`
**What it does:** Starts your Flask server
**Example:** `/server-start`
**What happens:**
1. Checks for virtual environment
2. Creates venv if needed
3. Installs requirements
4. Starts server on port 5001
5. Reports endpoints available

**When to use:** When you want to test the full system (puck + server + dashboard)

---

### `/patent-update [description]`
**What it does:** Updates provisional patent application
**Example:** `/patent-update "Add greyhound racing game description"`
**What happens:**
1. Reads current patent file
2. Finds appropriate section
3. Adds new content in proper format
4. Maintains patent language style

**When to use:** When you add new features/games/markets to document in patent

---

### `/game-ideas`
**What it does:** Brainstorms new game concepts
**Example:** `/game-ideas`
**What happens:**
1. Considers your hardware (puck capabilities)
2. Considers your markets (bars, seniors, corporate)
3. Generates 5-10 creative, FUN game ideas
4. Describes how each would work
5. Suggests TV graphics

**When to use:** When you're out of ideas or want fresh inspiration

---

### `/status`
**What it does:** Shows complete project health check
**Example:** `/status`
**What happens:**
1. Checks firmware files
2. Checks if server running
3. Checks hardware files (PCB, 3D models)
4. Checks documentation
5. Shows git status
6. Lists next priorities

**When to use:** Start of each work session, or when you're lost

---

## 🤖 USING AGENTS (THE MAGIC)

### **What are agents?**
Agents = Claude autonomously executing multi-step tasks

**Example without agents:**
```bash
claude "search for Config.h"
# You wait...
claude "now read that file"
# You wait...
claude "add this game ID"
# You wait...
claude "now compile and test"
# You wait...
```
**Time:** 20+ minutes, 4+ interactions

**Example WITH agents (using slash commands):**
```bash
/add-game "Stack Boxes"
```
**Time:** 2 minutes, 1 interaction
**What agent does automatically:**
- Searches codebase ✅
- Reads relevant files ✅
- Writes new code ✅
- Compiles and tests ✅
- Reports results ✅

**ALL WHILE YOU GET COFFEE** ☕

---

## 💪 HOW TO SWITCH MODELS

Remember those tweets about Opus 4.5? Here's when to use it:

### **Sonnet 4.5 (DEFAULT - Use 95% of the time)**
```bash
# Just use claude normally
claude "add shake detection algorithm"
```
**Use for:**
- Writing code ✅
- Implementing features ✅
- Debugging ✅
- Testing ✅
- Documentation ✅

---

### **Opus 4.5 (GENIUS MODE - Use 5% of the time)**
```bash
# Specify --model opus
claude --model opus "Design a completely new competitive game mechanic I haven't thought of that would blow people's minds"
```
**Use for:**
- Novel problem solving (stuck on hard problem)
- Architectural decisions (choosing between approaches)
- Creative brainstorming (need breakthrough ideas)
- Complex reasoning (multi-step strategy)

**Cost:** 5x more expensive than Sonnet
**Speed:** Slower
**Smarter:** Yes, for complex novel problems

**Reality:** Sonnet 4.5 is perfect for 95% of your work. Use Opus sparingly.

---

### **Haiku 4 (SPEED MODE - Quick tasks)**
```bash
claude --model haiku "fix this typo in README"
```
**Use for:**
- Simple edits
- Quick questions
- Typo fixes
- Fast simple tasks

**Cost:** Cheaper
**Speed:** Fastest
**Smarter:** No, but fast enough for simple stuff

---

## 🔥 BEST PRACTICES

### **1. Use ONE persistent session**

**DON'T do this:**
```bash
# Terminal 1
claude "task 1"
# Terminal 2
claude "task 2"
# Terminal 3
claude "task 3"
```

**DO this:**
```bash
# ONE terminal
cd table-wars-puck
claude

# Now have entire conversation here
# Context automatically persists
# No need to reference old conversations
```

---

### **2. Let agents work**

**DON'T micro-manage:**
```bash
> "Find Config.h"
(wait for response)
> "Now read line 47"
(wait for response)
> "Now change that to..."
```

**DO give complete instructions:**
```bash
> /add-game "Claw Machine - player tilts puck to move virtual claw, button to grab prize, TV shows 3D claw machine graphics"
```

Agent does ALL steps autonomously.

---

### **3. Use slash commands first**

**Before typing long instructions, check if there's a command:**
- Want to add game? → `/add-game`
- Want to test? → `/test-firmware`
- Want ideas? → `/game-ideas`
- Want status? → `/status`

Slash commands are optimized shortcuts.

---

### **4. Switch to Opus ONLY when truly stuck**

**Sonnet is enough for:**
- ✅ Implementing known solutions
- ✅ Following established patterns
- ✅ Debugging
- ✅ Testing

**Opus is for:**
- 🧠 "I have no idea how to approach this problem"
- 🧠 "I need a creative breakthrough"
- 🧠 "This requires novel thinking"

**If in doubt, start with Sonnet. Switch to Opus if it can't solve it.**

---

## 📝 YOUR WORKFLOW (START TO FINISH)

### **Morning Work Session:**

```bash
# 1. Navigate to project
cd table-wars-puck

# 2. Start Claude Code (ONE session)
claude

# 3. Check status
/status
# Tells you what needs attention

# 4. Add new game
/add-game "Greyhound Racing - players bet on dogs, shake to cheer, TV shows 3D race"
# Agent implements everything

# 5. Test it
/test-firmware
# Compiles, uploads, tests

# 6. Update patent
/patent-update "Added greyhound racing game with virtual betting mechanics"
# Updates patent file

# 7. Start server to test
/server-start
# Server runs, test full system

# 8. Done!
```

**Time:** 30-60 minutes for complete game addition (including testing)
**Old way:** Would take 3-4 hours

---

## 🎯 EXAMPLE: ADDING A NEW GAME (FULL WALKTHROUGH)

**Let's add "Duck Hunt" step-by-step:**

```bash
$ cd table-wars-puck
$ claude

> /add-game "Duck Hunt"

[Agent starts working...]

✅ Added game ID (GAME_DUCK_HUNT = 11) to Config.h
✅ Created src/game_duck_hunt.h with controller logic:
   - Tilt puck to aim
   - Button to shoot
   - LED shows aim quality (green = on target)
   - Buzzer for shot sound

✅ Updated src/main_ble_wifi_test.h to handle game 11

✅ Added server endpoint in server/app.py:
   - /game/duck_hunt renders TV graphics
   - Shows flying ducks
   - Shows crosshair based on puck tilt data
   - Scores hits

✅ Compiled firmware - SUCCESS (0 errors)

✅ Game ready to test!

[Agent done. Took 2 minutes.]

> Thanks! Now test it on the ESP32

/test-firmware

[Agent checks...]
✅ PlatformIO installed
✅ Compilation successful
✅ ESP32 detected on /dev/cu.usbserial-0001
✅ Uploading firmware...
✅ Upload complete!
✅ Serial monitor started

[You can now test Duck Hunt game on real hardware]
```

**That's it. Game added, tested, ready to play in 5 minutes.**

**Old way would take:** 2-3 hours (finding files, writing code, testing, debugging)

---

## 🚀 ADVANCED: CREATING YOUR OWN SLASH COMMANDS

You can add more commands easily!

### **Create new command:**
```bash
# 1. Create file in .claude/commands/
# Example: .claude/commands/order-pcb.md

# 2. Write the instructions:
```

**Example command - `/order-pcb`:**

```markdown
Help the user order PCBs from JLCPCB.

Steps:
1. Check if Gerber files exist
2. Remind user to upload to jlcpcb.com
3. Provide recommended settings:
   - Quantity: 5
   - Color: Black
   - Finish: ENIG
   - Thickness: 1.6mm
4. Estimate cost ($150-200)
5. Provide link: https://cart.jlcpcb.com/quote

Be encouraging and helpful.
```

**Save that, now you have `/order-pcb` command!**

---

## 💡 TIPS FROM THE PROS (What Twitter people are doing)

### **1. Ben Holmes: "Agentic Coding"**
**What he means:** Let Claude do entire features autonomously

**How you do it:**
```bash
/add-game "Complex multi-step game"
# Agent handles ALL implementation
```

### **2. Opus 4.5 hype**
**Reality check:** It's great but NOT needed for implementation
**Use Opus for:** Strategy, novel problems
**Use Sonnet for:** Execution (what you're doing 90% of the time)

### **3. "Steve Jobs persona"**
**What they mean:** Ask Claude to think like Steve Jobs for strategy

**How you do it:**
```bash
claude --model opus "Act as Steve Jobs. Review my Table Wars business strategy and tell me what I'm missing or doing wrong. Be brutally honest."
```

### **4. Slack/Discord/Linear integration (MCP)**
**Skip this for now.** You don't need it yet.
**Focus:** Ship product first, optimize workflow later

---

## ⚡ QUICK REFERENCE

| Task | Command | Time |
|------|---------|------|
| Add new game | `/add-game "Game Name"` | 2-5 mins |
| Test firmware | `/test-firmware` | 1-2 mins |
| Start server | `/server-start` | 30 secs |
| Update patent | `/patent-update "description"` | 1 min |
| Get ideas | `/game-ideas` | 2 mins |
| Check status | `/status` | 30 secs |
| Use genius mode | `claude --model opus "hard problem"` | Varies |
| Quick edits | `claude --model haiku "simple fix"` | < 1 min |

---

## 🎉 YOU'RE NOW A 10X DEVELOPER

**What you had before:**
- Opening multiple terminals ❌
- Manually tracking context ❌
- Repeating instructions ❌
- Slow iteration ❌

**What you have now:**
- ONE persistent session ✅
- Auto slash commands ✅
- Autonomous agents ✅
- 10x faster development ✅

---

## 🔥 30-DAY CHALLENGE

**Use Claude Code like a pro for 30 days:**

**Week 1: Learn the basics**
- Use `/status` every morning
- Use `/add-game` for at least 3 new games
- Use `/test-firmware` after every change

**Week 2: Get comfortable**
- Create 1 custom slash command
- Try Opus once for a hard problem
- Let agents work (don't micro-manage)

**Week 3: Optimize**
- Never open multiple Claude windows
- Use slash commands for EVERYTHING
- Measure time saved (you'll notice!)

**Week 4: Master it**
- Teach someone else your workflow
- Share your setup on Twitter
- Help others optimize

---

## 🚨 TROUBLESHOOTING

**Q: Slash command not working**
A: Make sure file is in `.claude/commands/` with `.md` extension

**Q: Agent seems stuck**
A: Let it finish. If truly stuck (> 5 mins), interrupt and try simpler instructions

**Q: Want to go back to old way**
A: Just use `claude` without commands. Everything still works.

**Q: How do I know which model I'm using?**
A: Default is Sonnet. You have to explicitly type `--model opus` or `--model haiku`

**Q: Slash command gives wrong result**
A: Edit the `.claude/commands/[command].md` file to fix instructions

---

## 💪 FINAL WORDS

**You just unlocked:**
- ✅ Professional development workflow
- ✅ Autonomous agents doing grunt work
- ✅ Custom shortcuts for YOUR project
- ✅ 10x productivity boost

**Now stop reading and START USING IT.**

Go add those new games. File that patent. Build your business.

**Let's fucking GO.** 🚀

---

**Questions? Just ask in Claude:**
```bash
> "How do I use the /add-game command?"
> "Show me all available slash commands"
> "Help me create a custom command for X"
```

**I'm here to help. That's literally what I'm for.**
