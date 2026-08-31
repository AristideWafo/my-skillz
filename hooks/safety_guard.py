#!/usr/bin/env python3
"""Block a small set of catastrophic local shell commands before execution."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional


def read_payload() -> dict:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def command_from(payload: dict) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for key in ("command", "cmd"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def repository_root(cwd: Path) -> Optional[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def dangerous_rm(command: str, cwd: Path) -> bool:
    broad_literals = {
        "/",
        "/*",
        ".",
        "./*",
        "..",
        "../*",
        "~",
        "~/",
        "~/*",
        "$HOME",
        "$HOME/",
        "$HOME/*",
        "${HOME}",
        "${HOME}/",
        "${HOME}/*",
        "*",
    }
    protected_paths = {cwd}
    home = Path.home().resolve()
    protected_paths.add(home)
    repo = repository_root(cwd)
    if repo is not None:
        protected_paths.add(repo)

    try:
        tokens = shlex.split(command, posix=os.name != "nt")
    except ValueError:
        tokens = command.split()

    for index, token in enumerate(tokens):
        if Path(token).name != "rm":
            continue
        flags: list[str] = []
        targets: list[str] = []
        for item in tokens[index + 1 :]:
            if item == "--":
                continue
            if item.startswith("-") and not targets:
                flags.append(item)
            else:
                targets.append(item)
        recursive_force = any("r" in flag.lower() for flag in flags) and any(
            "f" in flag.lower() for flag in flags
        )
        if not recursive_force:
            continue
        for target in targets:
            if target in broad_literals:
                return True
            expanded = Path(os.path.expandvars(os.path.expanduser(target)))
            try:
                resolved = (cwd / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()
            except OSError:
                continue
            if resolved in protected_paths:
                return True
    return False


def reason_for(command: str, cwd: Path) -> Optional[str]:
    normalized = " ".join(command.lower().split())
    if dangerous_rm(command, cwd):
        return "Blocked recursive forced deletion of a home, repository, working, or filesystem root."
    if re.search(r"\bgit\b[^;&|\n]*\breset\b[^;&|\n]*--hard\b", normalized):
        return "Blocked git reset --hard because it can discard uncommitted work."
    git_clean = re.search(r"\bgit\b[^;&|\n]*\bclean\b([^;&|\n]*)", normalized)
    if git_clean:
        clean_args = git_clean.group(1).split()
        forced = any(arg == "--force" or (arg.startswith("-") and "f" in arg) for arg in clean_args)
        directories = any(
            arg == "--directories" or (arg.startswith("-") and "d" in arg) for arg in clean_args
        )
        if forced and directories:
            return "Blocked forced git clean because it can permanently remove untracked work."
    if re.search(r"\bdocker\s+system\s+prune\b", normalized) and (
        "--volumes" in normalized
        or "--all" in normalized
        or re.search(r"(?:^|\s)-[^\s]*a", normalized)
    ):
        return "Blocked broad Docker system pruning because it can remove images, caches, and volumes."
    if re.search(r"\b(?:mkfs(?:\.[a-z0-9]+)?|diskutil\s+erasedisk)\b", normalized):
        return "Blocked a filesystem formatting command."
    if re.search(r"\bdd\b[^\n]*\bof=/dev/(?:disk|sd|nvme|vd)", normalized):
        return "Blocked raw writes to a block device."
    return None


def main() -> int:
    payload = read_payload()
    command = command_from(payload)
    if not command:
        return 0
    raw_cwd = payload.get("cwd")
    cwd = Path(raw_cwd).resolve() if isinstance(raw_cwd, str) else Path.cwd().resolve()
    reason = reason_for(command, cwd)
    if reason is None:
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
            + " Use a narrower recoverable operation, or have the user deliberately change the hook policy.",
        }
    }
    json.dump(output, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
