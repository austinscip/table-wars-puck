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
  // Per-match monotonic sequence stamped by the MatchManager. This is the
  // dedupe key — it only ever increases, unlike `ts`.
  seq: number;
  // Wall-clock emission time (seconds). Display/debug only; NOT used for
  // dedupe because NTP steps / container restarts can run it backwards.
  ts: number;
  payload: Record<string, unknown>;
};

// === Dispatcher ===
//
// The TV diffs snapshot.cues across updates so it only fires new cue
// emissions. Each cue carries a server-side `seq` — a per-match monotonic
// counter — and we keep the highest `seq` we've seen, treating anything
// at or below it as already dispatched. We deliberately do NOT key off
// the wall-clock `ts`: an NTP adjustment or container restart can make a
// later cue's ts smaller than an earlier one's, which would stick the
// watermark high and silently swallow every subsequent cue.
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

// Sentinel below any real seq (which start at 0), so the first cue of a
// match is always fresh.
const NO_SEQ = -1;

export class CueDispatcher {
  private handlers = new Map<CueChannelName, Set<CueHandler>>();
  private lastSeq = NO_SEQ;

  on(channel: CueChannelName, handler: CueHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);
    return () => this.handlers.get(channel)?.delete(handler);
  }

  // Call this every time matches.snapshot.cues changes. Cues at or below
  // the highest seq we've seen are skipped (already dispatched). A cue
  // missing `seq` falls back to its array index within this batch so a
  // pre-seq server snapshot still dispatches once rather than never.
  ingest(cues: CueEvent[]): void {
    if (!cues || cues.length === 0) return;
    // Resolve a dedupe seq per cue up front (server-stamped seq, or a
    // synthetic fallback keyed off the ORIGINAL index for a pre-seq
    // snapshot) so the post-filter index shift can't corrupt it.
    const withSeq = cues.map((cue, i) => ({
      cue,
      seq: typeof cue.seq === 'number' ? cue.seq : this.lastSeq + 1 + i,
    }));
    const fresh = withSeq.filter((x) => x.seq > this.lastSeq);
    if (fresh.length === 0) return;
    this.lastSeq = Math.max(...fresh.map((x) => x.seq));
    for (const { cue } of fresh) {
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
    this.lastSeq = NO_SEQ;
  }
}
