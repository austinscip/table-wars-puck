Test the ESP32 firmware compilation and upload process.

Steps:
1. Check if PlatformIO is installed
2. Navigate to project root
3. Run `pio run` to compile
4. If compilation succeeds, check for connected ESP32 via `pio device list`
5. If device found, offer to upload with `pio run --target upload`
6. If upload succeeds, offer to monitor serial output with `pio device monitor`

Report any errors clearly and suggest fixes.
