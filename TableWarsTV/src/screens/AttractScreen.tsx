import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, fonts } from '../theme';
import { useLeaderboardRotation } from '../lib/leaderboard';
import { supabase } from '../lib/supabase';
import { LOCATION_ID } from '../config';
import type { RootStackParamList } from '../navigation';

// Attract mode — what the TV shows when no one is playing. Cycles a
// top-5 leaderboard across day / week / all_time periods. Switches
// back to Title the instant any match (lobby or active) appears at
// this location, so a puck button-hold wakes the screen up.

const PERIOD_LABEL: Record<string, string> = {
  day: "TODAY'S TOP",
  week: 'THIS WEEK',
  month: 'THIS MONTH',
  all_time: 'ALL TIME',
};

export function AttractScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { period, rows } = useLeaderboardRotation(['day', 'week', 'all_time'], {
    gameSlug: 'speed_pyramid',
    limit: 5,
    rotateMs: 12_000,
  });

  // Realtime watchdog: any new match at this location flips us back to
  // Title so the pair flow can take over. Existing matches that flip
  // to active also count.
  useEffect(() => {
    const channel = supabase
      .channel(`attract:${LOCATION_ID}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'matches',
          filter: `location_id=eq.${LOCATION_ID}`,
        },
        (payload) => {
          const row = (payload.new ?? payload.old) as { status?: string };
          if (row?.status === 'lobby' || row?.status === 'active') {
            navigation.navigate('Title');
          }
        },
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [navigation]);

  // Breathing "pick up the puck" prompt.
  const promptOpacity = useRef(new Animated.Value(0.5)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(promptOpacity, {
          toValue: 1,
          duration: 1400,
          useNativeDriver: true,
        }),
        Animated.timing(promptOpacity, {
          toValue: 0.5,
          duration: 1400,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [promptOpacity]);

  return (
    <View style={styles.root}>
      <View style={styles.top}>
        <Text style={styles.brand}>TABLE WARS</Text>
        <Text style={styles.tagline}>Speed Pyramid · live at this bar</Text>
      </View>

      <View style={styles.middle}>
        <Text style={styles.periodLabel}>{PERIOD_LABEL[period] ?? period.toUpperCase()}</Text>
        <View style={styles.list}>
          {rows.length === 0 ? (
            <Text style={styles.empty}>No scores yet. Be the first.</Text>
          ) : (
            rows.map((r, i) => (
              <View key={`${r.puckId}-${r.gameSlug}`} style={styles.row}>
                <Text style={styles.rank}>{i + 1}</Text>
                <Text style={styles.name}>
                  Puck {r.puckIndex ?? '?'}
                </Text>
                <Text style={styles.score}>{r.highScore.toLocaleString()}</Text>
              </View>
            ))
          )}
        </View>
      </View>

      <Animated.View style={[styles.bottom, { opacity: promptOpacity }]}>
        <Text style={styles.prompt}>Pick up a puck to play.</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    justifyContent: 'space-between',
    paddingHorizontal: 96,
    paddingVertical: 64,
  },
  top: { alignItems: 'center', gap: 12 },
  brand: {
    fontFamily: fonts.display,
    fontSize: 96,
    fontWeight: '900',
    color: colors.text,
    letterSpacing: -2,
  },
  tagline: {
    fontFamily: fonts.body,
    fontSize: 24,
    color: colors.textDim,
    letterSpacing: 4,
    textTransform: 'uppercase',
  },
  middle: { alignItems: 'center', gap: 28 },
  periodLabel: {
    fontFamily: fonts.body,
    fontSize: 28,
    fontWeight: '700',
    color: colors.correct,
    letterSpacing: 6,
    textTransform: 'uppercase',
  },
  list: { gap: 18, width: '100%', maxWidth: 900 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 32,
    paddingHorizontal: 32,
    paddingVertical: 18,
    borderRadius: 16,
    backgroundColor: 'rgba(248,250,252,0.05)',
  },
  rank: {
    fontFamily: fonts.display,
    fontSize: 48,
    color: colors.correct,
    width: 64,
  },
  name: {
    fontFamily: fonts.display,
    fontSize: 36,
    color: colors.text,
    flex: 1,
  },
  score: {
    fontFamily: fonts.mono,
    fontSize: 48,
    fontWeight: '900',
    color: colors.text,
  },
  empty: {
    fontFamily: fonts.body,
    fontSize: 28,
    color: colors.textDim,
    textAlign: 'center',
  },
  bottom: { alignItems: 'center' },
  prompt: {
    fontFamily: fonts.body,
    fontSize: 32,
    fontWeight: '500',
    color: colors.text,
    letterSpacing: 2,
  },
});
