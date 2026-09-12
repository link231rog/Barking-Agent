<div align="center">

# Barking-Agent: Autonomous Robot Dog Radio Direction Finding & Jamming Countermeasures

**Multi-agent self-evolution benchmark and toolkit for CUMCM 2026 Problem B, adapted from CORAL (COLM 2026, [arXiv:2602.04655](https://arxiv.org/abs/2602.04655)).**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://python.org)

**English** | [中文](README_CN.md)

</div>

---

### Overview

**Barking-Agent** provides a standardized evaluation environment, simulation arena, and co-evolutionary agent coordination framework for autonomous robot dog navigation, bearing-only radio direction finding (RDF), and in-situ jammer neutralization.

### Key Features

1. **Packaged Grader Architecture (`barking-dog-grader`)**:
   - Packaged inside [`examples/barking_dog_jamming/grader/`](examples/barking_dog_jamming/grader/).
   - Embedded full physics simulation arena evaluating 30 contest seeds ($N \in [10, 16]$, total 395 targets) under bearing error, laser field-of-view, and strict attempt limits.
2. **Standardized Objective Function**:
   - Evaluates clearance rate (must achieve 100%), average neutralization time $\bar{T}$, path uncertainty index $\text{PUI}$, and variance reduction penalty.
3. **Multi-Agent Shared Memory Hub**:
   - `attempts/`: Stores chronological trajectory logs and scores across iterations.
   - `notes/`: Structured reflections and negative information pruning guidelines.
   - `skills/`: Extracted modular Python tactics (target-as-anchor leapfrogging, LSQ triangulation, fallback policies).
4. **Web UI Dashboard**:
   - [`web/`](web/): React + TypeScript dashboard for visualizing multi-agent generation progress, score convergence, and knowledge graph.

### Quickstart & Validation

```bash
# 1. Setup environment
uv venv
source .venv/bin/activate
uv pip install -e .

# 2. Validate task grader on initial seed
coral validate examples/barking_dog_jamming
```

### Validation Baseline Output

```text
==================================================
Score: 81.7202
  eval: Clearance: 395/395 (100.0%) | Avg Time: 283.37s/tgt | PUI: 0.580 | StdDev: 66.19s | Dist: 14401.6m | Score: 81.7202
==================================================
```

### Architecture

```
Barking-Agent/
├── coral/                  # Core Python orchestration engine
│   ├── cli/                # CLI interface (validate, start, status, eval)
│   ├── grader/             # Subprocess sandbox and TaskGrader protocols
│   ├── hub/                # Shared memory (attempts, notes, skills)
│   ├── web/                # Web dashboard backend API
│   └── workspace/          # Environment isolation and grader venv
├── examples/
│   └── barking_dog_jamming/ # Problem B task definition, grader, and initial strategy seed
└── web/                    # React + TypeScript dashboard frontend
```

### Citation

If you use this benchmark or the underlying CORAL architecture, please cite:

```bibtex
@inproceedings{qu2026coral,
  title={CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery},
  author={Qu, Ao and Zheng, Han and Zhou, Zijian and Yan, Yihao and Tang, Yihong and Ong, Shao Yong and Hong, Fenglu and Zhou, Kaichen and Jiang, Chonghe and Kong, Minwei and Zhu, Jiacheng and Jiang, Xuan and Li, Sirui and Wu, Cathy and Low, Bryan Kian Hsiang and Zhao, Jinhua and Liang, Paul Pu},
  booktitle={Conference on Language Modeling (COLM)},
  year={2026}
}
```

### License

This project is licensed under the Apache 2.0 License.

