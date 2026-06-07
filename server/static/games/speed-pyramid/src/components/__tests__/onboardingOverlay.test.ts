import { describe, it, expect } from 'vitest'
import { shouldShowOnboarding, markOnboardingSeen } from '../OnboardingOverlay'

function fakeStorage(initial: Record<string, string> = {}) {
  const m = new Map(Object.entries(initial))
  return {
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    setItem: (k: string, v: string) => void m.set(k, v),
  }
}

describe('onboarding gating', () => {
  it('shows on a fresh browser, then never again after being marked seen', () => {
    const s = fakeStorage()
    expect(shouldShowOnboarding(s)).toBe(true)
    markOnboardingSeen(s)
    expect(shouldShowOnboarding(s)).toBe(false)
  })

  it('does not nag when storage throws (private mode)', () => {
    const throwing = {
      getItem: () => {
        throw new Error('blocked')
      },
    }
    expect(shouldShowOnboarding(throwing)).toBe(false)
  })

  it('markOnboardingSeen swallows storage errors', () => {
    const throwing = {
      setItem: () => {
        throw new Error('blocked')
      },
    }
    expect(() => markOnboardingSeen(throwing)).not.toThrow()
  })
})
