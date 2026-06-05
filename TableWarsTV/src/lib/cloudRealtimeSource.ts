import type { RealtimeChannel } from '@supabase/supabase-js';
import { supabase } from './supabase';
import { fetchTvToken } from './runtimeApi';
import type { MatchSource, MatchStatus, SourceFrame } from './matchSource';

// Cloud fallback source (ADR 0004): Supabase Realtime on the match row.
// This is the data path the TV used exclusively before local-first; it now
// backs the selector as the fallback the TV reads when the venue LAN socket
// is down. Behaviour preserved verbatim from the old useMatchState:
//
// - mints the per-match anon Realtime token (RLS),
// - subscribes to matches UPDATE filtered by id,
// - re-fetches the row on every (re)subscribe so an UPDATE missed while the
//   socket was down is reconciled (Realtime doesn't replay), and
// - reconnects with exponential backoff + jitter.

const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 15_000;

function frameFromRow(row: {
  status?: MatchStatus;
  snapshot?: Record<string, unknown> | null;
  started_at?: string | null;
  ended_at?: string | null;
}): SourceFrame {
  return {
    status: (row.status ?? 'lobby') as MatchStatus,
    snapshot: (row.snapshot as Record<string, unknown> | null) ?? null,
    startedAt: row.started_at ?? null,
    endedAt: row.ended_at ?? null,
  };
}

export function createCloudRealtimeSource(matchId: string): MatchSource {
  let channel: RealtimeChannel | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let attempt = 0;
  let disposed = false;

  return {
    start(onFrame, _onConn) {
      // Cloud connection state never gates the selector (only local does),
      // so _onConn is intentionally unused here.
      const resync = async () => {
        const { data, error } = await supabase
          .from('matches')
          .select('status, snapshot, started_at, ended_at')
          .eq('id', matchId)
          .maybeSingle();
        if (disposed || error || !data) return;
        onFrame(frameFromRow(data as Parameters<typeof frameFromRow>[0]));
      };

      const scheduleReconnect = () => {
        if (disposed || retryTimer) return;
        const base = Math.min(
          RECONNECT_MAX_MS,
          RECONNECT_BASE_MS * 2 ** attempt,
        );
        const delay = base / 2 + Math.random() * (base / 2);
        attempt += 1;
        retryTimer = setTimeout(() => {
          retryTimer = null;
          connect();
        }, delay);
      };

      const connect = async () => {
        if (disposed) return;
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
              if (disposed) return;
              onFrame(
                frameFromRow(
                  payload.new as Parameters<typeof frameFromRow>[0],
                ),
              );
            },
          )
          .subscribe((status) => {
            if (disposed) return;
            if (status === 'SUBSCRIBED') {
              attempt = 0;
              resync();
            } else if (
              status === 'CHANNEL_ERROR' ||
              status === 'TIMED_OUT' ||
              status === 'CLOSED'
            ) {
              scheduleReconnect();
            }
          });
      };

      resync();
      connect();
    },

    stop() {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (channel) supabase.removeChannel(channel);
      channel = null;
    },
  };
}
