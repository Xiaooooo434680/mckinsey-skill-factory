from pathlib import Path

import pytest

from mckinsey_skill_factory.evolver.diffing import PackageDiffer
from mckinsey_skill_factory.evolver.evolver import SkillEvolver
from mckinsey_skill_factory.evolver.models import ChangeRequest
from mckinsey_skill_factory.generator import PackageGenerator
from mckinsey_skill_factory.io import load_request
from mckinsey_skill_factory.pipeline import SkillFactory


def _baseline(tmp_path: Path) -> Path:
    req = load_request(Path("examples/sales-opportunity/request.yaml"))
    spec = SkillFactory().compile(req)
    return PackageGenerator().generate(spec, tmp_path / "baseline")


def test_evolver_creates_new_version_and_artifacts(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    request = ChangeRequest.model_validate(
        {
            "id": "CR-TEST-001",
            "skill_name": "sales-opportunity-diagnosis",
            "reason": "强化 CRM 工具失败时的降级行为和防幻觉约束",
            "evolution_type": "corrective",
            "requested_by": "revenue-operations",
            "acceptance_criteria": ["工具失败时返回 partial"],
            "operations": [
                {
                    "component": "workflow",
                    "action": "update",
                    "selector": "S4",
                    "rationale": "增加明确降级策略",
                    "value": {"fallback": "返回 partial 并列出缺失证据"},
                },
                {
                    "component": "guardrails",
                    "action": "add",
                    "rationale": "禁止虚构 CRM 活动",
                    "value": "CRM 不可用时不得虚构活动记录",
                },
            ],
        }
    )

    result = SkillEvolver().evolve(baseline, request, tmp_path / "evolved")

    assert result.old_version == "0.1.0"
    assert result.new_version == "0.1.1"
    assert result.target.name == "sales-opportunity-diagnosis-0.1.1"
    assert (baseline / "skill.yaml").read_text(encoding="utf-8").find("0.1.0") >= 0
    assert (result.target / "skill.yaml").read_text(encoding="utf-8").find("0.1.1") >= 0
    assert (result.target / ".evolution/impact-report.md").exists()
    assert (result.target / ".evolution/package-diff.md").exists()
    assert (result.target / ".evolution/regression-results.json").exists()
    assert (result.target / "CHANGELOG.md").exists()
    assert result.rollback_archive.exists()
    assert result.regression_report.passed
    assert PackageDiffer().compare(baseline, result.target)


def test_high_impact_change_requires_owner_approval(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    request = ChangeRequest.model_validate(
        {
            "id": "CR-TEST-002",
            "reason": "删除现有工具会改变 Skill 的可用证据和运行行为",
            "evolution_type": "evolutionary",
            "requested_by": "platform-team",
            "operations": [
                {
                    "component": "tools",
                    "action": "remove",
                    "selector": "crm_read_api",
                    "rationale": "迁移到新的数据平台",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="owner_approval"):
        SkillEvolver().evolve(baseline, request, tmp_path / "evolved")


def test_rollback_restores_baseline(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    request = ChangeRequest.model_validate(
        {
            "id": "CR-TEST-003",
            "reason": "补充一个低风险的运行时约束以验证回滚能力",
            "evolution_type": "corrective",
            "requested_by": "platform-team",
            "operations": [
                {
                    "component": "guardrails",
                    "action": "add",
                    "rationale": "补充安全约束",
                    "value": "输出必须包含 evidence 字段",
                }
            ],
        }
    )
    result = SkillEvolver().evolve(baseline, request, tmp_path / "evolved")
    restored = SkillEvolver().rollback(result.rollback_archive, tmp_path / "restored")

    assert (restored / "skill.yaml").exists()
    assert "0.1.0" in (restored / "skill.yaml").read_text(encoding="utf-8")
