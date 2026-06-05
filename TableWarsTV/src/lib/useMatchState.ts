import { useEffect, useReducer } from 'react';
import {
  reduce,
  INITIAL_STATE,
  type MatchRowState,
} from './matchSource';
import { createLocalSocketSource } from './localSocketSource';
import { createCloudRealtimeSource } from './cloudRealtimeSource';

// Local-first TV match state (ADR 0004). Renders from the venue Flask box
// over a LAN SocketIO connection (primary) and falls back to Supabase
// Realtime (cloud) when the local socket is down — reconciled by a monotonic
// snapshot_seq so failover never paints an older frame. The reconciliation
// rules live in the pure `reduce` (matchSource.ts); this hook just wires the
// two sources to it. Public shape is unchanged, so consuming screens don't
// change.

export type { MatchRowState } from './matchSource';

export function useMatchState(matchId: string | null): MatchRowState {
  const [state, dispatch] = useReducer(reduce, INITIAL_STATE);

  useEffect(() => {
    dispatch({ type: 'reset' });
    if (!matchId) return;

    const local = createLocalSocketSource(matchId);
    const cloud = createCloudRealtimeSource(matchId);

    local.start(
      (frame) => dispatch({ type: 'frame', frame: { ...frame, source: 'local' } }),
      (connected) => dispatch({ type: 'conn', source: 'local', connected }),
    );
    cloud.start(
      (frame) => dispatch({ type: 'frame', frame: { ...frame, source: 'cloud' } }),
      () => {},
    );

    return () => {
      local.stop();
      cloud.stop();
    };
  }, [matchId]);

  return state.row;
}
