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

async function postJSON<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) {
      if (__DEV__) {
        console.warn(`[runtimeApi] POST ${path} returned ${res.status}`);
      }
      return null;
    }
    return (await res.json()) as T;
  } catch (e) {
    if (__DEV__) {
      console.warn(`[runtimeApi] POST ${path} failed`, e);
    }
    return null;
  }
}

// Mint the Supabase Realtime token that scopes this TV's anon session to a
// single match (see the anon-match-token RLS migration). The venue's own
// Flask box issues it for matches at this location only. Returns null when
// TV auth isn't configured (dev/open mode) — the caller then relies on
// whatever the plain anon key can read.
export function fetchTvToken(
  matchId: string,
): Promise<{ token: string; match_id: string } | null> {
  return postJSON(`/api/runtime/match/${matchId}/tv-token`);
}

export function fetchLobbyState(): Promise<LobbyStateWire | null> {
  return getJSON<LobbyStateWire>('/api/runtime/pair/lobby-state');
}

export function fetchMatchState(matchId: string): Promise<MatchStateWire | null> {
  return getJSON<MatchStateWire>(`/api/runtime/match/${matchId}/state`);
}

// QR the TV shows so a patron's phone can open the bind page for this match
// (ADR 0005). `qr_code` is a base64 PNG data URI usable directly as an
// <Image> source; `play_url` is the text fallback. Null when unreachable.
export type MatchQrWire = { play_url: string; qr_code: string | null };

export function fetchMatchQr(matchId: string): Promise<MatchQrWire | null> {
  return getJSON<MatchQrWire>(`/api/runtime/match/${matchId}/qr`);
}
