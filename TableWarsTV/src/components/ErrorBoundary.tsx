import { Component, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

interface Props {
  children: ReactNode;
  /** Base auto-recovery delay after a crash (ms); backs off per attempt. */
  recoverAfterMs?: number;
  /** Stop auto-recovering after this many rapid re-crashes (loop guard). */
  maxRecover?: number;
}

interface State {
  hasError: boolean;
  /** True once we've given up auto-recovering (persistent crash loop). */
  gaveUp: boolean;
}

// If the view survives this long after a recovery, the prior crash was
// transient — reset the loop counter.
const HEALTHY_RESET_MS = 60_000;

/**
 * Decide what to do on a crash given how many recoveries already happened this
 * loop. Pure + exported so it's unit-testable. Below the cap: recover, backing
 * off exponentially from `baseMs` (capped at 60s). At/above the cap: give up and
 * hold a static card instead of flapping card<->crash every few seconds forever.
 */
export function computeRecoverPlan(
  priorAttempts: number,
  baseMs: number,
  maxRecover: number,
): { recover: boolean; delayMs: number; nextAttempts: number } {
  const nextAttempts = priorAttempts + 1;
  if (nextAttempts > maxRecover) {
    return { recover: false, delayMs: 0, nextAttempts };
  }
  return {
    recover: true,
    delayMs: Math.min(baseMs * 2 ** priorAttempts, 60_000),
    nextAttempts,
  };
}

/**
 * Top-level crash net for the unattended TV.
 *
 * The TV runs for hours with nobody watching it, so a single render-time throw
 * (a partial snapshot that reaches a game view, an unexpected undefined field)
 * would otherwise blank the whole screen until a human power-cycles it. This
 * boundary catches the throw, shows a quiet "reconnecting" card, and
 * auto-recovers a few seconds later by re-rendering its children — by then the
 * next snapshot has usually arrived and the offending frame is gone. If the bad
 * frame persists, it simply re-shows the card on the same cadence (no tight
 * loop) rather than dying.
 *
 * React error boundaries only catch render/lifecycle errors, not async
 * callbacks — those are guarded at their call sites. This is the last line of
 * defence for the render tree (audit tablewars-tv-2026-06-06).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, gaveUp: false };
  private timer: ReturnType<typeof setTimeout> | null = null;
  private healthyTimer: ReturnType<typeof setTimeout> | null = null;
  // In-memory (state survives recovery — no reload here), so consecutive
  // re-crashes accumulate toward the give-up cap (audit followups #5).
  private attempts = 0;

  static getDerivedStateFromError(): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    // Surface to the console (and any future crash reporter) so the crash
    // isn't silent even though the UI auto-recovers.
    console.error('[TV ErrorBoundary] render crash:', error);
    if (this.healthyTimer) {
      clearTimeout(this.healthyTimer);
      this.healthyTimer = null;
    }
    const baseMs = this.props.recoverAfterMs ?? 6000;
    const maxRecover = this.props.maxRecover ?? 5;
    const plan = computeRecoverPlan(this.attempts, baseMs, maxRecover);
    this.attempts = plan.nextAttempts;
    if (!plan.recover) {
      // Persistent loop — stop flapping; hold the terminal card.
      this.setState({ gaveUp: true });
      return;
    }
    this.timer = setTimeout(() => {
      this.timer = null;
      this.setState({ hasError: false });
      // If we now stay healthy for a while, the crash was transient — reset.
      this.healthyTimer = setTimeout(() => {
        this.attempts = 0;
      }, HEALTHY_RESET_MS);
    }, plan.delayMs);
  }

  componentWillUnmount() {
    if (this.timer) clearTimeout(this.timer);
    if (this.healthyTimer) clearTimeout(this.healthyTimer);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const title = this.state.gaveUp ? 'Needs attention' : 'One sec…';
    const sub = this.state.gaveUp
      ? 'Please ask staff to restart the TV.'
      : 'Table Wars is reconnecting.';
    return (
      <View style={styles.root}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.sub}>{sub}</Text>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: colors.bg,
  },
  title: { fontFamily: fonts.display, fontSize: 48, color: colors.text },
  sub: { fontFamily: fonts.body, fontSize: 22, color: colors.textDim },
});
