import argparse
import json
import math
import os
import sys
import time

from . import __version__, fmt, install, metrics, ponr, store, tokens

NAMES = {"five_hour": "Session 5h", "seven_day": "Semaine"}
SHORT = {"five_hour": "5h", "seven_day": "W"}
SPANS = (("5 min", 300), ("1 h", 3600), ("5 h", 5 * 3600))


_conns = []


def _open():
    c = store.connect()
    _conns.append(c)
    return c


def _state(conn, lt, now):
    rows = store.samples(conn, lt, since=now - metrics.LENGTH[lt] - 3600)
    win, resets = metrics.current_window(rows, now)
    return win, resets


def _ponr(conn, now):
    # shortcut: k ré-appris à chaque rendu (~ms sur 14 j au heartbeat 5 min), le mettre en cache dans meta si ça ralentit.
    since = now - ponr.LOOKBACK_K_S
    return ponr.evaluate(store.samples(conn, "five_hour", since), store.samples(conn, "seven_day", since),
                         now, ponr.config(store.load_config()))


PONR_ICON = {"green": "🟢", "orange": "🟠", "red": "🔴"}
PONR_LABEL = {"green": "VERT - atteignable", "orange": "ORANGE - marge qui fond", "red": "ROUGE - inatteignable",
              "unknown": "n/d"}


def _ponr_segment(p, style):
    sep = ": " if style == "long" else " "
    if p.state == "unknown":
        return "PONR%s?" % sep
    # Arrondi vers le bas en rouge : -0.3 doit s'afficher -1, jamais "-0" ambigu.
    d = math.floor(p.distance) if p.state == "red" else round(p.distance)
    seg = "PONR%s%s %+dpp" % (sep, PONR_ICON[p.state], d)
    # ETA seulement si la tendance est mesurée et la confiance du modèle n'est pas faible.
    if p.eta_s is not None and p.confidence != "faible":
        seg += " | ETA%s%s" % (sep, fmt.dur(p.eta_s))
    return seg


# ---------- statusline ----------

def _line(states, now, style, p=None):
    parts, weekly_reset = [], None
    for lt in store.LIMITS:
        win, resets = states[lt]
        if not win:
            val, reset = "–", None
        else:
            stale = now - win[-1][0] > metrics.STALE_S
            val, reset = fmt.pct(win[-1][1]) + ("~" if stale else ""), resets
            val += " (%+.0f)" % metrics.pace(win[-1][1], resets, lt, now)
        if style == "long":
            parts.append("%s: %s" % (NAMES[lt], val))
            if reset:
                parts.append("Reset: %s" % (fmt.dur(reset - now) if lt == "five_hour" else fmt.when(reset, now)))
        else:
            parts.append("%s %s" % (SHORT[lt], val))
            if lt == "seven_day":
                weekly_reset = reset
    if style != "long" and weekly_reset:
        parts.append("Reset %s" % fmt.when(weekly_reset, now))
    if p is not None:
        parts.append(_ponr_segment(p, style))
    return " | ".join(parts)


def cmd_statusline(args):
    now = int(time.time())
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    try:
        conn = _open()
    except Exception:
        conn = None
    try:
        if conn:
            store.record(conn, payload, now)
            states = {lt: _state(conn, lt, now) for lt in store.LIMITS}
            if any(s[0] for s in states.values()):
                try:
                    p = _ponr(conn, now) if ponr.config(store.load_config())["statusline"] else None
                except Exception as e:  # le PONR ne doit jamais casser la ligne existante
                    store.log_error(conn, "ponr", repr(e), now)
                    p = None
                print(_line(states, now, args.format, p))
            else:
                print("usage n/d")
        else:
            print("usage n/d")
    except Exception as e:
        try:
            store.log_error(conn, "statusline", repr(e), now)
        except Exception:
            pass
        print("usage n/d")
    return 0


# ---------- affichage à la demande ----------

def _hdr(lt, win, resets, now):
    if not win:
        return "%s : aucune fenêtre active connue (pas de relevé, ou fenêtre expirée)" % NAMES[lt]
    age = now - win[-1][0]
    return "%s : %s [officiel, relevé il y a %s] | reset %s (dans %s)" % (
        NAMES[lt], fmt.pct(win[-1][1]), fmt.dur(age), fmt.full(resets), fmt.dur(resets - now))


