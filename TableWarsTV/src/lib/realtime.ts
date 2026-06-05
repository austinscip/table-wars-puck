import type { RealtimeChannel } from '@supabase/supabase-js';
import { supabase } from './supabase';

// Row shapes returned by Supabase Realtime postgres_changes events.
// Loose typing on purpose — the TV reconstructs visible state from these
// streams, so each screen narrows to the fields it cares about.

export type MatchRow = {
  id: string;
  location_id: string;
  game_id: string;
  table_number: number | null;
  status: 'lobby' | 'active' | 'finished' | 'abandoned';
  started_at: string;
  ended_at: string | null;
  player_count: number;
};

export type MatchPuckRow = {
  id: string;
  match_id: string;
  puck_id: string;
  role: 'host' | 'sibling';
  player_name: string | null;
  joined_at: string;
  left_at: string | null;
};

export type ScoreRow = {
  id: string;
  match_id: string;
  match_puck_id: string;
  round_number: number;
  score_delta: number;
  score_total: number;
  event_type: 'round' | 'final';
  recorded_at: string;
};

export type MatchSubscriptionCallbacks = {
  onMatchUpdate?: (row: MatchRow) => void;
  onPuckJoin?: (row: MatchPuckRow) => void;
  onPuckLeave?: (row: MatchPuckRow) => void;
  onScoreInsert?: (row: ScoreRow) => void;
};

// Subscribe to all interesting Realtime events for a single match.
// Returns an unsubscribe function the screen should call in its cleanup.
//
// Mike's "WebSockets, not POST/reply" advice is satisfied here without
// us running our own Socket.IO server — Supabase Realtime is the
// WebSocket transport, fanning Postgres row changes out to listeners.
export function subscribeToMatch(
  matchId: string,
  callbacks: MatchSubscriptionCallbacks,
): () => void {
  const channel: RealtimeChannel = supabase
    .channel(`match:${matchId}`)
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'matches',
        filter: `id=eq.${matchId}`,
      },
      (payload) => callbacks.onMatchUpdate?.(payload.new as MatchRow),
    )
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'match_pucks',
        filter: `match_id=eq.${matchId}`,
      },
      (payload) => callbacks.onPuckJoin?.(payload.new as MatchPuckRow),
    )
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'match_pucks',
        filter: `match_id=eq.${matchId}`,
      },
      (payload) => {
        const row = payload.new as MatchPuckRow;
        if (row.left_at) callbacks.onPuckLeave?.(row);
      },
    )
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'scores',
        filter: `match_id=eq.${matchId}`,
      },
      (payload) => callbacks.onScoreInsert?.(payload.new as ScoreRow),
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}
