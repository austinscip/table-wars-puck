import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Seconds before auto-reloading after a crash. */
  reloadAfterSec?: number
}

interface State {
  hasError: boolean
}

/**
 * Top-level crash net for the unattended bar TV.
 *
 * The TV runs for hours with nobody standing at it, so a single render-time
 * throw (a malformed socket payload that reaches render, an unexpected
 * undefined field, a bad animation value) would otherwise leave a blank white
 * screen until a human notices and reloads. This boundary catches any such
 * throw, shows a quiet branded "reconnecting" card, and auto-reloads the page
 * a few seconds later — the SPA boots fresh back to the title screen and the
 * pucks re-pair, recovering without intervention.
 *
 * Note: React error boundaries only catch errors thrown during render /
 * lifecycle, NOT inside async callbacks or socket event handlers. Those paths
 * are guarded at their call sites; this is the last line of defence for the
 * render tree (audit tv-speed-pyramid-web-2026-06-06).
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }
  private reloadTimer: number | null = null

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to the console (and any future Sentry/PostHog hook) so the
    // crash isn't silent even though the UI auto-recovers.
    console.error('[TV ErrorBoundary] render crash:', error, info.componentStack)
    const sec = this.props.reloadAfterSec ?? 8
    this.reloadTimer = window.setTimeout(() => {
      window.location.reload()
    }, sec * 1000)
  }

  componentWillUnmount() {
    if (this.reloadTimer !== null) window.clearTimeout(this.reloadTimer)
  }

  render() {
    if (!this.state.hasError) return this.props.children
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
          One sec…
        </div>
        <div style={{ fontSize: '1.25rem', opacity: 0.6 }}>
          Table Wars is reconnecting.
        </div>
      </main>
    )
  }
}
