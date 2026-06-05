import { API_BASE_URL } from '../config';
import type { MatchSource, MatchStatus, SourceFrame } from './matchSource';

// Local-first primary source (ADR 0004): a Flask-SocketIO connection to the
// venue's own Flask box over the LAN. The native TV joins a `match:<id>`
// room and renders the `state_update` frames the runtime pushes on every
// state change — no cloud round-trip, and resilient to a venue internet
// drop.
//
// Guarded adapter: `socket.io-client` is loaded lazily and defensively. If
// it isn't installed yet (the dep + native rebuild is a provisioning step),
// the source reports connected=false and delivers nothing, so the selector
// transparently falls back to Supabase Realtime — the SAME failover path as
// a real LAN outage. Once the dep ships, the local path activates with no
// other change.

// `require` exists in the React Native (Metro) runtime; declare it so this
// stays type-safe without pulling in @types/node.
declare const require: ((module: string) => unknown) | undefined;

type SocketLike = {
  on(event: string, cb: (...args: unknown[]) => void): void;
  emit(event: string, payload: unknown): void;
  close(): void;
};

type StateUpdateEnvelope = {
  match_id?: string;
  status?: MatchStatus;
  snapshot?: Record<string, unknown> | null;
};

// Resolve the socket.io-client `io` factory if the dependency is present.
// Returns null when it isn't, so the caller degrades to the cloud source.
function loadIo(): ((url: string, opts?: unknown) => SocketLike) | null {
  try {
    if (typeof require !== 'function') return null;
    const mod = require('socket.io-client') as
      | { io?: (url: string, opts?: unknown) => SocketLike }
      | ((url: string, opts?: unknown) => SocketLike)
      | undefined;
    if (!mod) return null;
    if (typeof mod === 'function') return mod;
    if (typeof mod.io === 'function') return mod.io;
    return null;
  } catch {
    return null;
  }
}

export function createLocalSocketSource(matchId: string): MatchSource {
  let socket: SocketLike | null = null;
  let disposed = false;

  return {
    start(onFrame, onConn) {
      const io = loadIo();
      if (!io) {
        // Dependency not installed — never connects; selector uses cloud.
        onConn(false);
        return;
      }

      socket = io(API_BASE_URL, {
        transports: ['websocket'],
        // socket.io-client auto-reconnects; the selector handles failover
        // via the connect/disconnect transitions below.
        reconnection: true,
      });

      socket.on('connect', () => {
        if (disposed || !socket) return;
        socket.emit('join_match', { match_id: matchId });
        onConn(true);
      });
      socket.on('disconnect', () => {
        if (disposed) return;
        onConn(false);
      });
      socket.on('connect_error', () => {
        if (disposed) return;
        onConn(false);
      });
      socket.on('state_update', (...args: unknown[]) => {
        if (disposed) return;
        const env = args[0] as StateUpdateEnvelope | undefined;
        if (!env || env.match_id !== matchId) return;
        const frame: SourceFrame = {
          status: (env.status ?? 'lobby') as MatchStatus,
          snapshot: env.snapshot ?? null,
          // The local envelope is gameplay-state-only; the cloud row carries
          // the started/ended timestamps. Leave null so the selector keeps
          // whatever the cloud source last provided.
          startedAt: null,
          endedAt: null,
        };
        onFrame(frame);
      });
    },

    stop() {
      disposed = true;
      if (socket) {
        socket.close();
        socket = null;
      }
    },
  };
}
