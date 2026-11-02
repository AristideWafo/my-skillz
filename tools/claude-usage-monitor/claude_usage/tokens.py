"""Tokens locaux (B) lus dans les transcripts de Claude Code, en lecture seule.

Ce n'est PAS le quota d'abonnement : l'app Claude et le web n'y apparaissent pas, et le
quota n'est pas proportionnel aux tokens bruts (cache, modèle, charge).
"""
import glob
import json
import os
from datetime import datetime


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def _ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def scan(since_ts, root=None):
    """Somme des tokens par catégorie depuis since_ts. Dédoublonne par id de message."""
    root = root or os.path.join(config_dir(), "projects")
    best = {}
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        try:
            if os.path.getmtime(path) < since_ts:
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"usage"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    m = o.get("message") if isinstance(o, dict) else None
                    u = m.get("usage") if isinstance(m, dict) else None
                    t = _ts(o.get("timestamp"))
                    if not isinstance(u, dict) or t is None or t < since_ts:
                        continue
                    key = m.get("id") or o.get("uuid")
                    out = u.get("output_tokens") or 0
                    # Les messages en streaming apparaissent plusieurs fois : on garde le plus complet.
                    if key not in best or out >= best[key][1].get("output_tokens", 0):
                        best[key] = (t, u)
        except OSError:
            continue
    tot = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "messages": len(best)}
    for _, u in best.values():
        tot["input"] += u.get("input_tokens") or 0
        tot["output"] += u.get("output_tokens") or 0
        tot["cache_write"] += u.get("cache_creation_input_tokens") or 0
        tot["cache_read"] += u.get("cache_read_input_tokens") or 0
    return tot
