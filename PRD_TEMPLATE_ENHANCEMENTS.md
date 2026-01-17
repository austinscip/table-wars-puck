# PRD Template Enhancements
## Based on Grok & ChatGPT Feedback Analysis

**Date:** January 17, 2026
**Purpose:** Document recommended improvements to PRD structure for future sprints based on AI feedback

---

## Executive Summary

Both Grok and ChatGPT reviewed the Sprint 0 PRD and validated the structure as **"A- (agent-ready, production-credible)"**. However, they identified several enhancements to improve autonomous agent execution (Ralph/Amp) and production reliability.

**Key Finding:** The current PRD is excellent for Sprint 0 (78% complete), but future sprints should incorporate:
1. **Loop control metadata** (from ChatGPT)
2. **Sentinel validation stories** (from ChatGPT)
3. **Hardware flags** (from ChatGPT)
4. **Risk assessment** (from Grok)
5. **Verification steps** (from Grok)

---

## Current PRD Structure (Sprint 0)

### What's Working Well ✅

```json
{
  "id": "US-001a-1",
  "title": "Add MPU6050 lib to platformio.ini",
  "description": "Add Adafruit MPU6050 library dependency",
  "sprint": "0A",
  "diff": "[env:esp32dev]\\n+ lib_deps = adafruit/Adafruit MPU6050@^2.2.0",
  "file": "platformio.ini",
  "acceptanceCriteria": [
    "pio pkg install succeeds",
    "pio run builds without error"
  ],
  "priority": 1,
  "effort": "5 min",
  "dependency": null,
  "passes": true,
  "notes": "Already present + NeoPixel added to fix build"
}
```

**Strengths:**
- ✅ Atomic granularity (5-20 min stories)
- ✅ Exact diffs for code changes
- ✅ Binary acceptance criteria
- ✅ Linear dependencies (no DAGs)
- ✅ Test commands included
- ✅ File targets specified

**Validation:** Both AIs rated this structure 9/10 for agent execution.

---

## Recommended Enhancements (Sprint 1+)

### 1. Loop Control Metadata (ChatGPT Recommendation) 🔴 **CRITICAL**

**Why:** Prevents agents from "fixing" failures and continuing silently.

**Add to Each Story:**
```json
{
  "on_success": "advance",
  "on_failure": "halt",
  "retry_policy": "none"
}
```

**Options:**
- `on_success`: `"advance"` | `"pause"` | `"branch"`
- `on_failure`: `"halt"` | `"rollback"` | `"notify"`
- `retry_policy`: `"none"` | `"once"` | `"max_3"`

**Example Use Case:**
```json
{
  "id": "US-005-HW-1",
  "title": "Flash firmware to physical ESP32",
  "on_success": "advance",
  "on_failure": "halt",
  "retry_policy": "once",
  "notes": "Halt if flash fails - don't attempt sensor tests with bad firmware"
}
```

**Impact:** Prevents compounding errors in hardware testing.

---

### 2. Sentinel Stories (ChatGPT Recommendation) 🟡 **HIGH PRIORITY**

**Why:** Catches drift and validates assumptions before moving forward.

**Add Every ~10 Stories:**
```json
{
  "id": "SENTINEL-0A-1",
  "title": "Validate MPU6050 pipeline assumptions",
  "diff": "NO CODE CHANGE",
  "file": "N/A",
  "acceptanceCriteria": [
    "shake_intensity ~9.8 m/s² when stationary (gravity)",
    "tilt_x stable within ±2 degrees when level",
    "gyro_z reads <0.1 rad/s when not spinning"
  ],
  "test_command": "pio device monitor",
  "priority": 20,
  "effort": "10 min",
  "dependency": "US-001d-2",
  "on_success": "advance",
  "on_failure": "halt"
}
```

**Purpose:**
- Stop progress if fundamental assumptions broken
- Prevent "silent success" (builds fine but sensor drift)
- Force human review of calculated values

**Recommended Sentinels for Sprint 0:**
1. **SENTINEL-0A-1:** After sensor initialization (gravity check)
2. **SENTINEL-0B-1:** After message struct extension (size check)
3. **SENTINEL-0C-1:** After server integration (latency check)

