# Examples

Example task configurations for CORAL. Each directory contains a `task.yaml` and any supporting files (graders, seed code, data).

To run any example:

```bash
coral start --config examples/<name>/task.yaml
```

Every task ships its grader as a standalone Python package — CORAL
bootstraps a fresh venv at `.coral/private/grader_venv/`, installs the
package via `grader.setup`, and runs evaluation in a worker subprocess
from there. No extra install step is required for the user.

## Task Structure

All tasks use the **packaged grader** layout:

```
my_task/
├── task.yaml              # references grader.entrypoint + grader.setup
├── seed/                  # initial codebase given to agents
│   └── solution.py
└── grader/                # standalone Python package
    ├── pyproject.toml
    └── src/my_task_grader/
        ├── __init__.py
        └── grader.py      # class Grader(TaskGrader): ...
```

### `task.yaml`

The central configuration file. All available fields (with defaults):

```yaml
task:
  name: "My Task"                    # Task name (required)
  description: |                     # Full problem description shown to agents (required)
    What the agent should do.
  tips: |                            # Hints shown to agents (timeouts, constraints, etc.)
    - Eval timeout is 120s.

grader:
  entrypoint: "my_task_grader.grader:Grader"   # required
  setup:                                        # shell commands run in .coral/private/grader_venv/
    - "uv pip install -e ./grader"
  timeout: 300                       # Max seconds per evaluation (default: 300)
  direction: maximize                # "maximize" or "minimize" (default: maximize)
  args:                              # Arbitrary kwargs accessible as self.args inside the grader
    program_file: "solution.py"
  private:                           # Files/dirs copied to .coral/private/ (hidden from agents)
    - "answers/"

agents:
  count: 1                           # Number of concurrent agents (default: 1)
  runtime: claude_code               # "claude_code", "opencode", or "codex" (default: claude_code)
  model: sonnet                      # Model name or path (default: sonnet)
  max_turns: 0                       # Max agent turns per session (default: 0 = no cap)
  timeout: 3600                      # Agent-level timeout in seconds (default: 3600)
  research: true                     # Enable web search / literature review (default: true)
  stagger_seconds: 0                 # Delay between spawning each agent (default: 0)
  gateway:                           # LiteLLM gateway for routing model traffic
    enabled: false
    port: 4000
    config: "./litellm_config.yaml"
    api_key: ""                      # Auto-generated if empty
  heartbeat:                         # Periodic agent self-reflection actions
    - name: reflect
      every: 1                       # Trigger every N evals
      global: false                  # false = per-agent count, true = global count
      trigger: interval              # "interval" or "plateau"
    - name: consolidate
      every: 10
      global: true
      trigger: interval
    - name: pivot
      every: 5
      trigger: plateau               # Triggers after N evals with no improvement

sharing:
  attempts: true                     # Share attempt history across agents (default: true)
  notes: true                        # Share notes across agents (default: true)
  skills: true                       # Share skills across agents (default: true)

workspace:
  repo_path: "./examples/my_task/seed"  # Path to seed directory (default: ".")
  results_dir: "./results"              # Where run outputs are stored (default: ./results)
  setup:                                # Shell commands run once per worktree before agents start
    - "uv pip install numpy scipy"

run:
  verbose: false                     # Verbose output (default: false)
  ui: false                          # Launch web dashboard (default: false)
  session: tmux                      # "local", "tmux", or "docker" (default: tmux)
  docker_image: ""                   # Custom docker image; empty = auto-build from docker/<runtime>/ (default: "")
```

### `grader/` (packaged)

A standalone Python package consumed by `grader.entrypoint`. Inherits from
`TaskGrader` and implements `evaluate()`. CORAL installs it into
`.coral/private/grader_venv/` so its dependencies stay separate from CORAL's
and from each agent's worktree env.

Hidden data the grader must keep from agents (answer keys, hidden test
fixtures) is declared under `grader.private` in task.yaml and read via
`self.private_dir` — CORAL copies those paths into `.coral/private/`, which
every agent runtime is denied read access to. Keep those paths **outside** the
`grader/` package (conventionally a sibling `taskdata/`, declared as
`taskdata`), because **everything inside `grader/` is visible to agents**: the
whole grader source is surfaced read-only at `<shared_dir>/grader/` so they can
read how they're scored, so a `grader.private` path inside `grader/` would leak
— `coral validate` errors on that. Non-secret bundled data (lookup tables,
helper modules) may live inside `grader/` and be read via `Path(__file__).parent`,
but it is visible — never put a secret there.

### `seed/`

The starting codebase that gets copied into each agent's git worktree. This is what agents see when they begin working. It should contain starter code (with a function signature the grader expects) and any data files the solution needs at runtime.

### Task Catalog

| Example | Description | Direction | Baseline Score |
|---------|-------------|-----------|----------------|
| [`barking_dog_jamming`](barking_dog_jamming) | CUMCM 2026 Problem B: Autonomous Robot Dog Radio Direction Finding & Jamming Countermeasures | Maximize | 81.72 |

## Details

### barking_dog_jamming

Evaluates autonomous robot dog navigation, bearing-only multi-station radio direction finding, and in-situ laser jammer neutralization in an adversarial circular combat theatre ($R=1750\,\text{m}$).
Evaluated across 30 standard contest seeds ($N \in [10, 16]$ random targets per seed, total 395 targets) with hard constraints on sensor accuracy, laser range, and attempt limits.

- **Agents**: Multi-agent co-evolution (Explorer, Strategist, Auditor)
- **Grader Package**: `barking-dog-grader`
- **Scoring**: Composite fitness function based on 100% clearance requirement, average time per target $\bar{T}$, path uncertainty index $\text{PUI}$, and variance reduction penalty.
- **Verification**: `coral validate examples/barking_dog_jamming`

## Writing Your Own

The quickest way to scaffold a new task is `coral init my-task`. To do it manually, create the three pieces:

1. **`seed/`** -- starter code with the function signature your grader will call
2. **`grader/`** -- a Python package whose `grader.py` holds a `TaskGrader` subclass that imports and runs the agent's code, then returns a score
3. **`task.yaml`** -- wire them together with `grader.entrypoint` + `grader.setup` and the config above

Use `coral validate my-task` to test your grader before launching agents.
