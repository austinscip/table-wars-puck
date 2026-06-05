import { API_BASE_URL } from '../config';

// Wire shape the Flask runtime returns from /api/runtime/pair/lobby-state.
// Mirrors PairingManager.lobby_snapshot() in server/runtime/pairing.py;
// keep field names in sync when that snapshot grows.

export type LobbyPlayerWire = {
  puck_index: number;
  color: string;
  color_name: string;
  is_host: boolean;
  joined_at: number;
};

export type LobbyStateWire =
  | { active: false }
  | {
      active: true;
      code: string;
      game_slug: string;
      location_id: string;
      table_number: number;
      host_puck_index: number;
      started: boolean;
      match_id: string | null;
      players: LobbyPlayerWire[];
    };

export type MatchStateWire = {
  state: Record<string, unknown>;
  status: 'lobby' | 'active' | 'finished' | 'abandoned' | 'unknown';
  players: { puck_index: number; name: string; color: string }[];
};

async function getJSON<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) {
      if (__DEV__) {
        console.warn(`[runtimeApi] ${path} returned ${res.status}`);
      }
      return null;
    }
    return (await res.json()) as T;
  } catch (e) {
    if (__DEV__) {
      console.warn(`[runtimeApi] ${path} failed`, e);
    }
    return null;
  }
}

export function fetchLobbyState(): Promise<LobbyStateWire | null> {
  return getJSON<LobbyStateWire>('/api/runtime/pair/lobby-state');
}

export function fetchMatchState(matchId: string): Promise<MatchStateWire | null> {
  return getJSON<MatchStateWire>(`/api/runtime/match/${matchId}/state`);
}
