import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

type Props = {
  code: string;
  progress?: (number | null)[];
  activeSlot?: number;
};

// 6-digit pair code with optional per-digit progress lighting up as the
// host dials. Skeleton only — full dial animation comes later.
export function PairCodeDisplay({ code, progress, activeSlot }: Props) {
  const digits = code.split('');
  return (
    <View style={styles.row}>
      {digits.map((d, i) => {
        const locked = progress?.[i] != null;
        const active = i === activeSlot && !locked;
        return (
          <View
            key={i}
            style={[
              styles.cell,
              locked && styles.cellLocked,
              active && styles.cellActive,
            ]}>
            <Text style={[styles.digit, locked && styles.digitLocked]}>{d}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 16 },
  cell: {
    width: 96,
    height: 128,
    borderRadius: 16,
    borderWidth: 3,
    borderColor: 'rgba(248,250,252,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cellActive: { borderColor: colors.primary },
  cellLocked: { borderColor: colors.correct, backgroundColor: 'rgba(251,191,36,0.08)' },
  digit: {
    fontFamily: fonts.mono,
    fontSize: 72,
    fontWeight: '700',
    color: colors.text,
  },
  digitLocked: { color: colors.correct },
});
