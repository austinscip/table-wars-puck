You are adding a new game mode to Table Wars.

IMPORTANT ARCHITECTURE:
- The PUCK is a CONTROLLER (motion input, button presses)
- The TV/DISPLAY shows the actual game graphics and animations
- The puck only provides: shake detection, tilt sensing, button input, LED feedback (simple colors/patterns), buzzer sounds

Steps to add a new game:

1. Add game ID and name to the game list in `src/Config.h`
2. Create game controller logic in a new header file `src/game_[name].h`
   - Handle puck input (motion, buttons)
   - Send input data to server via WiFi
   - Provide LED/buzzer feedback for puck holder
3. Update `src/main_ble_wifi_test.h` to include the new game case
4. Update server `server/app.py` to handle the new game type and render TV graphics
5. Test compilation with PlatformIO
6. Document the game mechanics in README

The user will provide the game name and concept. You implement it following the CONTROLLER architecture (not trying to show complex graphics on LED ring).
