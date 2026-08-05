from pathlib import Path

import yaml

from .models import ChangeRequest


def load_change_request(path: Path) -> ChangeRequest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ChangeRequest 必须是 YAML object")
    return ChangeRequest.model_validate(data)
