# Skill Evolver

`SkillEvolver` 与 `SkillFactory` 是两个独立子系统：

- `SkillFactory`：从 `SkillRequest` 创建全新的 Skill。
- `SkillEvolver`：读取已有 Skill Package，按 `ChangeRequest` 产生新版本。

## 演进流水线

```text
Existing Skill Package
  → Inspect and reconstruct SkillSpec
  → Change impact analysis
  → Owner-approval gate
  → Apply structured patch
  → Semantic version bump
  → Regenerate canonical artifacts
  → Regression checks
  → Package diff and migration plan
  → Rollback archive
```

`SkillEvolver` 不修改源目录。候选版本输出为 `<skill-name>-<new-version>`。

## ChangeRequest

核心字段：

- `evolution_type`：corrective、adaptive、perfective、evolutionary
- `version_bump`：auto、patch、minor、major
- `operations`：对 metadata、workflow、tools、guardrails、output_contract、evaluation 或非核心文件执行结构化修改
- `owner_approval`：高影响修改必须为 true
- `acceptance_criteria`：用于发布前人工和自动验证

## 产物

每次成功演进都会生成：

```text
.evolution/
├── change-request.yaml
├── impact-report.md
├── migration-plan.md
├── package-diff.md
├── regression-results.json
└── manifest.json
rollback/
└── <skill>-<old-version>.zip
CHANGELOG.md
```

## 安全边界

- 禁止通过演进修改 Skill name；新能力身份应创建新 Skill。
- 核心结构文件只能通过结构化组件修改，不能用 file 操作绕过。
- 删除契约、修改输入输出、修改输出 Schema、直接文件替换会触发高影响审批。
- 回滚压缩包在解压前执行路径穿越检查。
