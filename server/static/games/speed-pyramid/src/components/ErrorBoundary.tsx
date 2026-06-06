import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Base seconds before auto-reloading after a crash (backs off per attempt). */
  reloadAfterSec?: number
  /** Stop auto-reloading after this many rapid reloads (loop guard). */
  maxReloads?: number
}

interface State {
  hasError: boolean
  /** True once we've given up auto-reloading (persistent crash loop). */
  gaveUp: boolean
}

// Persisted ACROSS reloads (window.location.reload wipes component state) so a
// render error that recurs immediately on every boot is caught as a LOOP
// rather than reloading the TV every few seconds forever (audit followups #5).
const RELOAD_KEY = 'tv_reload_attempts'
// If the app survives this long without crashing, the prior crash was
// transient — reset the counter so isolated blips don't accumulate toward the
// loop cap.
const HEALTHY_RESET_MS = 60_000

function readAttempts(): number {
  try {
    return parseInt(sessionStorage.getItem(RELOAD_KEY) || '0', 10) || 0
  } catch {
    return 0
  }
}
function writeAttempts(n: number): void {
  try {
    sessionStorage.setItem(RELOAD_KEY, String(n))
  } catch {
    /* sessionStorage unavailable (private mode) — degrade to no loop guard */
  }
}
function clearAttempts(): void {
  try {
    sessionStorage.removeItem(RELOAD_KEY)
  } catch {
    /* ignore */
  }
}

/**
 * Decide what to do on a crash given how many auto-reloads have already
 * happened this loop. Pure + exported so it's unit-testable without a DOM.
 *
 * - Below the cap: reload, backing off exponentially from `baseSec`
 *   (8s, 16s, 32s, … capped at 60s) so a fast crash-loop doesn't hammer
 *   reloads every few seconds.
 * - At/above the cap: stop reloading and show a terminal "needs attention"
 *   card so the TV isn't stuck in an endless white-flash reload cycle.
 */
export function computeReloadPlan(
  priorAttempts: number,
  baseSec: number,
  maxReloads: number,
): { reload: boolean; delayMs: number; nextAttempts: number } {
  const nextAttempts = priorAttempts + 1
  if (nextAttempts > maxReloads) {
    return { reload: false, delayMs: 0, nextAttempts }
  }
  const backoffSec = Math.min(baseSec * 2 ** priorAttempts, 60)
  return { reload: true, delayMs: backoffSec * 1000, nextAttempts }
}

/**
 * Top-level crash net for the unattended bar TV.
 *
 * The TV runs for hours with nobody standing at it, so a single render-time
 * throw (a malformed socket payload that reaches render, an unexpected
 * undefined field, a bad animation value) would otherwise leave a blank white
 * screen until a human notices and reloads. This boundary catches any such
 * throw, shows a quiet branded "reconnecting" card, and auto-reloads the page —
 * the SPA boots fresh back to the title screen and the pucks re-pair, recovering
 * without intervention.
 *
 * Loop guard (audit followups #5): a render error that recurs immediately on
 * every boot used to reload every 8s forever. We now count reloads in
 * sessionStorage, back off exponentially, and after `maxReloads` give up and
 * show a static "needs attention" card instead of flashing the TV endlessly.
 *
 * Note: React error boundaries only catch errors thrown during render /
 * lifecycle, NOT inside async callbacks or socket event handlers. Those paths
 * are guarded at their call sites; this is the last line of defence for the
 * render tree (audit tv-speed-pyramid-web-2026-06-06).
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, gaveUp: false }
  private reloadTimer: number | null = null
  private healthyTimer: number | null = null

  componentDidMount() {
    // Survived to mount — if we stay up a while, the previous crash (if any)
    // was transient; clear the loop counter so it doesn't accumulate forever.
    this.healthyTimer = window.setTimeout(clearAttempts, HEALTHY_RESET_MS)
  }

  static getDerivedStateFromError(): Partial<State> {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to the console (and any future Sentry/PostHog hook) so the
    // crash isn't silent even though the UI auto-recovers.
    console.error('[TV ErrorBoundary] render crash:', error, info.componentStack)
    const baseSec = this.props.reloadAfterSec ?? 8
    const maxReloads = this.props.maxReloads ?? 5
    const plan = computeReloadPlan(readAttempts(), baseSec, maxReloads)
    writeAttempts(plan.nextAttempts)
    if (!plan.reload) {
      // Persistent loop — stop reloading; show the terminal card.
      this.setState({ gaveUp: true })
      return
    }
    this.reloadTimer = window.setTimeout(() => {
      window.location.reload()
    }, plan.delayMs)
  }

  componentWillUnmount() {
    if (this.reloadTimer !== null) window.clearTimeout(this.reloadTimer)
    if (this.healthyTimer !== null) window.clearTimeout(this.healthyTimer)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    const headline = this.state.gaveUp ? 'Needs attention' : 'One sec…'
    const sub = this.state.gaveUp
      ? 'Table Wars hit a snag — please ask staff to restart the TV.'
      : 'Table Wars is reconnecting.'
    return (
      <main
        style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
          background: '#0A0E1A',
          color: '#F8FAFC',
          fontFamily: 'system-ui, sans-serif',
          textAlign: 'center',
          padding: '2rem',
        }}
      >
        <div style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
          {headline}
        </div>
        <div style={{ fontSize: '1.25rem', opacity: 0.6 }}>{sub}</div>
      </main>
    )
  }
}
