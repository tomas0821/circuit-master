#!/bin/bash
# Shared Ollama server job — only needed for cross-model HvH.
# For same-model HvH, use hvh_same.sh instead (self-contained per job).
#
# Starts Ollama on a GPU node, writes URL + ready flag so worker jobs can connect.
#
# NOTE: serial partition has NO GPU → 70B inference would take minutes/call.
#       This job intentionally runs on the gpu partition for acceptable speed.

#SBATCH --job-name=ollama-server
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --output=cluster/logs/server_%j.out
#SBATCH --error=cluster/logs/server_%j.err

# ── Config ───────────────────────────────────────────────────────────────────
WORKDIR="$HOME/boardwalk"
URL_FILE="$WORKDIR/cluster/ollama_url.txt"
READY_FILE="$WORKDIR/cluster/ollama_ready.flag"
# ────────────────────────────────────────────────────────────────────────────

echo "=== Ollama server job $SLURM_JOB_ID on $(hostname) ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
echo "Start: $(date)"

cd "$WORKDIR" || { echo "ERROR: $WORKDIR not found"; exit 1; }
source /home/tomas.rojas_s/deepmd-kit/etc/profile.d/conda.sh
conda activate breadboard-ai

rm -f "$URL_FILE" "$READY_FILE"

PORT=$((15000 + SLURM_JOB_ID % 1000))
export OLLAMA_HOST="http://127.0.0.1:${PORT}"
echo "http://127.0.0.1:${PORT}/v1" > "$URL_FILE"
echo "URL: $(cat $URL_FILE)"

fuser -k ${PORT}/tcp 2>/dev/null; sleep 2
ollama serve > cluster/logs/ollama_server_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
sleep 15

# Signal readiness
touch "$READY_FILE"
echo "Server ready at $(date)"

wait $SERVER_PID
echo "Ollama exited at $(date)"
