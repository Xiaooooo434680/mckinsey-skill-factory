from __future__ import annotations

from ..models import RiskLevel, SkillSpec
from .models import ChangeAction, ChangeComponent, ChangeRequest, ImpactReport


class ImpactAnalyzer:
    FILE_MAP: dict[ChangeComponent, list[str]] = {
        ChangeComponent.metadata: ["skill.yaml", "skill.spec.json", "SKILL.md", "README.md"],
        ChangeComponent.workflow: ["workflow.yaml", "skill.spec.json", "SKILL.md"],
        ChangeComponent.tools: ["tools.yaml", "skill.spec.json"],
        ChangeComponent.guardrails: ["guardrails.yaml", "skill.spec.json", "SKILL.md", "policies.md"],
        ChangeComponent.output_contract: ["output.schema.json", "skill.spec.json"],
        ChangeComponent.evaluation: ["evals/rubric.yaml", "skill.spec.json"],
        ChangeComponent.file: [],
    }

    def analyze(self, spec: SkillSpec, request: ChangeRequest) -> ImpactReport:
        components = sorted({op.component.value for op in request.operations})
        files: set[str] = set()
        breaking: list[str] = []
        reasons: list[str] = []

        for operation in request.operations:
            files.update(self.FILE_MAP[operation.component])
            if operation.component == ChangeComponent.file and operation.selector:
                files.add(operation.selector)
                reasons.append("直接文件替换绕过部分结构化约束")
            if operation.action == ChangeAction.remove:
                breaking.append(f"删除 {operation.component.value}:{operation.selector or operation.value}")
            if operation.component == ChangeComponent.metadata and isinstance(operation.value, dict):
                sensitive = {"name", "inputs", "outputs", "risk_level"}.intersection(operation.value)
                if sensitive:
                    breaking.append(f"修改契约性元数据：{', '.join(sorted(sensitive))}")
            if operation.component == ChangeComponent.output_contract:
                breaking.append("修改输出契约可能影响下游消费者")
            if operation.component == ChangeComponent.tools:
                reasons.append("工具变更需要重新检查权限和失败路径")

        high_risk = (
            spec.risk_level in {RiskLevel.high, RiskLevel.critical}
            or bool(breaking)
            or any(op.component == ChangeComponent.file for op in request.operations)
        )
        if high_risk:
            risk = "high"
        elif len(components) >= 3:
            risk = "medium"
        else:
            risk = "low"
        return ImpactReport(
            change_id=request.id,
            impacted_components=components,
            impacted_files=sorted(files),
            breaking_changes=breaking,
            risk=risk,
            approval_required=high_risk,
            rationale=sorted(set(reasons)) or ["变更限定在结构化 Skill 组件内"],
        )