def _forecast_line(lt, fc, now, resets):
    if fc.status == "insufficient":
        return "  prévision : données insuffisantes (%s)" % fc.reason
    if fc.status == "idle":
        return "  prévision : consommation nulle/très faible (%s), pas d'épuisement attendu" % fmt.rate(fc.rate)
    eta = ("limite atteinte vers %s (dans ~%s)" % (fmt.when(now + fc.eta_s, now), fmt.dur(fc.eta_s))
           if fc.eta_s is not None else "limite non atteinte avant le reset")
    return "  prévision [estimation, confiance %s%s] : %s ; à %s : ~%s (plancher %s)" % (
        fc.confidence, (" – " + fc.reason) if fc.reason else "", eta, fmt.when(resets, now),
        fmt.pct(min(fc.pct_at_reset, 999)), fmt.pct(fc.pct_floor))


def _ponr_block(p, now, cfg):
    out = ["OPTIMISEUR DE QUOTA HEBDO (PONR) [estimation, modèle]"]
    row = lambda k, v: out.append("  %-28s %s" % (k, v))
    row("Objectif hebdo", fmt.pct(p.target) + (" (config.json)" if cfg != ponr.DEFAULTS else " (défaut)"))
    row("Usage hebdo actuel", "n/d" if p.weekly is None else fmt.pct(p.weekly) + " [officiel]")
    if p.state == "unknown":
        row("Statut", "n/d – %s" % p.reason)
        return out
    row("Rapport hebdo / pt 5h", "%.3f (appris de l'historique, %s)" % (p.k, p.confidence))
    row("Capacité 5h restante", "%.0f pts avant le reset hebdo (meilleur cas)" % p.capacity)
    row("Maximum atteignable", fmt.pct(p.max_reach))
    row("Distance PONR", "%+.1f pp" % p.distance)
    row("Marge brute (non plafonnée)", "%+.1f pp" % p.slack)
    row("Statut", "%s %s" % (PONR_ICON[p.state], PONR_LABEL[p.state]) + (" (%s)" % p.reason if p.reason else ""))
    if p.approach_rate is None:
        row("Vitesse d'approche", "données insuffisantes (tendance sur %s, min %s)" % (
            fmt.dur(p.trend_s), fmt.dur(ponr.MIN_TREND_S)))
    else:
        row("Vitesse d'approche", "%+.1f pp/h (%s, sur %s)" % (
            p.approach_rate, "la marge fond" if p.approach_rate >= ponr.IDLE_APPROACH else "stable ou en hausse",
            fmt.dur(p.trend_s)))
    if p.distance < 0:
        eta = "déjà franchi"
    elif p.eta_s is not None:
        eta = "vers %s (dans ~%s)" % (fmt.when(now + p.eta_s, now), fmt.dur(p.eta_s))
    else:
        eta = "non prévu avant le reset" if p.approach_rate is not None else "n/d"
    row("PONR estimé", eta)
    row("Confiance du modèle", p.confidence)
    return out


def cmd_ponr(args):
    now = int(time.time())
    conn = _open()
    cfg = ponr.config(store.load_config())
    p = _ponr(conn, now)
    print("\n".join(_ponr_block(p, now, cfg)))
    win, resets = _state(conn, "seven_day", now)
    if win:
        print("  %-28s %s (dans %s)" % ("Reset hebdo", fmt.full(resets), fmt.dur(resets - now)))
    return 0


def cmd_status(args):
    now = int(time.time())
    conn = _open()
    for lt in store.LIMITS:
        win, resets = _state(conn, lt, now)
        print(_hdr(lt, win, resets, now))
        if win:
            fc = metrics.forecast(win, resets, lt, now)
            print(_forecast_line(lt, fc, now, resets))
    return 0