---

### 3. Hardware Flags (ChatGPT Recommendation) 🟡 **HIGH PRIORITY**

**Why:** Enables simulator routing and CI skip logic.

**Add to Stories:**
```json
{
  "requires_hardware": true,
  "hardware": ["ESP32", "MPU6050"],
  "simulator_alternative": "Use test_puck_simulator.html"
}
```

**Example:**
```json
{
  "id": "US-001b-6",
  "title": "Add mpu.begin() initialization check",
  "requires_hardware": true,
  "hardware": ["ESP32", "MPU6050"],
  "simulator_alternative": "Skip in simulator mode",
  "on_failure": "halt"
}
```

**Benefits:**
- CI can skip hardware-dependent tests
- Ralph knows when to defer to simulator
- Clear separation of simulator vs hardware stories

---

### 4. Risk Assessment (Grok Recommendation) 🟢 **NICE TO HAVE**

**Why:** Helps prioritize debugging and human oversight.

**Add to Stories:**
```json
{
  "risk": "medium (hardware-dependent)",
  "risk_factors": ["I2C bus instability", "MPU6050 chip variation"]
}
```

**Risk Levels:**
- `"low"`: Pure software, no external dependencies
- `"medium"`: Hardware involved, predictable behavior
- `"high"`: Complex integration, network/timing sensitive

**Example High-Risk Story:**
```json
{
  "id": "US-002c-3",
  "title": "Add rate-limit check before broadcast",
  "risk": "high (timing-sensitive, ESP-NOW unreliable)",
  "risk_factors": [
    "ESP-NOW packet drops common",
    "millis() overflow edge case",
    "Rate limit may be too aggressive for fast spins"
  ]
}
```

---

### 5. Verification Steps (Grok Recommendation) 🟢 **NICE TO HAVE**

**Why:** Explicit manual checks complement automated tests.

**Add to Stories:**
```json
{
  "verification_steps": [
    "Hold puck stationary → shake_intensity reads 9.8 ± 0.5",
    "Tilt puck 45° left → tilt_x reads -45 ± 5",
    "Spin puck clockwise → gyro_z > 0"
  ]
}
```

**When to Use:**
- Hardware validation (sensor ranges)
- Visual checks (LED behavior, display updates)
- Timing-sensitive operations (latency, rate limits)

**Example:**
```json
{
  "id": "US-003c-2",
  "title": "TV Display: Update gyro_z value on WebSocket event",
  "verification_steps": [
    "Open browser at http://localhost:5001/test/puck-simulator",
    "Click 'Medium Spin (200)' button",
    "Verify debug panel shows gyro_z ≈ 200 within 100ms",
    "Observe smooth value transitions (no jitter)"
  ]
}
```

---

### 6. Numeric Time Estimates (Grok Recommendation) 🟢 **NICE TO HAVE**

**Why:** Enables sprint capacity planning and burndown charts.

**Add to Stories:**
```json
{
  "effort": "10 min",
  "estimated_time_minutes": 10
}
```

**Current:**
```json
"effort": "5 min"  // Human-readable string
```

**Enhanced:**
```json
"effort": "5 min",
"estimated_time_minutes": 5  // Machine-readable for summation
```

**Benefit:** Can sum total sprint effort programmatically.

---

## Enhanced PRD Template (Sprint 1+)

### Full Example Story

```json
{
  "id": "US-XXX-X",
  "title": "Story title (imperative form)",
  "description": "What this accomplishes and why it matters",
  "sprint": "1A",
  "diff": "exact code change with context",
  "file": "path/to/file.cpp",
  "acceptanceCriteria": [
    "Binary pass/fail check 1",
    "Binary pass/fail check 2"
  ],
  "verification_steps": [
    "Manual check 1 (e.g., visual inspection)",
    "Manual check 2 (e.g., physical test)"
  ],
  "test_command": "pio run && pio device monitor",
  "priority": 1,
  "effort": "10 min",
  "estimated_time_minutes": 10,
  "dependency": ["US-XXX-Y"],
  "risk": "medium (hardware-dependent)",
  "risk_factors": ["Sensor calibration variance", "I2C timing"],
  "on_success": "advance",
  "on_failure": "halt",
  "retry_policy": "none",
  "requires_hardware": true,
  "hardware": ["ESP32", "MPU6050"],
  "simulator_alternative": "Use test_puck_simulator.html",
  "passes": false,
  "tested_on": null,
  "notes": "",
  "human_notes": {
    "passes": true,
    "tested_on": "2026-01-17",
    "notes": "Sensor reads 9.7 m/s² (within tolerance)"
  }
}
```

