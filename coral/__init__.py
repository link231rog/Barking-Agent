"""CORAL - Orchestration system for autonomous coding agents."""

try:
    __version__ = version("coral")
except Exception:
    __version__ = "0.1.0.dev0"

from coral.config import CoralConfig
from coral.types import Attempt, Score, ScoreBundle, Task

__all__ = [
    "Attempt",
    "CoralConfig",
    "Score",
    "ScoreBundle",
    "Task",
]
