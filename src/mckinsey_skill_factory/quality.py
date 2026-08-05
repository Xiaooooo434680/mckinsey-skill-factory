from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from .models import SkillSpec


@dataclass(frozen=True)
class GateResult:
    passed: bool
    errors: list[str]
    warnings: list[str]


class QualityGate:
    def evaluate(self, spec: SkillSpec) -> GateResult:
        errors: list[str] = []
        warnings: list[str] = []

        if spec.owner == "UNASSIGNED":
            errors.append("缺少业务 Owner")
        if not spec.workflow:
            errors.append("工作流为空")
        if not spec.guardrails:
            errors.append("缺少 Guardrails")
        if spec.evaluation.minimum_cases < 10:
            errors.append("评估用例数量不足")
        if any(t.access_mode.value == "write" and not t.approval_required for t in spec.tools):
            errors.append("存在无人工审批的写工具")
        if not spec.output_contract:
            errors.append("缺少输出契约")
        if spec.release_gate.eval_threshold_met is False:
            warnings.append("尚未执行真实评估，不能标记 production-ready")
        if spec.risk_level.value in {"high", "critical"}:
            warnings.append("高风险 Skill 必须经过独立安全评审")

        return GateResult(passed=not errors, errors=errors, warnings=warnings)

    def validate_package(self, package_dir: Path) -> GateResult:
        required = [
            "SKILL.md",
            "skill.yaml",
            "workflow.yaml",
            "tools.yaml",
            "output.schema.json",
            "policies.md",
            "release-gate.yaml",
            "evals/rubric.yaml",
            "evals/cases.jsonl",
            "evals/adversarial_cases.jsonl",
        ]
        errors = [f"缺少文件：{name}" for name in required if not (package_dir / name).exists()]
        warnings: list[str] = []

        skill_path = package_dir / "skill.yaml"
        if skill_path.exists():
            data: dict[str, Any] = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
            if data.get("owner") == "UNASSIGNED":
                warnings.append("Skill Owner 尚未指定")

        spec_path = package_dir / "skill.spec.json"
        if spec_path.exists():
            try:
                SkillSpec.model_validate(json.loads(spec_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"skill.spec.json 无效：{exc}")
        else:
            warnings.append("缺少 skill.spec.json；SkillEvolver 将使用兼容重建模式")

        if not (package_dir / "guardrails.yaml").exists():
            warnings.append("缺少 guardrails.yaml；Guardrails 只能从文档兼容解析")

        return GateResult(passed=not errors, errors=errors, warnings=warnings)