def cmd_report(args):
    now = int(time.time())
    conn = _open()
    for lt in store.LIMITS:
        win, resets = _state(conn, lt, now)
        print(_hdr(lt, win, resets, now))
        if not win:
            continue
        print("  relevés dans la fenêtre : %d" % len(win))
        print("  delta (points de % du quota officiel) :")
        for label, s in SPANS:
            d = metrics.delta(win, resets, lt, s)
            if d:
                print("    %-6s %+.1f pts%s" % (label, d.pts, " (sur %s seulement)" % fmt.dur(d.span_s) if d.partial else ""))
        print("    depuis reset %+.1f pts" % win[-1][1])
        print("  vitesse :")
        print("    instantanée      %s" % fmt.rate(metrics.rate_instant(win)))
        print("    moyenne 1 h      %s" % fmt.rate(metrics.rate_over(win, resets, lt, 3600)))
        print("    moyenne 5 h      %s" % fmt.rate(metrics.rate_over(win, resets, lt, 5 * 3600)))
        print("    récente pondérée %s" % fmt.rate(metrics.rate_ewma(win)))
        print("    moy. fenêtre     %s" % fmt.rate(metrics.rate_window_avg(win, resets, lt)))
        print(_forecast_line(lt, metrics.forecast(win, resets, lt, now), now, resets))
    print()
    try:
        print("\n".join(_ponr_block(_ponr(conn, now), now, ponr.config(store.load_config()))))
    except Exception as e:  # le PONR ne doit pas casser le rapport existant
        store.log_error(conn, "ponr", repr(e), now)
        print("OPTIMISEUR DE QUOTA HEBDO (PONR) : n/d (erreur journalisée, voir doctor)")
    print("\nSource : statusline `rate_limits` (documentée, Pro/Max). Prévisions = estimations, pas des données officielles.")
    return 0


def cmd_forecast(args):
    now = int(time.time())
    conn = _open()
    for lt in store.LIMITS:
        win, resets = _state(conn, lt, now)
        print(_hdr(lt, win, resets, now))
        if win:
            fc = metrics.forecast(win, resets, lt, now)
            print(_forecast_line(lt, fc, now, resets))
            if fc.status == "ok":
                print("  base : vitesse %s = %s" % (fc.rate_kind, fmt.rate(fc.rate)))
    return 0


def cmd_history(args):
    conn = _open()
    since = time.time() - args.hours * 3600
    for lt in store.LIMITS:
        if args.type and lt != args.type:
            continue
        rows = store.samples(conn, lt, since)[-args.limit:]
        print("%s (%d relevés)" % (NAMES[lt], len(rows)))
        prev = None
        for ts, pct, resets in rows:
            d = "" if prev is None or not metrics.same_window(prev[2], resets) else "%+.1f" % (pct - prev[1])
            if prev is not None and not metrics.same_window(prev[2], resets):
                d = "reset"
            print("  %s  %6.1f%%  Δ %-6s reset %s" % (
                time.strftime("%d/%m %H:%M:%S", time.localtime(ts)), pct, d, fmt.full(resets) if resets else "?"))
            prev = (ts, pct, resets)
    return 0


def cmd_tokens(args):
    now = int(time.time())
    conn = _open()
    print("Tokens locaux lus dans les transcripts Claude Code (≠ quota d'abonnement).")
    for lt, label in (("five_hour", "Session 5h"), ("seven_day", "Semaine")):
        win, resets = _state(conn, lt, now)
        since = metrics.window_start(resets, lt) if win else now - metrics.LENGTH[lt]
        t = tokens.scan(since)
        print("%s (depuis %s%s) : %d msgs | in %s | out %s | cache écrit %s | cache lu %s" % (
            label, fmt.full(since), "" if win else ", fenêtre glissante",
            t["messages"], _k(t["input"]), _k(t["output"]), _k(t["cache_write"]), _k(t["cache_read"])))
    return 0


def _k(n):
    return "%.1fM" % (n / 1e6) if n >= 1e6 else "%.1fk" % (n / 1e3) if n >= 1e3 else str(n)


def cmd_doctor(args):
    ok = True
    print("claude-usage %s | python %s" % (__version__, sys.version.split()[0]))
    path = store.db_path()
    print("base : %s (%s)" % (path, "existe" if os.path.exists(path) else "absente"))
    try:
        conn = _open()
        for t in ("limit_samples", "session_samples", "errors"):
            print("  %-15s %d lignes" % (t, conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]))
        last = conn.execute("SELECT MAX(ts) FROM limit_samples").fetchone()[0]
        print("dernier relevé quota : %s" % ("jamais (rate_limits absent : abonnement Pro/Max ? 1re réponse API faite ?)"
                                            if not last else "il y a %s" % fmt.dur(time.time() - last)))
        for ts, src, msg in conn.execute("SELECT ts,source,message FROM errors ORDER BY id DESC LIMIT 5"):
            print("  erreur %s [%s] %s" % (time.strftime("%d/%m %H:%M", time.localtime(ts)), src, msg))
    except Exception as e:
        ok = False
        print("base KO : %r" % e)
    raw = store.load_config()
    cfg = ponr.config(raw)
    print("config PONR : %s" % cfg)
    bad = sorted(k for k in raw if k not in cfg or raw[k] != cfg[k])
    if bad:
        print("  clés config.json ignorées (inconnues ou invalides) : %s" % ", ".join(bad))
    try:
        with open(install.settings_path(), encoding="utf-8") as f:
            sl = json.load(f).get("statusLine")
        print("statusLine : %s" % (sl if sl else "non configurée (voir `claude-usage install`)"))
    except Exception as e:
        print("settings.json illisible : %r" % e)
    return 0 if ok else 1


