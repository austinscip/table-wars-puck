import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Scoreboard'>;

export function ScoreboardScreen({ route }: Props) {
  const { players, totalRounds } = route.params;
  const sorted = [...players].sort((a, b) => b.total - a.total);

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>MATCH COMPLETE</Text>
      <View style={styles.list}>
        {sorted.length === 0 ? (
          <Text style={styles.empty}>No scores recorded.</Text>
        ) : (
          sorted.map((p, i) => {
            const isWinner = i === 0 && p.total > 0;
            return (
              <View
                key={p.puckId}
                style={[styles.row, isWinner && styles.rowWinner]}>
                <View style={[styles.avatar, { backgroundColor: p.color }]}>
                  <Text style={styles.avatarText}>{p.puckId}</Text>
                </View>
                <View style={styles.middle}>
                  <Text style={styles.playerLabel}>
                    {isWinner ? '👑 ' : ''}Puck #{p.puckId}
                  </Text>
                  <Text style={styles.playerSub}>
                    {p.correct}/{totalRounds} correct
                  </Text>
                </View>
                <Text style={styles.score}>{p.total}</Text>
              </View>
            );
          })
        )}
      </View>
      <Text style={styles.footer}>Tap a puck to play again · Hold to switch players</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 64,
    gap: 32,
  },
  heading: {
    fontFamily: fonts.display,
    fontSize: 128,
    fontWeight: '900',
    color: colors.correct,
    letterSpacing: -2,
  },
  list: { width: '100%', maxWidth: 1100, gap: 16 },
  empty: { fontFamily: fonts.body, fontSize: 24, color: colors.textDim, textAlign: 'center' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 24,
    paddingHorizontal: 32,
    paddingVertical: 24,
    borderRadius: 24,
    borderWidth: 2,
    borderColor: 'rgba(248,250,252,0.1)',
    backgroundColor: 'rgba(248,250,252,0.05)',
  },
  rowWinner: { borderColor: colors.correct },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontFamily: fonts.display, fontSize: 48, color: colors.bg },
  middle: { flex: 1, gap: 4 },
  playerLabel: { fontFamily: fonts.display, fontSize: 56, color: colors.text },
  playerSub: { fontFamily: fonts.body, fontSize: 20, color: colors.textDim },
  score: { fontFamily: fonts.mono, fontSize: 72, fontWeight: '900', color: colors.text },
  footer: { fontFamily: fonts.body, fontSize: 20, color: colors.textDim },
});
