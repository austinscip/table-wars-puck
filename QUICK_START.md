# Quick Start Guide

## Create New Project (30 seconds)

```bash
cd ~/Projects/.hardware_project_template/tools/scripts
./new_project.sh
```

Follow prompts, done!

## Key Files to Update First

1. **`.claude.md`** ← AI memory (update as you work!)
2. **`README.md`** ← Project overview
3. **`CHANGELOG.md`** ← Version history

## Folder Structure Cheat Sheet

```
hardware/
  ├── altium/         ← Your PCB design files here
  ├── manufacturing/
  │   ├── gerbers/    ← Export Gerbers here
  │   ├── bom/        ← Export BOM.csv here
  │   ├── cpl/        ← Export pick-and-place here
  │   ├── drill/      ← Export drill files here
  │   └── outputs/    ← Zipped files appear here
  └── datasheets/     ← Save PDFs here

mechanical/
  └── stl/            ← 3D print files here

firmware/             ← Your code here

docs/
  ├── decisions/      ← Why you chose X over Y
  ├── specs/          ← Requirements
  └── cost_tracking.md ← Budget tracking

orders/
  ├── quotes/         ← Save quote PDFs here
  └── tracking/       ← Order numbers, shipping info

testing/
  └── procedures/     ← Test checklists
```

## Common Workflows

### Workflow 1: Ready to Order PCBs

```bash
# 1. Export files from Altium/KiCad to manufacturing folders
# 2. Run preparation script
cd tools/scripts
./prepare_manufacturing.sh

# 3. Files are zipped in hardware/manufacturing/outputs/
# 4. Upload to JLCPCB/PCBWay
```

### Workflow 2: Track Costs

```bash
# Edit docs/cost_tracking.md
# Add quotes to orders/quotes/
# Update budget as you go
```

### Workflow 3: Version Bump

```bash
cd tools/scripts
./version_bump.sh patch  # Bug fix (1.0.0 → 1.0.1)
./version_bump.sh minor  # New feature (1.0.0 → 1.1.0)
./version_bump.sh major  # New PCB (1.0.0 → 2.0.0)
```

### Workflow 4: Backup Project

```bash
cd tools/scripts
./backup_project.sh
# Saves to ~/Projects/backups/
```

### Workflow 5: Check Before Manufacturing

```bash
cd tools/scripts
./check_files.sh
# Verifies all files present
```

## Git Commands Quick Reference

```bash
# Daily commits
git add .
git commit -m "Describe what changed"

# Tag a version
git tag -a v1.0.0 -m "First production version"

# View history
git log --oneline

# See what changed
git diff
```

## Manufacturing Checklist

Before ordering:

- [ ] Run `./check_files.sh` - all green?
- [ ] Gerbers exported (12-25 files expected)
- [ ] Drill files exported (.drl files)
- [ ] BOM as CSV with part numbers
- [ ] CPL (pick-and-place) exported
- [ ] STL files for enclosure (if needed)
- [ ] Run `./prepare_manufacturing.sh`
- [ ] Check component availability on LCSC
- [ ] Updated cost tracking
- [ ] Git commit + version tag

## Helper Scripts Reference

| Script | What it does |
|--------|-------------|
| `new_project.sh` | Create project from template |
| `prepare_manufacturing.sh` | Zip all files for upload |
| `backup_project.sh` | Backup entire project |
| `check_files.sh` | Verify all files present |
| `version_bump.sh` | Increment version numbers |

All scripts in: `tools/scripts/`

## Cost Tracking Quick Tips

| What | Where to track |
|------|---------------|
| Component prices | `docs/cost_tracking.md` |
| PCB quotes | `orders/quotes/` + cost_tracking.md |
| Budget status | cost_tracking.md |
| Vendor comparison | cost_tracking.md |

## Working with Claude Code

### Update .claude.md after:
- Choosing components
- Making design decisions
- Receiving quotes
- Testing boards
- Each work session

### Session log template:
```markdown
### 2026-01-03: [What you did today]
**What was done:**
1. Thing 1
2. Thing 2

**Decisions:**
- Chose X because Y

**Next:**
- [ ] Task 1
```

## Common Issues & Fixes

### "Script won't run"
```bash
chmod +x tools/scripts/*.sh
```

### "Missing drill files"
Export from CAD: File → Fabrication Outputs → NC Drill

### "BOM not CSV"
Export from CAD: Reports → BOM → Export CSV

### "Git tracking too much"
Check `.gitignore` includes your CAD backup files

## Upload to Manufacturer

### JLCPCB
1. Go to jlcpcb.com
2. Upload `gerbers_TIMESTAMP.zip`
3. Review specs (layers, thickness, color)
4. Add SMT Assembly (if needed)
5. Upload BOM.csv and CPL.csv
6. Review component availability
7. Get quote
8. Order

### PCBWay
Similar process, or upload Altium project directly

## Need Help?

1. Check `HOW_TO_USE_TEMPLATE.md` for detailed guide
2. Check `docs/` folder for templates
3. Ask Claude Code - it reads `.claude.md` for context

---

**Pro Tips:**

1. Update `.claude.md` constantly - it's your AI's memory
2. Use scripts - they prevent errors
3. Commit to git frequently
4. Document decisions in `docs/decisions/`
5. Track costs early to avoid surprises
6. Order 5-10 units first, not 100
7. Keep datasheets in `docs/datasheets/`

---

**Template Version:** 1.0
**Created with Claude Code**
