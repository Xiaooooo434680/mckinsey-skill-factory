from __future__ import annotations

from .models import (
    AccessMode,
    Architecture,
    EvaluationPlan,
    Hypothesis,
    IssueNode,
    ProblemDefinition,
    ReleaseGate,
    SkillRequest,
    ToolContract,
    WorkflowStep,
)


def define_problem(req: SkillRequest) -> ProblemDefinition:
    assumptions = []
    if not req.inputs:
        assumptions.append("输入字段将在 Pilot 阶段由领域专家补全")
    if not req.outputs:
        assumptions.append("默认输出为结构化分析、证据、建议、风险和下一步动作")
    if req.owner == "UNASSIGNED":
        assumptions.append("尚未指定业务 Owner，发布前必须补齐")

    constraints = [
        f"风险等级：{req.risk_level.value}",
        f"部署环境：{req.deployment_environment}",
        "不得将推断伪装成事实",
        "工具失败时不得虚构结果",
    ]
    if req.latency_requirement:
        constraints.append(f"时延要求：{req.latency_requirement}")
    if req.quality_requirement:
        constraints.append(f"质量要求：{req.quality_requirement}")

    return ProblemDefinition(
        user=req.target_user,
        job_to_be_done=req.business_problem,
        business_value=req.desired_outcome,
        success_definition=[
            "输出满足机器可校验 Schema",
            "关键结论可追溯到证据或显式假设",
            "建议具有明确下一步动作",
        ],
        scope=[req.business_problem, "分析并形成可执行输出"],
        non_scope=req.non_goals or ["未经审批执行高风险写操作"],
        constraints=constraints,
        assumptions=assumptions,
    )


def build_issue_tree(req: SkillRequest) -> IssueNode:
    return IssueNode(
        title=f"{req.name} 如何稳定实现目标",
        children=[
            IssueNode(
                title="业务正确性",
                children=[IssueNode(title="目标定义"), IssueNode(title="判断标准"), IssueNode(title="证据质量")],
            ),
            IssueNode(
                title="流程完整性",
                children=[IssueNode(title="正常路径"), IssueNode(title="分支路径"), IssueNode(title="失败路径")],
            ),
            IssueNode(
                title="工具与知识",
                children=[IssueNode(title="数据可用性"), IssueNode(title="工具契约"), IssueNode(title="权限边界")],
            ),
            IssueNode(
                title="输出可执行性",
                children=[IssueNode(title="结构化输出"), IssueNode(title="建议优先级"), IssueNode(title="责任与下一步")],
            ),
            IssueNode(
                title="安全与治理",
                children=[IssueNode(title="审批"), IssueNode(title="审计"), IssueNode(title="降级与回滚")],
            ),
            IssueNode(
                title="评估与迭代",
                children=[IssueNode(title="质量指标"), IssueNode(title="对抗测试"), IssueNode(title="发布门禁")],
            ),
        ],
    )


def build_hypotheses(req: SkillRequest) -> list[Hypothesis]:
    return [
        Hypothesis(
            id="H1",
            statement="该场景具有足够重复性，值得被标准化为 Skill",
            rationale="重复场景才可能摊薄建设和维护成本",
            impact="high",
            confidence="medium",
            evidence_needed=["历史任务频次", "平均人工耗时", "错误成本"],
            validation_method="抽样最近 30-90 天任务记录",
            pass_condition="重复任务占比和节省成本达到业务阈值",
            fail_action="降级为模板或一次性 Workflow",
        ),
        Hypothesis(
            id="H2",
            statement="核心输入和成功标准可被结构化",
            rationale="不可结构化的任务难以稳定评估",
            impact="high",
            confidence="medium",
            evidence_needed=["输入样本", "专家评分标准", "历史优秀输出"],
            validation_method="由两名领域专家独立标注并比较一致性",
            pass_condition="关键字段覆盖率与专家一致性达到 80%",
            fail_action="缩小 Skill 范围并保留人工判断节点",
        ),
        Hypothesis(
            id="H3",
            statement="所需数据、知识和工具在运行时可用",
            rationale="模型不能替代真实数据访问",
            impact="high",
            confidence="low" if not req.tools_available else "medium",
            evidence_needed=req.tools_available or ["工具清单", "数据 Owner", "权限证明"],
            validation_method="执行只读连通性与权限测试",
            pass_condition="核心工具成功率达到 99%，字段满足契约",
            fail_action="输出 blocked/partial，不生成未经验证结论",
        ),
        Hypothesis(
            id="H4",
            statement="风险可以通过最小权限、审批和审计控制",
            rationale="工程级 Skill 必须限制错误影响半径",
            impact="high",
            confidence="medium",
            evidence_needed=["风险评审", "权限矩阵", "审批流程"],
            validation_method="安全评审与红队测试",
            pass_condition="高风险动作均有审批、审计和回滚",
            fail_action="强制只读运行或停止发布",
        ),
    ]


