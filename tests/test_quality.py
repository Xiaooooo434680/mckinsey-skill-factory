from pathlib import Path

from mckinsey_skill_factory.io import load_request
from mckinsey_skill_factory.pipeline import SkillFactory
from mckinsey_skill_factory.quality import QualityGate


def test_quality_gate_warns_before_real_eval() -> None:
    req = load_request(Path("examples/sales-opportunity/request.yaml"))
    spec = SkillFactory().compile(req)
    result = QualityGate().evaluate(spec)
    assert result.passed
    assert any("真实评估" in warning for warning in result.warnings)