### Sentinel Story Example

```json
{
  "id": "SENTINEL-1A-1",
  "title": "Validate wheel physics assumptions",
  "description": "NO CODE CHANGE - Validation checkpoint for spin calculations",
  "sprint": "1A",
  "diff": "NO CODE CHANGE",
  "file": "N/A",
  "acceptanceCriteria": [
    "Friction coefficient results in 3-5 second spin-down time",
    "Wheel stops within ±5° of calculated position",
    "No oscillation or jitter during spin-down"
  ],
  "verification_steps": [
    "Spin wheel with gyro_z = 300 deg/s",
    "Measure time to full stop (should be 3-5 seconds)",
    "Verify final position matches physics calculation",
    "Check for smooth deceleration curve (no jumps)"
  ],
  "test_command": "manual verification",
  "priority": 25,
  "effort": "15 min",
  "estimated_time_minutes": 15,
  "dependency": ["US-1A-8"],
  "risk": "high (physics model may be wrong)",
  "on_success": "advance",
  "on_failure": "halt",
  "retry_policy": "none",
  "requires_hardware": false,
  "simulator_alternative": "Test with simulator",
  "passes": false
}
```

---

## What NOT to Add (Keep It Lean)

### ❌ Epic Grouping (Grok Suggested)
**Why Skip:** File-based organization is clearer.

```json
// DON'T ADD THIS
"epic": "EPIC-001: Sensor Integration"
```

**Alternative:** Group by `sprint` field and `file` field naturally.

### ❌ Story Splitting for Front-Testing (Grok Suggested)
**Why Skip:** Only split if calculation and validation can fail independently.

**Bad Example:**
```json
// US-001c-3a: Compute shake_intensity
// US-001c-3b: Add Serial.print for shake_intensity
```

**Why Bad:** These are coupled - if calculation is wrong, print is meaningless.

**Good Example:**
```json
// US-005-1: Implement wheel friction physics
// SENTINEL-5-1: Validate friction results in 3-5s spin-down
```

**Why Good:** Physics can be wrong even if code compiles. Sentinel catches this.

---

## Bar Stability Enhancements (ChatGPT Recommendation)

### Sprint 0.5: Bar Deployment Readiness

**User Stories to Add:**

```json
{
  "id": "US-005-1",
  "title": "Add 'Last Update' timestamp to debug panel",
  "description": "Display seconds since last puck data received",
  "acceptanceCriteria": [
    "Debug panel shows 'Last update: X seconds ago'",
    "Value updates every second",
    "Red indicator if >5 seconds no data"
  ],
  "on_success": "advance",
  "on_failure": "halt"
},
{
  "id": "US-005-2",
  "title": "Track packet drop count in server",
  "description": "Log WebSocket disconnections and missed heartbeats",
  "acceptanceCriteria": [
    "Server logs packet drop events with timestamp",
    "Debug panel displays total drops since session start",
    "API endpoint returns drop count"
  ]
},
{
  "id": "US-005-3",
  "title": "Add visual staleness indicator",
  "description": "Red/yellow/green status for connection health",
  "acceptanceCriteria": [
    "Green: <1s since last update",
    "Yellow: 1-5s since last update",
    "Red: >5s since last update",
    "Indicator visible on TV display"
  ]
}
```

**Why This Matters:**
- Bars have WiFi interference (lots of patrons)
- Staff unplug things without warning
- Need to know when pucks go offline
- Prevents "it's broken" complaints from unclear status

---

## Migration Guide

### For Sprint 1 (Shot Roulette Royale)

1. **Start Fresh PRD File**
   ```bash
   cp prd.json prd-sprint-0.json  # Archive Sprint 0
   # Create prd-sprint-1.json with enhanced template
   ```

