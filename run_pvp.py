#!/usr/bin/env python3
"""
PvP Match Runner with detailed logging — Agent vs Agent on the same breadboard.
Per-player physics, row zones, visual replay, CSV output.

Usage:
  python run_pvp.py --matches 100 --output results/pvp_batch
  python run_pvp.py --p1 hybrid --p1-model llama3.3:70b --p2 hybrid --p2-model qwen3:32b \
                    --matches 50
"""
import os, sys, time, argparse, csv, json
from datetime import datetime
sys.path.insert(0, '.')

from breadboard_game import BreadboardGame
from breadboard_ai import HeuristicAgent, HybridAgent, OllamaAgent
from generate_plots import draw_board


def _verify_objective(game, pid, obj):
    """Re-run physics for player pid after a claimed completion using auto-connect.

    Returns (actual_val, verified, rails_ok):
      actual_val  — computed Req or Ceq with auto-connected rails
      verified    — True if actual_val is within 5% of target AND rails connected
      rails_ok    — whether + and - rails are both reached via auto-connect
    """
    is_cap = getattr(obj, 'objective_type', 'resistance') == "capacitance"

    if is_cap:
        my_comps = [c for c in game.placed_components
                    if c.owner == pid and getattr(c, 'card_type', 'resistor') == 'capacitor']
    else:
        my_comps = [c for c in game.placed_components
                    if c.owner == pid and c.value > 0
                    and getattr(c, 'card_type', 'resistor') != 'capacitor']

    # Check each circuit group independently (completed circuits must not interfere)
    target = obj.target_req
    for group in game._identify_circuit_groups(my_comps):
        auto_wires = game._auto_rail_connections(pid, comps=group)
        if is_cap:
            actual, _, plus, minus = game.calculate_graph_capacitance(
                virtual_components=auto_wires + group)
        else:
            actual, _, plus, minus = game.calculate_graph_equivalent(
                virtual_components=auto_wires + group)
        rails_ok = bool(plus and minus)
        in_range = actual != float('inf') and target * 0.95 <= actual <= target * 1.05
        if in_range and rails_ok:
            return actual, True, True

    return float('inf'), False, False


def get_agent(agent_type, name, pid, model="llama3.3:70b"):
    if agent_type == "ollama":
        return OllamaAgent(name=name, player_idx=pid, model=model)
    if agent_type == "hybrid":
        base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1")
        return HybridAgent(name=name, player_idx=pid, model=model, base_url=base_url)
    return HeuristicAgent(name=name, player_idx=pid)


def card_label(card):
    if card is None:
        return "None"
    v = int(card.value)
    return f"R{v}" if v > 0 else "W"


def _parse_obj_type(entry):
    """Return (points, circuit_type) from a completed-objective entry string."""
    import re
    pts_m = re.search(r'\((\d+)pts\)', entry)
    pts = int(pts_m.group(1)) if pts_m else 0
    if 'µF' in entry:                  return pts, 'cap'
    if 'Bridge' in entry:              return pts, 'bridge'
    if 'Mixed' in entry:               return pts, 'mixed'
    if 'Parallel' in entry:            return pts, 'parallel'
    if 'Series' in entry:              return pts, 'series'
    return pts, 'other'


def _score_breakdown(obj_entries):
    """Aggregate points by circuit type from a list of objective entry strings."""
    totals = {'series': 0, 'parallel': 0, 'mixed': 0, 'bridge': 0, 'cap': 0}
    for e in obj_entries:
        pts, ctype = _parse_obj_type(e)
        if ctype in totals:
            totals[ctype] += pts
    return totals


def _effective_api_rate(api_ok, fallbacks):
    """Fraction of get_action calls answered by the LLM (not heuristic fallback)."""
    total = api_ok + fallbacks
    return api_ok / total if total > 0 else None  # None = heuristic player, no API calls


