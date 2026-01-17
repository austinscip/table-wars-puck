# Hardware Project Template - Quick Start Guide

This template provides a complete structure for hardware projects with manufacturing, version control, and AI-assisted development.

## Creating a New Project

### Method 1: Using the Script (Recommended)

```bash
cd ~/Projects/.hardware_project_template/tools/scripts
./new_project.sh
```

The script will:
- Ask for project name
- Create project in ~/Projects/ (or custom location)
- Initialize git repository
- Customize template files with your project details
- Create initial commit

### Method 2: Manual Copy

```bash
cp -r ~/Projects/.hardware_project_template ~/Projects/YourProjectName
cd ~/Projects/YourProjectName
rm -rf tools/scripts/new_project.sh HOW_TO_USE_TEMPLATE.md
git init
git add .
git commit -m "Initial commit"
```

## Project Structure

```
YourProject/
├── .claude.md              ← AI context (update as you work!)
├── README.md               ← Project documentation
├── CHANGELOG.md            ← Version history
├── hardware/
│   ├── altium/            ← Altium Designer files
│   ├── kicad/             ← KiCad files (if using)
│   ├── eagle/             ← Eagle files (if using)
│   ├── manufacturing/     ← Manufacturing outputs
│   │   ├── gerbers/       ← Gerber files
│   │   ├── bom/           ← Bill of Materials (CSV)
│   │   ├── cpl/           ← Pick-and-place files
│   │   ├── drill/         ← Drill files
│   │   ├── outputs/       ← Packaged files for upload
│   │   └── revisions/     ← Previous versions
│   └── datasheets/        ← Component datasheets
├── mechanical/
│   ├── stl/               ← 3D print files
│   ├── step/              ← STEP files for assembly
│   └── cad/               ← Fusion 360/SolidWorks source
├── firmware/              ← Embedded software
├── docs/                  ← Documentation
│   ├── specs/             ← Technical specifications
│   ├── decisions/         ← Design decision logs
│   └── datasheets/        ← Component datasheets
├── orders/                ← Manufacturing orders
│   ├── quotes/            ← Price quotes
│   └── tracking/          ← Order tracking info
├── testing/               ← Test procedures & results
└── tools/                 ← Helper scripts
```

## Essential Files to Update

### 1. .claude.md (MOST IMPORTANT)
Update this file as you work. It maintains AI context across sessions.

**When to update:**
- After making component selections
- After design decisions
- After receiving quotes
- After testing
- End of each work session

### 2. README.md
Update with:
- Project description
- Component specifications
- Build instructions
- Cost estimates

### 3. CHANGELOG.md
Document all changes:
- Hardware revisions
- Firmware updates
- Bug fixes
- Design decisions

## Workflow

### Phase 1: Design
```bash
# Work in your CAD tool (Altium/KiCad/etc)
# Update .claude.md with component choices
# Document decisions in docs/decisions/
```

### Phase 2: Manufacturing Preparation
```bash
# Generate Gerbers, drill files, BOM, CPL from CAD
# Copy to manufacturing/ folders
# Run preparation script:
cd tools/scripts
./prepare_manufacturing.sh

# This creates:
# - gerbers_TIMESTAMP.zip
# - drill_TIMESTAMP.zip
# - BOM_TIMESTAMP.csv
# - CPL_TIMESTAMP.csv
# - MANUFACTURING_PACKAGE_TIMESTAMP.zip
```

### Phase 3: Ordering
```bash
# Upload files from hardware/manufacturing/outputs/
# Save quotes to orders/quotes/
# Update cost tracking in docs/cost_tracking.md
```

### Phase 4: Testing
```bash
# Document results in testing/
# Update CHANGELOG.md with issues found
# Create new version if needed
```

## Helper Scripts

All scripts in `tools/scripts/`:

### prepare_manufacturing.sh
Packages all manufacturing files for upload to PCB manufacturer.

**Usage:**
```bash
./prepare_manufacturing.sh
```

**Output:**
- Creates timestamped ZIPs in `hardware/manufacturing/outputs/`
- Includes README with upload instructions

### backup_project.sh
Creates timestamped backup of entire project.

**Usage:**
```bash
./backup_project.sh
```

### check_files.sh
Verifies all required manufacturing files are present.

**Usage:**
```bash
./check_files.sh
```

### version_bump.sh
Increments version numbers across project files.

**Usage:**
```bash
./version_bump.sh patch  # 1.0.0 → 1.0.1
./version_bump.sh minor  # 1.0.0 → 1.1.0
./version_bump.sh major  # 1.0.0 → 2.0.0
```

## Git Workflow

### Initial Setup
```bash
git init
git add .
git commit -m "Initial commit: ProjectName"
```

### Making Changes
```bash
# Make changes
git add .
git commit -m "Add feature X

- Added new sensor circuit
- Updated BOM with new parts

🤖 Generated with Claude Code
Co-Authored-By: Your Name <your@email.com>"
```

### Version Tags
```bash
# After completing a version
git tag -a v1.0.0 -m "Version 1.0.0 - Initial production release"
git push origin v1.0.0
```

## Working with Claude Code

### Start Each Session
Claude Code reads `.claude.md` automatically for context.

**Good practice:**
- Update `.claude.md` session log after each work session
- Document component costs and part numbers
- Note design decisions with reasoning

### Session Log Format
```markdown
### YYYY-MM-DD: [Session Title]
**What was done:**
1. Thing 1
2. Thing 2

**Decisions made:**
- Chose X over Y because Z

**Next steps:**
- [ ] Task 1
- [ ] Task 2
```

## Cost Tracking

Use `docs/cost_tracking.md` to track:
- Component costs
- PCB manufacturing quotes
- Assembly costs
- 3D printing costs
- Shipping estimates

**Update after:**
- Getting quotes
- Placing orders
- Receiving invoices

## Manufacturing Upload Checklist

Before ordering PCBs:

- [ ] Gerber files generated and verified
- [ ] Drill files included
- [ ] BOM exported as CSV with part numbers
- [ ] CPL (pick-and-place) file generated
- [ ] Ran `prepare_manufacturing.sh`
- [ ] Verified all files in `outputs/` folder
- [ ] Checked component availability on JLCPCB/LCSC
- [ ] Updated cost estimate
- [ ] Committed to git with version tag

## Tips

1. **Update .claude.md frequently** - It's your AI's memory
2. **Use scripts** - They prevent mistakes
3. **Version everything** - Tag each PCB revision in git
4. **Document decisions** - Future you will thank you
5. **Track costs early** - Prevents budget surprises
6. **Keep datasheets** - Store PDFs in docs/datasheets/
7. **Test before ordering bulk** - Order 5-10 units first

## Common Issues

### "Missing drill files"
- Export from CAD tool: File → Fabrication Outputs → NC Drill Files
- Copy to `hardware/manufacturing/drill/`

### "BOM not in CSV format"
- Export from CAD tool: Reports → Bill of Materials → Export CSV
- Include columns: Designator, Comment, Footprint, Quantity, Manufacturer Part

### "Can't run scripts"
```bash
chmod +x tools/scripts/*.sh
```

### "Git tracking too many files"
- Check `.gitignore` includes your CAD tool backup files
- Large binaries should be in `.gitignore`

## Getting Help

- Check `.claude.md` for project-specific context
- Review `docs/` folder for design decisions
- Ask Claude Code - it has full project context from `.claude.md`

---

**Template created with Claude Code**
**Version:** 1.0
**Last updated:** 2026-01-03
