// Shared route param types so screens can stay typed end-to-end.

export type LobbyPlayer = {
  puckId: number;
  color: string;
};

export type ScoreboardPlayer = {
  puckId: number;
  color: string;
  total: number;
  correct: number;
};

export type RootStackParamList = {
  Title: undefined;
  Pair: {
    code: string;
    progress: (number | null)[];
  };
  Lobby: {
    code: string;
    players: LobbyPlayer[];
    hostPuckId: number;
  };
  Scoreboard: {
    players: ScoreboardPlayer[];
    totalRounds: number;
  };
};
