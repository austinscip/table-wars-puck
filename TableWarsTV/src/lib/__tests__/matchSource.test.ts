import {
  reduce,
  seqOf,
  INITIAL_STATE,
  type SelectorState,
  type Frame,
  type SourceKind,
} from '../matchSource';

// Build a frame with a given source + seq (+ optional status/snapshot).
function frame(
  source: SourceKind,
  seq: number | null,
  extra: Partial<Omit<Frame, 'source'>> = {},
): Frame {
  return {
    source,
    status: 'active',
    snapshot: seq === null ? null : { snapshot_seq: seq, v: seq },
    startedAt: null,
    endedAt: null,
    ...extra,
  };
}

function applyFrame(state: SelectorState, f: Frame): SelectorState {
  return reduce(state, { type: 'frame', frame: f });
}

function conn(
  state: SelectorState,
  source: SourceKind,
  connected: boolean,
): SelectorState {
  return reduce(state, { type: 'conn', source, connected });
}

describe('matchSource.seqOf', () => {
  it('reads numeric snapshot_seq', () => {
    expect(seqOf({ snapshot_seq: 7 })).toBe(7);
  });
  it('is null for missing / non-numeric', () => {
    expect(seqOf(null)).toBeNull();
    expect(seqOf({})).toBeNull();
    expect(seqOf({ snapshot_seq: 'x' })).toBeNull();
  });
});

describe('matchSource.reduce — monotonic seq', () => {
  it('applies seq 0 from the initial state', () => {
    const s = applyFrame(INITIAL_STATE, frame('cloud', 0));
    expect(s.lastSeq).toBe(0);
    expect(s.row.loading).toBe(false);
    expect(s.row.snapshot).toEqual({ snapshot_seq: 0, v: 0 });
  });

  it('drops a frame whose seq is not strictly greater', () => {
    let s = applyFrame(INITIAL_STATE, frame('cloud', 5));
    s = applyFrame(s, frame('cloud', 5)); // equal — dropped
    s = applyFrame(s, frame('cloud', 3)); // older — dropped
    expect(s.lastSeq).toBe(5);
    expect((s.row.snapshot as { v: number }).v).toBe(5);
  });

  it('a seq-less frame always applies (status-only update)', () => {
    let s = applyFrame(INITIAL_STATE, frame('cloud', 4));
    s = applyFrame(s, frame('cloud', null, { status: 'finished' }));
    expect(s.row.status).toBe('finished');
    // lastSeq unchanged; the prior snapshot is preserved.
    expect(s.lastSeq).toBe(4);
    expect((s.row.snapshot as { v: number }).v).toBe(4);
  });
});

describe('matchSource.reduce — local-primary, cloud-fallback', () => {
  it('before local speaks, cloud fills the view', () => {
    let s = conn(INITIAL_STATE, 'local', true); // connected but silent
    s = applyFrame(s, frame('cloud', 1));
    expect(s.row.loading).toBe(false);
    expect((s.row.snapshot as { v: number }).v).toBe(1);
  });

  it('once local has spoken, cloud is ignored', () => {
    let s = conn(INITIAL_STATE, 'local', true);
    s = applyFrame(s, frame('local', 2)); // local takes authority
    const before = s.row.snapshot;
    s = applyFrame(s, frame('cloud', 3)); // newer cloud, but local wins
    expect(s.row.snapshot).toBe(before);
    expect(s.lastSeq).toBe(2);
  });

  it('failover: when local drops, cloud resumes and never goes backwards', () => {
    let s = conn(INITIAL_STATE, 'local', true);
    s = applyFrame(s, frame('local', 5));
    // Local drops.
    s = conn(s, 'local', false);
    expect(s.localConnected).toBe(false);
    expect(s.localHasFrame).toBe(false);
    // A stale cloud frame (<= lastSeq) must NOT paint over the newer local
    // frame the TV is still showing.
    s = applyFrame(s, frame('cloud', 4));
    expect(s.lastSeq).toBe(5);
    expect((s.row.snapshot as { v: number }).v).toBe(5);
    // Once cloud advances past the last local seq, it applies.
    s = applyFrame(s, frame('cloud', 6));
    expect((s.row.snapshot as { v: number }).v).toBe(6);
  });

  it('recovery: local reconnects, cloud fills the gap, then local retakes', () => {
    let s = conn(INITIAL_STATE, 'local', true);
    s = applyFrame(s, frame('local', 5));
    s = conn(s, 'local', false); // drop
    s = applyFrame(s, frame('cloud', 6)); // cloud advances during outage
    // Local reconnects but is briefly silent — cloud keeps filling.
    s = conn(s, 'local', true);
    expect(s.localHasFrame).toBe(false);
    s = applyFrame(s, frame('cloud', 7));
    expect((s.row.snapshot as { v: number }).v).toBe(7);
    // Local speaks again (its seq has caught up past cloud) — local retakes.
    s = applyFrame(s, frame('local', 8));
    expect(s.localHasFrame).toBe(true);
    s = applyFrame(s, frame('cloud', 9)); // ignored now
    expect((s.row.snapshot as { v: number }).v).toBe(8);
  });

  it('a stale local frame still flips authority to local', () => {
    // Cloud got ahead while local was reconnecting; local then delivers an
    // older-seq frame. It is not rendered (monotonic), but it proves local
    // is alive, so subsequent cloud frames are suppressed.
    let s = conn(INITIAL_STATE, 'local', true);
    s = applyFrame(s, frame('cloud', 10)); // gap-fill
    s = applyFrame(s, frame('local', 9)); // stale, not rendered...
    expect((s.row.snapshot as { v: number }).v).toBe(10);
    expect(s.localHasFrame).toBe(true); // ...but authority flipped
    s = applyFrame(s, frame('cloud', 11)); // now ignored
    expect((s.row.snapshot as { v: number }).v).toBe(10);
  });
});

describe('matchSource.reduce — misc', () => {
  it('reset returns the initial state', () => {
    let s = applyFrame(INITIAL_STATE, frame('local', 3));
    s = reduce(s, { type: 'reset' });
    expect(s).toEqual(INITIAL_STATE);
  });

  it('cloud connection transitions never gate the selector', () => {
    const s = conn(INITIAL_STATE, 'cloud', true);
    expect(s).toEqual(INITIAL_STATE);
  });

  it('keeps the prior snapshot when a frame carries none', () => {
    let s = applyFrame(INITIAL_STATE, frame('cloud', 1));
    s = applyFrame(s, {
      source: 'cloud',
      status: 'abandoned',
      snapshot: null,
      startedAt: null,
      endedAt: null,
    });
    expect(s.row.status).toBe('abandoned');
    expect((s.row.snapshot as { v: number }).v).toBe(1);
  });
});
