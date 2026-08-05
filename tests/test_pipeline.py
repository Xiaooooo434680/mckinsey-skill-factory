from pathlib import Path

from mckinsey_skill_factory.generator import PackageGenerator
from mckinsey_skill_factory.io import load_request
from mckinsey_skill_factory.pipeline import SkillFactory


def test_compile_example(tmp_path: Path) -> None:
    req = load_request(Path("examples/sales-opportunity/request.yaml"))
    spec = SkillFactory().compile(req)
    assert spec.name == "sales-opportunity-diagnosis"
    assert len(spec.workflow) >= 6
    assert spec.output_contract["additionalProperties"] is False

    target = PackageGenerator().generate(spec, tmp_path)
    assert (target / "SKILL.md").exists()
    assert (target / "output.schema.json").exists()
    assert (target / "evals/cases.jsonl").exists()
