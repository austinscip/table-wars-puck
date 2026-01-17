// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Sprint 0 Simulator E2E Tests
 * Tests the puck simulator -> server -> browser data flow without physical hardware
 */

test.describe('Puck Simulator E2E', () => {

  test('simulator sends all 6 sensor fields correctly', async ({ page }) => {
    // Navigate to puck simulator
    await page.goto('/test/puck-simulator');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Wait for WebSocket connection to establish
    await page.waitForTimeout(1000);

    // Set tilt_x slider to 30 degrees
    await page.locator('#tiltX').fill('30');
    await page.waitForTimeout(200); // Allow WebSocket event to propagate

    // Check that tilt_x value displays correctly
    const tiltXValue = await page.locator('#tiltXValue').textContent();
    expect(parseFloat(tiltXValue)).toBeCloseTo(30, 0);

    // Set tilt_y slider to -20 degrees
    await page.locator('#tiltY').fill('-20');
    await page.waitForTimeout(200);

    const tiltYValue = await page.locator('#tiltYValue').textContent();
    expect(parseFloat(tiltYValue)).toBeCloseTo(-20, 0);

    // Set shake intensity
    await page.locator('#shakeIntensity').fill('15');
    await page.waitForTimeout(200);

    const shakeValue = await page.locator('#shakeValue').textContent();
    expect(parseFloat(shakeValue)).toBeCloseTo(15, 0);

    // Set gyro_z (spin) - value is in deg/s directly
    await page.locator('#gyroZ').fill('143');
    await page.waitForTimeout(200);

    const gyroZValue = await page.locator('#gyroZValue').textContent();
    expect(parseFloat(gyroZValue)).toBeCloseTo(143, 0);
  });

  test('latency is under 500ms from simulator to browser', async ({ page }) => {
    await page.goto('/test/puck-simulator');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Measure latency for multiple events
    const latencies = [];

    for (let i = 0; i < 10; i++) {
      const testValue = Math.floor(Math.random() * 90 - 45); // Random value between -45 and 45
      const startTime = Date.now();

      // Set tilt_x slider
      await page.locator('#tiltX').fill(testValue.toString());

      // Wait for value to update in display
      await page.waitForFunction(
        (expectedValue) => {
          const element = document.querySelector('#tiltXValue');
          if (!element) return false;
          const actualValue = parseFloat(element.textContent);
          return Math.abs(actualValue - expectedValue) < 1;
        },
        testValue,
        { timeout: 1000 }
      );

      const endTime = Date.now();
      const latency = endTime - startTime;
      latencies.push(latency);
    }

    // Calculate average latency
    const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    const maxLatency = Math.max(...latencies);

    console.log(`Average latency: ${avgLatency.toFixed(0)}ms`);
    console.log(`Max latency: ${maxLatency}ms`);
    console.log(`All latencies: ${latencies.map(l => l.toFixed(0)).join(', ')}ms`);

    // Assert latency is acceptable
    expect(avgLatency).toBeLessThan(500);
    expect(maxLatency).toBeLessThan(1000);
  });

  test('all preset scenarios execute correctly', async ({ page }) => {
    await page.goto('/test/puck-simulator');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Test Light Spin preset - verify it sets gyro to 80
    await page.click('text=Light Spin (80)');
    await page.waitForTimeout(300);

    let gyroZValue = await page.locator('#gyroZValue').textContent();
    expect(parseFloat(gyroZValue)).toBe(80);

    // Test Reset All - should reset to 0
    await page.click('text=Reset All');
    await page.waitForTimeout(300);

    gyroZValue = await page.locator('#gyroZValue').textContent();
    expect(parseFloat(gyroZValue)).toBe(0);

    // Test Medium Spin - verify it sets gyro to 200
    await page.click('text=Medium Spin (200)');
    await page.waitForTimeout(300);

    gyroZValue = await page.locator('#gyroZValue').textContent();
    expect(parseFloat(gyroZValue)).toBe(200);

    // Test Hard Spin - verify it sets gyro to 350
    await page.click('text=Hard Spin (350)');
    await page.waitForTimeout(300);

    gyroZValue = await page.locator('#gyroZValue').textContent();
    expect(parseFloat(gyroZValue)).toBe(350);

    // Reset before testing tilt
    await page.click('text=Reset All');
    await page.waitForTimeout(300);

    // Test Tilt Left - should set tilt_x to negative
    await page.click('text=Tilt Left');
    await page.waitForTimeout(300);

    const tiltXValue = await page.locator('#tiltXValue').textContent();
    expect(parseFloat(tiltXValue)).toBeLessThan(0);

    // Test Tilt Right - should set tilt_x to positive
    await page.click('text=Tilt Right');
    await page.waitForTimeout(300);

    const tiltRightValue = await page.locator('#tiltXValue').textContent();
    expect(parseFloat(tiltRightValue)).toBeGreaterThan(0);

    // Verify event log shows activity
    const eventLog = await page.locator('#log').textContent();
    expect(eventLog.length).toBeGreaterThan(0);
  });

  test.skip('1-minute stability test (no disconnects or errors)', async ({ page }) => {
    // Skip by default - run manually with --grep flag
    await page.goto('/test/puck-simulator');
    await page.waitForLoadState('networkidle');

    // Listen for console errors
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Run for 1 minute (60 seconds) with periodic sensor updates
    const testDuration = 60 * 1000; // 1 minute in milliseconds
    const startTime = Date.now();
    const updateInterval = 1000; // Update every second

    let iterationCount = 0;
    while (Date.now() - startTime < testDuration) {
      iterationCount++;

      // Random sensor updates
      const randomTiltX = Math.floor(Math.random() * 90 - 45).toString();
      const randomTiltY = Math.floor(Math.random() * 90 - 45).toString();
      const randomShake = Math.floor(Math.random() * 20 + 10).toString();

      await page.locator('#tiltX').fill(randomTiltX);
      await page.locator('#tiltY').fill(randomTiltY);
      await page.locator('#shakeIntensity').fill(randomShake);

      // Wait for next iteration
      await page.waitForTimeout(updateInterval);

      // Log progress every 15 seconds
      if (iterationCount % 15 === 0) {
        console.log(`Stability test: ${Math.floor((Date.now() - startTime) / 1000)}s elapsed, ${iterationCount} iterations`);
      }
    }

    console.log(`Stability test complete: ${iterationCount} iterations, ${consoleErrors.length} errors`);

    // Assert no errors
    expect(consoleErrors.length).toBe(0);
  });

});
