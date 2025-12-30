#!/usr/bin/env python3
"""
Enhanced ESP32 Debugger
Captures serial output AND analyzes it for HTTP requests
"""

import serial
import sys
import time
import re
from datetime import datetime

SERIAL_PORT = '/dev/cu.usbserial-0001'
BAUD_RATE = 115200

def analyze_line(line):
    """Analyze a line for interesting patterns"""
    patterns = {
        'http_post': r'POST\s+/api/\w+',
        'http_get': r'GET\s+/api/\w+',
        'score': r'score[:\s]+(\d+)',
        'error': r'(error|failed|timeout|disconnect)',
        'wifi': r'(WiFi|IP\s+address)',
        'json': r'\{.*\}',
    }

    results = []
    line_lower = line.lower()

    for pattern_name, pattern in patterns.items():
        if re.search(pattern, line, re.IGNORECASE):
            results.append(pattern_name)

    return results

def monitor_serial(duration=60, log_file='esp32_debug.log'):
    """Monitor serial port and save to log file"""
    stats = {
        'total_lines': 0,
        'http_requests': 0,
        'scores_found': 0,
        'errors': 0,
        'json_packets': 0
    }

    try:
        print(f"🔌 Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(0.5)

        print(f"✅ Connected! Monitoring for {duration} seconds...")
        print(f"📝 Logging to: {log_file}")
        print("=" * 80)

        with open(log_file, 'w') as f:
            f.write(f"ESP32 Debug Log - {datetime.now()}\n")
            f.write("=" * 80 + "\n")

            start_time = time.time()
            while (time.time() - start_time) < duration:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').rstrip()
                        if line:
                            stats['total_lines'] += 1

                            # Analyze line
                            tags = analyze_line(line)

                            # Update stats
                            if 'http_post' in tags or 'http_get' in tags:
                                stats['http_requests'] += 1
                                print(f"🌐 HTTP: {line}")
                            if 'score' in tags:
                                stats['scores_found'] += 1
                                print(f"🎯 SCORE: {line}")
                            if 'error' in tags:
                                stats['errors'] += 1
                                print(f"❌ ERROR: {line}")
                            if 'json' in tags:
                                stats['json_packets'] += 1
                                print(f"📦 JSON: {line}")
                            if 'wifi' in tags:
                                print(f"📶 WiFi: {line}")

                            # Write to log
                            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                            f.write(f"[{timestamp}] {line}\n")
                            f.flush()

                    except Exception as e:
                        print(f"[Decode error: {e}]")

        ser.close()

        print("=" * 80)
        print(f"\n📊 STATISTICS:")
        print(f"  Total lines: {stats['total_lines']}")
        print(f"  HTTP requests: {stats['http_requests']}")
        print(f"  Scores found: {stats['scores_found']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  JSON packets: {stats['json_packets']}")
        print(f"\n✅ Log saved to: {log_file}")

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏸️  Monitoring stopped by user")
        if 'ser' in locals():
            ser.close()
        sys.exit(0)

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    monitor_serial(duration)
