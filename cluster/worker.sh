#!/bin/bash
# Cross-model HvH worker — connects to the shared Ollama server started by server.sh.
# For same-model HvH, use hvh_same.sh instead (self-contained, no shared server needed).
#
# Required env vars (set by launch scripts via --export):
#   P1_MODEL   — Ollama model name for player 1
#   P2_MODEL   — Ollama model name for player 2 (different from P1 for cross-model)
#   GAME_MODE  — "resistance" or "capacitance"
#   MATCHES    — number of games to play
#   OUT_LABEL  — output file label

#SBATCH --job-name=hvh-worker
#SBATCH --partition=serial
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=cluster/logs/worker_%j.out
#SBATCH --error=cluster/logs/worker_%j.err

# ── Config ─────────────────��─────────────────────────────────────────────────
WORKDIR="$HOME/boardwalk"
URL_FILE="$WORKDIR/cluster/ollama_url.txt"
READY_FILE="$WORKDIR/cluster/ollama_ready.flag"
# ─��──────────────────────────────��───────────────────────────────────────────

echo "=== Worker $SLURM_JOB_ID: $OUT_LABEL | mode=$GAME_MODE | n=$MATCHES ==="
echo "  P1=$P1_MODEL  P2=$P2_MODEL"
echo "Start: $(date)"
cd "$WORKDIR" || { echo "ERROR: $WORKDIR not found"; exit 1; }

source /home/tomas.rojas_s/deepmd-kit/etc/profile.d/conda.sh
conda activate breadboard-ai

# Wait for URL file (up to 10 min)
WAIT=0
until [ -f "$URL_FILE" ] || [ $WAIT -ge 120 ]; do sleep 5; WAIT=$((WAIT+5)); done
[ -f "$URL_FILE" ] || { echo "ERROR: URL file never appeared"; exit 1; }

export OLLAMA_URL=$(cat "$URL_FILE")
echo "Ollama URL: $OLLAMA_URL"

# Wait for ready flag (server up, models pulled)
WAIT=0
until [ -f "$READY_FILE" ] || [ $WAIT -ge 600 ]; do sleep 10; WAIT=$((WAIT+10)); done
[ -f "$READY_FILE" ] || { echo "ERROR: Ready flag never appeared"; exit 1; }
echo "Server ready (waited ${WAIT}s)"

OUTPUT="$WORKDIR/results/cluster_runs/${OUT_LABEL}_${SLURM_JOB_ID}"
python -u run_pvp.py \
    --p1 hybrid --p1-api ollama --p1-model "$P1_MODEL" \
    --p2 hybrid --p2-api ollama --p2-model "$P2_MODEL" \
    -m "$MATCHES" --mode "$GAME_MODE" --output "$OUTPUT"

EXIT_CODE=$?
echo "Done: $(date) | exit=$EXIT_CODE"
exit $EXIT_CODE
