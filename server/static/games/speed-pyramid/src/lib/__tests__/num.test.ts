import { describe, it, expect } from 'vitest'
import { clamp, pctRemaining } from '../num'

describe('clamp', () => {
  it('passes values already in range', () => {
    expect(clamp(0.5, 0, 1)).toBe(0.5)
    expect(clamp(50, 0, 100)).toBe(50)
  })
  it('clamps below/above the bounds', () => {
    expect(clamp(-3, 0, 1)).toBe(0)
    expect(clamp(2, 0, 1)).toBe(1)
    expect(clamp(150, 0, 100)).toBe(100)
  })
  it('collapses NaN to the low bound (no NaN leaks into CSS)', () => {
    expect(clamp(NaN, 0, 1)).toBe(0)
  })
})

describe('pctRemaining', () => {
  it('computes a normal percentage', () => {
    expect(pctRemaining(5000, 10000)).toBe(50)
    expect(pctRemaining(10000, 10000)).toBe(100)
    expect(pctRemaining(0, 10000)).toBe(0)
  })
  it('never exceeds [0, 100] even with out-of-range input', () => {
    expect(pctRemaining(15000, 10000)).toBe(100)
    expect(pctRemaining(-1, 10000)).toBe(0)
  })
  it('returns 0 for a zero / missing / NaN duration (the bar-blanking bug)', () => {
    expect(pctRemaining(0, 0)).toBe(0)
    expect(pctRemaining(5000, 0)).toBe(0)
    expect(pctRemaining(5000, NaN)).toBe(0)
  })
})
