from __future__ import annotations

import json
from pathlib import Path

import typer

from .evolver.diffing import PackageDiffer
from .evolver.evolver import SkillEvolver
from .evolver.inspector import PackageInspector
from .evolver.io import load_change_request
from .evolver.models import ChangeRequest
from .evolver.regression import RegressionRunner
from .generator import PackageGenerator
from .io import load_request
from .models import SkillRequest
from .pipeline import SkillFactory
from .quality import QualityGate

app = typer.Typer(no_args_is_help=True, help="McKinsey-style Skill Factory and Evolver")


@app.command()
def build(
    request_file: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("dist"), "--output", "-o"),
) -> None:
    """Create a new engineering Skill package from a SkillRequest."""
    req = load_request(request_file)
    spec = SkillFactory().compile(req)
    target = PackageGenerator().generate(spec, output)
    gate = QualityGate().evaluate(spec)

    typer.echo(f"Generated: {target}")
    typer.echo(f"Readiness: {spec.readiness.value}")
    for warning in gate.warnings:
        typer.echo(f"WARNING: {warning}")
    if gate.errors:
        for error in gate.errors:
            typer.echo(f"ERROR: {error}")
        raise typer.Exit(code=2)


@app.command()
def validate(package_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Validate a Skill package structure."""
    result = QualityGate().validate_package(package_dir)
    for warning in result.warnings:
        typer.echo(f"WARNING: {warning}")
    for error in result.errors:
        typer.echo(f"ERROR: {error}")
    if not result.passed:
        raise typer.Exit(code=2)
    typer.echo("Package validation passed")


@app.command()
def inspect(
    package_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Inspect an existing Skill package and calculate immutable checksums."""
    report = PackageInspector().inspect(package_dir)
    payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        typer.echo(f"Inspection written: {output}")
    else:
        typer.echo(payload.rstrip())


@app.command()
def modify(
    package_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    change_request: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("dist/evolved"), "--output", "-o"),
) -> None:
    """Create a new Skill version from an existing package and ChangeRequest."""
    request = load_change_request(change_request)
    try:
        result = SkillEvolver().evolve(package_dir, request, output)
    except (ValueError, KeyError, FileExistsError, RuntimeError) as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=2) from exc

    typer.echo(f"Generated: {result.target}")
    typer.echo(f"Version: {result.old_version} -> {result.new_version}")
    typer.echo(f"Impact risk: {result.impact_report.risk}")
    typer.echo(f"Regression: {'passed' if result.regression_report.passed else 'failed'}")
    typer.echo(f"Rollback: {result.rollback_archive}")


@app.command("diff")
def diff_packages(
    baseline: Path = typer.Argument(..., exists=True, file_okay=False),
    candidate: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Render a file-level and unified-text diff between Skill packages."""
    report = PackageDiffer().render_markdown(baseline, candidate)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        typer.echo(f"Diff written: {output}")
    else:
        typer.echo(report.rstrip())


@app.command("test")
def regression_test(
    candidate: Path = typer.Argument(..., exists=True, file_okay=False),
    baseline: Path = typer.Option(..., "--baseline", "-b", exists=True, file_okay=False),
    change_request: Path = typer.Option(..., "--change-request", "-c", exists=True, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Run deterministic regression checks against a baseline Skill package."""
    request = load_change_request(change_request)
    report = RegressionRunner().run(baseline, candidate, request)
    payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        typer.echo(f"Regression report written: {output}")
    else:
        typer.echo(payload.rstrip())
    if not report.passed:
        raise typer.Exit(code=2)


@app.command()
def rollback(
    archive: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("dist/restored"), "--output", "-o"),
) -> None:
    """Restore a Skill package from an Evolver rollback archive."""
    try:
        restored = SkillEvolver().rollback(archive, output)
    except (ValueError, FileExistsError) as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=2) from exc
    typer.echo(f"Restored: {restored}")


@app.command("schema")
def export_schema(
    output: Path = typer.Option(Path("schemas/skill-request.schema.json"), "--output", "-o"),
) -> None:
    """Export the SkillRequest JSON Schema."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(SkillRequest.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Schema written: {output}")


@app.command("evolution-schema")
def export_evolution_schema(
    output: Path = typer.Option(Path("schemas/change-request.schema.json"), "--output", "-o"),
) -> None:
    """Export the ChangeRequest JSON Schema."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(ChangeRequest.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Schema written: {output}")


if __name__ == "__main__":
    app()
