import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../../theme';
import type { PuckGolfSnapshot } from './types';
import { colorForPuck } from './types';

// Top-down lane view of the current hole. Tee is at the bottom, cup at
// the top. Each player's ball renders as a coloured dot along the
// fairway proportional to ball.y / hole_distance.

const FAIRWAY_HEIGHT = 480;

export function PuckGolfView({ snapshot }: { snapshot: PuckGolfSnapshot }) {
  const distance = snapshot.hole_distance ?? 100;
  return (
    <View style={styles.root}>
      <View style={styles.top}>
        <View>
          <Text style={styles.holeLabel}>HOLE</Text>
          <Text style={styles.holeNumber}>{snapshot.hole_number ?? '—'}</Text>
        </View>
        <View>
          <Text style={styles.metaLabel}>PAR</Text>
          <Text style={styles.metaValue}>{snapshot.hole_par ?? '—'}</Text>
        </View>
        <View>
          <Text style={styles.metaLabel}>DISTANCE</Text>
          <Text style={styles.metaValue}>{Math.round(distance)} yd</Text>
        </View>
        <View>
          <Text style={styles.metaLabel}>UP NEXT</Text>
          <Text style={styles.metaValue}>
            {snapshot.current_turn_puck_index != null
              ? `Puck ${snapshot.current_turn_puck_index}`
              : '—'}
          </Text>
        </View>
      </View>

      <View style={styles.fairway}>
        <View style={styles.cup}>
          <Text style={styles.cupLabel}>CUP</Text>
        </View>
        {snapshot.players.map((p) => {
          const pct = Math.max(0, Math.min(1, p.ball.y / distance));
          const bottom = pct * FAIRWAY_HEIGHT;
          // Dynamic (state-dependent) style — extracted to a variable so
          // it isn't an inline literal in the JSX.
          const ballStyle = {
            backgroundColor: colorForPuck(p.puck_index),
            bottom,
            borderColor:
              snapshot.current_turn_puck_index === p.puck_index
                ? colors.correct
                : 'transparent',
          };
          return (
            <View key={p.puck_index} style={[styles.ball, ballStyle]}>
              <Text style={styles.ballLabel}>{p.puck_index}</Text>
            </View>
          );
        })}
        <View style={styles.teeMark} />
        <Text style={styles.teeText}>TEE</Text>
      </View>

      <View style={styles.scoreboard}>
        {snapshot.players.map((p) => (
          <View key={p.puck_index} style={styles.scoreRow}>
            <View
              style={[styles.scoreAvatar, { backgroundColor: colorForPuck(p.puck_index) }]}>
              <Text style={styles.scoreAvatarText}>{p.puck_index}</Text>
            </View>
            <Text style={styles.scoreLabel}>
              Hole {snapshot.hole_number}: {p.hole_strokes}
              {p.hole_done ? ' ✓' : ''}
            </Text>
            <Text style={styles.scoreTotal}>Total: {p.total_strokes}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 32, gap: 24 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  holeLabel: { fontFamily: fonts.body, fontSize: 14, color: colors.textFaint, letterSpacing: 4 },
  holeNumber: { fontFamily: fonts.display, fontSize: 64, color: colors.text },
  metaLabel: { fontFamily: fonts.body, fontSize: 14, color: colors.textFaint, letterSpacing: 4 },
  metaValue: { fontFamily: fonts.display, fontSize: 32, color: colors.text },
  fairway: {
    height: FAIRWAY_HEIGHT,
    width: '100%',
    backgroundColor: 'rgba(16,185,129,0.10)',
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'flex-end',
    position: 'relative',
  },
  cup: {
    position: 'absolute',
    top: 8,
    alignSelf: 'center',
    backgroundColor: colors.correct,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  cupLabel: { fontFamily: fonts.display, fontSize: 16, color: colors.bg, letterSpacing: 2 },
  ball: {
    position: 'absolute',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
  },
  ballLabel: { fontFamily: fonts.display, fontSize: 18, color: colors.bg },
  teeMark: {
    position: 'absolute',
    bottom: 8,
    width: 80,
    height: 4,
    backgroundColor: colors.textFaint,
    borderRadius: 2,
  },
  teeText: {
    position: 'absolute',
    bottom: 16,
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.textFaint,
    letterSpacing: 4,
  },
  scoreboard: { gap: 8 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  scoreAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreAvatarText: { fontFamily: fonts.display, fontSize: 16, color: colors.bg },
  scoreLabel: { fontFamily: fonts.body, fontSize: 18, color: colors.text, flex: 1 },
  scoreTotal: { fontFamily: fonts.mono, fontSize: 18, color: colors.textDim },
});
