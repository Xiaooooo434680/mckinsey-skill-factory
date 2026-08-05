from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from ..models import (
    Architecture,
    EvaluationPlan,
    Hypothesis,
    IssueNode,
    ProblemDefinition,
    Readiness,
    ReleaseGate,
    RiskLevel,
    SkillSpec,
    ToolContract,
    WorkflowStep,
)
from ..quality import QualityGate
from .models import PackageInspection


class PackageInspector:
    def inspect(self, package_dir: Path) -> PackageInspection:
        package_dir = package_dir.resolve()
        skill_data = self._load_yaml(package_dir / "skill.yaml")
        warnings = list(QualityGate().validate_package(package_dir).warnings)
        if not (package_dir / "skill.spec.json").exists():
            warnings.append("缺少 skill.spec.json，将使用兼容模式重建 SkillSpec")

        files = [
            str(path.relative_to(package_dir))
            for path in sorted(package_dir.rglob("*"))
            if path.is_file()
        ]
        checksums = {
            relative: self._sha256(package_dir / relative)
            for relative in files
            if not relative.startswith("rollback/")
        }
        return PackageInspection(
            name=str(skill_data.get("name", package_dir.name)),
            version=str(skill_data.get("version", "0.0.0")),
            readiness=str(skill_data.get("readiness", "unknown")),
            root=str(package_dir),
            files=files,
            checksums=checksums,
            warnings=warnings,
        )

    def load_spec(self, package_dir: Path) -> SkillSpec:
        spec_path = package_dir / "skill.spec.json"
        if spec_path.exists():
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            return SkillSpec.model_validate(data)
        return self._reconstruct_spec(package_dir)

    def _reconstruct_spec(self, package_dir: Path) -> SkillSpec:
        skill = self._load_yaml(package_dir / "skill.yaml")
        workflow_data = self._load_yaml(package_dir / "workflow.yaml").get("workflow", [])
        tools_data = self._load_yaml(package_dir / "tools.yaml").get("tools", [])
        release_data = self._load_yaml(package_dir / "release-gate.yaml")
        rubric = self._load_yaml(package_dir / "evals/rubric.yaml")
        assumptions_data = self._load_yaml(package_dir / "assumptions.yaml")
        guardrails = self._load_guardrails(package_dir)

        name = str(skill["name"])
        purpose = str(skill.get("purpose", "未定义业务问题"))
        target_user = str(skill.get("target_user", "未定义用户"))
        architecture_data = skill.get("architecture") or {
            "entrypoint": "user_request",
            "core_capabilities": ["problem_solving"],
            "sub_capabilities": [],
            "workflow_mode": "branching",
            "tool_strategy": "least-privilege",
            "knowledge_strategy": "explicit-sources-only",
            "memory_strategy": "stateless",
            "human_in_the_loop": [],
            "fallback_strategy": "partial-or-blocked",
            "observability": ["invocation", "tool_call", "result"],
        }
        output_contract = json.loads((package_dir / "output.schema.json").read_text(encoding="utf-8"))
        problem = ProblemDefinition(
            user=target_user,
            job_to_be_done=purpose,
            business_value=purpose,
            success_definition=[str(item) for item in skill.get("outputs", [])] or ["产生可验证输出"],
            scope=[purpose],
            non_scope=[],
            constraints=["由兼容模式从旧 Skill Package 重建"],
            assumptions=["原包缺少完整 SkillSpec，部分语义使用保守默认值"],
        )
        issue_tree = IssueNode(
            title="Skill 成功",
            children=[IssueNode(title="业务正确性"), IssueNode(title="流程完整性"), IssueNode(title="安全与评估")],
        )
        hypotheses: list[Hypothesis] = []
        evaluation = EvaluationPlan(
            metrics={str(k): float(v) for k, v in (rubric.get("metrics") or {}).items()},
            required_case_types=["happy_path", "edge_case", "failure_case", "adversarial"],
            minimum_cases=12,
            release_threshold=float(rubric.get("release_threshold", 0.8)),
        )
        return SkillSpec(
            name=name,
            version=str(skill.get("version", "0.1.0")),
            purpose=purpose,
            target_user=target_user,
            trigger=str(skill.get("trigger", "由用户显式调用")),
            inputs=[str(item) for item in skill.get("inputs", [])],
            outputs=[str(item) for item in skill.get("outputs", [])],
            risk_level=RiskLevel(str(skill.get("risk_level", "medium"))),
            owner=str(skill.get("owner", "UNASSIGNED")),
            problem_definition=problem,
            issue_tree=issue_tree,
            hypotheses=hypotheses,
            architecture=Architecture.model_validate(architecture_data),
            tools=[ToolContract.model_validate(item) for item in tools_data],
            workflow=[WorkflowStep.model_validate(item) for item in workflow_data],
            output_contract=output_contract,
            guardrails=guardrails,
            evaluation=evaluation,
            release_gate=ReleaseGate.model_validate(release_data),
            assumptions=[str(item) for item in assumptions_data.get("assumptions", [])],
            readiness=Readiness(str(skill.get("readiness", "draft"))),
        )

    @staticmethod
    def _load_guardrails(package_dir: Path) -> list[str]:
        guardrails_path = package_dir / "guardrails.yaml"
        if guardrails_path.exists():
            data = yaml.safe_load(guardrails_path.read_text(encoding="utf-8")) or {}
            return [str(item) for item in data.get("guardrails", [])]
        skill_md = (package_dir / "SKILL.md").read_text(encoding="utf-8")
        marker = "## Guardrails"
        if marker not in skill_md:
            return ["不得虚构事实、工具结果或权限"]
        section = skill_md.split(marker, 1)[1].split("\n## ", 1)[0]
        values = [line[2:].strip() for line in section.splitlines() if line.startswith("- ")]
        return values or ["不得虚构事实、工具结果或权限"]

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"文件必须包含 YAML object：{path}")
        return data

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
