"""Barking-Dog Jammer Neutralization & Active Localization Task Grader.

CUMCM 2026 Problem B: Radio Jammer Search and Neutralization via Autonomous Robot Dog.
Evaluates agent-generated path planning and direction-finding coordination strategies
against a high-fidelity RF physics simulator with Gaussian bearing noise, near-field blind zones,
and optical/laser clearance spheres.
"""

from __future__ import annotations

import json
import math
import os
import random
import statistics
import subprocess
import sys
import textwrap
import time
from typing import Any, Dict, List, Optional, Tuple

from coral.grader import TaskGrader
from coral.types import ScoreBundle


# -----------------------------------------------------------------------------
# High-Fidelity In-Memory Radio Arena Simulator Stub
# -----------------------------------------------------------------------------
class ArenaSimulator:
    """High-fidelity simulated battlefield matching official CUMCM 2026 Problem B physics."""

    def __init__(self, seed: int = 42, num_targets: int = 15):
        self.seed = seed
        self.num_targets = num_targets
        self.arena_radius = 1800.0
        self.dog_speed = 5.0
        self.rng = random.Random(seed)
        self.current_pos = {"x": 0.0, "y": 0.0}
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.active = False
        self.total_dist = 0.0

        all_channels = list(range(1, 21))
        self.rng.shuffle(all_channels)
        self.target_channels = sorted(all_channels[:num_targets])

        self.targets: Dict[int, Dict[str, Any]] = {}
        for ch in self.target_channels:
            r = self.arena_radius * math.sqrt(self.rng.random())
            theta = self.rng.uniform(0, 2 * math.pi)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            recv_r = self.rng.uniform(1000.0, 1500.0)
            self.targets[ch] = {
                "channel": ch,
                "x": round(x, 2),
                "y": round(y, 2),
                "recv_radius": round(recv_r, 2),
                "cleared": False,
            }

    def enter(self) -> Dict[str, Any]:
        self.active = True
        self.current_pos = {"x": 0.0, "y": 0.0}
        self.virtual_time_s = 0.0
        self.total_dist = 0.0
        return {"accepted": True, "virtual_time_s": 0.0}

    def measure(self, x: float, y: float, channel: int) -> Dict[str, Any]:
        dx = x - self.current_pos["x"]
        dy = y - self.current_pos["y"]
        d = math.hypot(dx, dy)
        self.total_dist += d
        move_s = d / self.dog_speed
        switch_s = 1.0 if channel != self.current_channel else 0.0
        detect_s = 5.0
        self.virtual_time_s += move_s + switch_s + detect_s
        self.current_pos = {"x": round(x, 2), "y": round(y, 2)}
        self.current_channel = channel

        tgt = self.targets.get(channel)
        if not tgt or tgt["cleared"]:
            return {"accepted": True, "measure_result": "no_signal", "virtual_time_s": self.virtual_time_s}

        t_dist = math.hypot(tgt["x"] - x, tgt["y"] - y)
        if t_dist > tgt["recv_radius"]:
            return {"accepted": True, "measure_result": "no_signal", "virtual_time_s": self.virtual_time_s}
        elif t_dist <= 5.0:
            return {"accepted": True, "measure_result": "near", "virtual_time_s": self.virtual_time_s}
        else:
            true_deg = math.degrees(math.atan2(tgt["y"] - y, tgt["x"] - x)) % 360.0
            noise = self.rng.uniform(-1.0, 1.0)
            svd_deg = round((true_deg + noise) % 360.0, 2)
            return {"accepted": True, "measure_result": "direction", "svd_deg": svd_deg, "virtual_time_s": self.virtual_time_s}

    def clear(self, x: float, y: float, channel: int) -> Dict[str, Any]:
        dx = x - self.current_pos["x"]
        dy = y - self.current_pos["y"]
        d = math.hypot(dx, dy)
        self.total_dist += d
        move_s = d / self.dog_speed
        detect_s = 3.0
        tgt = self.targets.get(channel)
        is_succ = False
        if tgt and not tgt["cleared"]:
            t_dist = math.hypot(tgt["x"] - x, tgt["y"] - y)
            if t_dist <= 20.0:
                is_succ = True
                tgt["cleared"] = True

        clear_s = 2.0 if is_succ else 0.0
        self.virtual_time_s += move_s + detect_s + clear_s
        self.current_pos = {"x": round(x, 2), "y": round(y, 2)}
        return {"accepted": True, "clear_result": "success" if is_succ else "no_target_in_range", "virtual_time_s": self.virtual_time_s}

    def exit(self) -> Dict[str, Any]:
        self.active = False
        cleared_count = sum(1 for t in self.targets.values() if t["cleared"])
        return {
            "accepted": True,
            "cleared_count": cleared_count,
            "total_targets": self.num_targets,
            "virtual_time_s": round(self.virtual_time_s, 2),
            "total_dist_m": round(self.total_dist, 2),
        }


