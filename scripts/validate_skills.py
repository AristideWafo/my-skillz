#!/usr/bin/env python3
"""Validate portable Claude/Codex skill structure without third-party packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10 use the narrow fallback below.
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MUTABLE_ACTION_RE = re.compile(r"\buses:\s*[^\s#]+@(master|main)\b", re.IGNORECASE)
FORBIDDEN_PORTABLE_TERMS = ("create_file", "str_replace", "Reader Claude", "Claude.ai")
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
REQUIRED_AGENTS = {
    "frontend-implementer",
    "backend-implementer",
    "platform-release-engineer",
    "software-reviewer",
    "solution-architect",
}
READ_ONLY_AGENTS = {"software-reviewer", "solution-architect"}
WRITABLE_AGENTS = REQUIRED_AGENTS - READ_ONLY_AGENTS


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str] | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None

    values: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in match.group(1).splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith((" ", "\t")):
            if current_key is None:
                return None
            values[current_key] = f"{values[current_key]} {raw_line.strip()}".strip()
            continue
        if ":" not in raw_line:
            return None
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip().strip('"\'')
    return values, text[match.end() :]


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def validate_markdown(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    fences = [line for line in text.splitlines() if re.match(r"^\s*(```|~~~)", line)]
    if len(fences) % 2:
        errors.append(f"{relative(path)}: unbalanced fenced code block")

    for target in MARKDOWN_LINK_RE.findall(text):
        target = target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        file_target = target.split("#", 1)[0]
        if file_target and not (path.parent / file_target).resolve().exists():
            errors.append(f"{relative(path)}: broken link to {target}")

    for line_number, line in enumerate(text.splitlines(), 1):
        if MUTABLE_ACTION_RE.search(line):
            errors.append(
                f"{relative(path)}:{line_number}: mutable action or workflow branch in uses:"
            )


def validate_skill(skill_dir: Path, errors: list[str], warnings: list[str]) -> None:
    skill_file = skill_dir / "SKILL.md"
    parsed = parse_frontmatter(skill_file)
    if parsed is None:
        errors.append(f"{relative(skill_file)}: invalid or missing YAML frontmatter")
        return

    frontmatter, body = parsed
    unexpected = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
    if unexpected:
        errors.append(
            f"{relative(skill_file)}: unsupported frontmatter keys: {', '.join(sorted(unexpected))}"
        )

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if not NAME_RE.fullmatch(name):
        errors.append(f"{relative(skill_file)}: invalid skill name {name!r}")
    if name != skill_dir.name:
        errors.append(
            f"{relative(skill_file)}: frontmatter name {name!r} does not match folder"
        )
    if not description:
        errors.append(f"{relative(skill_file)}: missing description")
    if len(description) > 1024:
        errors.append(f"{relative(skill_file)}: description exceeds 1024 characters")
    if "<" in description or ">" in description:
        errors.append(f"{relative(skill_file)}: description contains angle brackets")
    if re.search(r"^\s*\[TODO:[^\]]*\]\s*$", body, re.MULTILINE):
        errors.append(f"{relative(skill_file)}: unfinished TODO placeholder")

    for term in FORBIDDEN_PORTABLE_TERMS:
        if term in body:
            errors.append(
                f"{relative(skill_file)}: product-specific tool or workflow term {term!r}"
            )

    line_count = len(skill_file.read_text(encoding="utf-8").splitlines())
    if line_count > 180:
        warnings.append(
            f"{relative(skill_file)}: {line_count} lines; consider progressive disclosure"
        )

    openai_file = skill_dir / "agents" / "openai.yaml"
    if not openai_file.exists():
        errors.append(f"{relative(skill_dir)}: missing agents/openai.yaml")
    else:
        metadata = openai_file.read_text(encoding="utf-8")
        if f"${name}" not in metadata:
            errors.append(
                f"{relative(openai_file)}: default_prompt must mention ${name}"
            )
        short_match = re.search(r'^\s*short_description:\s*"([^"]+)"\s*$', metadata, re.MULTILINE)
        if not short_match:
            errors.append(f"{relative(openai_file)}: quoted short_description is required")
        elif not 25 <= len(short_match.group(1)) <= 64:
            errors.append(
                f"{relative(openai_file)}: short_description must be 25-64 characters"
            )

    validate_markdown(skill_file, errors)
    for reference in sorted((skill_dir / "references").glob("*.md")):
        validate_markdown(reference, errors)


def validate_agents(errors: list[str]) -> None:
    claude_dir = ROOT / ".claude" / "agents"
    codex_dir = ROOT / ".codex" / "agents"
    claude_files = {path.stem: path for path in claude_dir.glob("*.md")}
    codex_files = {path.stem: path for path in codex_dir.glob("*.toml")}

    if set(claude_files) != REQUIRED_AGENTS:
        errors.append(".claude/agents: agent set does not match required roles")
    if set(codex_files) != REQUIRED_AGENTS:
        errors.append(".codex/agents: agent set does not match required roles")

    for name, path in claude_files.items():
        parsed = parse_frontmatter(path)
        if parsed is None:
            errors.append(f"{relative(path)}: invalid or missing YAML frontmatter")
            continue
        frontmatter, body = parsed
        if frontmatter.get("name") != name:
            errors.append(f"{relative(path)}: name must match filename")
        if not frontmatter.get("description"):
            errors.append(f"{relative(path)}: missing description")
        if not body.strip():
            errors.append(f"{relative(path)}: missing agent instructions")
        if name in READ_ONLY_AGENTS and frontmatter.get("permissionMode") != "plan":
            errors.append(f"{relative(path)}: review/design agents must use plan mode")
        if frontmatter.get("permissionMode") == "bypassPermissions":
            errors.append(f"{relative(path)}: bypassPermissions is not allowed")

    for name, path in codex_files.items():
        try:
            text = path.read_text(encoding="utf-8")
            if tomllib is not None:
                values = tomllib.loads(text)
            else:
                values = {
                    key: match.group(1)
                    for key in ("name", "description", "sandbox_mode")
                    if (match := re.search(rf'^\s*{key}\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE))
                }
                instructions = re.search(
                    r'^\s*developer_instructions\s*=\s*"""(.*?)"""\s*$',
                    text,
                    re.MULTILINE | re.DOTALL,
                )
                if instructions:
                    values["developer_instructions"] = instructions.group(1)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{relative(path)}: invalid TOML: {exc}")
            continue
        for required in ("name", "description", "developer_instructions"):
            if not values.get(required):
                errors.append(f"{relative(path)}: missing {required}")
        if values.get("name") != name:
            errors.append(f"{relative(path)}: name must match filename")
        if name in READ_ONLY_AGENTS and values.get("sandbox_mode") != "read-only":
            errors.append(f"{relative(path)}: review/design agents must be read-only")
        if name in WRITABLE_AGENTS and values.get("sandbox_mode") != "workspace-write":
            errors.append(f"{relative(path)}: implementation agents must use workspace-write")


def validate_hooks(errors: list[str]) -> None:
    config_files = (ROOT / ".claude" / "settings.json", ROOT / ".codex" / "hooks.json")
    required_events = {"SessionStart", "PreToolUse", "PostToolUse"}
    for path in config_files:
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative(path)}: invalid JSON: {exc}")
            continue
        hooks = values.get("hooks")
        if not isinstance(hooks, dict) or not required_events.issubset(hooks):
            errors.append(f"{relative(path)}: missing required hook events")
            continue
        serialized = json.dumps(hooks)
        for script_name in ("session_context.py", "safety_guard.py", "post_edit_check.py"):
            if script_name not in serialized:
                errors.append(f"{relative(path)}: does not reference {script_name}")

    for script_name in ("session_context.py", "safety_guard.py", "post_edit_check.py"):
        path = ROOT / "hooks" / script_name
        if not path.exists():
            errors.append(f"{relative(path)}: hook script is missing")
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{relative(path)}: invalid Python: {exc}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    skill_dirs = sorted(path.parent for path in ROOT.glob("*/SKILL.md"))

    if not skill_dirs:
        errors.append("no top-level skills found")

    for directory in sorted(path for path in ROOT.iterdir() if path.is_dir()):
        if directory.name.startswith(".") or directory.name in {"docs", "scripts", "tests"}:
            continue
        markdown_files = list(directory.glob("*.md"))
        if markdown_files and not (directory / "SKILL.md").exists():
            errors.append(f"{relative(directory)}: Markdown content without SKILL.md")

    for skill_dir in skill_dirs:
        validate_skill(skill_dir, errors, warnings)

    validate_agents(errors)
    validate_hooks(errors)

    for markdown in sorted(ROOT.rglob("*.md")):
        if ".git" not in markdown.parts and markdown.name != "SKILL.md" and "references" not in markdown.parts:
            validate_markdown(markdown, errors)

    scenarios = ROOT / "tests" / "behavioral-scenarios.md"
    if not scenarios.exists():
        errors.append("tests/behavioral-scenarios.md is missing")
    else:
        scenario_text = scenarios.read_text(encoding="utf-8")
        for skill_dir in skill_dirs:
            if f"## {skill_dir.name}" not in scenario_text:
                errors.append(f"behavioral scenarios missing for {skill_dir.name}")

    agent_scenarios = ROOT / "tests" / "agent-scenarios.md"
    if not agent_scenarios.exists():
        errors.append("tests/agent-scenarios.md is missing")
    else:
        agent_scenario_text = agent_scenarios.read_text(encoding="utf-8")
        for agent_name in REQUIRED_AGENTS:
            if f"## {agent_name}" not in agent_scenario_text:
                errors.append(f"agent scenarios missing for {agent_name}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    print(f"Validated {len(skill_dirs)} skills with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
