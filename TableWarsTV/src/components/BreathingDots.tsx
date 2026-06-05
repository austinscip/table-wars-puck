import { useEffect, useMemo, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { colors } from '../theme';

// Three dots that pulse opacity in sequence — the "ready, waiting" cue
// shared with the existing Speed Pyramid title screen.
export function BreathingDots() {
  // Stable Animated.Value refs; memo the array so the effect's dep is
  // stable across renders.
  const o0 = useRef(new Animated.Value(0.2)).current;
  const o1 = useRef(new Animated.Value(0.2)).current;
  const o2 = useRef(new Animated.Value(0.2)).current;
  const opacities = useMemo(() => [o0, o1, o2], [o0, o1, o2]);

  useEffect(() => {
    const loops = opacities.map((opacity, i) => {
      const seq = Animated.sequence([
        Animated.delay(i * 200),
        Animated.timing(opacity, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.2, duration: 800, useNativeDriver: true }),
      ]);
      const loop = Animated.loop(seq);
      loop.start();
      return loop;
    });
    return () => loops.forEach((l) => l.stop());
  }, [opacities]);

  return (
    <View style={styles.row}>
      {opacities.map((opacity, i) => (
        <Animated.View key={i} style={[styles.dot, { opacity }]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12, marginTop: 32 },
  dot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.text },
});
