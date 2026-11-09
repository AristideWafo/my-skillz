#!/usr/bin/env python3
"""Install this checkout's skills and agents locally; preview unless --apply.

Never installs hooks, changes global permissions, or overwrites unmanaged files.
Document skill is namespaced to coexist with the commonly synced original.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]
DOC_ALIAS = "my-skillz-doc-coauthoring"
# Codex reasoning effort applied from each role's default router profile.
# LONG_CONTEXT says nothing about reasoning depth, so it keeps the inherited effort.
PROFILE_EFFORT = {"FAST": "low", "BALANCED": "medium", "HIGH_REASONING": "high", "SECURITY_CRITICAL": "high"}


def codex_effort(profiles: dict, role: str) -> str | None:
    mapping = profiles.get("agents", {}).get(role)
    return PROFILE_EFFORT.get(mapping["default"]) if mapping else None


def with_effort(text: str, effort: str | None) -> str:
    """Insert a top-level model_reasoning_effort unless the agent already pins one."""
    if effort is None or re.search(r"^model_reasoning_effort\s*=", text, re.M):
        return text
    anchor = text.find("\ndeveloper_instructions")
    if anchor < 0:
        raise ValueError("Missing developer_instructions in Codex agent")
    return text[:anchor] + f'\nmodel_reasoning_effort = "{effort}"' + text[anchor:]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def contained(home: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(home.resolve()):
        raise ValueError(f"Destination escapes selected home: {path}")
    return resolved


def build_plan(source: Path, home: Path, targets: list[str]) -> dict[Path, bytes]:
    plan = {}
    profile_source = source / "model_router" / "agent_profiles.json"
    profile_target = contained(home, home / ".my-skillz" / "model_router" / "agent_profiles.json")
    router_source = source / "model_router"
    if router_source.is_dir():
        for item in sorted(router_source.iterdir()):
            if item.is_file() and item.suffix in (".py", ".json"):
                plan[contained(home, home / ".my-skillz" / "model_router" / item.name)] = item.read_bytes()
        guide = source / "docs" / "model-router-v01.md"
        if guide.is_file():
            plan[contained(home, home / ".my-skillz" / "model-router-v01.md")] = guide.read_bytes()
    profiles = json.loads(profile_source.read_text(encoding="utf-8")) if profile_source.is_file() else {}
    skills = sorted((source / "skills").glob("*/SKILL.md"))
    if not skills:
        raise ValueError("No skills found")
    manager = source / "manager" / "AGENTS.md"
    for target in targets:
        # Global manager rules let the primary Codex agent delegate on its own.
        # Claude Code delegates from agent descriptions instead, so ~/.claude/CLAUDE.md is left alone.
        if target == "codex" and manager.is_file():
            plan[contained(home, home / ".codex" / "AGENTS.md")] = manager.read_bytes()
        skill_root =home / (".agents" if target == "codex" else ".claude") / "skills"
        for entry in skills:
            name = entry.parent.name
            installed_name = DOC_ALIAS if name == "doc-coauthoring" else name
            for item in sorted(entry.parent.rglob("*")):
                if not item.is_file() or "__pycache__" in item.parts:
                    continue
                relative = item.relative_to(entry.parent)
                data = item.read_bytes()
                if name == "doc-coauthoring" and relative.as_posix() in ("SKILL.md", "agents/openai.yaml"):
                    data = data.decode("utf-8").replace("doc-coauthoring", DOC_ALIAS).encode("utf-8")
                destination = contained(home, skill_root / installed_name / relative)
                plan[destination] = data
        extension = "toml" if target == "codex" else "md"
        agents = sorted((source / f".{target}" / "agents").glob(f"*.{extension}"))
        if not agents:
            raise ValueError(f"No agents found for {target}")
        for agent in agents:
            text = agent.read_text(encoding="utf-8").replace("doc-coauthoring", DOC_ALIAS)
            if profile_source.is_file():
                text = text.replace("model_router/agent_profiles.json", profile_target.as_posix())
            # Exact local entrypoints disambiguate synced skills without loading them all.
            index = "\n\nInstalled my-skillz entrypoints (read only those relevant to this task):\n"
            for entry in skills:
                name = DOC_ALIAS if entry.parent.name == "doc-coauthoring" else entry.parent.name
                index += f"- {name}: {(skill_root / name / 'SKILL.md').as_posix()}\n"
            if router_source.is_dir():
                index += f"- Model Router V0.1 package (only when asked to select a model): {(home / '.my-skillz' / 'model_router').as_posix()}; guide: {(home / '.my-skillz' / 'model-router-v01.md').as_posix()}\n"
            if extension == "toml":
                text = with_effort(text, codex_effort(profiles, agent.stem))
                close = text.rfind('"""')
                if close < 0:
                    raise ValueError(f"Missing agent instruction block: {agent}")
                # TOML multiline basic strings require escaping Windows/special paths.
                escaped = index.replace("\\", "\\\\").replace('"', '\\"')
                text = text[:close] + escaped + text[close:]
            else:
                text += index
            plan[contained(home, home / f".{target}" / "agents" / agent.name)] = text.encode("utf-8")
    return plan


def install(source: Path, home: Path, targets: list[str], apply: bool = False) -> dict:
    home = home.resolve()
    state = contained(home, home / ".my-skillz")
    manifest_path = contained(home, state / "manifest.json")
    prior = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    plan = build_plan(source, home, targets)
    changes = []
    for path, data in plan.items():
        key = path.relative_to(home).as_posix()
        if path.exists():
            if not path.is_file():
                raise ValueError(f"Destination is not a file: {path}")
            current = path.read_bytes()
            if prior["files"].get(key) != digest(current):
                raise ValueError(f"Unmanaged or locally modified file; preserved: {path}")
            if current == data:
                continue
        changes.append(path)
    result = {"mode": "apply" if apply else "preview", "targets": targets,
              "files": len(plan), "changed": len(changes), "home": str(home),
              "document_skill": DOC_ALIAS}
    if not apply:
        return result
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = contained(home, state / "backups" / stamp)
    # Back up before the first overwrite. Backups are outside skill discovery roots.
    for path in changes:
        if path.exists():
            saved = contained(home, backup / path.relative_to(home))
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
    if manifest_path.exists() and changes:
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, backup / "manifest.json")
    managed = dict(prior["files"])
    managed.update({p.relative_to(home).as_posix(): digest(data) for p, data in plan.items()})
    state.mkdir(parents=True, exist_ok=True)
    manifest_data = (json.dumps({"source": str(source.resolve()), "files": managed}, indent=2) + "\n").encode("utf-8")
    previous = {p: p.read_bytes() if p.exists() else None for p in changes + [manifest_path]}
    written = []
    try:
        for path in changes:
            path.parent.mkdir(parents=True, exist_ok=True)
            written.append(path)
            atomic_write(path, plan[path])
        for path, data in plan.items():
            if path.read_bytes() != data:
                raise RuntimeError(f"Installed file verification failed: {path}")
        written.append(manifest_path)
        atomic_write(manifest_path, manifest_data)
    except BaseException:
        for path in reversed(written):
            contained(home, path)
            if previous[path] is None:
                if path.exists():
                    path.unlink()
            else:
                atomic_write(path, previous[path])
        raise
    result["manifest"] = str(manifest_path)
    result["backup"] = str(backup) if backup.exists() else None
    result["verified"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--target", choices=["codex", "claude", "both"], default="both")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    targets = ["codex", "claude"] if args.target == "both" else [args.target]
    print(json.dumps(install(ROOT, args.home, targets, args.apply), indent=2))


if __name__ == "__main__":
    main()
