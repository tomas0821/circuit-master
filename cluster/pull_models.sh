#!/bin/bash
# Pull all benchmark models onto the cluster — must run on a GPU node.
# Submit this ONCE before running the benchmark:
#   sbatch cluster/pull_models.sh
# Takes ~1-2h depending on download speed.
# Check progress: tail -f cluster/logs/pull_models_<JOBID>.out

#SBATCH --job-name=pull-models
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=cluster/logs/pull_models_%j.out
#SBATCH --error=cluster/logs/pull_models_%j.err

echo "=== Pulling benchmark models ==="
echo "Node: $(hostname)"
echo "Start: $(date)"

source /home/tomas.rojas_s/deepmd-kit/etc/profile.d/conda.sh
conda activate breadboard-ai

PORT=$((15000 + SLURM_JOB_ID % 1000))
export OLLAMA_HOST="http://127.0.0.1:${PORT}"
fuser -k ${PORT}/tcp 2>/dev/null; sleep 2
ollama serve > /tmp/ollama_pull_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
sleep 15

echo "--- Pulling llama3.3:70b (~42GB) ---"
ollama pull llama3.3:70b && echo "llama3.3:70b OK" || echo "llama3.3:70b FAILED"

echo "--- Pulling qwen3:32b (~20GB) ---"
ollama pull qwen3:32b && echo "qwen3:32b OK" || echo "qwen3:32b FAILED"

echo "--- mixtral:latest (already present, verifying) ---"
ollama pull mixtral:latest && echo "mixtral:latest OK" || echo "mixtral:latest FAILED"

kill $SERVER_PID 2>/dev/null
echo "Done: $(date)"
ollama list 2>/dev/null || true
