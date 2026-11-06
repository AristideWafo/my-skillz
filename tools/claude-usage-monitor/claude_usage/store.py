import json
import os
import sqlite3
import time

LIMITS = ("five_hour", "seven_day")
HEARTBEAT_S = 300
RETENTION_DAYS = 90
MAX_ERRORS = 500

SCHEMA = """
CREATE TABLE IF NOT EXISTS limit_samples(
  id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, source TEXT NOT NULL,
  limit_type TEXT NOT NULL, pct REAL NOT NULL, resets_at INTEGER, session_id TEXT);
CREATE INDEX IF NOT EXISTS ix_limit ON limit_samples(limit_type, ts);
CREATE TABLE IF NOT EXISTS session_samples(
  id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, session_id TEXT NOT NULL,
  cost_usd REAL, ctx_in INTEGER, ctx_out INTEGER);
CREATE INDEX IF NOT EXISTS ix_sess ON session_samples(session_id, ts);
CREATE TABLE IF NOT EXISTS errors(
  id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""


def home():
    return os.environ.get("CLAUDE_USAGE_HOME") or os.path.expanduser("~/.claude-usage")


def load_config():
    """config.json utilisateur (dict brut, validé par l'appelant) ; {} si absent ou illisible."""
    try:
        with open(os.path.join(home(), "config.json"), encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:  # config optionnelle : jamais bloquante (JSON invalide, imbrication extrême…)
        return {}


def db_path():
    return os.path.join(home(), "usage.db")


def connect(path=None):
    path = path or db_path()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    conn = sqlite3.connect(path, timeout=2)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _num(v):
    # bool est un int en Python : on l'exclut explicitement.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def log_error(conn, source, message, now=None):
    now = int(now if now is not None else time.time())
    conn.execute("INSERT INTO errors(ts,source,message) VALUES(?,?,?)", (now, source, str(message)[:300]))
    conn.execute(
        "DELETE FROM errors WHERE id <= (SELECT id FROM errors ORDER BY id DESC LIMIT 1 OFFSET ?)",
        (MAX_ERRORS,),
    )
    conn.commit()


def record(conn, payload, now=None, source="statusline"):
    """Persiste un relevé issu du JSON statusline. Retourne le nombre de lignes écrites.

    Ne stocke ni prompt ni chemin : uniquement pourcentages, resets, coût, tokens de contexte.
    """
    now = int(now if now is not None else time.time())
    written = 0
    sid = payload.get("session_id") if isinstance(payload.get("session_id"), str) else None
    rl = payload.get("rate_limits")
    rl = rl if isinstance(rl, dict) else {}
    for lt in LIMITS:
        w = rl.get(lt)
        if w is None:
            continue
        pct = _num(w.get("used_percentage")) if isinstance(w, dict) else None
        if pct is None or pct < 0:
            log_error(conn, source, "valeur %s invalide: %r" % (lt, w), now)
            continue
        resets = _num(w.get("resets_at"))
        resets = int(resets) if resets is not None else None
        last = conn.execute(
            "SELECT ts,pct,resets_at FROM limit_samples WHERE limit_type=? ORDER BY ts DESC,id DESC LIMIT 1",
            (lt,),
        ).fetchone()
        if last is None or last[1] != pct or last[2] != resets or now - last[0] >= HEARTBEAT_S:
            conn.execute(
                "INSERT INTO limit_samples(ts,source,limit_type,pct,resets_at,session_id) VALUES(?,?,?,?,?,?)",
                (now, source, lt, pct, resets, sid),
            )
            written += 1
    cost = payload.get("cost") if isinstance(payload.get("cost"), dict) else {}
    cw = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    usd = _num(cost.get("total_cost_usd"))
    if sid and usd is not None:
        last = conn.execute(
            "SELECT cost_usd FROM session_samples WHERE session_id=? ORDER BY id DESC LIMIT 1", (sid,)
        ).fetchone()
        if last is None or last[0] != usd:
            cin, cout = _num(cw.get("total_input_tokens")), _num(cw.get("total_output_tokens"))
            conn.execute(
                "INSERT INTO session_samples(ts,session_id,cost_usd,ctx_in,ctx_out) VALUES(?,?,?,?,?)",
                (now, sid, usd, None if cin is None else int(cin), None if cout is None else int(cout)),
            )
            written += 1
    conn.commit()
    prune_if_due(conn, now)
    return written


def prune(conn, now=None, days=RETENTION_DAYS):
    cutoff = int(now if now is not None else time.time()) - days * 86400
    n = 0
    for t in ("limit_samples", "session_samples", "errors"):
        n += conn.execute("DELETE FROM %s WHERE ts < ?" % t, (cutoff,)).rowcount
    conn.commit()
    return n


def prune_if_due(conn, now):
    row = conn.execute("SELECT v FROM meta WHERE k='last_prune'").fetchone()
    if row is None or now - int(row[0]) > 86400:
        prune(conn, now)
        conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('last_prune',?)", (str(now),))
        conn.commit()


def samples(conn, limit_type, since=None):
    q = "SELECT ts,pct,resets_at FROM limit_samples WHERE limit_type=?"
    args = [limit_type]
    if since is not None:
        q += " AND ts>=?"
        args.append(int(since))
    return conn.execute(q + " ORDER BY ts,id", args).fetchall()
