from __future__ import annotations

import json
import shutil
import zipfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ..generator import PackageGenerator
from ..models import SkillSpec, ToolContract, WorkflowStep
from ..quality import QualityGate
from .diffing import PackageDiffer
from .impact import ImpactAnalyzer
from .inspector import PackageInspector
from .models import (
    ChangeAction,
    ChangeComponent,
    ChangeOperation,
    ChangeRequest,
    EvolutionResult,
)
from .regression import RegressionRunner
from .versioning import SemVer, resolve_bump


class SkillEvolver:
    """Create a new, traceable Skill version without mutating the baseline package."""

    def __init__(self) -> None:
        self.inspector = PackageInspector()
        self.impact_analyzer = ImpactAnalyzer()
        self.regression_runner = RegressionRunner()
        self.differ = PackageDiffer()

    def evolve(self, package_dir: Path, request: ChangeRequest, output_root: Path) -> EvolutionResult:
        package_dir = package_dir.resolve()
        package_gate = QualityGate().validate_package(package_dir)
        if not package_gate.passed:
            raise ValueError("基线 Skill Package 无效：" + "; ".join(package_gate.errors))
        inspection = self.inspector.inspect(package_dir)
        if request.skill_name and request.skill_name != inspection.name:
            raise ValueError(
                f"ChangeRequest skill_name={request.skill_name} 与基线 {inspection.name} 不一致"
            )

        spec = self.inspector.load_spec(package_dir)
        impact = self.impact_analyzer.analyze(spec, request)
        if impact.approval_required and not request.owner_approval:
            raise ValueError("该变更被判定为高影响，必须设置 owner_approval: true")

        old_version = spec.version
        bump = resolve_bump(request.version_bump, request.evolution_type)
        new_version = str(SemVer.parse(old_version).bump(bump))
        target = output_root.resolve() / f"{spec.name}-{new_version}"
        if target.exists():
            raise FileExistsError(f"目标版本已存在：{target}")

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package_dir, target, ignore=shutil.ignore_patterns("rollback", ".evolution"))
        rollback_archive = self._create_rollback(package_dir, target, spec.name, old_version)

        evolved_spec = deepcopy(spec)
        structured_operations = [
            operation for operation in request.operations
            if operation.component != ChangeComponent.file
        ]
        file_operations = [
            operation for operation in request.operations
            if operation.component == ChangeComponent.file
        ]
        self._apply_operations(evolved_spec, structured_operations, target)
        evolved_spec.version = new_version
        PackageGenerator().generate_into(evolved_spec, target)
        for operation in file_operations:
            self._apply_file(target, operation)
        self._write_evolution_artifacts(
            package_dir=package_dir,
            target=target,
            request=request,
            impact=impact,
            old_version=old_version,
            new_version=new_version,
        )

        regression = self.regression_runner.run(package_dir, target, request)
        (target / ".evolution/regression-results.json").write_text(
            json.dumps(regression.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        diff_text = self.differ.render_markdown(package_dir, target)
        (target / ".evolution/package-diff.md").write_text(diff_text, encoding="utf-8")

        if not regression.passed:
            raise RuntimeError(
                "Skill 演进已生成但回归失败：" + "; ".join(regression.errors)
            )
        return EvolutionResult(
            source=package_dir,
            target=target,
            old_version=old_version,
            new_version=new_version,
            impact_report=impact,
            regression_report=regression,
            rollback_archive=rollback_archive,
        )

    def rollback(self, archive: Path, output_dir: Path) -> Path:
        archive = archive.resolve()
        output_dir = output_dir.resolve()
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(f"回滚目标目录非空：{output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            self._validate_archive(bundle)
            bundle.extractall(output_dir)
        children = [path for path in output_dir.iterdir() if path.is_dir()]
        return children[0] if len(children) == 1 else output_dir

    def _apply_operations(
        self,
        spec: SkillSpec,
        operations: list[ChangeOperation],
        target: Path,
    ) -> None:
        for operation in operations:
            if operation.component == ChangeComponent.metadata:
                self._apply_metadata(spec, operation)
            elif operation.component == ChangeComponent.workflow:
                self._apply_collection(spec.workflow, operation, "step_id", WorkflowStep)
            elif operation.component == ChangeComponent.tools:
                self._apply_collection(spec.tools, operation, "name", ToolContract)
            elif operation.component == ChangeComponent.guardrails:
                self._apply_guardrails(spec, operation)
            elif operation.component == ChangeComponent.output_contract:
                self._apply_mapping(spec.output_contract, operation)
            elif operation.component == ChangeComponent.evaluation:
                self._apply_evaluation(spec, operation)
            elif operation.component == ChangeComponent.file:
                self._apply_file(target, operation)

    @staticmethod
    def _apply_metadata(spec: SkillSpec, operation: ChangeOperation) -> None:
        if operation.action not in {ChangeAction.update, ChangeAction.replace}:
            raise ValueError("metadata 仅支持 update/replace")
        if not isinstance(operation.value, dict):
            raise ValueError("metadata value 必须是 object")
        protected = {"name", "version"}
        attempted = protected.intersection(operation.value)
        if attempted:
            raise ValueError(f"Skill 演进不得直接修改：{', '.join(sorted(attempted))}")
        data = spec.model_dump(mode="json")
        for key, value in operation.value.items():
            if key not in data:
                raise KeyError(f"未知 SkillSpec 字段：{key}")
            data[key] = value
        updated = SkillSpec.model_validate(data)
        for field in SkillSpec.model_fields:
            setattr(spec, field, getattr(updated, field))
        if "purpose" in operation.value:
            spec.problem_definition.job_to_be_done = spec.purpose
        if "target_user" in operation.value:
            spec.problem_definition.user = spec.target_user

    @staticmethod
    def _apply_collection(
        collection: list[Any],
        operation: ChangeOperation,
        identity_field: str,
        model_type: type[Any],
    ) -> None:
        index = next(
            (i for i, item in enumerate(collection) if getattr(item, identity_field) == operation.selector),
            None,
        )
        if operation.action == ChangeAction.add:
            item = model_type.model_validate(operation.value)
            identity = getattr(item, identity_field)
            if any(getattr(existing, identity_field) == identity for existing in collection):
                raise ValueError(f"重复 {identity_field}：{identity}")
            collection.append(item)
            return
        if index is None:
            raise KeyError(f"未找到 {identity_field}={operation.selector}")
        if operation.expected_old is not None:
            current = collection[index].model_dump(mode="json")
            if current != operation.expected_old:
                raise ValueError(f"乐观锁失败：{identity_field}={operation.selector} 已变化")
        if operation.action == ChangeAction.remove:
            collection.pop(index)
            return
        current_data = collection[index].model_dump(mode="json")
        if operation.action == ChangeAction.update:
            if not isinstance(operation.value, dict):
                raise ValueError("update value 必须是 object")
            current_data.update(operation.value)
        elif operation.action == ChangeAction.replace:
            current_data = operation.value
        collection[index] = model_type.model_validate(current_data)

    @staticmethod
    def _apply_guardrails(spec: SkillSpec, operation: ChangeOperation) -> None:
        values = operation.value if isinstance(operation.value, list) else [operation.value]
        if operation.action == ChangeAction.add:
            for value in values:
                text = str(value)
                if text not in spec.guardrails:
                    spec.guardrails.append(text)
        elif operation.action == ChangeAction.remove:
            target = operation.selector or str(operation.value)
            if target not in spec.guardrails:
                raise KeyError(f"未找到 Guardrail：{target}")
            spec.guardrails.remove(target)
        elif operation.action == ChangeAction.replace:
            spec.guardrails = [str(value) for value in values]
        else:
            raise ValueError("guardrails 不支持 update；使用 add/remove/replace")

    @staticmethod
    def _apply_mapping(mapping: dict[str, Any], operation: ChangeOperation) -> None:
        if operation.expected_old is not None and operation.selector:
            if mapping.get(operation.selector) != operation.expected_old:
                raise ValueError(f"乐观锁失败：{operation.selector} 已变化")
        if operation.action == ChangeAction.update:
            if not isinstance(operation.value, dict):
                raise ValueError("mapping update value 必须是 object")
            SkillEvolver._deep_merge(mapping, operation.value)
        elif operation.action == ChangeAction.replace:
            if not isinstance(operation.value, dict):
                raise ValueError("mapping replace value 必须是 object")
            mapping.clear()
            mapping.update(operation.value)
        elif operation.action == ChangeAction.remove:
            if operation.selector is None:
                raise ValueError("mapping remove 必须提供 selector")
            if operation.selector not in mapping:
                raise KeyError(f"未找到字段：{operation.selector}")
            del mapping[operation.selector]
        else:
            raise ValueError("mapping 不支持 add；使用 update")

    @staticmethod
    def _apply_evaluation(spec: SkillSpec, operation: ChangeOperation) -> None:
        if operation.action not in {ChangeAction.update, ChangeAction.replace}:
            raise ValueError("evaluation 仅支持 update/replace")
        data = spec.evaluation.model_dump(mode="json")
        if operation.action == ChangeAction.replace:
            data = operation.value
        else:
            if not isinstance(operation.value, dict):
                raise ValueError("evaluation update value 必须是 object")
            data.update(operation.value)
        spec.evaluation = type(spec.evaluation).model_validate(data)

    @staticmethod
    def _apply_file(target: Path, operation: ChangeOperation) -> None:
        assert operation.selector is not None
        relative = Path(operation.selector)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("file selector 必须是包内安全相对路径")
        protected = {"skill.yaml", "workflow.yaml", "tools.yaml", "output.schema.json", "skill.spec.json"}
        if str(relative) in protected:
            raise ValueError(f"核心结构文件必须通过结构化组件修改：{relative}")
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(operation.value), encoding="utf-8")

    @staticmethod
    def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                SkillEvolver._deep_merge(target[key], value)
            else:
                target[key] = value

    @staticmethod
    def _create_rollback(package_dir: Path, target: Path, name: str, version: str) -> Path:
        rollback_dir = target / "rollback"
        rollback_dir.mkdir(parents=True, exist_ok=True)
        archive = rollback_dir / f"{name}-{version}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(package_dir.rglob("*")):
                if path.is_file() and "rollback" not in path.relative_to(package_dir).parts:
                    arcname = Path(f"{name}-{version}") / path.relative_to(package_dir)
                    bundle.write(path, arcname)
        return archive

    def _write_evolution_artifacts(
        self,
        package_dir: Path,
        target: Path,
        request: ChangeRequest,
        impact: Any,
        old_version: str,
        new_version: str,
    ) -> None:
        evolution_dir = target / ".evolution"
        evolution_dir.mkdir(parents=True, exist_ok=True)
        (evolution_dir / "change-request.yaml").write_text(
            yaml.safe_dump(request.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (evolution_dir / "impact-report.md").write_text(
            self._impact_markdown(impact), encoding="utf-8"
        )
        (evolution_dir / "migration-plan.md").write_text(
            self._migration_markdown(request, old_version, new_version), encoding="utf-8"
        )
        manifest = {
            "change_id": request.id,
            "baseline": str(package_dir),
            "old_version": old_version,
            "new_version": new_version,
            "evolution_type": request.evolution_type.value,
            "requested_by": request.requested_by,
            "owner_approval": request.owner_approval,
            "generated_on": date.today().isoformat(),
        }
        (evolution_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._update_changelog(target, request, new_version)

    @staticmethod
    def _impact_markdown(impact: Any) -> str:
        lines = [
            "# Change Impact Report",
            "",
            f"- Change ID: `{impact.change_id}`",
            f"- Risk: **{impact.risk}**",
            f"- Owner approval required: `{str(impact.approval_required).lower()}`",
            "",
            "## Impacted Components",
            "",
        ]
        lines.extend(f"- {item}" for item in impact.impacted_components)
        lines.extend(["", "## Impacted Files", ""])
        lines.extend(f"- `{item}`" for item in impact.impacted_files)
        lines.extend(["", "## Breaking Changes", ""])
        lines.extend(f"- {item}" for item in impact.breaking_changes or ["None detected"])
        lines.extend(["", "## Rationale", ""])
        lines.extend(f"- {item}" for item in impact.rationale)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _migration_markdown(request: ChangeRequest, old_version: str, new_version: str) -> str:
        lines = [
            "# Migration Plan",
            "",
            f"Upgrade `{old_version}` → `{new_version}`.",
            "",
            "## Procedure",
            "",
            "1. Review impact report and package diff.",
            "2. Run regression checks in a non-production environment.",
            "3. Verify tool permissions and downstream output-contract compatibility.",
            "4. Promote the candidate only after owner approval and release gates pass.",
            "5. Restore the rollback archive if acceptance criteria fail.",
            "",
            "## Acceptance Criteria",
            "",
        ]
        lines.extend(f"- {item}" for item in request.acceptance_criteria or ["No explicit criteria supplied"])
        lines.extend(["", "## Rollback", "", request.rollback_strategy])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _update_changelog(target: Path, request: ChangeRequest, version: str) -> None:
        path = target / "CHANGELOG.md"
        existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n"
        entry = [
            "",
            f"## [{version}] - {date.today().isoformat()}",
            "",
            f"- Change ID: `{request.id}`",
            f"- Type: `{request.evolution_type.value}`",
            f"- Reason: {request.reason}",
        ]
        entry.extend(f"- {op.action.value} `{op.component.value}`: {op.rationale}" for op in request.operations)
        path.write_text(existing.rstrip() + "\n" + "\n".join(entry) + "\n", encoding="utf-8")

    @staticmethod
    def _validate_archive(bundle: zipfile.ZipFile) -> None:
        for member in bundle.infolist():
            path = Path(member.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("回滚包包含不安全路径")
