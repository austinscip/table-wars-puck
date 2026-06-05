import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, fonts } from '../theme';
import { useLobbyState } from '../lib/useLobbyState';
import type { RootStackParamList } from '../navigation';

// Live lobby. Reads from the polling hook directly instead of
// route.params so the screen stays in sync if the lobby grows /
// shrinks / starts a match while we're already mounted.

export function LobbyScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const lobby = useLobbyState(1000);

  // When the host taps start, the runtime sets match_id. Hand off to
  // the in-match GameScreen which subscribes to matches.snapshot.
  useEffect(() => {
    if (lobby.active && lobby.match_id) {
      navigation.navigate('Game', { matchId: lobby.match_id });
    }
  }, [lobby, navigation]);

  // Lobby cleared (host cancelled, ttl expired, server bounced) ->
  // back to Title so attract / idle paths take over.
  useEffect(() => {
    if (!('loading' in lobby) && !lobby.active) {
      navigation.navigate('Title');
    }
  }, [lobby, navigation]);

  if (!lobby.active) {
    return (
      <View style={styles.root}>
        <Text style={styles.heading}>LOBBY</Text>
        <Text style={styles.empty}>Waiting for a puck to start pairing…</Text>
      </View>
    );
  }

  const players = lobby.players;
  const hostPuckIndex = lobby.host_puck_index;

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>LOBBY</Text>

      <View style={styles.codeBlock}>
        <Text style={styles.codeLabel}>Code to join</Text>
        <Text style={styles.code}>{lobby.code}</Text>
      </View>

      <View style={styles.playersBlock}>
        <Text style={styles.playersLabel}>
          {players.length === 0
            ? 'Waiting for first player…'
            : `${players.length} player${players.length === 1 ? '' : 's'} joined`}
        </Text>
        <View style={styles.playersRow}>
          {players.map((p) => (
            <View key={p.puck_index} style={styles.playerCol}>
              <View style={[styles.avatar, { backgroundColor: p.color }]}>
                <Text style={styles.avatarText}>{p.puck_index}</Text>
              </View>
              <Text style={styles.playerName}>
                {p.puck_index === hostPuckIndex
                  ? `Puck ${p.puck_index} · HOST`
                  : `Puck ${p.puck_index}`}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {players.length > 0 && (
        <View style={styles.hints}>
          <Text style={styles.hintPrimary}>
            Host (Puck {hostPuckIndex}): tap your puck to start
          </Text>
          <Text style={styles.hintSecondary}>
            Other players: hold your puck button for 1 second to join
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
    alignItems: 'center',
    justifyContent: 'center',
    gap: 48,
    padding: 64,
  },
  heading: {
    fontFamily: fonts.display,
    fontSize: 96,
    fontWeight: '900',
    color: colors.text,
    letterSpacing: -2,
  },
  empty: { fontFamily: fonts.body, fontSize: 24, color: colors.textDim },
  codeBlock: { alignItems: 'center', gap: 12 },
  codeLabel: {
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: '500',
    letterSpacing: 4,
    textTransform: 'uppercase',
    color: colors.textFaint,
  },
  code: {
    fontFamily: fonts.mono,
    fontSize: 112,
    fontWeight: '900',
    letterSpacing: 12,
    color: colors.text,
  },
  playersBlock: { alignItems: 'center', gap: 12 },
  playersLabel: {
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: '500',
    letterSpacing: 4,
    textTransform: 'uppercase',
    color: colors.textFaint,
  },
  playersRow: { flexDirection: 'row', gap: 24, flexWrap: 'wrap', justifyContent: 'center' },
  playerCol: { alignItems: 'center', gap: 8 },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontFamily: fonts.display, fontSize: 48, color: colors.text },
  playerName: { fontFamily: fonts.body, fontSize: 18, color: colors.textDim },
  hints: { alignItems: 'center', gap: 8 },
  hintPrimary: { fontFamily: fonts.body, fontSize: 20, color: colors.textDim },
  hintSecondary: { fontFamily: fonts.body, fontSize: 18, color: colors.textFaint },
});
