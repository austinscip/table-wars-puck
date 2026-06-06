// Small numeric guards shared by the time/progress bars. Pure + dependency-
// free so they can be unit-tested without the React tree (see
// __tests__/num.test.ts). The bar TV renders these into CSS widths/positions,
// so a NaN/Infinity here paints an invisible or off-screen bar on an
// unattended display — these helpers keep the output in [0, 100] / [0, 1]
// even when the server hands us a degenerate duration (audit
// tv-speed-pyramid-web-2026-06-06).

/** Clamp `v` into [lo, hi]. NaN collapses to `lo`. */
export function clamp(v: number, lo: number, hi: number): number {
  if (Number.isNaN(v)) return lo
  return Math.min(hi, Math.max(lo, v))
}

/**
 * Percentage [0, 100] of time remaining. Guards the divide-by-zero /
 * missing-duration case (`total <= 0` → 0) that would otherwise yield
 * `NaN%` / `Infinity%` and make the timer bar vanish.
 */
export function pctRemaining(remainingMs: number, totalMs: number): number {
  if (!(totalMs > 0)) return 0 // also catches NaN/undefined totalMs
  return clamp((remainingMs / totalMs) * 100, 0, 100)
}
