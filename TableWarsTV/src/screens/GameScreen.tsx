import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type {
  NativeStackNavigationProp,
  NativeStackScreenProps,
} from '@react-navigation/native-stack';
import { colors, fonts } from '../theme';
import { useMatchState } from '../lib/useMatchState';
import { GameViewDispatcher } from './games';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Game'>;

// In-match TV view. Subscribes to matches.snapshot and delegates the
// actual rendering to GameViewDispatcher, which picks a per-game view
// based on snapshot.game_slug. Routes to Scoreboard on terminal status.

export function GameScreen({ route }: Props) {
  const { matchId } = route.params;
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const match = useMatchState(matchId);

  useEffect(() => {
    if (match.status === 'finished' || match.status === 'abandoned') {
      navigation.replace('Scoreboard', { matchId });
    }
  }, [match.status, matchId, navigation]);

  return (
    <View style={styles.root}>
      {match.loading || !match.snapshot ? (
        <Text style={styles.empty}>Waiting for first state update…</Text>
      ) : (
        <GameViewDispatcher snapshot={match.snapshot} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  empty: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 28,
    color: colors.textDim,
    textAlign: 'center',
    marginTop: 96,
  },
});
