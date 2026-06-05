import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { BreathingDots } from '../components/BreathingDots';
import { colors, fonts } from '../theme';
import type { RootStackParamList } from '../navigation';

// Idle threshold before the TV drops to attract mode. Picked at ~30s so
// it's long enough that a puck-pair flow can fail and retry without
// losing context, short enough that an empty bar TV doesn't sit dark.
const IDLE_MS = 30_000;

export function TitleScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  useEffect(() => {
    const timer = setTimeout(() => {
      navigation.navigate('Attract');
    }, IDLE_MS);
    return () => clearTimeout(timer);
  }, [navigation]);

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
