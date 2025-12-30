#!/usr/bin/env python3
"""
Simple ESP32 Serial Monitor
Reads and displays serial output from ESP32
"""

import serial
import sys
import time

SERIAL_PORT = '/dev/cu.usbserial-0001'
BAUD_RATE = 115200

def monitor_serial(duration=30):
    """Monitor serial port for specified duration in seconds"""
    try:
        print(f"🔌 Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(0.5)  # Wait for serial connection to establish

        print(f"✅ Connected! Monitoring for {duration} seconds...")
        print("=" * 80)

        start_time = time.time()
        while (time.time() - start_time) < duration:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if line:  # Only print non-empty lines
                        print(line)
                except Exception as e:
                    print(f"[Decode error: {e}]")

        print("=" * 80)
        print(f"✅ Monitoring complete ({duration}s)")

        ser.close()

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏸️  Monitoring stopped by user")
        if 'ser' in locals():
            ser.close()
        sys.exit(0)

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    monitor_serial(duration)
