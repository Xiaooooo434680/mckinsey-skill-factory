from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..quality import QualityGate
from .models import ChangeRequest, RegressionCheck, RegressionReport
from .versioning import SemVer


class RegressionRunner:
    def run(self, baseline: Path, candidate: Path, request: ChangeRequest) -> RegressionReport:
        checks: list[RegressionCheck] = []
        errors: list[str] = []
        warnings: list[str] = []

        package_result = QualityGate().validate_package(candidate)
        checks.append(RegressionCheck(
            name="package_structure",
            passed=package_result.passed,
            detail="; ".join(package_result.errors) or "工程包结构完整",
        ))
        errors.extend(package_result.errors)
        warnings.extend(package_result.warnings)

        old_skill = self._yaml(baseline / "skill.yaml")
        new_skill = self._yaml(candidate / "skill.yaml")
        same_name = old_skill.get("name") == new_skill.get("name")
        checks.append(RegressionCheck(
            name="skill_identity",
            passed=same_name,
            detail="Skill name 保持不变" if same_name else "Skill name 被修改",
        ))
        if not same_name:
            errors.append("Skill 演进不得修改 name；应创建新 Skill")

        old_version = str(old_skill.get("version", "0.0.0"))
        new_version = str(new_skill.get("version", "0.0.0"))
        version_advanced = SemVer.parse(new_version) > SemVer.parse(old_version)
        checks.append(RegressionCheck(
            name="version_advanced",
            passed=version_advanced,
            detail=f"{old_version} → {new_version}",
        ))
        if not version_advanced:
            errors.append("候选版本必须高于基线版本")

        workflow = self._yaml(candidate / "workflow.yaml").get("workflow", [])
        workflow_ids = [str(item.get("step_id")) for item in workflow]
        workflow_unique = len(workflow_ids) == len(set(workflow_ids))
        checks.append(RegressionCheck(
            name="workflow_ids_unique",
            passed=workflow_unique,
            detail="Workflow step_id 唯一" if workflow_unique else "存在重复 step_id",
        ))
        if not workflow_unique:
            errors.append("Workflow step_id 必须唯一")

        tools = self._yaml(candidate / "tools.yaml").get("tools", [])
        tool_names = [str(item.get("name")) for item in tools]
        tools_unique = len(tool_names) == len(set(tool_names))
        checks.append(RegressionCheck(
            name="tool_names_unique",
            passed=tools_unique,
            detail="Tool name 唯一" if tools_unique else "存在重复 Tool name",
        ))
        if not tools_unique:
            errors.append("Tool name 必须唯一")

        schema = json.loads((candidate / "output.schema.json").read_text(encoding="utf-8"))
        schema_valid = schema.get("type") == "object" and isinstance(schema.get("properties"), dict)
        checks.append(RegressionCheck(
            name="output_contract_shape",
            passed=schema_valid,
            detail="输出契约为 object schema" if schema_valid else "输出契约结构无效",
        ))
        if not schema_valid:
            errors.append("输出契约必须是 JSON object schema")

        placeholder_files = self._placeholder_files(candidate)
        no_placeholders = not placeholder_files
        checks.append(RegressionCheck(
            name="unresolved_placeholders",
            passed=no_placeholders,
            detail="无未解析模板变量" if no_placeholders else f"发现：{', '.join(placeholder_files)}",
        ))
        if placeholder_files:
            errors.append("候选包包含未解析模板变量")

        if not request.acceptance_criteria:
            warnings.append("ChangeRequest 未定义 acceptance_criteria")

        return RegressionReport(
            passed=not errors,
            baseline_version=old_version,
            candidate_version=new_version,
            checks=checks,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _yaml(path: Path) -> dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"YAML 文件必须是 object：{path}")
        return data

    @staticmethod
    def _placeholder_files(root: Path) -> list[str]:
        markers = ("{{", "}}", "{%", "%}")
        found: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in text for marker in markers):
                found.append(str(path.relative_to(root)))
        return found
