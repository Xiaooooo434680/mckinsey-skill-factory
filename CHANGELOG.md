# Changelog

## 0.2.0

- 新增独立 `SkillEvolver` 子系统，和 `SkillFactory` 职责分离。
- 新增 inspect、modify、diff、test、rollback 和 evolution-schema CLI。
- 新增 ChangeRequest DSL、影响分析、审批门禁和语义化版本升级。
- 新增结构化 Workflow、Tool、Guardrail、Output Contract 和 Evaluation 修改。
- 新增回归报告、Package Diff、迁移计划、Changelog 和 Rollback Archive。
- Skill Package 新增 `skill.spec.json` 和 `guardrails.yaml`。
- 新增 Evolver 单元测试和端到端 CLI 验证。

## 0.1.0

- 初始工程级 Meta Skill Factory。
- 提供请求 DSL、确定性编译流水线、Skill 包生成器、质量门禁、CLI、测试和 CI。
