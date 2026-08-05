import pytest
from pydantic import ValidationError

from mckinsey_skill_factory.models import SkillRequest


def test_high_risk_write_requires_approval() -> None:
    with pytest.raises(ValidationError):
        SkillRequest(
            name="unsafe-writer",
            business_problem="执行高风险且不可逆的外部系统写操作",
            target_user="运营人员",
            desired_outcome="自动完成变更",
            permissions=["write"],
            risk_level="high",
        )