2. **Add Loop Control to All Stories**
   - Most stories: `"on_failure": "halt"`
   - Visual stories: `"on_failure": "notify"`
   - Physics calculations: `"on_failure": "halt"`

3. **Add Sentinels Every ~10 Stories**
   - After wheel rendering: Validate FPS >30
   - After physics: Validate spin-down time
   - After prize logic: Validate zone detection

4. **Flag Hardware vs Simulator**
   - All wheel rendering: `"requires_hardware": false`
   - Gyro integration: `"requires_hardware": true`
   - Server logic: `"requires_hardware": false`

5. **Risk Assessment**
   - Physics calculations: `"risk": "high"`
   - WebSocket events: `"risk": "medium"`
   - UI rendering: `"risk": "low"`

### For Ralph Agent Integration

**Ralph Executor Script:**
```python
# ralph_executor.py
def execute_story(story):
    if story.get('requires_hardware') and not hardware_available():
        print(f"Skipping {story['id']} - hardware not available")
        return 'skip'

    apply_diff(story['diff'], story['file'])
    result = run_test(story['test_command'])

    if result.success:
        if story.get('on_success') == 'advance':
            mark_complete(story['id'])
            return 'continue'
    else:
        if story.get('on_failure') == 'halt':
            print(f"HALTING at {story['id']} - failure detected")
            return 'halt'

    return 'error'
```

---

## Validation Checklist

Before finalizing a new sprint PRD, validate:

- [ ] All stories have `on_success` / `on_failure`
- [ ] Sentinel stories added every ~10 user stories
- [ ] Hardware flags set for physical tests
- [ ] Risk levels assigned to non-obvious stories
- [ ] `estimated_time_minutes` matches `effort` string
- [ ] Dependencies form linear chain (no DAGs)
- [ ] Acceptance criteria are binary (pass/fail)
- [ ] Test commands are exact (not "run tests")
- [ ] File paths are absolute or clear relative paths
- [ ] No epic grouping (use sprint + file organization)

---

## Tools Needed (Future Work)

1. **PRD Validator Script**
   ```bash
   python validate_prd.py prd-sprint-1.json
   # Checks: schema, dependencies, required fields
   ```

2. **Ralph Executor**
   ```bash
   python ralph_executor.py --story US-1A-1
   # Applies diff, runs test, handles failure
   ```

3. **Sentinel Generator**
   ```bash
   python generate_sentinels.py prd-sprint-1.json
   # Auto-suggests sentinel stories every 10 user stories
   ```

4. **GitHub Actions Workflow**
   ```yaml
   # .github/workflows/prd-validation.yml
   - name: Validate PRD JSON
     run: python validate_prd.py tasks/prd-*.json
   ```

---

## Summary of Changes

### Must Have (Sprint 1)
1. ✅ Loop control metadata (`on_success`, `on_failure`, `retry_policy`)
2. ✅ Sentinel stories (1 per epic or every ~10 stories)
3. ✅ Hardware flags (`requires_hardware`, `hardware`, `simulator_alternative`)

### Should Have (Sprint 1)
4. ✅ Risk assessment (`risk`, `risk_factors`)
5. ✅ Verification steps (manual checks)
6. ✅ Numeric time estimates (`estimated_time_minutes`)

### Skip
7. ❌ Epic grouping (use file/sprint organization)
8. ❌ Over-splitting stories (only if independently testable)

---

## Next Actions

1. **Create `prd-schema.json`** - JSON schema for validation
2. **Write `validate_prd.py`** - Automated schema + dependency checker
3. **Update Sprint 1 PRD** - Apply enhancements to Shot Roulette Royale
4. **Test Ralph executor** - Validate loop control with sample stories
5. **Add Sprint 0.5 stories** - Bar stability monitoring

**Estimated Setup Time:** 2-3 hours to create validation tooling

---

## Questions?

See also:
- `SPRINT_0_COMPLETE.md` - Current state and metrics
- `prd.json` - Sprint 0 baseline PRD
- `progress.txt` - Daily updates and learnings

**Status:** 📋 TEMPLATE READY | 🔄 APPLY TO SPRINT 1 | ⏳ TOOLING PENDING
