# ⚡ TABLE WARS - QUICK START (1 PAGE)

## 🎯 YOUR NEW WORKFLOW (SIMPLE VERSION)

### **OLD WAY** ❌
```bash
# Multiple terminal windows
# Repeating context
# Manual work
```

### **NEW WAY** ✅
```bash
cd table-wars-puck
claude

# Use slash commands - that's it!
```

---

## 📱 YOUR 6 SLASH COMMANDS

| Command | What It Does | Example |
|---------|--------------|---------|
| `/add-game [name]` | Adds complete new game (code + server + docs) | `/add-game "Duck Hunt"` |
| `/test-firmware` | Compiles & uploads to ESP32 | `/test-firmware` |
| `/server-start` | Starts Flask server | `/server-start` |
| `/patent-update [desc]` | Updates patent application | `/patent-update "new game"` |
| `/game-ideas` | Brainstorms game concepts | `/game-ideas` |
| `/status` | Shows project health | `/status` |

---

## 🤖 WHEN TO USE WHICH MODEL

| Model | Use For | Command |
|-------|---------|---------|
| **Sonnet 4.5** (default) | 95% of work: coding, debugging, implementing | `claude` |
| **Opus 4.5** | 5%: hard problems, novel ideas, strategy | `claude --model opus` |
| **Haiku 4** | Quick simple tasks, typos, fast edits | `claude --model haiku` |

**Reality: Just use Sonnet (default). It's perfect.**

---

## ⚡ TYPICAL WORK SESSION

```bash
# 1. Start ONE session
cd table-wars-puck
claude

# 2. Check what needs attention
/status

# 3. Add new game
/add-game "Greyhound Racing"

# 4. Test it
/test-firmware

# 5. Update patent
/patent-update "Added greyhound racing"

# 6. Done!
```

**Time: 30 mins** (used to take 3-4 hours)

---

## 🚨 3 GOLDEN RULES

1. **USE ONE SESSION** - No multiple terminals
2. **LET AGENTS WORK** - Give full instructions, don't micro-manage
3. **USE SLASH COMMANDS** - Don't type long instructions if there's a command

---

## 📞 HELP

Type in Claude:
```
> "show me all commands"
> "help with [command]"
> "how do I..."
```

**Full guide:** `CLAUDE_CODE_SETUP.md`

---

**NOW GO BUILD** 🚀
