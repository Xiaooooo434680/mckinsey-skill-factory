from __future__ import annotations

from dataclasses import dataclass

from .models import EvolutionType, VersionBump


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        core = value.split("+", 1)[0].split("-", 1)[0]
        parts = core.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError(f"无效语义版本：{value}")
        return cls(*(int(part) for part in parts))

    def bump(self, kind: VersionBump) -> "SemVer":
        if kind == VersionBump.major:
            return SemVer(self.major + 1, 0, 0)
        if kind == VersionBump.minor:
            return SemVer(self.major, self.minor + 1, 0)
        if kind == VersionBump.patch:
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError("auto 必须先解析为具体 bump 类型")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def resolve_bump(requested: VersionBump, evolution_type: EvolutionType) -> VersionBump:
    if requested != VersionBump.auto:
        return requested
    mapping = {
        EvolutionType.corrective: VersionBump.patch,
        EvolutionType.perfective: VersionBump.patch,
        EvolutionType.adaptive: VersionBump.minor,
        EvolutionType.evolutionary: VersionBump.major,
    }
    return mapping[evolution_type]
