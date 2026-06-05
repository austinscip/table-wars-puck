// Source-selector core for the local-first TV data path (ADR 0004).
//
// The TV renders match state from two sources behind one interface:
//   - a LOCAL Flask-SocketIO connection on the venue LAN (primary), and
//   - Supabase Realtime over the cloud (fallback).
//
// This module is the pure reconciliation reducer that decides which frame
// to render. It has no transport dependency so it is exhaustively unit-
// testable. The rules:
//
//   1. Local wins whenever the local socket is connected AND has delivered
//      at least one frame on the current connection. While local is the
//      authority, cloud frames are ignored. Before local's first frame (or
//      after it drops) cloud fills in, so a cold/reconnecting local socket
//      never blanks the TV.
//   2. A monotonic `snapshot_seq` guards against rendering an older frame
//      over a newer one on failover in either direction — a frame whose seq
//      is not strictly greater than the last applied seq is dropped. Frames
//      with no seq (a status-only / pre-seq update) always apply.

export type MatchStatus = 'lobby' | 'active' | 'finished' | 'abandoned';

export type MatchRowState = {
  status: MatchStatus;
  snapshot: Record<string, unknown> | null;
  startedAt: string | null;
  endedAt: string | null;
  loading: boolean;
};

export type SourceKind = 'local' | 'cloud';

// A frame as emitted by a source, before the selector tags its origin.
export type SourceFrame = {
  status: MatchStatus;
  snapshot: Record<string, unknown> | null;
  startedAt: string | null;
  endedAt: string | null;
};

export type Frame = SourceFrame & { source: SourceKind };

// A transport behind the selector. start() begins delivering frames and
// (for local) connection transitions; stop() tears everything down. A
// source that can't connect (e.g. the local socket dep isn't installed)
// simply reports connected=false and delivers no frames — the selector then
// renders the other source.
export type MatchSource = {
  start(
    onFrame: (frame: SourceFrame) => void,
    onConn: (connected: boolean) => void,
  ): void;
  stop(): void;
};

export type SelectorState = {
  localConnected: boolean;
  // Whether local has delivered a frame on the CURRENT connection. Reset on
  // every local (re)connect/disconnect so a freshly-(re)connected but silent
  // local socket lets cloud fill the gap until local speaks again.
  localHasFrame: boolean;
  lastSeq: number; // highest applied snapshot_seq; -1 so seq 0 applies
  row: MatchRowState;
};

export type SelectorEvent =
  | { type: 'reset' }
  | { type: 'conn'; source: SourceKind; connected: boolean }
  | { type: 'frame'; frame: Frame };

export const EMPTY_ROW: MatchRowState = {
  status: 'lobby',
  snapshot: null,
  startedAt: null,
  endedAt: null,
  loading: true,
};

export const INITIAL_STATE: SelectorState = {
  localConnected: false,
  localHasFrame: false,
  lastSeq: -1,
  row: EMPTY_ROW,
};

// Extract the monotonic snapshot seq the runtime stamps on every frame
// (server: Match.snapshot_seq, inside the snapshot payload). Missing/non-
// numeric => null (treated as "always apply", e.g. a pre-seq status update).
export function seqOf(snapshot: Record<string, unknown> | null): number | null {
  const v = snapshot?.snapshot_seq;
  return typeof v === 'number' ? v : null;
}

export function reduce(
  state: SelectorState,
  event: SelectorEvent,
): SelectorState {
  switch (event.type) {
    case 'reset':
      return INITIAL_STATE;

    case 'conn': {
      // Only the local connection gates the selector; cloud "connection"
      // never suppresses anything. Reset localHasFrame so a (re)connected
      // local socket must deliver a fresh frame before it suppresses cloud.
      if (event.source !== 'local') return state;
      return {
        ...state,
        localConnected: event.connected,
        localHasFrame: false,
      };
    }

    case 'frame': {
      const { frame } = event;

      // Local wins: once local is connected and has spoken, ignore cloud.
      if (
        frame.source === 'cloud' &&
        state.localConnected &&
        state.localHasFrame
      ) {
        return state;
      }

      // Monotonic guard: never render an older frame over a newer one.
      const seq = seqOf(frame.snapshot);
      if (seq !== null && seq <= state.lastSeq) {
        // Still note that local produced a frame on this connection, so a
        // stale-but-present local frame flips authority to local.
        if (frame.source === 'local' && !state.localHasFrame) {
          return { ...state, localHasFrame: true };
        }
        return state;
      }

      return {
        ...state,
        lastSeq: seq !== null ? seq : state.lastSeq,
        localHasFrame:
          frame.source === 'local' ? true : state.localHasFrame,
        row: {
          status: frame.status,
          // Keep the last snapshot if this frame carries none (e.g. a
          // lobby/status-only update) so we never blank a live view.
          snapshot: frame.snapshot ?? state.row.snapshot,
          startedAt: frame.startedAt ?? state.row.startedAt,
          endedAt: frame.endedAt ?? state.row.endedAt,
          loading: false,
        },
      };
    }

    default:
      return state;
  }
}
