import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { BreathingDots } from '../components/BreathingDots';
import { colors, fonts } from '../theme';
import { useLobbyState } from '../lib/useLobbyState';
import type { RootStackParamList } from '../navigation';

// Idle threshold before the TV drops to attract mode. Picked at ~30s so
// it's long enough that a puck-pair flow can fail and retry without
// losing context, short enough that an empty bar TV doesn't sit dark.
const IDLE_MS = 30_000;

export function TitleScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const lobby = useLobbyState(1000);

  // Idle -> Attract.
  useEffect(() => {
    const timer = setTimeout(() => {
      navigation.navigate('Attract');
    }, IDLE_MS);
    return () => clearTimeout(timer);
  }, [navigation]);

  // Active lobby -> Pair (host dial in progress) or Lobby (others
  // joining). The Pair screen is where the host's live dial mirror
  // renders; Lobby is the waiting room once any puck has confirmed.
  useEffect(() => {
    if (!lobby.active) return;
    if (lobby.players.length === 0) {
      navigation.navigate('Pair', {
        code: lobby.code,
        progress: [null, null, null, null, null, null],
      });
    } else {
      const lobbyPlayers = lobby.players.map((p) => ({
        puckId: p.puck_index,
        color: p.color,
      }));
      navigation.navigate('Lobby', {
        code: lobby.code,
        players: lobbyPlayers,
        hostPuckId: lobby.host_puck_index,
      });
    }
  }, [lobby, navigation]);

  return (
    <View style={styles.root}>
      <Text style={styles.wordmark}>TABLE WARS</Text>
      <Text style={styles.subtitle}>Hold the puck button to pair.</Text>
      <BreathingDots />
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
  },
  wordmark: {
    fontFamily: fonts.display,
    fontSize: 160,
    fontWeight: '900',
    letterSpacing: -4,
    color: colors.text,
    textShadowColor: 'rgba(251,191,36,0.22)',
    textShadowRadius: 40,
  },
  subtitle: {
    fontFamily: fonts.body,
    fontSize: 32,
    fontWeight: '500',
    color: colors.textDim,
    marginTop: 40,
  },
});
