// Cue language mirror of server/runtime/cues.py. Keep these enum values
// in lockstep with the Python side; the runtime ships cue names in
// matches.snapshot.cues and the dispatcher matches on the string value.

export const Cue = {
  // Match lifecycle
  MATCH_START: 'match_start',
  MATCH_END: 'match_end',
  MATCH_RESET: 'match_reset',
  // Round structure
  ROUND_START: 'round_start',
  ROUND_END: 'round_end',
  ROUND_TRANSITION: 'round_transition',
  // Player events
  PLAYER_JOINED: 'player_joined',
  PLAYER_LEFT: 'player_left',
  PLAYER_CORRECT: 'player_correct',
  PLAYER_WRONG: 'player_wrong',
  PLAYER_TIMEOUT: 'player_timeout',
  PLAYER_LOCKED_IN: 'player_locked_in',
  PLAYER_ELIMINATED: 'player_eliminated',
  PLAYER_VICTORY: 'player_victory',
  // Score moments
  SCORE_GOLD: 'score_gold',
  SCORE_SILVER: 'score_silver',
  SCORE_BRONZE: 'score_bronze',
  SCORE_COMBO: 'score_combo',
  // Timer beats
  TIMER_TICK: 'timer_tick',
  TIMER_WARNING: 'timer_warning',
  TIMER_EXPIRED: 'timer_expired',
} as const;

export type CueName = (typeof Cue)[keyof typeof Cue];

export const CueChannel = {
  VO: 'vo',
  MUSIC: 'music',
  SFX: 'sfx',
  LED: 'led',
  MOTOR: 'motor',
  BUZZER: 'buzzer',
  HAPTIC: 'haptic',
} as const;

export type CueChannelName = (typeof CueChannel)[keyof typeof CueChannel];

export type CueEvent = {
  cue: CueName;
  target: number | null;
  channels: CueChannelName[] | null;
  ts: number;
  payload: Record<string, unknown>;
};

// === Dispatcher ===
//
// The TV diffs snapshot.cues across updates so it only fires new cue
// emissions. Each cue carries a server-side `ts`; we keep the highest
// `ts` we've seen and treat anything older as already dispatched.
//
// Subscribers register by channel; the dispatcher fans cue events out
// to every subscriber whose channel is in the cue's channels list (or
// to all subscribers when channels is null, meaning "broadcast").
//
// Audio playback library is intentionally not wired yet — react-native
// audio choice (sound vs track-player) gets decided when the first
// real cue lands. For now, subscribers receive the typed event and the
// audio handler is a stub the polish system can swap in.

export type CueHandler = (event: CueEvent) => void;

export class CueDispatcher {
  private handlers = new Map<CueChannelName, Set<CueHandler>>();
  private lastTs = 0;

  on(channel: CueChannelName, handler: CueHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);
    return () => this.handlers.get(channel)?.delete(handler);
  }

  // Call this every time matches.snapshot.cues changes. Cues older than
  // the highest ts we've seen are skipped.
  ingest(cues: CueEvent[]): void {
    if (!cues || cues.length === 0) return;
    const fresh = cues.filter((c) => c.ts > this.lastTs);
    if (fresh.length === 0) return;
    this.lastTs = Math.max(...fresh.map((c) => c.ts));
    for (const cue of fresh) {
      const targetChannels =
        cue.channels && cue.channels.length > 0
          ? cue.channels
          : (Array.from(this.handlers.keys()) as CueChannelName[]);
      for (const ch of targetChannels) {
        const set = this.handlers.get(ch);
        if (!set) continue;
        for (const handler of set) handler(cue);
      }
    }
  }

  // Reset on new match so old cues don't carry over.
  reset(): void {
    this.lastTs = 0;
  }
}
