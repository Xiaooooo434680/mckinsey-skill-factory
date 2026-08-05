from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvolutionType(str, Enum):
    corrective = "corrective"
    adaptive = "adaptive"
    perfective = "perfective"
    evolutionary = "evolutionary"


class VersionBump(str, Enum):
    auto = "auto"
    patch = "patch"
    minor = "minor"
    major = "major"


class ChangeAction(str, Enum):
    add = "add"
    update = "update"
    remove = "remove"
    replace = "replace"


class ChangeComponent(str, Enum):
    metadata = "metadata"
    workflow = "workflow"
    tools = "tools"
    guardrails = "guardrails"
    output_contract = "output_contract"
    evaluation = "evaluation"
    file = "file"


class ChangeOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component: ChangeComponent
    action: ChangeAction
    selector: str | None = None
    value: Any = None
    expected_old: Any = None
    rationale: str = Field(min_length=3)

    @model_validator(mode="after")
    def validate_shape(self) -> "ChangeOperation":
        if self.action in {ChangeAction.add, ChangeAction.update, ChangeAction.replace}:
            if self.value is None:
                raise ValueError(f"{self.action.value} 操作必须提供 value")
        if self.action == ChangeAction.remove and self.selector is None:
            if self.component not in {ChangeComponent.guardrails, ChangeComponent.output_contract}:
                raise ValueError("remove 操作必须提供 selector")
        if self.component in {ChangeComponent.workflow, ChangeComponent.tools, ChangeComponent.file}:
            if self.action != ChangeAction.add and self.selector is None:
                raise ValueError(f"{self.component.value} 的非 add 操作必须提供 selector")
        if self.component == ChangeComponent.file and self.action != ChangeAction.replace:
            raise ValueError("file 组件仅支持 replace")
        return self


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    skill_name: str | None = None
    reason: str = Field(min_length=10)
    evolution_type: EvolutionType
    requested_by: str = Field(min_length=2)
    version_bump: VersionBump = VersionBump.auto
    operations: list[ChangeOperation] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)
    rollback_strategy: str = "恢复演进前的完整 Skill Package"
    owner_approval: bool = False


class PackageInspection(BaseModel):
    name: str
    version: str
    readiness: str
    root: str
    files: list[str]
    checksums: dict[str, str]
    warnings: list[str]


class ImpactReport(BaseModel):
    change_id: str
    impacted_components: list[str]
    impacted_files: list[str]
    breaking_changes: list[str]
    risk: str
    approval_required: bool
    rationale: list[str]


class RegressionCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class RegressionReport(BaseModel):
    passed: bool
    baseline_version: str
    candidate_version: str
    checks: list[RegressionCheck]
    errors: list[str]
    warnings: list[str]


class EvolutionResult(BaseModel):
    source: Path
    target: Path
    old_version: str
    new_version: str
    impact_report: ImpactReport
    regression_report: RegressionReport
    rollback_archive: Path
