import { useEffect, useRef, useState } from 'react';
import { supabase } from './supabase';

// Subscribes to a match's row in Supabase and surfaces the JSONB
// snapshot column plus the status field. The runtime writes the
// snapshot on every input that changes visible state + on
// finalisation; the TV picks it up via Realtime postgres_changes
// rather than polling the Flask endpoint.

export type MatchRowState = {
  status: 'lobby' | 'active' | 'finished' | 'abandoned';
  snapshot: Record<string, unknown> | null;
  startedAt: string | null;
  endedAt: string | null;
  loading: boolean;
};

const EMPTY: MatchRowState = {
  status: 'lobby',
  snapshot: null,
  startedAt: null,
  endedAt: null,
  loading: true,
};

export function useMatchState(matchId: string | null): MatchRowState {
  const [state, setState] = useState<MatchRowState>(EMPTY);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    if (!matchId) {
      setState(EMPTY);
      return;
    }

    // Initial fetch — the snapshot row exists from the moment the
    // match is created so we paint a real frame on first mount.
    void (async () => {
      const { data, error } = await supabase
        .from('matches')
        .select('status, snapshot, started_at, ended_at')
        .eq('id', matchId)
        .maybeSingle();
      if (!mountedRef.current) return;
      if (error || !data) {
        setState({ ...EMPTY, loading: false });
        return;
      }
      setState({
        status: data.status as MatchRowState['status'],
        snapshot: (data.snapshot as Record<string, unknown> | null) ?? null,
        startedAt: (data.started_at as string | null) ?? null,
        endedAt: (data.ended_at as string | null) ?? null,
        loading: false,
      });
    })();

    const channel = supabase
      .channel(`match:${matchId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'matches',
          filter: `id=eq.${matchId}`,
        },
        (payload) => {
          if (!mountedRef.current) return;
          const row = payload.new as {
            status?: MatchRowState['status'];
            snapshot?: Record<string, unknown> | null;
            started_at?: string | null;
            ended_at?: string | null;
          };
          setState((prev) => ({
            status: row.status ?? prev.status,
            snapshot:
              row.snapshot === undefined
                ? prev.snapshot
                : (row.snapshot ?? null),
            startedAt: row.started_at ?? prev.startedAt,
            endedAt: row.ended_at ?? prev.endedAt,
            loading: false,
          }));
        },
      )
      .subscribe();

    return () => {
      mountedRef.current = false;
      supabase.removeChannel(channel);
    };
  }, [matchId]);

  return state;
}
