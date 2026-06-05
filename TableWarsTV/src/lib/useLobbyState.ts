import { useEffect, useRef, useState } from 'react';
import { fetchLobbyState, type LobbyStateWire } from './runtimeApi';

// Polls /api/runtime/pair/lobby-state at 1 Hz.
//
// NOTE: as of the lobbies-realtime migration the PairingManager now ALSO
// publishes each lobby mutation to the Supabase `lobbies` table (location-
// scoped anon RLS), so a Realtime subscription is now possible and would
// remove this poll. The swap is deferred until the TV has a location-token
// + table-binding flow (it needs a location_id-claim token to read lobbies
// via anon RLS, the same mechanism as useMatchState's match token). Until
// then the poll is the working path; 1 Hz lands a pair request within one
// heartbeat while barely taxing Wi-Fi.

export type LobbyState = LobbyStateWire | { active: false; loading: boolean };

export function useLobbyState(intervalMs: number = 1000): LobbyState {
  const [state, setState] = useState<LobbyState>({ active: false, loading: true });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    async function poll() {
      const fresh = await fetchLobbyState();
      if (cancelled || !mountedRef.current) return;
      if (fresh === null) {
        // Keep last good state; mark loading false so screens stop
        // showing a spinner forever when the server is down.
        setState((prev) =>
          prev.active ? prev : { active: false, loading: false },
        );
      } else {
        setState(fresh);
      }
    }

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return state;
}
