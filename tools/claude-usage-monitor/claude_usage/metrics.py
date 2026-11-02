"""Calculs purs sur des relevés (ts, pct, resets_at). Aucune E/S.

Unités : pct = points de pourcentage du quota officiel ; temps en secondes ; vitesses en pts/h.
"""
from collections import namedtuple

LENGTH = {"five_hour": 5 * 3600, "seven_day": 7 * 86400}
SAME_WINDOW_TOL = 120  # resets_at peut varier de quelques secondes d'un relevé à l'autre
IDLE_RATE = 0.05  # pts/h en dessous : consommation considérée nulle
MIN_SPAN_S = 600
STALE_S = 900

Delta = namedtuple("Delta", "pts span_s partial")
Forecast = namedtuple(
    "Forecast",
    "status rate rate_kind eta_s pct_at_reset pct_floor confidence reason",
)


def same_window(a, b):
    return a is not None and b is not None and abs(a - b) <= SAME_WINDOW_TOL


def current_window(rows, now):
    """Relevés de la fenêtre courante, monotones. (rows, resets_at) ou ([], None) si expirée/inconnue."""
    rows = sorted((r for r in rows if r[2] is not None), key=lambda r: r[0])
    if not rows:
        return [], None
    resets = rows[-1][2]
    if resets <= now:
        return [], None
    win, peak = [], 0.0
    for ts, pct, r in rows:
        if not same_window(r, resets):
            continue
        # Un pourcentage qui baisse dans la même fenêtre est incohérent : on l'ignore.
        if pct + 1e-9 < peak:
            continue
        peak = pct
        win.append((ts, pct, resets))
    return win, resets


def window_start(resets_at, limit_type):
    return resets_at - LENGTH[limit_type]


def pace(pct, resets_at, limit_type, now):
    """Écart en points entre le quota consommé et la part de fenêtre écoulée.

    > 0 : en avance sur une consommation linéaire (on brûle trop vite) ; < 0 : de la marge.
    """
    length = LENGTH[limit_type]
    elapsed = min(max(now - window_start(resets_at, limit_type), 0), length) / length * 100
    return pct - elapsed


def _pct_at(win, t, start):
    """Valeur au temps t, palier (dernier relevé <= t) ; 0 au début de fenêtre. None si inconnu."""
    prev = None
    for ts, pct, _ in win:
        if ts <= t:
            prev = pct
        else:
            break
    if prev is not None:
        return prev
    return 0.0 if t <= start else None


def delta(win, resets_at, limit_type, span_s):
    """Variation en points de % sur span_s se terminant au dernier relevé."""
    if not win:
        return None
    start = window_start(resets_at, limit_type)
    end_ts, end_pct, _ = win[-1]
    t0 = end_ts - span_s
    base = _pct_at(win, max(t0, start), start)
    if base is not None:
        return Delta(round(end_pct - base, 6), end_ts - max(t0, start), t0 < start)
    # Fenêtre déjà entamée avant le 1er relevé : base inconnue, on part du 1er relevé.
    first_ts, first_pct, _ = win[0]
    if first_ts >= end_ts:
        return None
    return Delta(round(end_pct - first_pct, 6), end_ts - first_ts, True)


def delta_since_reset(win, resets_at, limit_type):
    return win[-1][1] if win else None


def rate_over(win, resets_at, limit_type, span_s):
    d = delta(win, resets_at, limit_type, span_s)
    if d is None or d.span_s < 300:
        return None
    return d.pts / (d.span_s / 3600.0)


def rate_instant(win, min_gap_s=60):
    """Entre le dernier relevé et le plus récent relevé distinct d'au moins min_gap_s."""
    if len(win) < 2:
        return None
    end_ts, end_pct, _ = win[-1]
    for ts, pct, _ in reversed(win[:-1]):
        if end_ts - ts >= min_gap_s:
            return (end_pct - pct) / ((end_ts - ts) / 3600.0)
    return None


