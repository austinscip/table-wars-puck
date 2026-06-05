import { StyleSheet, Text, View } from 'react-native';
import { BreathingDots } from '../components/BreathingDots';
import { colors, fonts } from '../theme';

export function TitleScreen() {
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
