import { describe, it, expect } from 'vitest'
import { computeReloadPlan } from '../ErrorBoundary'

describe('computeReloadPlan (TV crash loop guard)', () => {
  it('reloads with exponential backoff under the cap', () => {
    // base 8s: 8s, 16s, 32s, then capped at 60s.
    expect(computeReloadPlan(0, 8, 5)).toMatchObject({ reload: true, delayMs: 8_000 })
    expect(computeReloadPlan(1, 8, 5)).toMatchObject({ reload: true, delayMs: 16_000 })
    expect(computeReloadPlan(2, 8, 5)).toMatchObject({ reload: true, delayMs: 32_000 })
    expect(computeReloadPlan(3, 8, 5)).toMatchObject({ reload: true, delayMs: 60_000 })
    expect(computeReloadPlan(4, 8, 5)).toMatchObject({ reload: true, delayMs: 60_000 })
  })

  it('gives up once the reload cap is exceeded (no endless loop)', () => {
    const plan = computeReloadPlan(5, 8, 5)
    expect(plan.reload).toBe(false)
    expect(plan.delayMs).toBe(0)
    expect(plan.nextAttempts).toBe(6)
  })

  it('increments the attempt counter each crash', () => {
    expect(computeReloadPlan(0, 8, 5).nextAttempts).toBe(1)
    expect(computeReloadPlan(3, 8, 5).nextAttempts).toBe(4)
  })
})
