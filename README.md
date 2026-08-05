<div align="center">

# 🏭 McKinsey Skill Factory

> 用结构化问题定义（MECE 问题树、关键假设、能力架构）创建与演进工程级 Skill

**v0.2.0** · Python ≥ 3.10

[![CI](https://img.shields.io/github/actions/workflow/status/Xiaooooo434680/mckinsey-skill-factory/ci.yml?style=flat&color=0080ff)](https://github.com/Xiaooooo434680/mckinsey-skill-factory/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-0080ff?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![GitHub repo size](https://img.shields.io/github/repo-size/Xiaooooo434680/mckinsey-skill-factory?style=flat&color=0080ff)](https://github.com/Xiaooooo434680/mckinsey-skill-factory)

</div>

---

一个平台无关、可运行的工程级 **Meta Skill** 系统，把“创建新 Skill”和“修改已有 Skill”拆成两个独立子系统：

- **SkillFactory**：从业务需求创建全新的工程级 Skill。
- **SkillEvolver**：检查已有 Skill，生成可追踪、可测试、可回滚的新版本。

```text
Create: SkillRequest → SkillFactory → SkillSpec → Skill Package
Evolve: Existing Package + ChangeRequest → SkillEvolver → Versioned Package
```

## ✨ 功能特性

| 类别 | 能力 |
| --- | --- |
| 规范定义 | YAML DSL、Pydantic 校验、JSON Schema 自动导出 |
| 问题分析 | 麦肯锡式问题定义、MECE 问题树、关键假设、能力架构 |
| 产物生成 | Workflow、Tool Contract、Guardrails、Output Schema、Evaluation 自动生成 |
| 演进修改 | 结构化修改不直接覆盖基线，按变更类型做语义化版本升级 |
| 变更控制 | 影响分析、Owner 审批门禁、Package Diff、回归检查、迁移计划 |
| 可追溯 | Changelog、Rollback Archive、.evolution 审计目录 |
| 工程质量 | CLI、Pytest、Ruff、Mypy、GitHub Actions CI |

## 📁 目录结构

```text
mckinsey-skill-factory/
├── .github/
│   └── workflows/ci.yml          # CI：lint + typecheck + test + 端到端示例
├── config/
│   └── defaults.yaml              # 编译流水线默认配置
├── docs/
│   ├── architecture.md            # 系统架构
│   ├── evolution.md               # SkillEvolver 设计
│   └── extension-guide.md         # 扩展指南
├── examples/
│   ├── evolution/                 # 演进 ChangeRequest 示例
│   └── sales-opportunity/         # 创建 SkillRequest 示例
├── schemas/
│   ├── skill-request.schema.json  # 请求 DSL JSON Schema
│   ├── change-request.schema.json # 变更 DSL JSON Schema
│   └── README.md
├── src/
│   └── mckinsey_skill_factory/
│       ├── evolver/               # SkillEvolver 子系统（inspect/modify/diff/test/rollback）
│       ├── templates/             # Skill 包 Jinja2 模板
│       ├── cli.py                 # skill-factory 命令入口
│       ├── generator.py           # Skill 包生成器
│       ├── models.py              # SkillRequest / SkillSpec Pydantic 模型
│       ├── pipeline.py            # SkillFactory 编译流水线
│       ├── quality.py             # 质量门禁
│       └── stages.py              # 流水线阶段
├── tests/
│   ├── test_evolver.py
│   ├── test_models.py
│   ├── test_pipeline.py
│   └── test_quality.py
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Makefile
├── README.md
├── SECURITY.md
└── pyproject.toml
```

## 🚀 快速开始

**环境要求**

- Python ≥ 3.10
- 依赖：`pydantic >=2.7,<3` · `PyYAML >=6,<7` · `Jinja2 >=3.1,<4` · `typer >=0.12,<1`

**安装**

```bash
git clone https://github.com/Xiaooooo434680/mckinsey-skill-factory.git
cd mckinsey-skill-factory
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
```

验证安装：

```bash
skill-factory --help
```

## 📖 使用

**创建 Skill** —— 从 `SkillRequest`（`examples/sales-opportunity/request.yaml`）编译出完整 Skill 包并验证：

```bash
skill-factory build examples/sales-opportunity/request.yaml --output dist/base
skill-factory validate dist/base/sales-opportunity-diagnosis
```

**演进 Skill** —— 检查基线、用 `ChangeRequest` 生成新版本、diff 并回归测试：

```bash
skill-factory inspect dist/base/sales-opportunity-diagnosis

skill-factory modify \
  dist/base/sales-opportunity-diagnosis \
  examples/evolution/change-request.yaml \
  --output dist/evolved

skill-factory diff \
  dist/base/sales-opportunity-diagnosis \
  dist/evolved/sales-opportunity-diagnosis-0.1.1

skill-factory test \
  dist/evolved/sales-opportunity-diagnosis-0.1.1 \
  --baseline dist/base/sales-opportunity-diagnosis \
  --change-request examples/evolution/change-request.yaml
```

**回滚** —— 从演进产物自带的 Rollback Archive 恢复基线版本：

```bash
skill-factory rollback \
  dist/evolved/sales-opportunity-diagnosis-0.1.1/rollback/sales-opportunity-diagnosis-0.1.0.zip \
  --output dist/restored
```

**修改模式与版本升级**

| 模式 | 说明 | 默认版本 |
| --- | --- | --- |
| `corrective` | 修复缺陷 | patch |
| `perfective` | 改善质量、成本或延迟 | patch |
| `adaptive` | 适配新工具或业务环境 | minor |
| `evolutionary` | 改变能力边界或契约 | major |

高影响修改（删除组件、修改输入输出或输出契约、直接替换文件）必须设置 `owner_approval: true`。

## 🧪 测试与质量

```bash
make test        # pytest -q
make lint        # ruff check src tests
make typecheck   # mypy src
make build-example
make evolve-example
```

CI（`.github/workflows/ci.yml`）对每次 push / PR 依次执行 `ruff check`、`mypy src`、`pytest -q`，并跑一遍完整创建→验证→演进→回归的端到端示例。

## 🤝 社区与支持

- **文档**：`docs/architecture.md`（架构）、`docs/evolution.md`（演进设计）、`docs/extension-guide.md`（扩展）
- **问题反馈**：[GitHub Issues](https://github.com/Xiaooooo434680/mckinsey-skill-factory/issues)
- **安全漏洞**：见 [`SECURITY.md`](SECURITY.md)

## 🙋 贡献

欢迎提交 Issue 和 Pull Request。请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，开发流程为 `make lint` → `make typecheck` → `make test` 全绿后再提交。

## 📄 License

本仓库**尚未声明 License**（`pyproject.toml` 无 `license` 字段，仓库无 `LICENSE` 文件）。在补充 License 之前，代码默认保留所有权利，请在对外使用前与维护者确认。
