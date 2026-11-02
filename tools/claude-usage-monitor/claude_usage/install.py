import json
import os
import shutil
import time

from .tokens import config_dir

MARK = "claude-usage"


def settings_path():
    return os.path.join(config_dir(), "settings.json")


def shim_command(shim):
    return "%s statusline" % shim


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, data):
    tmp = path + ".tmp-claude-usage"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def plan_install(shim, force=False):
    data = _load(settings_path())
    cur = data.get("statusLine")
    new = {"type": "command", "command": shim_command(shim)}
    if cur == new:
        return "already", cur, new
    if cur and MARK not in str(cur.get("command", "")) and not force:
        return "conflict", cur, new
    return "ok", cur, new


def apply_install(shim, force=False):
    status, cur, new = plan_install(shim, force)
    if status != "ok":
        return status, None
    path = settings_path()
    backup = None
    if os.path.exists(path):
        backup = "%s.bak-claude-usage-%d" % (path, time.time())
        shutil.copy2(path, backup)
    data = _load(path)
    data["statusLine"] = new
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write(path, data)
    return "ok", backup


def apply_uninstall():
    path = settings_path()
    data = _load(path)
    cur = data.get("statusLine")
    if not cur or MARK not in str(cur.get("command", "")):
        return "absent", None
    backup = "%s.bak-claude-usage-%d" % (path, time.time())
    shutil.copy2(path, backup)
    del data["statusLine"]
    _write(path, data)
    return "ok", backup
