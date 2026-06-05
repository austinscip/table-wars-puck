import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { StyleSheet, Text, View } from 'react-native';
import { PairCodeDisplay } from '../components/PairCodeDisplay';
import { colors, fonts } from '../theme';
import type { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Pair'>;

export function PairScreen({ route }: Props) {
  const { code, progress } = route.params;
  const activeSlot = progress.findIndex((d) => d == null);
  return (
    <View style={styles.root}>
      <Text style={styles.heading}>DIAL TO START</Text>
      <PairCodeDisplay code={code} progress={progress} activeSlot={activeSlot < 0 ? 6 : activeSlot} />
      <Text style={styles.hint}>
        Hold the puck button for one second, then tilt up/down to dial each digit.
      </Text>
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
  hint: {
    fontFamily: fonts.body,
    fontSize: 24,
    color: colors.textDim,
    textAlign: 'center',
  },
});