def run_match(match_id, p1_type, p2_type, p1_model, p2_model,
              min_api_rate=0.0, save_frames=False, make_video=False,
              frames_base_dir="frames_pvp", mode="resistance",
              trace_file=None):
    t0 = time.time()
    ai1 = get_agent(p1_type, f"P1-{p1_type}", 0, model=p1_model)
    ai2 = get_agent(p2_type, f"P2-{p2_type}", 1, model=p2_model)

    game = BreadboardGame(player_names=[ai1.name, ai2.name], mode=mode)
    state = game.get_initial_state()

    p1_played = []
    p2_played = []
    p1_objs_completed = []
    p2_objs_completed = []

    p1_invalid = p2_invalid = 0
    p1_api_success = p2_api_success = 0
    p1_api_attempts = p2_api_attempts = 0
    p1_fallbacks = p2_fallbacks = 0
    p1_verify_fails = p2_verify_fails = 0
    p1_place = p2_place = 0
    p1_draw = p2_draw = 0
    p1_complete = p2_complete = 0
    p1_complete_scored = p2_complete_scored = 0
    p1_targeted = []   # route_descs of objectives in hand at each complete call
    p2_targeted = []
    frame_idx = 0
    frame_dir = None
    action_log = []
    _COL_NAMES = ['+','-','A','B','C','D','E','F','G','H','I','J','+','-']

    if save_frames:
        import shutil
        frame_dir = f"{frames_base_dir}/match_{match_id:03d}"
        if os.path.isdir(frame_dir):
            shutil.rmtree(frame_dir, ignore_errors=True)
        os.makedirs(frame_dir, exist_ok=True)

    while not game.game_finished(state):
        pid = game.current_player_idx
        agent = ai1 if pid == 0 else ai2

        fb_before = getattr(agent, 'fallback_count', 0)
        api_before = getattr(agent, '_api_attempts', 0)
        api_ok_before = getattr(agent, '_api_ok', 0)

        try:
            move = agent.get_action(game, state)
        except Exception as e:
            move = None

        if trace_file:
            for t in getattr(agent, 'flush_traces', lambda: [])():
                t["match"] = match_id
                trace_file.write(json.dumps(t) + "\n")
            trace_file.flush()

        api_after = getattr(agent, '_api_attempts', 0)
        api_ok_after = getattr(agent, '_api_ok', 0)
        fb_after = getattr(agent, 'fallback_count', 0)

        if pid == 0:
            p1_api_attempts += api_after - api_before
            p1_api_success += api_ok_after - api_ok_before
        else:
            p2_api_attempts += api_after - api_before
            p2_api_success += api_ok_after - api_ok_before

        if fb_after > fb_before:
            if pid == 0: p1_fallbacks += 1
            else: p2_fallbacks += 1

        pname = f"P{pid+1}"
        if move is not None and game.validate_move(state, move):
            mtype = move[0]
            if mtype == 'place':
                idx = move[1]
                inv = game.inventories[pid]
                card = inv[idx] if 0 <= idx < len(inv) else None
                label = f"{card_label(card)} ({move[2]}→{move[3]})"
                if pid == 0: p1_played.append(label); p1_place += 1
                else:        p2_played.append(label); p2_place += 1
            elif mtype == 'draw':
                if pid == 0: p1_draw += 1
                else:        p2_draw += 1
            elif mtype == 'complete':
                # Capture what objectives were being targeted before scoring
                targets = [o.route_desc for o in game.objectives[pid]]
                if pid == 0: p1_complete += 1; p1_targeted.append(targets)
                else:        p2_complete += 1; p2_targeted.append(targets)

            before_completed = len(game.completed_objectives[pid])
            state = game.execute_move(state, move)
            after_completed = len(game.completed_objectives[pid])

            if mtype == 'complete' and after_completed > before_completed:
                if pid == 0: p1_complete_scored += 1
                else:        p2_complete_scored += 1

            if after_completed > before_completed:
                new_objs = game.completed_objectives[pid][before_completed:]
                for obj in new_objs:
                    unit = "µF" if getattr(obj, 'objective_type', 'resistance') == "capacitance" else "Ω"
                    actual, verified, rails_ok = _verify_objective(game, pid, obj)
                    status = "✓" if verified else "✗"
                    action_log.append(
                        f"T{state['turn_count']} {pname}: ✓ {obj.route_desc} +{obj.points}pts")
                    entry = (f"{int(obj.target_req)}{unit} ({obj.points}pts) {obj.route_desc} "
                             f"[actual={actual:.1f}{unit} rails={'Y' if rails_ok else 'N'} {status}]")
                    if not verified:
                        print(f"  *** VERIFICATION FAILED M{match_id} P{pid}: "
                              f"target={obj.target_req}{unit} actual={actual:.1f}{unit} "
                              f"rails={rails_ok} obj={obj.route_desc}")
                        if pid == 0: p1_verify_fails += 1
                        else: p2_verify_fails += 1
                    if pid == 0: p1_objs_completed.append(entry)
                    else: p2_objs_completed.append(entry)
        else:
            if pid == 0: p1_invalid += 1
            else: p2_invalid += 1
            game._end_turn(state)

        if save_frames and frame_dir:
            draw_board(game, f"{frame_dir}/frame_{frame_idx:03d}.png",
                       title=f"Match {match_id} — Turn {state['turn_count']}  P1:{game.scores[0]} P2:{game.scores[1]}",
                       action_log=action_log)
            frame_idx += 1

        if state['turn_count'] > 200:
            break

    elapsed = time.time() - t0
    winner = game.get_winner_idx()
    winner_str = "P1" if winner == 0 else ("P2" if winner == 1 else "Draw")

    # ── API guard: void match if LLM fell back too heavily ──
    voided = False
    void_reason = ""
    if min_api_rate > 0.0:
        p1_rate = _effective_api_rate(p1_api_success, p1_fallbacks)
        p2_rate = _effective_api_rate(p2_api_success, p2_fallbacks)
        if p1_rate is not None and p1_rate < min_api_rate:
            voided = True
            void_reason = f"P1 API rate {p1_rate:.0%} < {min_api_rate:.0%}"
        if p2_rate is not None and p2_rate < min_api_rate:
            voided = True
            r = f"P2 API rate {p2_rate:.0%} < {min_api_rate:.0%}"
            void_reason = f"{void_reason}; {r}" if void_reason else r

    if save_frames:
        p0_highlight = game.get_player_circuit_components(0) if game.scores[0] > 0 else []
        p1_highlight = game.get_player_circuit_components(1) if game.scores[1] > 0 else []
        all_highlights = p0_highlight + p1_highlight
        draw_board(game, f"{frame_dir}/final_snapshot.png",
                   title=f"Match {match_id} — FINAL  P1:{game.scores[0]} P2:{game.scores[1]}  Winner: {winner_str}",
                   highlight_comps=all_highlights if all_highlights else None,
                   action_log=action_log)
        if make_video and frame_idx > 0:
            _stitch_video(frame_dir, f"visuals/pvp_match_{match_id:03d}.mp4")

    p1_bd = _score_breakdown(p1_objs_completed)
    p2_bd = _score_breakdown(p2_objs_completed)

    return {
        "match": match_id,
        "p1_type": p1_type, "p2_type": p2_type,
        "p1_model": p1_model if p1_type != "heuristic" else "heuristic",
        "p2_model": p2_model if p2_type != "heuristic" else "heuristic",
        "winner": winner_str,
        "turns": state['turn_count'],
        "p1_score": game.scores[0], "p2_score": game.scores[1],
        "p1_obj_count": len(p1_objs_completed), "p2_obj_count": len(p2_objs_completed),
        "p1_place": p1_place, "p2_place": p2_place,
        "p1_draw": p1_draw, "p2_draw": p2_draw,
        "p1_complete": p1_complete, "p2_complete": p2_complete,
        "p1_complete_scored": p1_complete_scored, "p2_complete_scored": p2_complete_scored,
        "p1_pts_series": p1_bd['series'], "p2_pts_series": p2_bd['series'],
        "p1_pts_parallel": p1_bd['parallel'], "p2_pts_parallel": p2_bd['parallel'],
        "p1_pts_mixed": p1_bd['mixed'], "p2_pts_mixed": p2_bd['mixed'],
        "p1_pts_bridge": p1_bd['bridge'], "p2_pts_bridge": p2_bd['bridge'],
        "p1_pts_cap": p1_bd['cap'], "p2_pts_cap": p2_bd['cap'],
        "p1_invalid": p1_invalid, "p2_invalid": p2_invalid,
        "p1_api_ok": p1_api_success, "p2_api_ok": p2_api_success,
        "p1_api_total": p1_api_attempts, "p2_api_total": p2_api_attempts,
        "p1_fallbacks": p1_fallbacks, "p2_fallbacks": p2_fallbacks,
        "p1_verify_fails": p1_verify_fails, "p2_verify_fails": p2_verify_fails,
        "voided": "1" if voided else "0",
        "void_reason": void_reason,
        "elapsed": elapsed,
        # internal only (not written to summary CSV):
        "p1_played": p1_played, "p2_played": p2_played,
        "p1_objectives": p1_objs_completed, "p2_objectives": p2_objs_completed,
        "p1_targeted": p1_targeted, "p2_targeted": p2_targeted,
    }


