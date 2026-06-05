import { useEffect, useRef, useState } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { supabase } from './supabase';
import { fetchTvToken } from './runtimeApi';

// Subscribes to a match's row in Supabase and surfaces the JSONB
// snapshot column plus the status field. The runtime writes the
// snapshot on every input that changes visible state + on
// finalisation; the TV picks it up via Realtime postgres_changes
// rather than polling the Flask endpoint.
//
// Resilience: bar Wi-Fi drops. A Realtime channel that errors or times
// out is torn down and re-subscribed with exponential backoff, and on a
// successful re-subscribe we re-fetch the row so any UPDATE missed while
// the socket was down is reconciled (Realtime does not replay missed
// changes). Without this the TV silently freezes on the last frame it
// got before the blip.

// Backoff bounds for channel reconnect.
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 15_000;

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

    let channel: RealtimeChannel | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let disposed = false;

    const live = () => mountedRef.current && !disposed;

    // Re-fetch the current row. Run on first mount AND after every
    // successful (re)subscribe so a snapshot UPDATE that landed while the
    // socket was down is reconciled — Realtime won't replay it.
    const resync = async () => {
      const { data, error } = await supabase
        .from('matches')
        .select('status, snapshot, started_at, ended_at')
        .eq('id', matchId)
        .maybeSingle();
      if (!live()) return;
      if (error || !data) {
        setState((prev) => ({ ...prev, loading: false }));
        return;
      }
      setState({
        status: data.status as MatchRowState['status'],
        snapshot: (data.snapshot as Record<string, unknown> | null) ?? null,
        startedAt: (data.started_at as string | null) ?? null,
        endedAt: (data.ended_at as string | null) ?? null,
        loading: false,
      });
    };

    const scheduleReconnect = () => {
      if (disposed || retryTimer) return;
      // Exponential backoff with jitter so a flock of TVs reconnecting
      // after the same outage don't stampede the Realtime server.
      const base = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** attempt);
      const delay = base / 2 + Math.random() * (base / 2);
      attempt += 1;
      retryTimer = setTimeout(() => {
        retryTimer = null;
        void connect();
      }, delay);
    };

    const connect = async () => {
      if (disposed) return;
      // Scope this TV's anon Realtime session to just this match. The
      // venue Flask box mints a token the anon RLS policies accept; without
      // it, RLS exposes zero rows in prod. Best-effort: if minting isn't
      // configured (dev) the call returns null and we proceed on the plain
      // anon key.
      const minted = await fetchTvToken(matchId);
      if (disposed) return;
      if (minted?.token) {
        supabase.realtime.setAuth(minted.token);
      }
      if (channel) {
        supabase.removeChannel(channel);
        channel = null;
      }
      channel = supabase
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
            if (!live()) return;
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
        .subscribe((status) => {
          if (disposed) return;
          if (status === 'SUBSCRIBED') {
            attempt = 0; // healthy — reset backoff
            void resync();
          } else if (
            status === 'CHANNEL_ERROR' ||
            status === 'TIMED_OUT' ||
            status === 'CLOSED'
          ) {
            // Unexpected drop (a deliberate teardown sets disposed first,
            // so this only fires on a real failure). Back off and retry.
            scheduleReconnect();
          }
        });
    };

    void resync();
    void connect();

    return () => {
      disposed = true;
      mountedRef.current = false;
      if (retryTimer) clearTimeout(retryTimer);
      if (channel) supabase.removeChannel(channel);
    };
  }, [matchId]);

  return state;
}
