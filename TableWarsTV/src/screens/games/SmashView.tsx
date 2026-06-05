import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../../theme';
import type { SmashSnapshot } from './types';
import { colorForPuck } from './types';

// Top-down arena. Fighters render as coloured circles inside the
// arena bounds; size of their damage % bubble grows with damage.
// Damage % colour goes white -> yellow -> red as it climbs.

const ARENA_HEIGHT = 460;
const ARENA_ASPECT = 100 / 60; // matches ARENA_X width / ARENA_Y height

export function SmashView({ snapshot }: { snapshot: SmashSnapshot }) {
  const [arenaXMin, arenaXMax] = snapshot.arena.x;
  const [arenaYMin, arenaYMax] = snapshot.arena.y;
  const xSpan = arenaXMax - arenaXMin;
  const ySpan = arenaYMax - arenaYMin;

  return (
    <View style={styles.root}>
      <View style={styles.top}>
        <View>
          <Text style={styles.label}>TIME</Text>
          <Text style={styles.timeValue}>{snapshot.match_time_sec.toFixed(1)}s</Text>
        </View>
        <Text style={styles.title}>SMASH</Text>
        <View>
          <Text style={styles.label}>WINNER</Text>
          <Text style={styles.metaValue}>
            {snapshot.winner_index != null ? `Puck ${snapshot.winner_index}` : '—'}
          </Text>
        </View>
      </View>

      <View
        style={[
          styles.arena,
          { height: ARENA_HEIGHT, aspectRatio: ARENA_ASPECT },
        ]}>
        {snapshot.fighters.map((f) => {
          if (f.eliminated) return null;
          const xPct = (f.x - arenaXMin) / xSpan;
          const yPct = (f.y - arenaYMin) / ySpan;
          // y inverted so positive y renders toward top of screen.
          const left = `${xPct * 100}%`;
          const bottom = `${yPct * 100}%`;
          return (
            <View
              key={f.puck_index}
              style={[
                styles.fighter,
                {
                  backgroundColor: colorForPuck(f.puck_index),
                  left: left as `${number}%`,
                  bottom: bottom as `${number}%`,
                },
              ]}>
              <Text style={styles.fighterLabel}>{f.puck_index}</Text>
            </View>
          );
        })}
      </View>

      <View style={styles.scoreboard}>
        {snapshot.fighters.map((f) => (
          <View
            key={f.puck_index}
            style={[styles.scoreRow, f.eliminated && styles.scoreRowDead]}>
            <View style={[styles.scoreAvatar, { backgroundColor: colorForPuck(f.puck_index) }]}>
              <Text style={styles.scoreAvatarText}>{f.puck_index}</Text>
            </View>
            <Text style={[styles.dmg, dmgStyle(f.damage_pct)]}>
              {f.damage_pct.toFixed(0)}%
            </Text>
            <Text style={styles.stocks}>{'●'.repeat(f.stocks) || '✗'}</Text>
            <Text style={styles.kos}>KOs {f.kos_landed}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function dmgStyle(pct: number) {
  if (pct >= 100) return { color: colors.wrong };
  if (pct >= 60) return { color: colors.correct };
  return { color: colors.text };
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 32, gap: 16 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontFamily: fonts.body, fontSize: 14, color: colors.textFaint, letterSpacing: 4 },
  title: { fontFamily: fonts.display, fontSize: 48, color: colors.accent, letterSpacing: 4 },
  timeValue: { fontFamily: fonts.mono, fontSize: 24, fontWeight: '900', color: colors.text },
  metaValue: { fontFamily: fonts.display, fontSize: 28, color: colors.text },
  arena: {
    alignSelf: 'center',
    backgroundColor: 'rgba(248,250,252,0.04)',
    borderRadius: 24,
    borderWidth: 2,
    borderColor: 'rgba(248,250,252,0.1)',
    position: 'relative',
  },
  fighter: {
    position: 'absolute',
    width: 48,
    height: 48,
    borderRadius: 24,
    transform: [{ translateX: -24 }, { translateY: 24 }],
    alignItems: 'center',
    justifyContent: 'center',
  },
  fighterLabel: { fontFamily: fonts.display, fontSize: 20, color: colors.bg },
  scoreboard: { gap: 8 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  scoreRowDead: { opacity: 0.4 },
  scoreAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreAvatarText: { fontFamily: fonts.display, fontSize: 18, color: colors.bg },
  dmg: { fontFamily: fonts.mono, fontSize: 28, fontWeight: '900', minWidth: 70 },
  stocks: { fontFamily: fonts.display, fontSize: 22, color: colors.correct, letterSpacing: 4 },
  kos: { fontFamily: fonts.body, fontSize: 16, color: colors.textDim },
});
