// Per-game snapshot shapes. Mirror server/games/<slug>.py get_state().
// The dispatcher in GameScreen narrows by game_slug before passing
// snapshot to a view.

export type SpeedPyramidSnapshot = {
  game_slug: 'speed_pyramid';
  round_number: number;
  total_rounds: number;
  round_elapsed_ms: number;
  question: {
    id: number;
    setup: string;
    question: string;
    answers: { A: string; B: string; C: string; D: string };
    category: string;
    time_limit_ms: number;
  } | null;
  selected: Record<string, 'A' | 'B' | 'C' | 'D' | null>;
  locked: Record<
    string,
    {
      answer: string | null;
      is_correct: boolean;
      tier: string;
      points: number;
      response_time_ms: number;
    }
  >;
  scores: Record<string, number>;
  finished: boolean;
};

export type PuckGolfSnapshot = {
  game_slug: 'puck_golf';
  hole_number: number | null;
  hole_par: number | null;
  hole_distance: number | null;
  hole_radius: number | null;
  current_turn_puck_index: number | null;
  finished: boolean;
  players: {
    puck_index: number;
    aim: { x: number; y: number };
    power: number;
    ball: { x: number; y: number };
    distance_remaining: number;
    hole_strokes: number;
    hole_done: boolean;
    total_strokes: number;
  }[];
};

export type PuckRacerSnapshot = {
  game_slug: 'puck_racer';
  race_time_sec: number;
  race_seconds: number;
  finish_distance: number;
  first_finish_time: number | null;
  finished: boolean;
  racers: {
    puck_index: number;
    lane: number;
    lane_name: string;
    position: number;
    speed: number;
    throttle_held: boolean;
    boosts_remaining: number;
    boost_active: boolean;
    finished: boolean;
    finish_time_sec: number | null;
  }[];
};

export type SmashSnapshot = {
  game_slug: 'smash';
  match_time_sec: number;
  match_seconds: number;
  arena: { x: [number, number]; y: [number, number] };
  finished: boolean;
  winner_index: number | null;
  fighters: {
    puck_index: number;
    x: number;
    y: number;
    damage_pct: number;
    stocks: number;
    facing: { x: number; y: number };
    kos_landed: number;
    eliminated: boolean;
    special_ready_in_sec: number;
  }[];
};

export type AnyGameSnapshot =
  | SpeedPyramidSnapshot
  | PuckGolfSnapshot
  | PuckRacerSnapshot
  | SmashSnapshot;

// Mirrors server/runtime/pairing.PUCK_PALETTE so views colour player
// avatars consistently with the lobby + scoreboard.
export const PUCK_PALETTE: Record<number, string> = {
  1: '#3B82F6',
  2: '#EC4899',
  3: '#FBBF24',
  4: '#10B981',
  5: '#A855F7',
  6: '#F97316',
  7: '#06B6D4',
  8: '#EF4444',
};

export function colorForPuck(puckIndex: number): string {
  return PUCK_PALETTE[puckIndex] ?? '#F8FAFC';
}
