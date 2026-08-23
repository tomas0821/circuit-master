#!/bin/bash
# Self-contained cross-model HvH job.
# Both models served by the same local Ollama instance (swaps between calls).
# Follows the same pattern as hvh_same.sh / cap_llama_100.sh.
#
# Required env vars:
#   P1_MODEL   — Ollama model name for player 1
#   P2_MODEL   — Ollama model name for player 2
#   GAME_MODE  — "resistance" or "capacitance"
#   MATCHES    — number of games to play
#   OUT_LABEL  — output filename label

#SBATCH --job-name=hvh-cross
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=05:00:00     # longer: Ollama swaps models between turns
#SBATCH --output=cluster/logs/hvh_cross_%j.out
#SBATCH --error=cluster/logs/hvh_cross_%j.err

echo "=== HvH cross-model: $P1_MODEL vs $P2_MODEL | mode=$GAME_MODE | n=$MATCHES ==="
echo "Node: $(hostname) | GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
echo "Start: $(date)"

cd "$HOME/boardwalk" || { echo "ERROR: ~/boardwalk not found"; exit 1; }

source /home/tomas.rojas_s/deepmd-kit/etc/profile.d/conda.sh
conda activate breadboard-ai

PORT=$((15000 + SLURM_JOB_ID % 1000))
export OLLAMA_HOST="http://127.0.0.1:${PORT}"
export OLLAMA_URL="http://127.0.0.1:${PORT}/v1"
echo "Using port ${PORT}"

fuser -k ${PORT}/tcp 2>/dev/null; sleep 2
ollama serve > cluster/logs/ollama_hvh_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
sleep 15

OUTPUT="results/cluster_runs/${OUT_LABEL}_${SLURM_JOB_ID}"
FRAMES="results/cluster_runs/frames_${OUT_LABEL}_${SLURM_JOB_ID}"
mkdir -p results/cluster_runs

EXTRA=""
[ "${SAVE_FRAMES:-0}" = "1" ] && EXTRA="$EXTRA --save-frames --frames-dir $FRAMES"
[ "${TRACE:-1}" != "0" ]      && EXTRA="$EXTRA --trace"

python -u run_pvp.py \
    --p1 hybrid --p1-api ollama --p1-model "$P1_MODEL" \
    --p2 hybrid --p2-api ollama --p2-model "$P2_MODEL" \
    -m "$MATCHES" --mode "$GAME_MODE" --output "$OUTPUT" $EXTRA

EXIT_CODE=$?
kill $SERVER_PID 2>/dev/null
echo "Done: $(date) | exit=$EXIT_CODE"
exit $EXIT_CODE