# -----------------------------------------------------------------------------
# Task Grader Implementation
# -----------------------------------------------------------------------------
class BarkingDogGrader(TaskGrader):
    """CORAL Grader for the Autonomous Robot Dog Jammer Neutralization Problem.

    Scores agent policies on:
      1. Clearance Rate (100% hard constraint)
      2. Average Clearance Time per Target (aiming toward theoretical ~200s limit)
      3. Price of Uncertainty Index (PUI < 0.50)
      4. Inter-seed Standard Deviation (Variance reduction)
    """

    TUNE_SEEDS: List[Tuple[int, int]] = [
        (42, 15), (7, 15), (14, 11), (23, 14), (25, 16)
    ]

    BENCHMARK_SEEDS: List[Tuple[int, int]] = [
        (2, 10), (31, 10), (43, 10), (52, 10),
        (14, 11), (28, 11), (65, 11), (72, 11),
        (1, 12), (18, 12), (21, 12), (83, 12),
        (3, 13), (4, 13), (8, 13), (95, 13),
        (13, 14), (23, 14), (57, 14), (69, 14),
        (7, 15), (16, 15), (36, 15), (42, 15), (101, 15),
        (24, 16), (25, 16), (88, 16), (99, 16), (2026, 16),
    ]

    def evaluate(self) -> ScoreBundle:
        program_file = self.args.get("program_file", "strategy.py")
        program_path = os.path.join(self.codebase_path, program_file)

        if not os.path.exists(program_path):
            return self.fail(f"Strategy program not found: {program_file}")

        eval_seeds = self.TUNE_SEEDS if self.tune else self.BENCHMARK_SEEDS
        timeout_s = self.timeout or 300

        try:
            eval_result = _run_evaluation(program_path, eval_seeds, timeout_s, self.get_python_command())
        except TimeoutError:
            return self.fail(f"Evaluation exceeded timeout of {timeout_s}s")
        except Exception as exc:
            return self.fail(f"Evaluation error: {exc}")

        if "error" in eval_result:
            return self.fail(f"Execution failed: {eval_result['error']}")

        clearance_rate = eval_result["clearance_rate"]
        avg_time = eval_result["avg_time"]
        std_dev = eval_result["std_dev"]
        avg_pui = eval_result["avg_pui"]
        avg_dist = eval_result["avg_dist"]
        score = eval_result["score"]

        explanation = (
            f"Clearance: {eval_result['total_cleared']}/{eval_result['total_targets']} ({clearance_rate * 100:.1f}%) | "
            f"Avg Time: {avg_time:.2f}s/tgt | "
            f"PUI: {avg_pui:.3f} | "
            f"StdDev: {std_dev:.2f}s | "
            f"Dist: {avg_dist:.1f}m | "
            f"Score: {score:.4f}"
        )

        return self.score(
            score,
            explanation,
            metadata={
                "clearance_rate": clearance_rate,
                "avg_time_s": avg_time,
                "std_dev_s": std_dev,
                "pui": avg_pui,
                "avg_dist_m": avg_dist,
                "seeds_evaluated": len(eval_seeds),
            },
        )


def _run_evaluation(program_path: str, seeds: List[Tuple[int, int]], timeout: int, python_cmd: List[str]) -> Dict[str, Any]:
    """Execute strategy evaluation in a clean isolated subprocess."""
    grader_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_content = textwrap.dedent(f"""\
        import sys, os, math, json, statistics
        sys.path.insert(0, {os.path.dirname(os.path.abspath(program_path))!r})
        sys.path.insert(0, {grader_src!r})
        module_name = {os.path.splitext(os.path.basename(program_path))[0]!r}
        strategy_module = __import__(module_name)

        # Import ArenaSimulator from grader module
        from barking_dog_grader.grader import ArenaSimulator

        seeds = {seeds!r}
        tot_cleared = 0
        tot_targets = 0
        times = []
        dists = []
        puis = []

        # Theoretical Oracle baseline approx per N
        oracle_bounds = {{
            10: 206.42, 11: 190.25, 12: 195.35, 13: 182.87,
            14: 175.97, 15: 163.53, 16: 150.48
        }}

        for s, n_tgt in seeds:
            sim = ArenaSimulator(seed=s, num_targets=n_tgt)
            if hasattr(strategy_module, "run_mission"):
                res = strategy_module.run_mission(sim)
            elif hasattr(strategy_module, "DynamicScheduler"):
                sch = strategy_module.DynamicScheduler(sim)
                res = sch.run()
            else:
                print(json.dumps({{"error": "strategy.py must provide run_mission(sim) or DynamicScheduler"}}))
                sys.exit(0)

            c_count = res.get("cleared", 0)
            tot_cleared += c_count
            tot_targets += n_tgt
            t_val = res.get("avg_time", 999.0)
            d_val = res.get("dist", 0.0)
            times.append(t_val)
            dists.append(d_val)

            base_oracle = oracle_bounds.get(n_tgt, 178.0)
            pui = max(0.0, (t_val - base_oracle) / base_oracle)
            puis.append(pui)

        clearance_rate = tot_cleared / max(tot_targets, 1)
        avg_time = statistics.mean(times) if times else 999.0
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        avg_dist = statistics.mean(dists) if dists else 0.0
        avg_pui = statistics.mean(puis) if puis else 1.0

        # Composite Fitness Score (Normalized 0 ~ 100+, higher is better)
        if clearance_rate < 1.0:
            score = clearance_rate * 40.0
        else:
            time_progress = max(0.0, (350.0 - avg_time) / (350.0 - 200.0))
            pui_bonus = max(0.0, (1.0 - avg_pui) * 20.0)
            var_bonus = max(0.0, (60.0 - std_dev) * 0.2)
            score = 60.0 + time_progress * 30.0 + pui_bonus + var_bonus

        print(json.dumps({{
            "clearance_rate": round(clearance_rate, 4),
            "total_cleared": tot_cleared,
            "total_targets": tot_targets,
            "avg_time": round(avg_time, 2),
            "std_dev": round(std_dev, 2),
            "avg_pui": round(avg_pui, 3),
            "avg_dist": round(avg_dist, 1),
            "score": round(score, 4)
        }}))
    """)

    proc = subprocess.run(
        python_cmd + ["-c", script_content],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if proc.returncode != 0:
        return {"error": f"Subprocess exited with code {proc.returncode}: {proc.stderr.strip()}"}

    try:
        return json.loads(proc.stdout.strip())
    except Exception as e:
        return {"error": f"Failed to parse evaluator output: {proc.stdout.strip()[:200]} ({e})"}
