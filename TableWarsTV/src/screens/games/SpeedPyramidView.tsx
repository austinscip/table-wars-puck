import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../../theme';
import type { SpeedPyramidSnapshot } from './types';
import { colorForPuck } from './types';

const LETTERS: Array<'A' | 'B' | 'C' | 'D'> = ['A', 'B', 'C', 'D'];

const TIER_COLOR: Record<string, string> = {
  LEGENDARY: colors.correct,
  EXPERT: colors.primary,
  AVERAGE: colors.accent,
  TIMEOUT: colors.textFaint,
  WRONG: colors.wrong,
};

export function SpeedPyramidView({ snapshot }: { snapshot: SpeedPyramidSnapshot }) {
  const q = snapshot.question;
  const scoreboard = Object.entries(snapshot.scores)
    .map(([puck, total]) => ({ puckIndex: Number(puck), total }))
    .sort((a, b) => b.total - a.total);

  return (
    <View style={styles.root}>
      <View style={styles.top}>
        <Text style={styles.round}>
          ROUND {snapshot.round_number} / {snapshot.total_rounds}
        </Text>
        {q?.category ? <Text style={styles.category}>{q.category}</Text> : null}
      </View>

      <View style={styles.middle}>
        <View style={styles.questionBlock}>
          {q ? (
            <>
              {q.setup ? <Text style={styles.setup}>{q.setup}</Text> : null}
              <Text style={styles.question}>{q.question}</Text>
              <View style={styles.answersGrid}>
                {LETTERS.map((letter) => (
                  <AnswerCell
                    key={letter}
                    letter={letter}
                    text={q.answers[letter]}
                    pickedBy={pickedBy(snapshot, letter)}
                  />
                ))}
              </View>
            </>
          ) : (
            <Text style={styles.empty}>Loading next question…</Text>
          )}
        </View>

        <View style={styles.scoreboard}>
          <Text style={styles.scoreboardLabel}>SCORES</Text>
          {scoreboard.length === 0 ? (
            <Text style={styles.empty}>—</Text>
          ) : (
            scoreboard.map(({ puckIndex, total }) => {
              const lockedRecord = snapshot.locked[String(puckIndex)];
              const tier = lockedRecord?.tier;
              return (
                <View key={puckIndex} style={styles.scoreRow}>
                  <View
                    style={[styles.scoreAvatar, { backgroundColor: colorForPuck(puckIndex) }]}>
                    <Text style={styles.scoreAvatarText}>{puckIndex}</Text>
                  </View>
                  <Text style={styles.scoreTotal}>{total.toLocaleString()}</Text>
                  {tier ? (
                    <Text style={[styles.tier, { color: TIER_COLOR[tier] ?? colors.text }]}>
                      {tier}
                    </Text>
                  ) : null}
                </View>
              );
            })
          )}
        </View>
      </View>
    </View>
  );
}

function pickedBy(snapshot: SpeedPyramidSnapshot, letter: string): number[] {
  const out: number[] = [];
  for (const [puck, locked] of Object.entries(snapshot.locked)) {
    if (locked.answer === letter) out.push(Number(puck));
  }
  return out;
}

function AnswerCell({
  letter,
  text,
  pickedBy,
}: {
  letter: string;
  text: string;
  pickedBy: number[];
}) {
  return (
    <View style={styles.answerCell}>
      <Text style={styles.answerLetter}>{letter}</Text>
      <Text style={styles.answerText} numberOfLines={2}>
        {text}
      </Text>
      {pickedBy.length > 0 ? (
        <View style={styles.pickedBy}>
          {pickedBy.map((p) => (
            <View key={p} style={[styles.pickerDot, { backgroundColor: colorForPuck(p) }]}>
              <Text style={styles.pickerText}>{p}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 48, gap: 32 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  round: {
    fontFamily: fonts.body,
    fontSize: 24,
    fontWeight: '700',
    letterSpacing: 6,
    color: colors.textDim,
  },
  category: {
    fontFamily: fonts.body,
    fontSize: 24,
    fontWeight: '700',
    letterSpacing: 6,
    color: colors.accent,
  },
  middle: { flex: 1, flexDirection: 'row', gap: 32 },
  questionBlock: { flex: 3, gap: 24 },
  setup: { fontFamily: fonts.body, fontSize: 22, color: colors.textDim },
  question: { fontFamily: fonts.display, fontSize: 52, color: colors.text, letterSpacing: -1, lineHeight: 60 },
  answersGrid: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', gap: 16 },
  answerCell: {
    width: '48%',
    minHeight: 110,
    padding: 20,
    borderRadius: 16,
    backgroundColor: 'rgba(248,250,252,0.06)',
    borderWidth: 2,
    borderColor: 'rgba(248,250,252,0.1)',
    gap: 8,
  },
  answerLetter: {
    fontFamily: fonts.display,
    fontSize: 28,
    color: colors.correct,
    letterSpacing: 4,
  },
  answerText: { fontFamily: fonts.body, fontSize: 22, color: colors.text, lineHeight: 28 },
  pickedBy: { flexDirection: 'row', gap: 6, position: 'absolute', right: 12, top: 12 },
  pickerDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickerText: { fontFamily: fonts.display, fontSize: 16, color: colors.bg },
  scoreboard: {
    flex: 1,
    padding: 16,
    borderRadius: 16,
    backgroundColor: 'rgba(248,250,252,0.04)',
    gap: 12,
  },
  scoreboardLabel: {
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 4,
    color: colors.textFaint,
  },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  scoreAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreAvatarText: { fontFamily: fonts.display, fontSize: 18, color: colors.bg },
  scoreTotal: { fontFamily: fonts.mono, fontSize: 22, fontWeight: '900', color: colors.text, flex: 1 },
  tier: { fontFamily: fonts.body, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
  empty: { fontFamily: fonts.body, fontSize: 18, color: colors.textDim },
});
