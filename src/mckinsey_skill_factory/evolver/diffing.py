from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileDiff:
    path: str
    status: str
    diff: str


class PackageDiffer:
    def compare(self, old_dir: Path, new_dir: Path) -> list[FileDiff]:
        old_files = self._files(old_dir)
        new_files = self._files(new_dir)
        results: list[FileDiff] = []
        for relative in sorted(set(old_files) | set(new_files)):
            if relative.startswith("rollback/"):
                continue
            old_path = old_files.get(relative)
            new_path = new_files.get(relative)
            if old_path is None:
                results.append(FileDiff(relative, "added", ""))
                continue
            if new_path is None:
                results.append(FileDiff(relative, "removed", ""))
                continue
            old_bytes = old_path.read_bytes()
            new_bytes = new_path.read_bytes()
            if old_bytes == new_bytes:
                continue
            try:
                old_text = old_bytes.decode("utf-8").splitlines(keepends=True)
                new_text = new_bytes.decode("utf-8").splitlines(keepends=True)
                diff = "".join(
                    difflib.unified_diff(
                        old_text,
                        new_text,
                        fromfile=f"old/{relative}",
                        tofile=f"new/{relative}",
                    )
                )
            except UnicodeDecodeError:
                diff = "Binary file changed\n"
            results.append(FileDiff(relative, "modified", diff))
        return results

    def render_markdown(self, old_dir: Path, new_dir: Path) -> str:
        diffs = self.compare(old_dir, new_dir)
        lines = ["# Skill Package Diff", "", f"- Baseline: `{old_dir}`", f"- Candidate: `{new_dir}`", ""]
        if not diffs:
            lines.append("No changes detected.")
            return "\n".join(lines) + "\n"
        lines.extend(["## Summary", ""])
        for item in diffs:
            lines.append(f"- `{item.path}`: {item.status}")
        for item in diffs:
            if item.diff:
                lines.extend(["", f"## {item.path}", "", "```diff", item.diff.rstrip(), "```"])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _files(root: Path) -> dict[str, Path]:
        return {
            str(path.relative_to(root)): path
            for path in root.rglob("*")
            if path.is_file()
        }
