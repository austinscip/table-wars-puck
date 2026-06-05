import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'react-native';
import { TitleScreen } from './src/screens/TitleScreen';
import { AttractScreen } from './src/screens/AttractScreen';
import { PairScreen } from './src/screens/PairScreen';
import { LobbyScreen } from './src/screens/LobbyScreen';
import { ScoreboardScreen } from './src/screens/ScoreboardScreen';
import type { RootStackParamList } from './src/navigation';
import { colors } from './src/theme';

const Stack = createNativeStackNavigator<RootStackParamList>();

const navTheme = {
  dark: true,
  colors: {
    primary: colors.primary,
    background: colors.bg,
    card: colors.bg,
    text: colors.text,
    border: 'transparent',
    notification: colors.accent,
  },
  fonts: {
    regular: { fontFamily: 'System', fontWeight: '400' as const },
    medium: { fontFamily: 'System', fontWeight: '500' as const },
    bold: { fontFamily: 'System', fontWeight: '700' as const },
    heavy: { fontFamily: 'System', fontWeight: '900' as const },
  },
};

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg} hidden />
      <NavigationContainer theme={navTheme}>
        <Stack.Navigator
          initialRouteName="Title"
          screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
          <Stack.Screen name="Title" component={TitleScreen} />
          <Stack.Screen name="Attract" component={AttractScreen} />
          <Stack.Screen
            name="Pair"
            component={PairScreen}
            initialParams={{ code: '482917', progress: [null, null, null, null, null, null] }}
          />
          <Stack.Screen
            name="Lobby"
            component={LobbyScreen}
            initialParams={{ code: '482917', players: [], hostPuckId: 1 }}
          />
          <Stack.Screen
            name="Scoreboard"
            component={ScoreboardScreen}
            initialParams={{ players: [], totalRounds: 0 }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
