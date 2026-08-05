from pathlib import Path

import yaml

from .models import SkillRequest


def load_request(path: Path) -> SkillRequest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("请求文件必须是 YAML object")
    return SkillRequest.model_validate(data)
