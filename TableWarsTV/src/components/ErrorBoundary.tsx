import { Component, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

interface Props {
  children: ReactNode;
  /** Auto-recovery delay after a crash (ms). */
  recoverAfterMs?: number;
}

interface State {
  hasError: boolean;
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
  state: State = { hasError: false };
  private timer: ReturnType<typeof setTimeout> | null = null;

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    // Surface to the console (and any future crash reporter) so the crash
    // isn't silent even though the UI auto-recovers.
    console.error('[TV ErrorBoundary] render crash:', error);
    const ms = this.props.recoverAfterMs ?? 6000;
    this.timer = setTimeout(() => {
      this.timer = null;
      this.setState({ hasError: false });
    }, ms);
  }

  componentWillUnmount() {
    if (this.timer) clearTimeout(this.timer);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <View style={styles.root}>
        <Text style={styles.title}>One sec…</Text>
        <Text style={styles.sub}>Table Wars is reconnecting.</Text>
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
