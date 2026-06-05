import { CueDispatcher, CueEvent } from '../cues';

// Build a minimal cue. seq is the dedupe key; ts is display-only.
function cue(partial: Partial<CueEvent> & { seq: number }): CueEvent {
  return {
    cue: 'player_correct',
    target: null,
    channels: null,
    ts: 0,
    payload: {},
    ...partial,
  };
}

function collector() {
  const fired: CueEvent[] = [];
  const handler = (e: CueEvent) => fired.push(e);
  return { fired, handler };
}

describe('CueDispatcher seq watermark', () => {
  it('dispatches each cue once and skips re-delivered cues', () => {
    const d = new CueDispatcher();
    const { fired, handler } = collector();
    d.on('sfx', handler);

    d.ingest([cue({ seq: 0 }), cue({ seq: 1 })]);
    expect(fired).toHaveLength(2);

    // Same snapshot redelivered (Realtime is at-least-once) — no replay.
    d.ingest([cue({ seq: 0 }), cue({ seq: 1 })]);
    expect(fired).toHaveLength(2);

    // A genuinely new cue advances.
    d.ingest([cue({ seq: 2 })]);
    expect(fired).toHaveLength(3);
  });

  it('still dispatches when wall-clock ts runs backwards but seq increases', () => {
    // This is the regression: NTP step / container restart makes a later
    // cue have a SMALLER ts than an earlier one. A ts-based watermark
    // would swallow it forever; a seq-based one does not.
    const d = new CueDispatcher();
    const { fired, handler } = collector();
    d.on('sfx', handler);

    d.ingest([cue({ seq: 0, ts: 1_000_000 })]);
    expect(fired).toHaveLength(1);

    d.ingest([cue({ seq: 1, ts: 5 })]); // ts went backwards, seq forwards
    expect(fired).toHaveLength(2);
  });

  it('reset() clears the watermark so a new match replays from seq 0', () => {
    const d = new CueDispatcher();
    const { fired, handler } = collector();
    d.on('sfx', handler);

    d.ingest([cue({ seq: 0 }), cue({ seq: 1 })]);
    expect(fired).toHaveLength(2);

    d.reset();
    d.ingest([cue({ seq: 0 })]); // new match, seq restarts at 0
    expect(fired).toHaveLength(3);
  });

  it('broadcasts (channels null) to every registered channel', () => {
    const d = new CueDispatcher();
    const sfx = collector();
    const led = collector();
    d.on('sfx', sfx.handler);
    d.on('led', led.handler);

    d.ingest([cue({ seq: 0, channels: null })]);
    expect(sfx.fired).toHaveLength(1);
    expect(led.fired).toHaveLength(1);
  });

  it('routes a channel-scoped cue only to that channel', () => {
    const d = new CueDispatcher();
    const sfx = collector();
    const led = collector();
    d.on('sfx', sfx.handler);
    d.on('led', led.handler);

    d.ingest([cue({ seq: 0, channels: ['led'] })]);
    expect(sfx.fired).toHaveLength(0);
    expect(led.fired).toHaveLength(1);
  });

  it('dispatches seq-less cues (pre-seq snapshot) rather than swallowing them', () => {
    // A snapshot from before the server stamped seq still makes forward
    // progress via the synthetic index fallback. Cross-batch dedup is
    // impossible without a stable seq, but the server always stamps one
    // now, so the fallback only matters for the cutover window — its job
    // is just "fire, don't silently drop".
    const d = new CueDispatcher();
    const { fired, handler } = collector();
    d.on('sfx', handler);

    const legacy = [
      { cue: 'match_start', target: null, channels: null, ts: 1, payload: {} },
      { cue: 'round_start', target: null, channels: null, ts: 2, payload: {} },
    ] as unknown as CueEvent[];
    d.ingest(legacy);
    expect(fired).toHaveLength(2);

    // And a seq-stamped cue arriving after the fallback still advances.
    d.ingest([cue({ seq: 5 })]);
    expect(fired).toHaveLength(3);
  });
});