def build_architecture(req: SkillRequest) -> Architecture:
    return Architecture(
        entrypoint="validated_skill_request",
        core_capabilities=["问题定义", "结构化拆解", "假设验证", "证据综合", "行动建议"],
        sub_capabilities=["工具选择", "失败降级", "输出校验", "风险检查"],
        workflow_mode="branching",
        tool_strategy="实时事实必须通过显式工具契约获取；默认只读和最小权限",
        knowledge_strategy="版本化知识源；记录来源、更新时间和适用范围",
        memory_strategy="默认无长期记忆；会话状态由宿主 Runtime 管理",
        human_in_the_loop=req.human_approval_points or ["高风险写操作", "低置信度重大决策"],
        fallback_strategy="工具失败或证据不足时返回 partial/blocked，并列出缺失信息",
        observability=["stage_latency", "tool_success_rate", "schema_validity", "quality_score", "policy_events"],
    )


def build_tools(req: SkillRequest) -> list[ToolContract]:
    tools = []
    for name in req.tools_available:
        write = "write" in name.lower() or any("write" in p.lower() for p in req.permissions)
        tools.append(
            ToolContract(
                name=name,
                purpose=f"为 {req.name} 提供受控数据或动作能力",
                access_mode=AccessMode.write if write else AccessMode.read,
                input_schema={"type": "object", "additionalProperties": False},
                output_schema={"type": "object"},
                permission="least-privilege",
                approval_required=write,
            )
        )
    return tools


def build_workflow(req: SkillRequest) -> list[WorkflowStep]:
    steps = [
        WorkflowStep(
            step_id="S1",
            name="validate_input",
            objective="校验请求完整性和权限",
            inputs=["skill_request"],
            action="执行 Schema、范围和权限校验",
            outputs=["validated_request", "validation_errors"],
            audit_event="input_validated",
        ),
        WorkflowStep(
            step_id="S2",
            name="define_problem",
            objective="将模糊需求转化为可验证问题",
            inputs=["validated_request"],
            action="明确用户、场景、目标、边界、约束和成功标准",
            outputs=["problem_definition"],
            audit_event="problem_defined",
        ),
        WorkflowStep(
            step_id="S3",
            name="build_issue_tree",
            objective="建立 MECE 问题树并找到关键杠杆",
            inputs=["problem_definition"],
            action="按业务、流程、工具、治理和评估拆解",
            outputs=["issue_tree", "priority_issues"],
            audit_event="issue_tree_built",
        ),
        WorkflowStep(
            step_id="S4",
            name="validate_hypotheses",
            objective="优先验证高影响低置信度假设",
            inputs=["priority_issues"],
            action="收集证据并记录假设状态",
            tool=req.tools_available[0] if req.tools_available else None,
            outputs=["validated_hypotheses", "evidence_gaps"],
            audit_event="hypotheses_validated",
        ),
        WorkflowStep(
            step_id="S5",
            name="generate_recommendation",
            objective="形成结论先行、证据可追溯的输出",
            inputs=["validated_hypotheses", "evidence_gaps"],
            action="生成结论、证据、风险、建议和下一步",
            outputs=["draft_output"],
            audit_event="recommendation_generated",
        ),
        WorkflowStep(
            step_id="S6",
            name="quality_and_policy_gate",
            objective="执行 Schema、质量、安全和审批检查",
            inputs=["draft_output"],
            action="校验输出，阻断越权和高风险动作",
            outputs=["final_output", "gate_result"],
            approval_required=req.risk_level.value in {"high", "critical"},
            audit_event="release_gate_evaluated",
        ),
    ]
    return steps


def build_evaluation() -> EvaluationPlan:
    return EvaluationPlan(
        metrics={
            "task_success": 0.85,
            "factuality": 0.95,
            "schema_validity": 1.00,
            "tool_selection_accuracy": 0.90,
            "policy_compliance": 1.00,
            "actionability": 0.80,
        },
        required_case_types=[
            "happy_path",
            "missing_information",
            "conflicting_evidence",
            "tool_failure",
            "permission_denied",
            "boundary_case",
            "adversarial_input",
            "high_risk_request",
            "negative_routing",
        ],
    )


def build_release_gate(req: SkillRequest, tools: list[ToolContract]) -> ReleaseGate:
    permissions_reviewed = all(t.permission == "least-privilege" for t in tools)
    return ReleaseGate(
        scope_clear=True,
        owner_assigned=req.owner != "UNASSIGNED",
        schema_validated=True,
        tool_permissions_reviewed=permissions_reviewed,
        safety_review_passed=req.risk_level.value in {"low", "medium"},
        eval_threshold_met=False,
        rollback_defined=True,
        observability_ready=True,
        documentation_complete=True,
    )
