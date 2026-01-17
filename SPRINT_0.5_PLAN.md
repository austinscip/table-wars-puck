# Sprint 0.5: Bar Stability - Implementation Plan

**Created:** January 17, 2026
**Status:** Ready to start
**Estimated Time:** 2.9 hours (175 minutes)

---

## Goal

Build production-ready connection health monitoring for bar deployment. Solve real-world problems:
- 🛜 **WiFi interference** from 100+ patron phones
- 🔌 **Unplugged devices** (staff cleaning without warning)
- ⏱️ **Staleness detection** (know when pucks go offline)
- 📊 **Packet drop tracking** (diagnose network issues)

---

## What You'll Build

### 1. Visual Connection Health Indicator
- **Green** (<1s): "Connected" - Everything working
- **Yellow** (1-5s): "Stale" - Data delayed but recovering
- **Red** (>5s): "Disconnected" - Puck offline

### 2. "Last Update" Timer
- Shows "Last update: 3s ago"
- Updates every second
- Helps staff diagnose issues

### 3. Packet Statistics Dashboard
- Total packets received
- Dropped packets count
- Drop rate percentage
- Visual warning when >10% drop rate

### 4. Health API Endpoint
- `GET /api/health` returns JSON
- Status, stats, timestamps
- For external monitoring/debugging

### 5. TV Display Integration
- Health overlay in top-right corner
- Visible during all 10 games
- Doesn't obstruct gameplay

---

## User Stories Breakdown

### Epic 1: Connection Staleness Detection (Stories 1-7 + Sentinel)
**Time:** 60 minutes

| ID | Description | Time |
|----|-------------|------|
| US-0.5-1 | Add timestamp to sensor events | 10 min |
| US-0.5-2 | Track last update in JavaScript | 5 min |
| US-0.5-3 | Add "Last Update" display element | 5 min |
| US-0.5-4 | Update timer every second | 10 min |
| US-0.5-5 | Add status indicator element | 5 min |
| US-0.5-6 | Add CSS for red/yellow/green | 5 min |
| US-0.5-7 | Update status based on staleness | 15 min |
| **SENTINEL-0.5-1** | **Validate timing accuracy** | **10 min** |

**Deliverable:** Working connection status indicator (green/yellow/red) that updates in real-time.

---

### Epic 2: Packet Statistics (Stories 8-12 + Sentinel)
**Time:** 55 minutes

| ID | Description | Time |
|----|-------------|------|
| US-0.5-8 | Add packet counter to server | 10 min |
| US-0.5-9 | Create /api/health endpoint | 15 min |
| US-0.5-10 | Add stats display to debug panel | 5 min |
| US-0.5-11 | Poll health API every 2 seconds | 10 min |
| **SENTINEL-0.5-2** | **Validate packet counting** | **10 min** |
| US-0.5-12 | Add warning for high drop rate | 5 min |
| US-0.5-13 | Add CSS for warning animation | 5 min |

**Deliverable:** Real-time packet statistics with visual warnings for network issues.

---

### Epic 3: TV Display Integration (Stories 14-15 + Sentinel)
**Time:** 35 minutes

| ID | Description | Time |
|----|-------------|------|
| US-0.5-14 | Copy health to TV template | 10 min |
| US-0.5-15 | Style overlay for TV display | 5 min |
| **SENTINEL-0.5-3** | **Validate no game regressions** | **20 min** |

**Deliverable:** Health indicators visible on all 10 games without breaking gameplay.

---

## Implementation Order

### Phase 1: Foundation (30 min)
```bash
# Stories 1-4: Basic timer functionality
1. Add timestamps to events
2. Track last update time
3. Display "Last update: Xs ago"
4. Update every second
```

**Test:** Open debug panel, send data from simulator, watch counter increment.

### Phase 2: Visual Indicators (25 min)
```bash
# Stories 5-7: Color-coded status
5. Add status indicator HTML
6. Add red/yellow/green CSS
7. Update color based on staleness
```

**Test:** Watch status change: green → yellow → red over 6 seconds.

### Phase 3: Validation Checkpoint (10 min)
```bash
# Sentinel-0.5-1: Verify timing
- Status green within 1s of data
- Status yellow at 1-5s
- Status red after 5s
```

**HALT if timing is wrong!**

### Phase 4: Packet Tracking (40 min)
```bash
# Stories 8-11: Server-side stats
8. Add packet counter to server
9. Create /api/health endpoint
10. Display stats in UI
11. Poll API every 2 seconds
```

**Test:** Send 10 inputs, refresh browser, verify counts.

### Phase 5: Validation Checkpoint (10 min)
```bash
# Sentinel-0.5-2: Verify math
- Send 20 inputs, verify total=20
- Refresh 2x, verify dropped=2
- Check drop rate = 6.7%
```

**HALT if math is wrong!**

### Phase 6: Warnings & Alerts (10 min)
```bash
# Stories 12-13: Visual warnings
12. Add warning for drop rate >10%
13. Add pulsing red CSS animation
```

**Test:** Simulate high drops, verify warning appears.

### Phase 7: TV Integration (15 min)
```bash
# Stories 14-15: Production deployment
14. Add health overlay to TV template
15. Style overlay (top-right corner)
```

**Test:** Open TV game, verify overlay doesn't obstruct gameplay.

### Phase 8: Final Validation (20 min)
```bash
# Sentinel-0.5-3: Regression testing
- Open all 10 games
- Verify health overlay works
- Check no performance issues
- Verify no visual obstruction
```

**HALT if any game breaks!**

---

## Success Criteria

