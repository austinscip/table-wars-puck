import { useEffect, useMemo, useRef } from 'react';
import { CueDispatcher, type CueEvent } from './cues';

// Owns a CueDispatcher per match. When useMatchState pushes a new
// snapshot, this hook extracts snapshot.cues and runs them through the
// dispatcher's monotonic-ts watermark. The dispatcher dedupes cues
// already fired in earlier snapshots so subscribers only see fresh
// emissions.
//
// Screens subscribe via dispatcher.on('sfx', handler) etc. The
// dispatcher itself is stable across renders so subscriptions don't
// churn.

export function useCues(
  snapshot: Record<string, unknown> | null,
  matchId: string | null,
): CueDispatcher {
  // Keep one dispatcher per matchId. When matchId changes (new match
  // pairs), reset so cue timestamps from the prior match don't carry
  // over.
  const dispatcher = useMemo(() => new CueDispatcher(), [matchId]);

  const seenMatchId = useRef<string | null>(null);
  useEffect(() => {
    if (seenMatchId.current !== matchId) {
      dispatcher.reset();
      seenMatchId.current = matchId;
    }
  }, [matchId, dispatcher]);

  // Ingest on every snapshot change. The dispatcher's watermark
  // prevents replays so this is safe to call on every render even if
  // the snapshot reference changes but the cues list didn't.
  useEffect(() => {
    if (!snapshot) return;
    const cues = (snapshot.cues as CueEvent[] | undefined) ?? [];
    if (cues.length > 0) {
      dispatcher.ingest(cues);
    }
  }, [snapshot, dispatcher]);

  return dispatcher;
}
