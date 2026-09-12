<div align="center">

# Barking-Agent：机器狗无线电测向与干扰源清剿多智能体自进化基准工具箱

**专为全国大学生数学建模竞赛（CUMCM）2026 年 B 题定制的多智能体协同自进化基准与评测工具，基于 CORAL（COLM 2026, [arXiv:2602.04655](https://arxiv.org/abs/2602.04655)）架构深度改造。**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://python.org)

[English](README.md) | **中文**

</div>

---

### 项目概述

**Barking-Agent** 为复杂对抗电磁战区（$R=1750\,\text{m}$ 圆形区域）中的机器狗动态机动、纯方位多测站交叉定位（RDF）与就地激光清剿，提供了一套标准化的黑盒评测隔离沙箱、物理竞技场模拟器以及多智能体协同变异演化框架。

### 核心特性

1. **打包化评测套件架构 (`barking-dog-grader`)**：
   - 位于 [`examples/barking_dog_jamming/grader/`](examples/barking_dog_jamming/grader/)。
   - 内置高保真物理竞技场模拟器，自动化评测横跨 30 组国赛随机场景（每个场景 $N \in [10, 16]$ 个目标，全谱系共 395 个目标），严格施加测向角误差、激光视场与尝试次数硬约束。
2. **多目标自进化适应度函数**：
   - 刚性要求 100% 全歼率，对单目标平均耗时 $\bar{T}$、探索不确定性代价指数 $\text{PUI}$ 及方差控制提供平滑收敛引导。
3. **多智能体共享持久记忆库（Shared Memory Hub）**：
   - `attempts/`：全代际时空轨迹与评分档案。
   - `notes/`：结构化反思与负信息（Negative Information）剪枝笔记。
   - `skills/`：通过单元测试的可复用 Python 战术算子库（如目标即前哨跳跃、加权 LSQ 闭式三角网等）。
4. **Web UI 可视化看板**：
   - [`web/`](web/)：基于 React + TypeScript 的轻量化前端，支持多代际得分收敛曲线、智能体知识图谱与实时日志回放。

### 快速开始与基准自检

```bash
# 1. 初始化虚拟环境并安装
uv venv
source .venv/bin/activate
uv pip install -e .

# 2. 对基线初始种子执行闭环校验
coral validate examples/barking_dog_jamming
```

### 校验输出基准（Validation Output）

```text
==================================================
Score: 81.7202
  eval: Clearance: 395/395 (100.0%) | Avg Time: 283.37s/tgt | PUI: 0.580 | StdDev: 66.19s | Dist: 14401.6m | Score: 81.7202
==================================================
```

### 目录架构

```
Barking-Agent/
├── coral/                  # Python 协同与评测核心引擎
│   ├── cli/                # 命令行入口 (validate, start, status, eval)
│   ├── grader/             # 评测隔离沙箱与 TaskGrader 规范
│   ├── hub/                # 共享记忆中心 (attempts, notes, skills)
│   ├── web/                # Web 看板后端 API 服务
│   └── workspace/          # 工作空间隔离与虚拟环境管理
├── examples/
│   └── barking_dog_jamming/ # B 题专属任务配置、评测器与基线策略种子
└── web/                    # React + TypeScript 看板前端工程
```

### 引用 (Citation)

如果您在学术论文中使用了本基准或底层的 CORAL 架构，请引用：

```bibtex
@inproceedings{qu2026coral,
  title={CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery},
  author={Qu, Ao and Zheng, Han and Zhou, Zijian and Yan, Yihao and Tang, Yihong and Ong, Shao Yong and Hong, Fenglu and Zhou, Kaichen and Jiang, Chonghe and Kong, Minwei and Zhu, Jiacheng and Jiang, Xuan and Li, Sirui and Wu, Cathy and Low, Bryan Kian Hsiang and Zhao, Jinhua and Liang, Paul Pu},
  booktitle={Conference on Language Modeling (COLM)},
  year={2026}
}
```

### 开源许可证 (License)

本项目采用 Apache 2.0 开源许可证。

### 致谢

我们感谢 [TNT Accelerator](https://www.tnt.so/) 提供的慷慨支持，包括在开发过程中给予帮助的各种 API 积分。也要感谢许多如 [OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve)、[autoresearch](https://github.com/karpathy/autoresearch)、[TTT Discover](https://arxiv.org/abs/2601.16175) 等的十分有启发性的工作，这些工作为 Coral 的诞生奠定了基础。
