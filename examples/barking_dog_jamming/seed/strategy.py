"""Seed Operational Strategy for Autonomous Robot Dog Jammer Neutralization.

CUMCM 2026 Problem B: Radio Jammer Search and Neutralization via Autonomous Robot Dog.
This file serves as the initial seed program that autonomous agents in CORAL
can mutate, evolve, and optimize.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

Point = Tuple[float, float]

# -----------------------------------------------------------------------------
# Evolving Strategy Hyperparameters (Search Space for Autonomous Agents)
# -----------------------------------------------------------------------------
PROXIMITY_IMMEDIATE_RADIUS_M = 150.0       # Immediate strike threshold without rerouting
CLOSE_CANDIDATE_RADIUS_M = 650.0           # Local cluster search radius
CORRIDOR_FORWARD_WINDOW_DEG = 45.0         # Primary forward angular search corridor
CORRIDOR_SOFT_PENALTY_WEIGHT = 5.0         # Angular deviation penalty coefficient
REAR_GUARD_MIN_DEG = -35.0                 # Bounded rear cleanup minimum angle
REAR_GUARD_MAX_DEG = 0.0                   # Bounded rear cleanup maximum angle
SNIFF_THROTTLE_DISPLACEMENT_M = 850.0      # Spatial displacement threshold for silent sniffing
OUTPOST_COVERAGE_RADIUS_M = 750.0          # Uncovered sector outpost fallback coverage


def deg2rad(deg: float) -> float:
    return math.radians(deg)


def rad2deg(rad: float) -> float:
    return math.degrees(rad) % 360.0


def angle_diff_deg(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def dist(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def directed_angle_diff(cur_ang: float, tgt_ang: float, is_cw: bool) -> float:
    diff = (tgt_ang - cur_ang + 180.0) % 360.0 - 180.0
    return diff if is_cw else -diff


def solve_multiray_lsq(rays: List[Tuple[Point, float]]) -> Optional[Point]:
    """Linear Least Squares solver for intersection of N bearing rays."""
    if len(rays) < 2:
        return None
    A11, A12, A22 = 0.0, 0.0, 0.0
    B1, B2 = 0.0, 0.0
    for (x0, y0), deg in rays:
        rad = deg2rad(deg)
        nx = -math.sin(rad)
        ny = math.cos(rad)
        c = nx * x0 + ny * y0
        A11 += nx * nx
        A12 += nx * ny
        A22 += ny * ny
        B1 += nx * c
        B2 += ny * c
    det = A11 * A22 - A12 * A12
    if abs(det) < 1e-6:
        return None
    return ((B1 * A22 - B2 * A12) / det, (B2 * A11 - B1 * A12) / det)


def get_best_sweep_direction(heard_angles: List[float]) -> Tuple[float, bool]:
    """Largest Empty Wedge theorem: find largest gap and advance from edge."""
    if not heard_angles:
        return 0.0, True
    if len(heard_angles) == 1:
        return heard_angles[0], True
    sorted_angles = sorted(heard_angles)
    n = len(sorted_angles)
    gaps = []
    for i in range(n):
        next_ang = sorted_angles[(i + 1) % n]
        gap = (next_ang - sorted_angles[i]) % 360.0
        gaps.append((gap, sorted_angles[i], next_ang))
    gaps.sort(key=lambda x: x[0], reverse=True)
    max_gap, ang_start, ang_end = gaps[0]
    return ang_end, True


class TargetBelief:
    def __init__(self, channel: int):
        self.channel = channel
        self.rays: List[Tuple[Point, float]] = []
        self.center_est: Optional[Point] = None
        self.is_cleared = False
        self.attempt_count = 0
        self.probe_positions: List[Point] = []
        self.last_probe_pos: Optional[Point] = None

    def add_ray(self, st: Point, deg: float):
        for s, d in self.rays:
            if dist(s, st) < 5.0 and abs(angle_diff_deg(d, deg)) < 1.0:
                return
        self.rays.append((st, deg))


class DynamicScheduler:
    """Target-as-Anchor Gated Polar Corridor Scheduler."""

    def __init__(self, sim: Any):
        self.sim = sim
        self.dog_pos: Point = (0.0, 0.0)
        self.total_dist: float = 0.0
        self.virtual_time: float = 0.0
        self.beliefs: Dict[int, TargetBelief] = {ch: TargetBelief(ch) for ch in range(1, 21)}
        self.cleared_order: List[int] = []

    def move_to(self, x: float, y: float):
        r = math.hypot(x, y)
        if r > 1850.0:
            scale = 1850.0 / r
            x, y = x * scale, y * scale
        d = dist((x, y), self.dog_pos)
        self.total_dist += d
        self.virtual_time += d / 5.0
        self.dog_pos = (round(x, 2), round(y, 2))

    def measure(self, x: float, y: float, channel: int) -> Dict[str, Any]:
        self.move_to(x, y)
        if channel in self.cleared_order:
            return {"measure_result": "cleared"}
        res = self.sim.measure(x=self.dog_pos[0], y=self.dog_pos[1], channel=channel)
        self.virtual_time = res.get("virtual_time_s", self.virtual_time)
        res_type = res.get("measure_result")
        svd_deg = res.get("svd_deg")
        self.beliefs[channel].last_probe_pos = self.dog_pos
        self.beliefs[channel].probe_positions.append(self.dog_pos)
        if res_type == "direction" and svd_deg is not None:
            self.beliefs[channel].add_ray(self.dog_pos, svd_deg)
        elif res_type == "near":
            c_res = self.clear(self.dog_pos[0], self.dog_pos[1], channel)
            if c_res.get("clear_result") == "success":
                self.beliefs[channel].is_cleared = True
        return res

    def clear(self, x: float, y: float, channel: int) -> Dict[str, Any]:
        self.move_to(x, y)
        res = self.sim.clear(x=self.dog_pos[0], y=self.dog_pos[1], channel=channel)
        self.virtual_time = res.get("virtual_time_s", self.virtual_time)
        if res.get("clear_result") == "success":
            self.beliefs[channel].is_cleared = True
            if channel not in self.cleared_order:
                self.cleared_order.append(channel)
        return res

    def get_undiscovered_count(self, total_targets: int) -> int:
        known = sum(1 for c in range(1, 21) if len(self.beliefs[c].rays) > 0 or self.beliefs[c].is_cleared)
        return max(0, total_targets - known)

    def sniff_silent_channels(self, total_targets: int, force: bool = False):
        if self.get_undiscovered_count(total_targets) <= 0:
            return
        rem_silent = [c for c in range(1, 21) if not self.beliefs[c].is_cleared and len(self.beliefs[c].rays) == 0]
        for c in rem_silent:
            b = self.beliefs[c]
            if not force and any(dist(self.dog_pos, p) < SNIFF_THROTTLE_DISPLACEMENT_M for p in b.probe_positions):
                continue
            self.measure(self.dog_pos[0], self.dog_pos[1], c)

    def estimate_target_pos(self, b: TargetBelief) -> Point:
        if b.center_est:
            return b.center_est
        if len(b.rays) >= 2:
            est = solve_multiray_lsq(b.rays)
            if est and math.hypot(est[0], est[1]) <= 1900.0:
                b.center_est = est
                return est
        if len(b.rays) == 1:
            p0, deg = b.rays[-1]
            rad = deg2rad(deg)
            vx, vy = math.cos(rad), math.sin(rad)
            default_r = 500.0 if dist(p0, (0.0, 0.0)) > 300.0 else 950.0
            return (p0[0] + default_r * vx, p0[1] + default_r * vy)
        return self.dog_pos

    def get_target_polar_angle(self, b: TargetBelief) -> float:
        est = self.estimate_target_pos(b)
        if math.hypot(est[0], est[1]) > 10.0:
            return rad2deg(math.atan2(est[1], est[0]))
        return b.rays[0][1] if len(b.rays) > 0 else 0.0

    def strike(self, ch: int) -> bool:
        b = self.beliefs[ch]
        if b.is_cleared:
            return True
        b.attempt_count += 1
        if b.attempt_count > 6:
            return False

        # Build baseline if only 1 ray exists
        if len(b.rays) == 1 and dist(self.dog_pos, (0.0, 0.0)) > 200.0:
            if dist(self.dog_pos, b.rays[0][0]) > 150.0:
                self.measure(self.dog_pos[0], self.dog_pos[1], ch)
                if b.is_cleared:
                    return True

        est = solve_multiray_lsq(b.rays)
        if not est or math.hypot(est[0], est[1]) > 1900.0:
            last_p, last_deg = b.rays[-1]
            rad_l = deg2rad(last_deg)
            default_d = 450.0 if dist(last_p, (0.0, 0.0)) > 300.0 else 750.0
            est = (last_p[0] + default_d * math.cos(rad_l), last_p[1] + default_d * math.sin(rad_l))
        b.center_est = est

        res_c = self.clear(est[0], est[1], ch)
        if res_c.get("clear_result") == "success":
            return True

        # Recovery guidance if miss
        for _ in range(2):
            if b.is_cleared:
                return True
            res_m = self.measure(self.dog_pos[0], self.dog_pos[1], ch)
            if b.is_cleared:
                return True
            if res_m.get("measure_result") == "near":
                return self.clear(self.dog_pos[0], self.dog_pos[1], ch).get("clear_result") == "success"
            elif res_m.get("measure_result") == "direction":
                rad = deg2rad(res_m["svd_deg"])
                lat_x = self.dog_pos[0] - math.sin(rad) * 60.0
                lat_y = self.dog_pos[1] + math.cos(rad) * 60.0
                self.measure(lat_x, lat_y, ch)
                if b.is_cleared:
                    return True
                new_est = solve_multiray_lsq(b.rays[-2:]) or solve_multiray_lsq(b.rays)
                if new_est and math.hypot(new_est[0], new_est[1]) <= 1900.0:
                    b.center_est = new_est
                    if self.clear(new_est[0], new_est[1], ch).get("clear_result") == "success":
                        return True
        return b.is_cleared

    def run(self) -> Dict[str, Any]:
        self.sim.enter()
        total_targets = self.sim.num_targets if hasattr(self.sim, "num_targets") else 15

        # 1. Origin full-band sweep
        for ch in range(1, 21):
            self.measure(0.0, 0.0, ch)

        heard_angles = [self.beliefs[c].rays[0][1] for c in range(1, 21) if len(self.beliefs[c].rays) > 0]
        start_ang, is_cw = get_best_sweep_direction(heard_angles)

        # 2. Polar corridor progression
        current_frontier = start_ang
        visited_outposts: Set[float] = set()

        while len(self.cleared_order) < total_targets:
            cands = []
            for c in range(1, 21):
                b = self.beliefs[c]
                if b.is_cleared or b.attempt_count >= 5 or len(b.rays) == 0:
                    continue
                ang = self.get_target_polar_angle(b)
                rel_ang = directed_angle_diff(current_frontier, ang, is_cw)
                est = self.estimate_target_pos(b)
                d = dist(self.dog_pos, est)
                cands.append((rel_ang, d, c, est))

            if not cands:
                undiscovered = self.get_undiscovered_count(total_targets)
                if undiscovered > 0:
                    best_op = None
                    best_op_diff = 999.0
                    for s_idx in range(6):
                        s_deg = s_idx * 60.0
                        if s_deg in visited_outposts:
                            continue
                        op_rel = directed_angle_diff(current_frontier, s_deg, is_cw)
                        op_fwd = op_rel if op_rel >= 0 else op_rel + 360.0
                        if op_fwd < best_op_diff:
                            best_op_diff = op_fwd
                            best_op = s_deg
                    if best_op is not None:
                        visited_outposts.add(best_op)
                        s_rad = deg2rad(best_op)
                        self.move_to(900.0 * math.cos(s_rad), 900.0 * math.sin(s_rad))
                        current_frontier = best_op
                        self.sniff_silent_channels(total_targets, force=True)
                        continue
                break

            # Immediate proximity rule
            immediate = [c for c in cands if c[1] <= PROXIMITY_IMMEDIATE_RADIUS_M]
            if immediate:
                fwd_imm = [c for c in immediate if c[0] >= 0.0]
                target_cand = min(fwd_imm, key=lambda x: x[1]) if fwd_imm else min(immediate, key=lambda x: x[1])
            else:
                close = [c for c in cands if c[1] <= CLOSE_CANDIDATE_RADIUS_M]
                if close:
                    rear_close = [c for c in close if REAR_GUARD_MIN_DEG <= c[0] < REAR_GUARD_MAX_DEG]
                    target_cand = min(rear_close, key=lambda x: x[0]) if rear_close else min(close, key=lambda x: x[1])
                else:
                    fwd_cands = [c for c in cands if c[0] >= 0.0]
                    if not fwd_cands:
                        target_cand = min(cands, key=lambda x: x[1])
                    else:
                        fwd_window = [c for c in fwd_cands if c[0] <= CORRIDOR_FORWARD_WINDOW_DEG]
                        if fwd_window:
                            target_cand = min(fwd_window, key=lambda x: x[1] + CORRIDOR_SOFT_PENALTY_WEIGHT * x[0])
                        else:
                            target_cand = min(fwd_cands, key=lambda x: x[0])

            _, _, tc, _ = target_cand
            if self.strike(tc):
                t_ang = self.get_target_polar_angle(self.beliefs[tc])
                t_rel = directed_angle_diff(current_frontier, t_ang, is_cw)
                if t_rel > 0.0:
                    current_frontier = t_ang
                self.sniff_silent_channels(total_targets, force=False)

        # 3. Final mop-up sweep
        for _ in range(2):
            rem = [c for c in range(1, 21) if not self.beliefs[c].is_cleared and len(self.beliefs[c].rays) > 0]
            if not rem or len(self.cleared_order) >= total_targets:
                break
            rem.sort(key=lambda c: dist(self.dog_pos, self.estimate_target_pos(self.beliefs[c])))
            for c in rem:
                if len(self.cleared_order) >= total_targets:
                    break
                self.strike(c)
                self.sniff_silent_channels(total_targets, force=False)

        # 4. Outpost directional blind clearance
        if len(self.cleared_order) < total_targets:
            cleared_pts = [self.beliefs[c].center_est for c in self.cleared_order if self.beliefs[c].center_est]
            for s_idx in range(6):
                if len(self.cleared_order) >= total_targets:
                    break
                s_deg = (start_ang + (s_idx if is_cw else -s_idx) * 60.0) % 360.0
                s_rad = deg2rad(s_deg)
                op_pos = (900.0 * math.cos(s_rad), 900.0 * math.sin(s_rad))
                if any(dist(op_pos, cp) < OUTPOST_COVERAGE_RADIUS_M for cp in cleared_pts):
                    continue
                self.move_to(op_pos[0], op_pos[1])
                self.sniff_silent_channels(total_targets, force=True)
                rem = [c for c in range(1, 21) if not self.beliefs[c].is_cleared and len(self.beliefs[c].rays) > 0]
                rem.sort(key=lambda c: dist(self.dog_pos, self.estimate_target_pos(self.beliefs[c])))
                for c in rem:
                    self.strike(c)
                    if len(self.cleared_order) >= total_targets:
                        break

        self.sim.exit()
        n_cleared = len(self.cleared_order)
        avg_time = self.virtual_time / max(n_cleared, 1)
        return {
            "cleared": n_cleared,
            "total": total_targets,
            "dist": round(self.total_dist, 1),
            "time": round(self.virtual_time, 1),
            "avg_time": round(avg_time, 2),
        }


def run_mission(sim: Any) -> Dict[str, Any]:
    """Top-level entrypoint invoked by the evaluation harness."""
    sch = DynamicScheduler(sim)
    return sch.run()