### Must Have ✅
- [  ] Green/yellow/red status indicator working
- [  ] "Last update: Xs ago" timer accurate
- [  ] Packet statistics tracking correctly
- [  ] /api/health endpoint functional
- [  ] TV display overlay positioned correctly
- [  ] All 3 sentinel checkpoints passed
- [  ] No regressions in existing games

### Nice to Have 🎯
- [  ] Warning animation smooth and non-distracting
- [  ] Overlay responsive to window resize
- [  ] API response time <50ms
- [  ] Drop rate calculation accurate to 0.1%

---

## Testing Strategy

### Unit Testing (Per Story)
Each story has:
- **Acceptance Criteria:** Binary pass/fail checks
- **Verification Steps:** Manual validation procedure
- **Test Command:** How to verify it works

### Integration Testing (Sentinels)
3 critical checkpoints:
1. **Timing accuracy** (after status indicators)
2. **Math validation** (after packet tracking)
3. **Regression testing** (after TV integration)

**HALT execution if any sentinel fails!**

### E2E Testing (After Sprint)
Create new Playwright test:
```javascript
test('connection health indicator updates correctly', async ({ page }) => {
  await page.goto('/test/puck-simulator');

  // Send data, verify green
  await page.click('#send-input-btn');
  await expect(page.locator('#status-text')).toHaveText('Connected');

  // Wait 2s, verify yellow
  await page.waitForTimeout(2000);
  await expect(page.locator('#status-text')).toHaveText('Stale');

  // Wait 4s more, verify red
  await page.waitForTimeout(4000);
  await expect(page.locator('#status-text')).toHaveText('Disconnected');
});
```

---

## Risk Mitigation

### Medium Risks
1. **Timing Logic** (US-0.5-7, US-0.5-4)
   - **Risk:** setInterval may drift over time
   - **Mitigation:** Use Date.now() for absolute timing
   - **Validation:** SENTINEL-0.5-1 catches drift

2. **Math Accuracy** (US-0.5-11)
   - **Risk:** Drop rate calculation edge cases (divide by zero)
   - **Mitigation:** Check total > 0 before dividing
   - **Validation:** SENTINEL-0.5-2 tests edge cases

3. **Game Regression** (US-0.5-14, US-0.5-15)
   - **Risk:** Overlay breaks existing games
   - **Mitigation:** Test all 10 games manually
   - **Validation:** SENTINEL-0.5-3 full regression suite

### Low Risks
- HTML/CSS changes (stories 3, 5, 6, 10, 13, 15)
- Server-side counters (story 8)
- REST endpoint (story 9)

---

## Files to Modify

### Server
1. **server/app.py**
   - Add `packet_stats` dict
   - Add `@app.route('/api/health')`
   - Update `@socketio.on('puck_input')`
   - Update `@socketio.on('disconnect')`
   - Add `timestamp` to `sensor_data_update` event

### Templates
2. **server/templates/tv_games/_debug_panel.html**
   - Add connection health HTML structure
   - Add status indicator (green/yellow/red)
   - Add "Last update" timer
   - Add packet stats display
   - Add JavaScript for polling and updates
   - Add CSS for styling

3. **server/templates/tv_games/tv_game_base.html** (or main TV template)
   - Copy health overlay from debug panel
   - Add TV-specific positioning CSS
   - Ensure z-index above game elements

---

## Tools & Commands

### Development
```bash
# Start server (auto-reload on changes)
cd server
./venv/bin/python3 app.py

# Open simulator
open http://localhost:5001/test/puck-simulator

# Test API endpoint
curl http://localhost:5001/api/health | json_pp
```

### Testing
```bash
# Manual testing in browser
# 1. Open dev console
# 2. Send sensor data
# 3. Watch status change
# 4. Check timing with stopwatch

# API testing with curl
curl -s http://localhost:5001/api/health | \
  jq '{status, total_packets, dropped_packets, seconds_since_last}'
```

### Verification
```bash
# After each story:
1. Check acceptance criteria (binary checks)
2. Follow verification steps (manual procedure)
3. Run test command (automated or manual)
4. Mark story as complete if all pass

# After each sentinel:
1. HALT if any check fails
2. Debug before proceeding
3. Only continue when all checks pass
```

---

## Progress Tracking

Update `progress.txt` after each epic:

```
## 2026-01-17 - Sprint 0.5 Bar Stability

### Epic 1 Complete (1:30 PM)
- ✅ Connection staleness detection working
- ✅ Green/yellow/red status indicator
- ✅ "Last update" timer accurate
- ✅ SENTINEL-0.5-1 passed (timing validated)

### Epic 2 Complete (2:20 PM)
- ✅ Packet statistics tracking
- ✅ /api/health endpoint live
- ✅ Real-time stats display
- ✅ SENTINEL-0.5-2 passed (math validated)

### Epic 3 Complete (3:00 PM)
- ✅ TV display overlay integrated
- ✅ All 10 games still working
- ✅ SENTINEL-0.5-3 passed (no regressions)
```

---

## Next Steps After Sprint 0.5

### Option 1: Hardware Testing (When Pucks Arrive)
- Sprint 0-HW: Physical validation (2-3 hours)
- Test real-world latency with hardware
- Validate WiFi interference handling

### Option 2: First Game Development
- Sprint 1: Shot Roulette Royale (8-12 hours)
- Wheel rendering and spin physics
- Prize zone detection
- Multiplayer turn management

### Option 3: Enhanced Monitoring
- Add email/SMS alerts for disconnections
- Historical drop rate graphs
- Per-puck health tracking
- Admin dashboard for bar staff

---

## Questions Before Starting?

- Need clarification on any story?
- Want to adjust the timeline?
- Should we start implementing now?

**Ready to start coding?** Let me know and I'll begin with US-0.5-1! 🚀
