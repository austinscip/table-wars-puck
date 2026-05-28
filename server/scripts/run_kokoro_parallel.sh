#!/usr/bin/env bash
# Launch N parallel Kokoro regen workers, each on a disjoint shard of
# the question IDs. Single-thread is ~80min; 8-way parallel is ~10min on
# a 10-core M-series Mac.
#
# Usage:
#   ./scripts/run_kokoro_parallel.sh           # defaults: 8 workers, overwrite
#   ./scripts/run_kokoro_parallel.sh 4         # 4 workers
#
# Logs:   /tmp/kokoro_regen_<k>_of_<N>.log per worker
# Wait:   `wait` blocks until all workers finish; or run in background.

set -e
cd "$(dirname "$0")/.."

N=${1:-8}
echo "=== launching $N parallel Kokoro workers (am_michael, --overwrite) ==="
PIDS=()
for ((k=0; k<N; k++)); do
  LOG=/tmp/kokoro_regen_${k}_of_${N}.log
  DATABASE_URL= venv/bin/python scripts/generate_narration_kokoro.py \
      --shard "$k/$N" --overwrite > "$LOG" 2>&1 &
  PIDS+=($!)
  echo "  worker $k/$N  PID=$!  log=$LOG"
done

echo ""
echo "waiting on all $N workers ..."
START=$(date +%s)
for pid in "${PIDS[@]}"; do
  wait "$pid"
done
ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "=== ALL WORKERS DONE in ${ELAPSED}s ==="
for ((k=0; k<N; k++)); do
  LOG=/tmp/kokoro_regen_${k}_of_${N}.log
  STATS=$(tail -1 "$LOG")
  echo "  shard $k/$N: $STATS"
done

# Final file count
TOTAL=$(ls ~/table-wars-puck-sandbox/server/static/games/speed-pyramid/audio/questions/q_*.mp3 | wc -l | tr -d ' ')
echo ""
echo "total MP3 files: $TOTAL  (target: 1296)"
