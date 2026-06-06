import { useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet } from 'react-native';
import { colors } from '../theme';
import { Cue, CueChannel, type CueDispatcher, type CueEvent } from '../lib/cues';

// Per-cue tint + fade duration. Visual placeholder until the real
// polish layer wires Lottie animations + sprite reactions per cue.
const TINT_BY_CUE: Partial<Record<string, string>> = {
  [Cue.SCORE_GOLD]: colors.correct,
  [Cue.SCORE_SILVER]: colors.primary,
  [Cue.SCORE_BRONZE]: colors.accent,
  [Cue.PLAYER_CORRECT]: colors.correct,
  [Cue.PLAYER_WRONG]: colors.wrong,
  [Cue.PLAYER_TIMEOUT]: colors.textFaint,
  [Cue.PLAYER_ELIMINATED]: colors.wrong,
  [Cue.PLAYER_VICTORY]: colors.correct,
  [Cue.MATCH_START]: colors.primary,
  [Cue.MATCH_END]: colors.correct,
  [Cue.TIMER_WARNING]: colors.accent,
  [Cue.TIMER_EXPIRED]: colors.wrong,
};

// All cues fall through here when polish-system handlers (audio,
// animation) aren't subscribed elsewhere. The "haptic" channel
// catches every visual-eligible cue regardless of its specific
// channels list — we treat the screen flash as a fallback haptic
// channel rather than fighting per-cue channel routing.

export function CueFlashOverlay({ dispatcher }: { dispatcher: CueDispatcher }) {
  const opacity = useRef(new Animated.Value(0)).current;
  // tint must be STATE, not a ref: a ref mutation doesn't re-render, so the
  // flash would paint with the PREVIOUS cue's colour until some unrelated
  // render happened (audit tablewars-tv-2026-06-06).
  const [tint, setTint] = useState<string>(colors.text);

  useEffect(() => {
    const handler = (event: CueEvent) => {
      const colour = TINT_BY_CUE[event.cue];
      if (!colour) return;
      setTint(colour);
      // Cancel any in-flight fade so rapid back-to-back cues each get a clean
      // full flash rather than stacking partially-faded animations.
      opacity.stopAnimation();
      opacity.setValue(0.6);
      Animated.timing(opacity, {
        toValue: 0,
        duration: 380,
        useNativeDriver: true,
      }).start();
    };
    // Subscribe across the channels most likely to fire a "look here"
    // beat. Audio / music / led handlers will subscribe to their own
    // channels independently when real assets land.
    const unsubs = [
      dispatcher.on(CueChannel.SFX, handler),
      dispatcher.on(CueChannel.VO, handler),
      dispatcher.on(CueChannel.HAPTIC, handler),
    ];
    return () => unsubs.forEach((u) => u());
  }, [dispatcher, opacity]);

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        styles.overlay,
        { opacity, backgroundColor: tint },
      ]}
    />
  );
}

const styles = StyleSheet.create({
  overlay: { zIndex: 100 },
});
