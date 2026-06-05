import { useEffect, useRef, useState } from 'react';
import { fetchLobbyState, type LobbyStateWire } from './runtimeApi';

// Polls /api/runtime/pair/lobby-state at 1 Hz. The lobby lives in Flask
// process memory (not Supabase), so Realtime postgres_changes can't
// reach it. 1 Hz is fast enough that a puck's pair request lands on
// the TV within one heartbeat and slow enough that an idle TV barely
// taxes Wi-Fi.

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
