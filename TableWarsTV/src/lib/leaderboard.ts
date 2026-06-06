import { useCallback, useEffect, useState } from 'react';
import { supabase } from './supabase';
import { LOCATION_ID } from '../config';

export type LeaderboardPeriod = 'day' | 'week' | 'month' | 'all_time';

export type LeaderboardRow = {
  puckId: string;
  puckIndex: number | null;
  gameSlug: string;
  highScore: number;
  totalMatches: number;
};

// Wraps the leaderboards view-shape that Track A's trigger maintains:
// (location_id, game_id, puck_id, period, period_start) -> high_score.
// We join through pucks + games so the screen can render
// human-friendly identifiers without doing those lookups itself.
async function fetchLeaderboard(
  period: LeaderboardPeriod,
  options: { gameSlug?: string; limit?: number } = {},
): Promise<LeaderboardRow[]> {
  const { gameSlug, limit = 5 } = options;

  let query = supabase
    .from('leaderboards')
    .select(
      `
      high_score,
      total_matches,
      puck_id,
      pucks ( puck_index ),
      games ( slug )
    `,
    )
    .eq('location_id', LOCATION_ID)
    .eq('period', period)
    .order('high_score', { ascending: false })
    .limit(limit);

  if (gameSlug) {
    query = query.eq('games.slug', gameSlug);
  }

  const { data, error } = await query;
  if (error) {
    if (__DEV__) {
      console.warn('[leaderboard] fetch failed', error.message);
    }
    return [];
  }
  if (!data) return [];

  return data.map((row) => {
    const puckRel = row.pucks as { puck_index?: number } | { puck_index?: number }[] | null;
    const gameRel = row.games as { slug?: string } | { slug?: string }[] | null;
    const puckIndex = Array.isArray(puckRel)
      ? puckRel[0]?.puck_index ?? null
      : puckRel?.puck_index ?? null;
    const slug = Array.isArray(gameRel)
      ? gameRel[0]?.slug ?? ''
      : gameRel?.slug ?? '';
    return {
      puckId: row.puck_id as string,
      puckIndex,
      gameSlug: slug,
      highScore: row.high_score as number,
      totalMatches: row.total_matches as number,
    };
  });
}

// Rotates through periods on the supplied cadence so the attract loop
// can show "Today's top players" → "This week" → "All time" without the
// screen needing to manage its own timer.
export function useLeaderboardRotation(
  periods: LeaderboardPeriod[] = ['day', 'week', 'all_time'],
  options: { gameSlug?: string; limit?: number; rotateMs?: number } = {},
) {
  const { rotateMs = 10_000, gameSlug, limit = 5 } = options;
  const [periodIndex, setPeriodIndex] = useState(0);
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);

  const period = periods[periodIndex];

  const refetch = useCallback(async () => {
    setLoading(true);
    const data = await fetchLeaderboard(period, { gameSlug, limit });
    setRows(data);
    setLoading(false);
  }, [period, gameSlug, limit]);

  // Auto-fetch on period change, guarded so a fetch that resolves AFTER the
  // attract screen unmounts (or rotates) doesn't setState on a gone component
  // (audit tablewars-tv-2026-06-06).
  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchLeaderboard(period, { gameSlug, limit }).then((data) => {
      if (!active) return;
      setRows(data);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [period, gameSlug, limit]);

  useEffect(() => {
    const id = setInterval(() => {
      setPeriodIndex((i) => (i + 1) % periods.length);
    }, rotateMs);
    return () => clearInterval(id);
  }, [periods.length, rotateMs]);

  return { period, rows, loading, refetch };
}
