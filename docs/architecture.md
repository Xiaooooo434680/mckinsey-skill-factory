# Architecture

## 双子系统

```text
                         ┌────────────────────┐
SkillRequest ───────────▶│    SkillFactory    │
                         └─────────┬──────────┘
                                   │ SkillSpec
                                   ▼
                         Engineering Skill Package
                                   │
Existing Package + ChangeRequest   │
              └────────────────────┼──────────────┐
                                   ▼              │
                         ┌────────────────────┐    │
                         │    SkillEvolver    │◀───┘
                         └─────────┬──────────┘
                                   ▼
                    Versioned, tested Skill Package
```

`SkillFactory` 和 `SkillEvolver` 共享 `SkillSpec`、`PackageGenerator` 与 `QualityGate`，但职责分离：

- Factory 只处理新建，不承担历史兼容和版本迁移。
- Evolver 只处理已有包，不允许改变 Skill identity。

## SkillFactory 流水线

```text
Request DSL
  → Pydantic Validation
  → Problem Definition
  → Issue Tree
  → Hypotheses
  → Architecture
  → Workflow and Tool Contracts
  → Evaluation and Release Gate
  → SkillSpec
  → Package Generator
```

## SkillEvolver 流水线

```text
Package Inspection
  → SkillSpec Load/Reconstruction
  → Change Impact Analysis
  → Approval Gate
  → Structured Patch
  → Semantic Version Bump
  → Canonical Artifact Regeneration
  → Regression Runner
  → Diff, Migration and Changelog
  → Rollback Archive
```

## 关键设计决策

### SkillSpec 是规范源

新生成的包包含 `skill.spec.json`。Evolver 修改结构化对象，再重新生成规范文件，避免直接操作多个互相矛盾的 YAML/Markdown 文件。旧包没有 `skill.spec.json` 时，Inspector 会进入兼容重建模式并标记警告。

### 不原地修改

Evolver 始终输出 `<skill>-<new-version>`。基线包保持不变，候选包通过回归后再由外部发布系统提升。

### 确定性逻辑优先

Schema、权限门禁、版本升级、文件路径安全、回归检查和回滚使用代码实现。模型只适合用于语义增强，不承担强约束逻辑。

### 乐观锁

ChangeOperation 可提供 `expected_old`。候选值与预期不一致时停止修改，防止基于过期版本覆盖人工变更。

## 扩展点

- `LLMClient`：增强问题树、假设和案例生成
- `ImpactAnalyzer`：接入组织级风险矩阵
- `RegressionRunner`：接入真实数据集、模型评估和成本测试
- `PackageGenerator`：适配 OpenAI Agents、Claude Skills、Cursor、Codex 或自研 Runtime
- `QualityGate`：加入安全、合规、SLO 和成本门禁
- `ChangeOperation`：增加组织专用组件类型

## 运行时责任

仓库不负责：

- 真实工具执行和凭证管理
- 用户身份与资源授权
- 分布式重试和状态持久化
- 生产审计存储
- 模型推理服务
- 候选版本流量切换

这些能力由宿主 Agent Runtime、CI/CD 和发布平台提供。
