# McKinsey Skill Factory

一个平台无关、可运行的工程级 Meta Skill 系统。项目将“创建新 Skill”和“修改已有 Skill”分成两个独立子系统：

- **SkillFactory**：从业务需求创建全新的工程级 Skill。
- **SkillEvolver**：检查已有 Skill，生成可追踪、可测试、可回滚的新版本。

```text
Create: SkillRequest → SkillFactory → SkillSpec → Skill Package
Evolve: Existing Package + ChangeRequest → SkillEvolver → Versioned Package
```

## 核心能力

- YAML DSL、Pydantic 校验和 JSON Schema
- 麦肯锡式问题定义、MECE 问题树、关键假设和能力架构
- Workflow、Tool Contract、Guardrails、Output Schema 和 Evaluation 自动生成
- 结构化 Skill 修改，不直接覆盖基线版本
- 影响分析、Owner 审批门禁、语义化版本升级
- Package Diff、回归检查、迁移计划、Changelog 和 Rollback Archive
- CLI、Pytest、Ruff、Mypy 和 GitHub Actions

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

创建 Skill：

```bash
skill-factory build examples/sales-opportunity/request.yaml --output dist/base
skill-factory validate dist/base/sales-opportunity-diagnosis
```

演进 Skill：

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

回滚：

```bash
skill-factory rollback \
  dist/evolved/sales-opportunity-diagnosis-0.1.1/rollback/sales-opportunity-diagnosis-0.1.0.zip \
  --output dist/restored
```

## 创建产物

```text
<skill>/
├── README.md
├── SKILL.md
├── skill.yaml
├── skill.spec.json
├── workflow.yaml
├── tools.yaml
├── guardrails.yaml
├── output.schema.json
├── policies.md
├── assumptions.yaml
├── release-gate.yaml
├── evals/
└── examples/
```

## 演进产物

```text
<skill>-<new-version>/
├── .evolution/
│   ├── change-request.yaml
│   ├── impact-report.md
│   ├── migration-plan.md
│   ├── package-diff.md
│   ├── regression-results.json
│   └── manifest.json
├── rollback/<skill>-<old-version>.zip
├── CHANGELOG.md
└── ...完整 Skill Package
```

## 修改模式

- `corrective`：修复缺陷，默认升级 patch
- `perfective`：改善质量、成本或延迟，默认升级 patch
- `adaptive`：适配新工具或业务环境，默认升级 minor
- `evolutionary`：改变能力边界或契约，默认升级 major

高影响修改必须设置 `owner_approval: true`。删除组件、修改输入输出或输出契约、直接替换文件，都可能触发高影响门禁。

## 工程边界

本仓库负责规范、编译、演进、验证和发布制品，不负责真实工具执行、凭证存储、用户鉴权、分布式状态或生产审计存储。这些能力应由宿主 Agent Runtime 提供。

详见：

- `docs/architecture.md`
- `docs/evolution.md`
- `docs/extension-guide.md`
