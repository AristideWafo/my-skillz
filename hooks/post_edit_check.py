#!/usr/bin/env python3
"""Report syntax errors in directly edited JSON, TOML, Python, and Markdown files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10: skip optional TOML parsing.
    tomllib = None


PATCH_PATH_RE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$", re.MULTILINE)


def read_payload() -> dict:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def candidate_paths(payload: dict, cwd: Path) -> list[Path]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    raw_paths: set[str] = set()
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            raw_paths.add(value)
    command = tool_input.get("command")
    if isinstance(command, str):
        raw_paths.update(PATCH_PATH_RE.findall(command))

    paths: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        resolved = (cwd / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            resolved.relative_to(cwd)
        except ValueError:
            continue
        if resolved.is_file():
            paths.append(resolved)
    return sorted(set(paths))


def check(path: Path) -> Optional[str]:
    try:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".toml" and tomllib is not None:
            tomllib.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".py":
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        elif path.suffix == ".md":
            text = path.read_text(encoding="utf-8")
            fences = [line for line in text.splitlines() if re.match(r"^\s*(```|~~~)", line)]
            if len(fences) % 2:
                return "unbalanced fenced code block"
    except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
        return str(exc)
    return None


def main() -> int:
    payload = read_payload()
    raw_cwd = payload.get("cwd")
    cwd = Path(raw_cwd).resolve() if isinstance(raw_cwd, str) else Path.cwd().resolve()
    failures = [(path, check(path)) for path in candidate_paths(payload, cwd)]
    failures = [(path, error) for path, error in failures if error]
    if not failures:
        return 0
    summary = "; ".join(f"{path.relative_to(cwd)}: {error}" for path, error in failures)
    json.dump(
        {"systemMessage": "Post-edit syntax check found an issue: " + summary},
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
