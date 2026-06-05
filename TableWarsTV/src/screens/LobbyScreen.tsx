import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Lobby'>;

export function LobbyScreen({ route }: Props) {
  const { code, players, hostPuckId } = route.params;

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>LOBBY</Text>

      <View style={styles.codeBlock}>
        <Text style={styles.codeLabel}>Code to join</Text>
        <Text style={styles.code}>{code}</Text>
      </View>

      <View style={styles.playersBlock}>
        <Text style={styles.playersLabel}>
          {players.length === 0
            ? 'Waiting for first player…'
            : `${players.length} player${players.length === 1 ? '' : 's'} joined`}
        </Text>
        <View style={styles.playersRow}>
          {players.map((p) => (
            <View key={p.puckId} style={styles.playerCol}>
              <View style={[styles.avatar, { backgroundColor: p.color }]}>
                <Text style={styles.avatarText}>{p.puckId}</Text>
              </View>
              <Text style={styles.playerName}>
                {p.puckId === hostPuckId ? `Puck ${p.puckId} · HOST` : `Puck ${p.puckId}`}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {players.length > 0 && (
        <View style={styles.hints}>
          <Text style={styles.hintPrimary}>
            Host (Puck {hostPuckId}): tap your puck to start
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
