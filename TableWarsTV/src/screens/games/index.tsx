import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../../theme';
import { SpeedPyramidView } from './SpeedPyramidView';
import { PuckGolfView } from './PuckGolfView';
import { PuckRacerView } from './PuckRacerView';
import { SmashView } from './SmashView';
import type { AnyGameSnapshot } from './types';

// Slug dispatcher. GameScreen receives raw matches.snapshot from the
// useMatchState hook; this narrows by game_slug and renders the
// matching per-game view. Unknown / missing slugs fall back to a
// debug JSON dump so we can see what landed.

export function GameViewDispatcher({ snapshot }: { snapshot: unknown }) {
  if (!snapshot || typeof snapshot !== 'object') {
    return <Fallback note="No snapshot." raw={snapshot} />;
  }
  const slug = (snapshot as { game_slug?: string }).game_slug;
  switch (slug) {
    case 'speed_pyramid':
      return <SpeedPyramidView snapshot={snapshot as AnyGameSnapshot & { game_slug: 'speed_pyramid' }} />;
    case 'puck_golf':
      return <PuckGolfView snapshot={snapshot as AnyGameSnapshot & { game_slug: 'puck_golf' }} />;
    case 'puck_racer':
      return <PuckRacerView snapshot={snapshot as AnyGameSnapshot & { game_slug: 'puck_racer' }} />;
    case 'smash':
      return <SmashView snapshot={snapshot as AnyGameSnapshot & { game_slug: 'smash' }} />;
    default:
      return <Fallback note={`Unknown game_slug: ${slug ?? 'missing'}`} raw={snapshot} />;
  }
}

function Fallback({ note, raw }: { note: string; raw: unknown }) {
  return (
    <View style={styles.root}>
      <Text style={styles.note}>{note}</Text>
      <Text style={styles.code}>{JSON.stringify(raw, null, 2)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 32, gap: 16 },
  note: { fontFamily: fonts.body, fontSize: 18, color: colors.textDim },
  code: { fontFamily: fonts.mono, fontSize: 14, color: colors.text },
});