def _shim():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "claude-usage"))


def cmd_install(args):
    status, cur, new = install.plan_install(_shim(), args.force)
    print("settings : %s" % install.settings_path())
    if status == "already":
        print("déjà installé.")
        return 0
    if status == "conflict":
        print("statusLine existante différente : %s\nRelancer avec --force pour la remplacer (sauvegarde créée)." % cur)
        return 1
    print("statusLine actuelle : %s\nstatusLine nouvelle : %s" % (cur, new))
    if not args.yes:
        print("Dry-run. Ajouter --yes pour appliquer (sauvegarde automatique).")
        return 0
    _, backup = install.apply_install(_shim(), args.force)
    print("installé. sauvegarde : %s\nRedémarrer Claude Code (ou ouvrir une nouvelle session)." % backup)
    return 0


def cmd_uninstall(args):
    if not args.yes:
        print("Dry-run : retirerait la statusLine claude-usage de %s. Ajouter --yes." % install.settings_path())
        return 0
    status, backup = install.apply_uninstall()
    print("statusLine retirée. sauvegarde : %s" % backup if status == "ok" else "rien à retirer.")
    if args.purge:
        import shutil
        shutil.rmtree(store.home(), ignore_errors=True)
        print("historique supprimé : %s" % store.home())
    return 0


def cmd_prune(args):
    conn = _open()
    print("%d lignes supprimées (> %d jours)" % (store.prune(conn, days=args.days), args.days))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="claude-usage", description="Suivi local du quota Claude Pro (source : statusline officielle).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("statusline", help="commande statusLine de Claude Code (JSON sur stdin)")
    s.add_argument("--format", choices=("short", "long"), default="short")
    s.set_defaults(fn=cmd_statusline)
    sub.add_parser("status", help="état compact").set_defaults(fn=cmd_status)
    sub.add_parser("report", help="détails : deltas, vitesses, prévisions").set_defaults(fn=cmd_report)
    sub.add_parser("forecast", help="prévisions").set_defaults(fn=cmd_forecast)
    sub.add_parser("ponr", help="objectif hebdo encore atteignable ? (point of no return)").set_defaults(fn=cmd_ponr)
    h = sub.add_parser("history", help="relevés stockés")
    h.add_argument("--hours", type=float, default=24)
    h.add_argument("--limit", type=int, default=40)
    h.add_argument("--type", choices=store.LIMITS)
    h.set_defaults(fn=cmd_history)
    sub.add_parser("tokens", help="tokens locaux (transcripts), distincts du quota").set_defaults(fn=cmd_tokens)
    sub.add_parser("doctor", help="diagnostic").set_defaults(fn=cmd_doctor)
    i = sub.add_parser("install", help="ajoute la statusLine dans settings.json (dry-run par défaut)")
    i.add_argument("--yes", action="store_true")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_install)
    u = sub.add_parser("uninstall", help="retire la statusLine claude-usage")
    u.add_argument("--yes", action="store_true")
    u.add_argument("--purge", action="store_true", help="supprime aussi l'historique")
    u.set_defaults(fn=cmd_uninstall)
    pr = sub.add_parser("prune", help="purge l'historique ancien")
    pr.add_argument("--days", type=int, default=store.RETENTION_DAYS)
    pr.set_defaults(fn=cmd_prune)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except BrokenPipeError:
        return 0
    except Exception as e:
        if args.cmd == "statusline":
            print("usage n/d")
            return 0
        print("erreur : %r" % e, file=sys.stderr)
        return 1
    finally:
        while _conns:
            _conns.pop().close()