def _stitch_video(frame_dir, mp4_path):
    try:
        import imageio, numpy as np
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        frames = sorted(os.listdir(frame_dir))
        if not frames:
            return
        os.makedirs("visuals", exist_ok=True)
        # Use the first frame's size as canonical; resize all others to match
        first = Image.open(os.path.join(frame_dir, frames[0])).convert('RGB')
        # Round up to nearest multiple of 16 for codec compatibility
        w = ((first.width  + 15) // 16) * 16
        h = ((first.height + 15) // 16) * 16
        target_size = (w, h)
        writer = imageio.get_writer(mp4_path, fps=3)
        for fname in frames:
            img = Image.open(os.path.join(frame_dir, fname)).convert('RGB')
            if img.size != target_size:
                img = img.resize(target_size, Image.LANCZOS)
            writer.append_data(np.array(img))
        writer.close()
        print(f"  Video: {mp4_path} ({os.path.getsize(mp4_path)//1024}KB)")
    except Exception as e:
        print(f"  Video error: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--p1", default="heuristic", choices=["heuristic", "ollama", "hybrid"])
    parser.add_argument("--p2", default="heuristic", choices=["heuristic", "ollama", "hybrid"])
    parser.add_argument("--p1-model", default="llama3.3:70b", dest="p1_model")
    parser.add_argument("--p2-model", default="llama3.3:70b", dest="p2_model")
    parser.add_argument("--min-api-rate", type=float, default=0.0, dest="min_api_rate",
                        help="Void match if any LLM player's API success rate falls below this (0.0 = disabled)")
    parser.add_argument("-m", "--matches", type=int, default=1)
    parser.add_argument("--mode", default="resistance", choices=["resistance", "capacitance"])
    parser.add_argument("--visual", action="store_true",
                        help="Save all frames + stitch MP4 video")
    parser.add_argument("--save-frames", action="store_true", dest="save_frames",
                        help="Save frames and final_snapshot.png without stitching video")
    parser.add_argument("--frames-dir", default="frames_pvp", dest="frames_dir",
                        help="Base directory for frame output (default: frames_pvp)")
    parser.add_argument("--trace", action="store_true",
                        help="Write per-turn LLM trace to {output}_trace.jsonl")
    parser.add_argument("--output", default="results/pvp_batch")
    args = parser.parse_args()

    os.makedirs("results", exist_ok=True)
    csv_path = f"{args.output}.csv"
    detail_csv = f"{args.output}_details.csv"

    header = [
        "match", "p1_model", "p2_model", "winner", "turns", "p1_score", "p2_score",
        "p1_obj_count", "p2_obj_count",
        "p1_place", "p2_place", "p1_draw", "p2_draw",
        "p1_complete", "p2_complete", "p1_complete_scored", "p2_complete_scored",
        "p1_pts_series", "p2_pts_series", "p1_pts_parallel", "p2_pts_parallel",
        "p1_pts_mixed", "p2_pts_mixed", "p1_pts_bridge", "p2_pts_bridge",
        "p1_pts_cap", "p2_pts_cap",
        "p1_invalid", "p2_invalid", "p1_api_ok", "p2_api_ok",
        "p1_api_total", "p2_api_total", "p1_fallbacks", "p2_fallbacks",
        "p1_verify_fails", "p2_verify_fails", "voided", "void_reason", "elapsed",
    ]
    with open(csv_path, 'w', newline='') as f:
        csv.DictWriter(f, fieldnames=header).writeheader()

    p1_label = args.p1_model if args.p1 != "heuristic" else "heuristic"
    p2_label = args.p2_model if args.p2 != "heuristic" else "heuristic"
    print(f"PvP: {p1_label} (P1) vs {p2_label} (P2) — {args.matches} matches")
    if args.min_api_rate > 0:
        print(f"API guard: void if rate < {args.min_api_rate:.0%}")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    trace_path = f"{args.output}_trace.jsonl" if args.trace else None
    trace_fh = open(trace_path, 'w') if trace_path else None
    if trace_path:
        print(f"Trace: {trace_path}")

    results = []
    try:
        for m in range(args.matches):
            r = run_match(m + 1, args.p1, args.p2, args.p1_model, args.p2_model,
                          min_api_rate=args.min_api_rate,
                          save_frames=args.visual or args.save_frames,
                          make_video=args.visual,
                          frames_base_dir=args.frames_dir,
                          mode=args.mode,
                          trace_file=trace_fh)
            results.append(r)

            with open(csv_path, 'a', newline='') as f:
                row = {k: r[k] for k in header}
                csv.DictWriter(f, fieldnames=header).writerow(row)

            void_tag = " [VOID]" if r['voided'] == "1" else ""
            status = "✓" if r['winner'] != 'Draw' else "—"
            p1_rate = _effective_api_rate(r['p1_api_ok'], r['p1_fallbacks'])
            p2_rate = _effective_api_rate(r['p2_api_ok'], r['p2_fallbacks'])
            rate_str = (f"P1={p1_rate:.0%}" if p1_rate is not None else "P1=—") + " " + \
                       (f"P2={p2_rate:.0%}" if p2_rate is not None else "P2=—")
            print(f"  [{status}] M{r['match']:3d} | {r['winner']:>4s} | "
                  f"P1={r['p1_score']:3d} P2={r['p2_score']:3d} | "
                  f"{r['turns']:2d}t | {r['elapsed']:.0f}s | "
                  f"LLM%: {rate_str}{void_tag}")
    finally:
        if trace_fh:
            trace_fh.close()

    # ── Summary (exclude voided) ──
    valid = [r for r in results if r['voided'] == "0"]
    voided_count = len(results) - len(valid)
    p1_wins = sum(1 for r in valid if r['winner'] == 'P1')
    p2_wins = sum(1 for r in valid if r['winner'] == 'P2')
    draws   = sum(1 for r in valid if r['winner'] == 'Draw')
    scored  = sum(1 for r in valid if r['p1_score'] > 0 or r['p2_score'] > 0)
    avg_turns = sum(r['turns'] for r in valid) / len(valid) if valid else 0
    avg_time  = sum(r['elapsed'] for r in results) / len(results) if results else 0

    print(f"\n{'='*70}")
    print(f"SUMMARY — {args.matches} matches ({voided_count} voided, {len(valid)} valid)")
    print(f"  {p1_label} wins: {p1_wins} | {p2_label} wins: {p2_wins} | Draws: {draws}")
    print(f"  Matches with scoring: {scored}/{len(valid)}")
    print(f"  Avg turns: {avg_turns:.1f} | Avg time: {avg_time:.1f}s")
    print(f"  End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"Summary CSV: {csv_path}")

    with open(detail_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            "match", "player", "model", "winner", "voided", "score",
            "obj_count", "place_count", "draw_count", "complete_count", "complete_scored",
            "pts_series", "pts_parallel", "pts_mixed", "pts_bridge", "pts_cap",
            "played_cards", "objectives_completed", "objectives_targeted",
        ])
        for r in results:
            winner = r['winner']
            for pid_str, pfx, model_key in [("P1", "p1", "p1_model"), ("P2", "p2", "p2_model")]:
                bd = _score_breakdown(r[f'{pfx}_objectives'])
                targeted_str = "; ".join(
                    " | ".join(ts) for ts in r[f'{pfx}_targeted']
                )
                w.writerow([
                    r['match'], pid_str, r[model_key],
                    "WIN" if winner == pid_str else "", r['voided'],
                    r[f'{pfx}_score'],
                    r[f'{pfx}_obj_count'],
                    r[f'{pfx}_place'], r[f'{pfx}_draw'],
                    r[f'{pfx}_complete'], r[f'{pfx}_complete_scored'],
                    bd['series'], bd['parallel'], bd['mixed'], bd['bridge'], bd['cap'],
                    " | ".join(r[f'{pfx}_played']),
                    " | ".join(r[f'{pfx}_objectives']),
                    targeted_str,
                ])
    print(f"Detail CSV: {detail_csv}")
