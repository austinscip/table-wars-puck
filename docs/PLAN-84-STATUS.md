# Plan 84 — live status tracker

Goal: drive **every** step in `~/Desktop/ESP32_Puck_RevB_Project/meeting_notes/
Next_Steps_Post_Caxy.md` to ✅. Each session updates this file as it closes items.

Status: ✅ done · 🟡 partial · 🔴 not started (codeable). Owner: 🤖 = I can close
it · 👤 = only the owner can (business / hardware / manual / pilot).

> Honest ceiling: the 👤 rows can't be made green from a keyboard. "All 84 green"
> = every 🤖 row ✅ + the owner working the 👤 checklist.

## Week 1 — Tools
1. GitHub Projects board — 🟡 👤
2. Supabase project — ✅
3. AI coding stack — ✅ (Claude Code)
4. Figma mockups — 🟡 🤖 *(design-QA + fill frames via the figma MCP)*

## A — Architecture
5. Supabase Postgres, multi-tenant — ✅
6. Bar portal (login, active games, ROI) — 🟡 🤖 *(build active-games + ROI)*
7. Super-admin observability app — 🟡 🤖 *(health+activity built; finish + verify in dev)*

## B — Google TV app
8. RN for Android TV — ✅
9. Port title/lobby/pair/scoreboard — ✅
10. Wire to Supabase — ✅
11. Test on Chromecast — 🔴 👤 (hardware)

## G — Multi-Game Runtime
12. Pairing — ✅ · 13. Scoring + leaderboards — 🟡 🤖 (leaderboard UI) · 14. Matchmaking + state machine — ✅ · 15. Real-time sync — ✅ · 16. Power-up framework — 🟡 🤖 (make cross-game shared) · 17. Ghost sweep/heartbeat — ✅ · 18. Plug-in API — ✅

## C — Shared polish
19. Host TTS voice — 🟡 🤖 · 20. Music beds — 🔴 🤖 · 21. SFX vocabulary — 🟡 🤖 · 22. Animated visual language — 🟡 🤖 · 23. Lottie — 🔴 🤖 · 24. Hardware cue language — ✅ · 25. Storybook — 🔴 🤖

## D — Firmware OTA + pluggable
26. ArduinoOTA/HTTPUpdate — ✅ (compile) · 27. Code signing — ✅ · 28. A/B partitions + auto-rollback — 🟡 🤖 (bootloader cfg) + 👤 (hw verify) · 29. Battery check before update — 🔴 🤖 · 30. Pluggable firmware (puck=sensor) — 🟡 🤖 · 31. Full loop e2e — 🔴 👤 (hardware)

## E — Customer self-serve
32. TV attract mode — ✅ · 33. Puck attract (idle/wake) — 🟡 🤖 · 34. First-time onboarding overlay — ✅ · 35. Strip Hub from prod — ✅ · 36. No-staff audit — 🔴 👤 (manual walk) · 37. Table tents — 🔴 🤖 (copy) + 👤 (print)

## F1 — Trivia rework
38. 50 quality Qs/season — 🔴 🤖 (bootstrap, owner curates) · 39. Themed round formats — 🔴 🤖 · 40. Per-category personalities — 🔴 🤖 · 41. Per-round host commentary — 🟡 🤖 · 42. Pacing — 🟡 🤖 · 43. Wired into runtime+polish — 🟡 🤖

## F2 — Puck Golf
44. Real physics (club/wind) — 🟡 🤖 · 45. Multiplayer turn-based — ✅ · 46. 9-hole course design — 🔴 🤖 · 47. Input mapping — ✅ · 48. Golf commentary — 🔴 🤖 · 49. Wired into runtime+polish — 🟡 🤖

## F3 — Puck Racer
50. Drag-race model — ✅ · 51. Position sync (predict/reconcile) — 🟡 🤖 · 52. 3 track designs — 🔴 🤖 · 53. Power-ups (banana/lightning) — 🟡 🤖 · 54. Input mapping — 🟡 🤖 · 55. Racing commentary — 🔴 🤖 · 56. Wired into runtime+polish — 🟡 🤖

## F4 — Smash
57. 4 chars/1 stage/movesets — 🟡 🤖 (distinct characters) · 58. 4-player simultaneous — ✅ · 59. Physics — ✅ · 60. Input mapping — ✅ · 61. Combat commentary — 🔴 🤖 · 62. Wired into runtime+polish — 🟡 🤖

## Observability
63. PostHog — ✅ (dormant plumbing) · 64. Sentry — ✅

## Soft launch (all hardware/manual)
65. Run 4 games on dev pucks — 🔴 👤 · 66. Test OTA mid-match — 🔴 👤 · 67. Cold self-serve + <30s pair — 🔴 👤 · 68. Attract 30-min test — 🔴 👤

## Legal / business (all owner)
69. LLC — 🔴 👤 · 70. Bank — 🔴 👤 · 71. Insurance — 🔴 👤 · 72. Pilot agreement + lawyer — 🔴 👤 · 73. Name/.com/logo — 🟡 👤 · 74. Sales 1-pager + demo video — 🔴 🤖 (1-pager) + 👤 (video)

## Pilot (all owner)
75. Google Play submit — 🔴 👤 · 76. Site survey — 🔴 👤 · 77. Pre-provision — 🔴 👤 · 78. Install kit delivered — 🔴 🤖 (copy) + 👤 (physical) · 79. Install + walkthrough — 🔴 👤

## Pilot iteration (post-pilot, owner)
80–84. Run / OTA fixes / daily bug fixes / OTA content / Mike update — 🔴 👤

---

## The 🤖 work queue (what a session drives to green, roughly in order)
1. **Figma design-QA** (#4) — pull `table_wars`, every built screen vs its frame → align code; fill thin frames (write access).
2. **Portal + super-admin** (#6, #7) — active-games/ROI + finish super-admin.
3. **Install-kit + sales copy** (#37, #74, #78) — cheat sheet, table tents, 1-pager, written into the Figma Install-kit page.
4. **Firmware completeness** (#29 battery check, #28 rollback cfg, #30 pluggable).
5. **Polish track C** (#19–25) — music beds, SFX, Storybook, Lottie.
6. **Content + game design** (#38–62) — bootstrap balanced trivia, golf courses, racer tracks, smash characters, per-game host commentary. Owner curates voice.
7. **Runtime niceties** (#13 leaderboard UI, #16 shared power-ups).

## The 👤 checklist (only the owner can green these)
GitHub Projects board · Chromecast/hardware tests (#11,31,65–68) · LLC/bank/
insurance/agreement/name+logo (#69–73) · demo video (#74) · Google Play +
site survey + provision + physical install kit + install (#75–79) · run the
pilot (#80–84).