def rate_ewma(win, half_life_s=1800):
    """Moyenne pondérée par l'âge (demi-vie 30 min) des vitesses par intervalle."""
    if len(win) < 2:
        return None
    end_ts = win[-1][0]
    num = den = total = 0.0
    for (t1, p1, _), (t2, p2, _) in zip(win, win[1:]):
        dt = t2 - t1
        if dt <= 0:
            continue
        w = 0.5 ** ((end_ts - (t1 + t2) / 2.0) / half_life_s)
        num += w * (p2 - p1)
        den += w * dt
        total += dt
    if total < 300 or den == 0:
        return None
    return num / (den / 3600.0)


def rate_window_avg(win, resets_at, limit_type):
    """Moyenne depuis le début de la fenêtre (base officielle 0 % à l'ouverture)."""
    if not win:
        return None
    el = win[-1][0] - window_start(resets_at, limit_type)
    if el < 300:
        return None
    return win[-1][1] / (el / 3600.0)


def time_to_exhaustion(pct, rate):
    if pct >= 100:
        return 0.0
    if rate is None or rate < IDLE_RATE:
        return None
    return (100.0 - pct) / rate * 3600.0


def project_at_reset(pct, rate, now, resets_at):
    return pct + max(rate, 0.0) * max(resets_at - now, 0) / 3600.0


def _variability(win):
    """Coefficient de variation des vitesses par intervalle (pondéré par la durée)."""
    xs = []
    for (t1, p1, _), (t2, p2, _) in zip(win, win[1:]):
        dt = t2 - t1
        if dt >= 60:
            xs.append((dt, (p2 - p1) / (dt / 3600.0)))
    if len(xs) < 3:
        return None
    tot = sum(w for w, _ in xs)
    mean = sum(w * r for w, r in xs) / tot
    if mean < IDLE_RATE:
        return None
    var = sum(w * (r - mean) ** 2 for w, r in xs) / tot
    return (var ** 0.5) / mean


def forecast(win, resets_at, limit_type, now):
    if not win or resets_at is None:
        return Forecast("insufficient", None, None, None, None, None, None, "aucun relevé dans la fenêtre")
    pct = win[-1][1]
    span = win[-1][0] - win[0][0]
    distinct = len({p for _, p, _ in win})
    if limit_type == "seven_day":
        rate, kind = rate_window_avg(win, resets_at, limit_type), "moyenne fenêtre"
    else:
        rate, kind = rate_ewma(win), "moyenne pondérée récente"
        if rate is None:
            rate, kind = rate_over(win, resets_at, limit_type, 3600), "moyenne 1h"
    short = len(win) < 2 or (limit_type == "five_hour" and (len(win) < 3 or span < MIN_SPAN_S))
    if rate is None or short:
        return Forecast("insufficient", rate, kind, None, None, pct, None, "relevés trop peu nombreux ou trop rapprochés")
    if rate < IDLE_RATE:
        return Forecast("idle", rate, kind, None, pct, pct, "bonne", "consommation nulle ou très faible")
    eta = time_to_exhaustion(pct, rate)
    end = project_at_reset(pct, rate, now, resets_at)
    cv = _variability(win)
    conf, why = "bonne", ""
    if cv is None:
        conf, why = "moyenne", "variabilité non mesurable"
    elif cv > 1.0:
        conf, why = "faible", "rythme très variable"
    elif cv > 0.5:
        conf, why = "moyenne", "rythme assez variable"
    if limit_type == "five_hour" and (span < 1800 or distinct < 3):
        conf = "faible" if conf == "faible" else "moyenne"
        why = why or "historique court"
    if limit_type == "seven_day" and span < 86400:
        conf, why = "faible", "moins de 24h d'historique"
    if now - win[-1][0] > STALE_S:
        conf, why = "faible", "dernier relevé ancien"
    if eta is not None and eta > resets_at - now:
        eta = None  # limite non atteinte avant le reset au rythme actuel
    return Forecast("ok", rate, kind, eta, end, pct, conf, why)
