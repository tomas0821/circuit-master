#!/bin/bash
# Full benchmark: 1200 games total.
#   Same-model HvH:  3 models × 2 modules × 100 games =  600 games (6 jobs)
#   Cross-model HvH: 3 pairs  × 2 modules × 100 games =  600 games (6 jobs)
#   Total: 12 GPU jobs, ~2-5h each
#
# Each job is self-contained (own Ollama server on GPU node).
# Run from ~/boardwalk on the LOGIN NODE.

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
MODEL_LLAMA="llama3.3:70b"
MODEL_QWEN="qwen3:32b"
MODEL_MIXTRAL="mixtral:latest"  # 8x7B already on cluster
# ─────────────────────────────────────────────────────────────────────────────

WORKDIR="$HOME/boardwalk"
cd "$WORKDIR"
mkdir -p cluster/logs results/cluster_runs

echo "=== Submitting FULL benchmark (900 games, 12 jobs) ==="

# ── Helper ────────────────────────────────────────────────────────────────────
submit_same() {
    local MODEL="$1" MODE="$2" N="$3"
    local SAFE="${MODEL//[:\/]/_}"
    local LABEL="hvh_same_${SAFE}_${MODE}"
    local JID
    JID=$(sbatch --parsable \
        --export=ALL,MODEL="$MODEL",GAME_MODE="$MODE",MATCHES="$N",OUT_LABEL="$LABEL" \
        cluster/hvh_same.sh)
    echo "  job $JID — same:$MODEL / $MODE / $N games"
}

submit_cross() {
    local M1="$1" M2="$2" MODE="$3" N="$4"
    local S1="${M1//[:\/]/_}" S2="${M2//[:\/]/_}"
    local LABEL="hvh_cross_${S1}_vs_${S2}_${MODE}"
    local JID
    JID=$(sbatch --parsable \
        --export=ALL,P1_MODEL="$M1",P2_MODEL="$M2",GAME_MODE="$MODE",MATCHES="$N",OUT_LABEL="$LABEL" \
        cluster/hvh_cross.sh)
    echo "  job $JID — cross:$M1 vs $M2 / $MODE / $N games"
}

# ── Same-model (600 games) ────────────────────────────────────────────────────
echo "--- Same-model HvH (600 games) ---"
for MODEL in "$MODEL_LLAMA" "$MODEL_QWEN" "$MODEL_MIXTRAL"; do
    submit_same "$MODEL" resistance 100
    submit_same "$MODEL" capacitance 100
done

# ── Cross-model (600 games) ───────────────────────────────────────────────────
echo "--- Cross-model HvH (600 games) ---"
for MODE in resistance capacitance; do
    submit_cross "$MODEL_LLAMA"   "$MODEL_QWEN"    "$MODE" 100
    submit_cross "$MODEL_LLAMA"   "$MODEL_MIXTRAL" "$MODE" 100
    submit_cross "$MODEL_QWEN"    "$MODEL_MIXTRAL" "$MODE" 100
done

echo ""
echo "=== All 12 jobs submitted ==="
echo "Monitor: squeue -u \$USER"
echo "Logs:    $WORKDIR/cluster/logs/"
echo "Results: $WORKDIR/results/cluster_runs/"
