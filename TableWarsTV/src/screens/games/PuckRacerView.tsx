import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../../theme';
import type { PuckRacerSnapshot } from './types';
import { colorForPuck } from './types';

// 3-lane drag race. Track scrolls vertically; finish line at the top,
// start at the bottom. Each racer renders as a coloured dot in its
// lane at the position proportional to its progress.

const TRACK_HEIGHT = 500;

export function PuckRacerView({ snapshot }: { snapshot: PuckRacerSnapshot }) {
  const timeLeft = Math.max(0, snapshot.race_seconds - snapshot.race_time_sec);
  return (
    <View style={styles.root}>
      <View style={styles.top}>
        <View>
          <Text style={styles.label}>TIME</Text>
          <Text style={styles.timeValue}>
            {snapshot.race_time_sec.toFixed(1)}s / {timeLeft.toFixed(1)}s left
          </Text>
        </View>
        <View>
          <Text style={styles.label}>FINISH</Text>
          <Text style={styles.metaValue}>{snapshot.finish_distance} yd</Text>
        </View>
      </View>

      <View style={styles.track}>
        {[0, 1, 2].map((lane) => (
          <View key={lane} style={styles.lane}>
            <View style={styles.laneDivider} />
            {snapshot.racers
              .filter((r) => r.lane === lane)
              .map((r) => {
                const pct = Math.min(1, r.position / snapshot.finish_distance);
                const bottom = pct * TRACK_HEIGHT;
                // Dynamic style extracted to a variable (not an inline literal).
                const carStyle = {
                  backgroundColor: colorForPuck(r.puck_index),
                  bottom,
                  borderColor: r.boost_active ? colors.correct : 'transparent',
                };
                return (
                  <View key={r.puck_index} style={[styles.car, carStyle]}>
                    <Text style={styles.carLabel}>{r.puck_index}</Text>
                  </View>
                );
              })}
          </View>
        ))}
        <View style={styles.finishLine} />
      </View>

      <View style={styles.scoreboard}>
        {snapshot.racers
          .slice()
          .sort((a, b) => b.position - a.position)
          .map((r, i) => (
            <View key={r.puck_index} style={styles.scoreRow}>
              <Text style={styles.rank}>{i + 1}</Text>
              <View
                style={[styles.scoreAvatar, { backgroundColor: colorForPuck(r.puck_index) }]}>
                <Text style={styles.scoreAvatarText}>{r.puck_index}</Text>
              </View>
              <Text style={styles.scoreLabel}>
                {Math.round(r.position)} yd · {r.speed.toFixed(1)} y/s
                {r.boost_active ? ' · BOOST' : ''}
                {r.finished ? ' · FINISHED' : ''}
              </Text>
              <Text style={styles.boost}>boost x{r.boosts_remaining}</Text>
            </View>
          ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 32, gap: 16 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontFamily: fonts.body, fontSize: 14, color: colors.textFaint, letterSpacing: 4 },
  timeValue: { fontFamily: fonts.mono, fontSize: 24, fontWeight: '900', color: colors.text },
  metaValue: { fontFamily: fonts.display, fontSize: 32, color: colors.text },
  track: {
    height: TRACK_HEIGHT,
    flexDirection: 'row',
    backgroundColor: 'rgba(248,250,252,0.04)',
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
  },
  lane: { flex: 1, position: 'relative' },
  laneDivider: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: 1,
    backgroundColor: 'rgba(248,250,252,0.1)',
  },
  car: {
    position: 'absolute',
    width: 36,
    height: 36,
    borderRadius: 18,
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
  },
  carLabel: { fontFamily: fonts.display, fontSize: 16, color: colors.bg },
  finishLine: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 6,
    backgroundColor: colors.correct,
  },
  scoreboard: { gap: 6 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rank: {
    fontFamily: fonts.display,
    fontSize: 22,
    color: colors.correct,
    width: 28,
  },
  scoreAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreAvatarText: { fontFamily: fonts.display, fontSize: 16, color: colors.bg },
  scoreLabel: { flex: 1, fontFamily: fonts.body, fontSize: 18, color: colors.text },
  boost: { fontFamily: fonts.mono, fontSize: 14, color: colors.textDim },
});
