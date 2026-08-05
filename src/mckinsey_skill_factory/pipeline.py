from __future__ import annotations

from .models import Readiness, SkillRequest, SkillSpec
from .quality import QualityGate
from .stages import (
    build_architecture,
    build_evaluation,
    build_hypotheses,
    build_issue_tree,
    build_release_gate,
    build_tools,
    build_workflow,
    define_problem,
)


class SkillFactory:
    """Deterministic meta-skill pipeline.

    An LLM may enrich individual stages, but correctness, schemas and gates remain deterministic.
    """

    def compile(self, req: SkillRequest) -> SkillSpec:
        problem = define_problem(req)
        issue_tree = build_issue_tree(req)
        hypotheses = build_hypotheses(req)
        architecture = build_architecture(req)
        tools = build_tools(req)
        workflow = build_workflow(req)
        evaluation = build_evaluation()
        release_gate = build_release_gate(req, tools)

        output_contract = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "status",
                "summary",
                "findings",
                "recommendations",
                "evidence",
                "assumptions",
                "risks",
                "confidence",
                "next_actions",
            ],
            "properties": {
                "status": {"enum": ["success", "partial", "blocked"]},
                "summary": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "recommendations": {"type": "array", "items": {"type": "object"}},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "next_actions": {"type": "array", "items": {"type": "object"}},
            },
        }

        assumptions = problem.assumptions + [
            "默认工具访问为最小权限",
            "未配置的外部系统不得被假设为可用",
            "真实发布前必须使用领域数据执行评估",
        ]

        spec = SkillSpec(
            name=req.name,
            purpose=req.business_problem,
            target_user=req.target_user,
            trigger=req.trigger,
            inputs=req.inputs or ["user_request", "available_context"],
            outputs=req.outputs or ["structured_recommendation"],
            risk_level=req.risk_level,
            owner=req.owner,
            problem_definition=problem,
            issue_tree=issue_tree,
            hypotheses=hypotheses,
            architecture=architecture,
            tools=tools,
            workflow=workflow,
            output_contract=output_contract,
            guardrails=[
                "不得虚构事实、工具结果、权限或引用",
                "所有关键结论必须附带证据或标记为假设",
                "工具失败时返回 partial 或 blocked",
                "高风险写操作必须人工审批",
                "默认使用最小权限和完整审计",
                "不得输出超出用户权限范围的敏感数据",
                "低置信度重大结论必须升级给人工",
                "输出必须通过 JSON Schema 校验",
            ],
            evaluation=evaluation,
            release_gate=release_gate,
            assumptions=assumptions,
            readiness=Readiness.draft,
        )

        gate = QualityGate().evaluate(spec)
        if gate.passed and release_gate.passed:
            spec.readiness = Readiness.pilot_ready
        return spec
