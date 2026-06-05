import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type {
  NativeStackNavigationProp,
  NativeStackScreenProps,
} from '@react-navigation/native-stack';
import { colors, fonts } from '../theme';
import { supabase } from '../lib/supabase';
import { useMatchState } from '../lib/useMatchState';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Scoreboard'>;

// Auto-return-to-title timeout. Matches the previous SpeedPyramid
// scoreboard behaviour — a bar TV must not park on a finished
// match forever or the attract loop never gets back on screen.
const AUTO_RETURN_MS = 30_000;

type FinalRow = {
  puckIndex: number;
  color: string;
  total: number;
};

export function ScoreboardScreen({ route }: Props) {
  const { matchId } = route.params;
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const match = useMatchState(matchId);
  const [rows, setRows] = useState<FinalRow[]>([]);

  // Pull the final scores written by MatchManager._finalize. These
  // live in the scores table with event_type='final'; the runtime
  // guarantees one row per puck via uniq_final_score_per_match_puck.
  useEffect(() => {
    void (async () => {
      const { data } = await supabase
        .from('scores')
        .select(
          `
          score_total,
          match_pucks (
            pucks ( puck_index )
          )
        `,
        )
        .eq('match_id', matchId)
        .eq('event_type', 'final')
        .order('score_total', { ascending: false });
      if (!data) return;
      const next: FinalRow[] = data.flatMap((row) => {
        const mp = row.match_pucks as
          | { pucks?: { puck_index?: number } | { puck_index?: number }[] | null }
          | { pucks?: { puck_index?: number } | { puck_index?: number }[] | null }[]
          | null;
        const mpFirst = Array.isArray(mp) ? mp[0] : mp;
        const pucks = mpFirst?.pucks;
        const puckRow = Array.isArray(pucks) ? pucks[0] : pucks;
        const puckIndex = puckRow?.puck_index ?? null;
        if (puckIndex == null) return [];
        return [
          {
            puckIndex,
            color: colorForPuckIndex(puckIndex),
            total: row.score_total as number,
          },
        ];
      });
      setRows(next);
    })();
  }, [matchId]);

  useEffect(() => {
    const t = setTimeout(() => {
      navigation.navigate('Title');
    }, AUTO_RETURN_MS);
    return () => clearTimeout(t);
  }, [navigation]);

  const slug = (match.snapshot as { game_slug?: string } | null)?.game_slug;

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>MATCH COMPLETE</Text>
      {slug ? <Text style={styles.subheading}>{slug}</Text> : null}
      <View style={styles.list}>
        {rows.length === 0 ? (
          <Text style={styles.empty}>Tallying scores…</Text>
        ) : (
          rows.map((p, i) => {
            const isWinner = i === 0;
            return (
              <View
                key={p.puckIndex}
                style={[styles.row, isWinner && styles.rowWinner]}>
                <View style={[styles.avatar, { backgroundColor: p.color }]}>
                  <Text style={styles.avatarText}>{p.puckIndex}</Text>
                </View>
                <View style={styles.middle}>
                  <Text style={styles.playerLabel}>
                    {isWinner ? '👑 ' : ''}Puck #{p.puckIndex}
                  </Text>
                </View>
                <Text style={styles.score}>{p.total.toLocaleString()}</Text>
              </View>
            );
          })
        )}
      </View>
      <Text style={styles.footer}>Tap a puck to play again · Hold to switch players</Text>
    </View>
  );
}

// Mirrors server/runtime/pairing.PUCK_PALETTE so the scoreboard colors
// match the lobby avatars without a separate lookup. Keep these in sync.
const PALETTE: Record<number, string> = {
  1: '#3B82F6',
  2: '#EC4899',
  3: '#FBBF24',
  4: '#10B981',
  5: '#A855F7',
  6: '#F97316',
  7: '#06B6D4',
  8: '#EF4444',
};

function colorForPuckIndex(puckIndex: number): string {
  return PALETTE[puckIndex] ?? '#F8FAFC';
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 64,
    gap: 24,
  },
  heading: {
    fontFamily: fonts.display,
    fontSize: 128,
    fontWeight: '900',
    color: colors.correct,
    letterSpacing: -2,
  },
  subheading: {
    fontFamily: fonts.body,
    fontSize: 24,
    color: colors.textDim,
    letterSpacing: 4,
    textTransform: 'uppercase',
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
  score: { fontFamily: fonts.mono, fontSize: 72, fontWeight: '900', color: colors.text },
  footer: { fontFamily: fonts.body, fontSize: 20, color: colors.textDim },
});
