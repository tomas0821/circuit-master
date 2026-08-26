# Circuit Master

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22072475.svg)](https://doi.org/10.5281/zenodo.22072475)

A two-player board game for teaching series and parallel resistor and capacitor circuits. Players build circuits on a shared breadboard, drawing resistor/capacitor cards to match target-value Objective cards for points.

Circuit Master was balance-tested before classroom deployment using AI self-play — open-source language models playing the game against each other at volume — to catch design flaws (an unreachable objective tier, a turn-order imbalance) that a small human playtest pool would likely miss. This repository contains everything needed to print and play the game, reproduce the self-play balance-testing analysis, and inspect the classroom pilot data.

A paper describing the game, the self-play methodology, and the classroom pilot is [in preparation / forthcoming — citation to follow].

## Print and play

Everything needed to physically produce the game is in this repo:

| File | Contents |
|---|---|
| `board_a4.pdf`, `board_a4_es.pdf` | Printable A4 breadboard (English / Spanish) |
| `deck_a4_print.pdf`, `deck_a4_print_es.pdf` | Objective card deck, front/back interleaved for duplex printing |
| `components_a4_print.pdf`, `components_a4_print_es.pdf` | Resistor/capacitor component card deck, front/back interleaved |
| `instructions_en.pdf`, `instructions_es.pdf` | Full player-facing rulebook |
| `card_images/` | Individual card artwork (PNG) |

Print the board and the two decks, cut out the cards, and you have a physical copy of the game — no software or computer needed to play. `instructions_en.pdf` covers setup, turn structure, scoring, and the circuit physics (series/parallel formulas for both resistors and capacitors) a player needs.

To regenerate any of these from source (e.g. after editing card values or artwork):

```bash
pip install -r requirements.txt
python3 generate_deck.py          # deck_a4_*.pdf, components_a4_*.pdf, card_images/
python3 generate_board.py         # board_a4.pdf (English)
python3 generate_board_es.py      # board_a4_es.pdf (Spanish)
python3 generate_instructions.py  # instructions_en.pdf, instructions_es.pdf
```

## The digital game engine and physics tests

`breadboard_game.py` implements the full game — board state, card deck, turn/action handling, and a four-step graph-reduction physics engine that computes the equivalent resistance or capacitance of whatever a player has built (series/parallel reduction, rail connectivity, short-circuit detection). `boardwalk.py` provides the generic game-loop scaffolding it's built on.

```bash
pip install -r requirements.txt
python3 test_suite.py    # physics correctness tests (pre-placed components → assert expected R_eq/C_eq)
```

`test_suite.py` also renders visual replays of each test circuit as MP4s, which requires `ffmpeg` on your system `PATH` (the physics assertions themselves run without it).

## AI self-play (balance-testing method)

`breadboard_ai.py` implements the agents used to balance-test the ruleset:

- **`HeuristicAgent`** — deterministic, zone-aware, no AI involved. Executes physical placements for `HybridAgent` below.
- **`OllamaAgent`** — an LLM given full control over every placement, via a local [Ollama](https://ollama.com) server (OpenAI-compatible API, no cloud dependency, no API key).
- **`HybridAgent`** — the agent used to produce the released self-play corpus. Once per turn, the LLM chooses *which* objective to pursue; `HeuristicAgent`'s logic executes the physical placement. This split isolates strategic decision-making from mechanical execution.

All AI agents in this repository run against a **local Ollama server only** — there is no cloud API dependency, no API key required, and nothing here was used against a paid inference service.

```bash
# Start a local Ollama server and pull a model (see https://ollama.com)
ollama pull llama3.3:70b

# Run matches
python3 run_pvp.py --p1 hybrid --p1-model llama3.3:70b \
                    --p2 hybrid --p2-model llama3.3:70b \
                    --matches 10 --output results/my_run --trace
```

`--trace` writes a `*_trace.jsonl` file with the full per-turn LLM reasoning trace (prompt, response, chosen objective, success/fallback), used for the completion-rate analysis below.

`cluster/` contains the SLURM batch scripts used to run the released 1,200-game corpus on a GPU cluster (`hvh_same.sh`, `hvh_cross.sh`, `launch_full.sh`) — adapt the `#SBATCH` headers for your own cluster.

## Released data and analysis

`results/cluster_runs/` contains the full 1,200-game self-play corpus: 600 same-model games (each of 3 open-source LLMs against itself) and 600 cross-model games (each pair against each other), split evenly between the resistance and capacitance modules. Each game has a summary CSV row and a full per-turn trace JSONL.

```bash
python3 analyze_hvh.py                 # regenerates results/hvh_analysis/*.png figures
python3 analyze_completion_rates.py     # per-card/per-category completion rates from the trace files
python3 analyze_turn_order.py           # turn-order balance significance tests (binomial, chi-square, Welch's t, Mann-Whitney)
```

`results/classroom_pilot/` contains anonymized data from a classroom pilot of the printed physical game (n=25 students, played head-to-head in small groups): post-game survey responses (`survey_responses.csv`) and post-test quiz results (`quiz_item_accuracy.csv`, `quiz_participant_summary.csv`). No names, emails, or other identifying information are included.

## Repository layout

```
breadboard_game.py       Game engine + physics
breadboard_ai.py          Agents (Heuristic, Ollama, Hybrid)
boardwalk.py               Generic game-loop base classes
generate_plots.py         Board/game-state renderer (used by tests)
run_pvp.py                 Match runner (CSV + trace logging)
test_suite.py               Physics correctness tests

generate_deck.py, generate_deck_es.py       Card deck generator (EN/ES)
generate_card_pngs.py                       Individual card artwork
generate_board.py, generate_board_es.py     Board generator (EN/ES)
generate_circuit_examples.py                Example-circuit diagrams for cards
generate_instructions.py                    Rulebook generator (EN/ES)

analyze_hvh.py                 Self-play corpus analysis + figures
analyze_completion_rates.py    Card/category completion-rate reconstruction
analyze_turn_order.py          Turn-order balance significance tests

cluster/                 SLURM scripts for running self-play on a GPU cluster
results/cluster_runs/    1,200-game self-play corpus (CSVs + per-turn traces)
results/hvh_analysis/    Pre-generated figures
results/classroom_pilot/ Anonymized classroom pilot data
card_images/              Individual card artwork
```

## Requirements

```bash
pip install -r requirements.txt
```

Python 3.10+. `ffmpeg` (system install, not pip) is needed only for `test_suite.py`'s visual-replay video output — the physics assertions run without it. Running AI self-play locally requires [Ollama](https://ollama.com) with a pulled model; no cloud API key is used anywhere in this repository.

## Citation

If you use this game, its code, or the released data, please cite the associated paper (details to be added upon publication) and/or this repository:

```
Rojas S., T. (2026). Circuit Master. https://doi.org/10.5281/zenodo.22072475
```

## License

Code is released under the MIT License (see `LICENSE`). Data (`results/`) and print materials (rulebook, cards, board) are released under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
