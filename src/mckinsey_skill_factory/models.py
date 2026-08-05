from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AccessMode(str, Enum):
    read = "read"
    write = "write"


class Readiness(str, Enum):
    concept = "concept"
    draft = "draft"
    pilot_ready = "pilot-ready"
    production_ready = "production-ready"


class SkillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9-]+$")
    business_problem: str = Field(min_length=10)
    target_user: str = Field(min_length=2)
    desired_outcome: str = Field(min_length=5)
    current_process: list[str] = Field(default_factory=list)
    trigger: str = "由用户显式调用"
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    tools_available: list[str] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=lambda: ["read-only"])
    risk_level: RiskLevel = RiskLevel.medium
    latency_requirement: str | None = None
    quality_requirement: str | None = None
    human_approval_points: list[str] = Field(default_factory=list)
    deployment_environment: str = "platform-agnostic"
    examples: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    owner: str = "UNASSIGNED"

    @model_validator(mode="after")
    def high_risk_requires_approval(self) -> "SkillRequest":
        has_write = any("write" in p.lower() for p in self.permissions)
        if self.risk_level in {RiskLevel.high, RiskLevel.critical} and has_write:
            if not self.human_approval_points:
                raise ValueError("高风险写操作必须定义 human_approval_points")
        return self


class ProblemDefinition(BaseModel):
    user: str
    job_to_be_done: str
    business_value: str
    success_definition: list[str]
    scope: list[str]
    non_scope: list[str]
    constraints: list[str]
    assumptions: list[str]


class IssueNode(BaseModel):
    title: str
    children: list["IssueNode"] = Field(default_factory=list)


class Hypothesis(BaseModel):
    id: str
    statement: str
    rationale: str
    impact: str
    confidence: str
    evidence_needed: list[str]
    validation_method: str
    pass_condition: str
    fail_action: str


class ToolContract(BaseModel):
    name: str
    purpose: str
    access_mode: AccessMode = AccessMode.read
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permission: str = "least-privilege"
    timeout_seconds: int = Field(default=20, ge=1, le=300)
    retries: int = Field(default=2, ge=0, le=5)
    failure_handling: str = "返回 partial，不得虚构工具结果"
    approval_required: bool = False
    audit: bool = True


class WorkflowStep(BaseModel):
    step_id: str
    name: str
    objective: str
    inputs: list[str]
    action: str
    tool: str | None = None
    decision_rule: str | None = None
    outputs: list[str]
    retry: int = 0
    timeout_seconds: int = 30
    fallback: str = "标记 partial 并说明缺失证据"
    approval_required: bool = False
    audit_event: str


class Architecture(BaseModel):
    entrypoint: str
    core_capabilities: list[str]
    sub_capabilities: list[str]
    workflow_mode: str
    tool_strategy: str
    knowledge_strategy: str
    memory_strategy: str
    human_in_the_loop: list[str]
    fallback_strategy: str
    observability: list[str]


class EvaluationPlan(BaseModel):
    metrics: dict[str, float]
    required_case_types: list[str]
    minimum_cases: int = 12
    release_threshold: float = 0.80


class ReleaseGate(BaseModel):
    scope_clear: bool
    owner_assigned: bool
    schema_validated: bool
    tool_permissions_reviewed: bool
    safety_review_passed: bool
    eval_threshold_met: bool
    rollback_defined: bool
    observability_ready: bool
    documentation_complete: bool

    @property
    def passed(self) -> bool:
        return all(self.model_dump().values())


class SkillSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "0.1.0"
    purpose: str
    target_user: str
    trigger: str
    inputs: list[str]
    outputs: list[str]
    risk_level: RiskLevel
    owner: str
    problem_definition: ProblemDefinition
    issue_tree: IssueNode
    hypotheses: list[Hypothesis]
    architecture: Architecture
    tools: list[ToolContract]
    workflow: list[WorkflowStep]
    output_contract: dict[str, Any]
    guardrails: list[str]
    evaluation: EvaluationPlan
    release_gate: ReleaseGate
    assumptions: list[str]
    readiness: Readiness
