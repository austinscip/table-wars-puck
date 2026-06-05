import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type {
  NativeStackNavigationProp,
  NativeStackScreenProps,
} from '@react-navigation/native-stack';
import { colors, fonts } from '../theme';
import { useMatchState } from '../lib/useMatchState';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Game'>;

// Game-agnostic match view. Subscribes to matches.snapshot and renders
// a minimal data-readout. Per-game renderers (Speed Pyramid question,
// Puck Golf course, Puck Racer track, Smash arena) get wired in as
// the polish system lands; the structural surface is here.

export function GameScreen({ route }: Props) {
  const { matchId } = route.params;
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const match = useMatchState(matchId);

  // Match finalised -> Scoreboard. The Scoreboard subscribes to the
  // same row so the snapshot it renders is already in cache.
  useEffect(() => {
    if (match.status === 'finished' || match.status === 'abandoned') {
      navigation.replace('Scoreboard', { matchId });
    }
  }, [match.status, matchId, navigation]);

  const slug = (match.snapshot as { game_slug?: string } | null)?.game_slug;

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.gameSlug}>{slug ?? 'Loading…'}</Text>
        <Text style={styles.status}>{match.status.toUpperCase()}</Text>
      </View>

      {match.loading || !match.snapshot ? (
        <Text style={styles.empty}>Waiting for first state update…</Text>
      ) : (
        <View style={styles.snapshotBox}>
          <Text style={styles.snapshotLabel}>SNAPSHOT</Text>
          <Text style={styles.snapshot}>
            {JSON.stringify(match.snapshot, null, 2)}
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    padding: 48,
    gap: 32,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  gameSlug: {
    fontFamily: fonts.display,
    fontSize: 64,
    color: colors.text,
    letterSpacing: -1,
  },
  status: {
    fontFamily: fonts.body,
    fontSize: 24,
    color: colors.correct,
    letterSpacing: 4,
  },
  empty: {
    fontFamily: fonts.body,
    fontSize: 28,
    color: colors.textDim,
    textAlign: 'center',
    marginTop: 64,
  },
  snapshotBox: {
    flex: 1,
    backgroundColor: 'rgba(248,250,252,0.04)',
    borderRadius: 16,
    padding: 24,
  },
  snapshotLabel: {
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 4,
    color: colors.textFaint,
    marginBottom: 12,
  },
  snapshot: {
    fontFamily: fonts.mono,
    fontSize: 14,
    color: colors.text,
    lineHeight: 22,
  },
});
