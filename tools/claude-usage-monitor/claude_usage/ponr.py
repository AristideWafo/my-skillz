"""Point of No Return (PONR) : l'objectif hebdomadaire est-il encore atteignable ? Calculs purs, aucune E/S.

Modèle (estimation, jamais une donnée officielle) :
- k = points hebdo consommés par point de quota 5h, appris de l'historique (ΣΔ7j / ΣΔ5h sur des intervalles
  dans une même fenêtre 5h). Anthropic ne publie pas ce rapport ; il dépend du modèle utilisé et peut changer.
- capacité 5h restante avant le reset hebdo = reste de la fenêtre 5h courante + 100 pts par tranche de 5h
  ensuite, la dernière tranche au prorata (meilleur cas : chaque fenêtre démarre dès la fin de la précédente).
- max_reachable = min(100, W + k × capacité) ; distance = max_reachable − objectif (≤ 100 − objectif).
- marge brute (slack) = W + k × capacité − objectif, non plafonnée : sert à la tendance et à l'ETA.
Le temps qui passe sans consommer détruit de la capacité ; consommer la déplace vers W sans perte.
"""
from bisect import bisect_right
from collections import namedtuple

from .metrics import LENGTH, STALE_S, same_window

LOOKBACK_K_S = 14 * 86400  # rapport récent : Anthropic peut changer les limites
MIN_K_PTS = 15.0  # Δ5h cumulé minimal pour estimer k
TREND_STEP_S = 900
MIN_TREND_S = 2 * 3600
MIN_TREND_POINTS = 4
IDLE_APPROACH = 0.1  # pp/h en dessous : distance stable

DEFAULTS = {"weekly_target": 95.0, "orange_margin_pp": 2.0, "orange_eta_h": 12.0, "trend_hours": 12.0,
            "statusline": True}
MAX_RATE5 = 100.0 / LENGTH["five_hour"]  # pts 5h/s : rythme max supposé (fenêtre remplie en 5h)
LIMITS = {"weekly_target": (1.0, 100.0), "orange_margin_pp": (0.0, 100.0),
          "orange_eta_h": (0.0, 168.0), "trend_hours": (2.0, 168.0)}

Ratio = namedtuple("Ratio", "k d5 confidence")
Ponr = namedtuple(
    "Ponr",
    "state target weekly max_reach distance slack k capacity approach_rate eta_s trend_s confidence reason",
)


def config(raw):
    """Valide la config utilisateur (dict issu de config.json) ; valeur invalide => défaut."""
    cfg = dict(DEFAULTS)
    if isinstance(raw, dict):
        for key, (lo, hi) in LIMITS.items():
            v = raw.get(key)
            if not isinstance(v, bool) and isinstance(v, (int, float)) and lo <= v <= hi:
                cfg[key] = float(v)
        if isinstance(raw.get("statusline"), bool):
            cfg["statusline"] = raw["statusline"]
    return cfg


def _at(rows, t):
    """Dernier relevé (ts, pct, resets) <= t, ou None. rows triés par ts."""
    i = bisect_right(rows, (t, float("inf"), float("inf")))
    return rows[i - 1] if i else None


def _clean(rows):
    return sorted((r for r in rows if r[2] is not None), key=lambda r: r[0])


def exchange_ratio(rows5, rows7, now):
    """k = ΣΔ7j / ΣΔ5h sur les intervalles consécutifs de relevés 5h d'une même fenêtre 5h et 7j."""
    rows5, rows7 = _clean(rows5), _clean(rows7)
    d5 = d7 = 0.0
    for a, b in zip(rows5, rows5[1:]):
        if a[0] < now - LOOKBACK_K_S or not same_window(a[2], b[2]):
            continue
        wa, wb = _at(rows7, a[0]), _at(rows7, b[0])
        if wa is None or wb is None or not same_window(wa[2], wb[2]):
            continue
        x5, x7 = b[1] - a[1], wb[1] - wa[1]
        if x5 < 0 or x7 < 0:  # baisse incohérente : intervalle ignoré
            continue
        d5 += x5
        d7 += x7
    if d5 < MIN_K_PTS:
        return Ratio(None, d5, None)
    conf = "faible" if d5 < 40 else "moyenne" if d5 < 150 else "bonne"
    return Ratio(d7 / d5, d5, conf)


def capacity_5h(p5, r5, now, r7):
    """Points de quota 5h encore consommables avant r7 (meilleur cas, fenêtres enchaînées)."""
    if r7 <= now:
        return 0.0
    cur, start = 0.0, now
    if p5 is not None and r5 is not None and r5 > now:
        cur, start = max(100.0 - p5, 0.0), r5
        if r5 > r7:  # reset hebdo avant la fin de la fenêtre 5h : même rythme max que les tranches suivantes
            cur = min(cur, (r7 - now) * MAX_RATE5)
            start = r7
    return cur + max(r7 - start, 0) * MAX_RATE5


def max_reachable(weekly, k, capacity):
    return min(100.0, weekly + k * capacity)


def _distance_at(rows5, rows7, t, k, target, r7_now):
    w = _at(rows7, t)
    if w is None or not same_window(w[2], r7_now):
        return None
    s = _at(rows5, t)
    p5, r5 = (s[1], s[2]) if s else (None, None)
    # Non plafonnée : sinon la tendance reste plate tant que le max atteignable est bloqué à 100 %.
    return w[1] + k * capacity_5h(p5, r5, t, w[2]) - target


def _slope(points):
    n = len(points)
    mt = sum(t for t, _ in points) / n
    md = sum(d for _, d in points) / n
    var = sum((t - mt) ** 2 for t, _ in points)
    return 0.0 if var == 0 else sum((t - mt) * (d - md) for t, d in points) / var


def trend(rows5, rows7, k, target, r7, now, hours):
    """Distance échantillonnée toutes les 15 min (état en escalier, robuste aux trous) puis régression.

    Retourne (approach_rate pp/h — > 0 : la marge fond, span_s) ou (None, span_s).
    """
    first = max(rows7[0][0], now - int(hours * 3600), r7 - LENGTH["seven_day"])
    pts, t = [], now
    while t >= first:
        d = _distance_at(rows5, rows7, t, k, target, r7)
        if d is not None:
            pts.append((t, d))
        t -= TREND_STEP_S
    span = now - pts[-1][0] if pts else 0
    if len(pts) < MIN_TREND_POINTS or span < MIN_TREND_S:
        return None, span
    return -_slope(pts) * 3600.0, span


def evaluate(rows5, rows7, now, cfg=None):
    cfg = cfg or DEFAULTS
    target = cfg["weekly_target"]
    rows5, rows7 = _clean(rows5), _clean(rows7)
    w = rows7[-1] if rows7 else None
    if w is None or w[2] <= now:
        return Ponr("unknown", target, None, None, None, None, None, None, None, None, 0, None,
                    "aucune fenêtre hebdo active connue")
    weekly, r7 = w[1], w[2]
    ratio = exchange_ratio(rows5, rows7, now)
    if ratio.k is None:
        return Ponr("unknown", target, weekly, None, None, None, None, None, None, None, 0, None,
                    "rapport 5h/hebdo pas encore mesurable (%.0f/%.0f pts 5h observés)" % (ratio.d5, MIN_K_PTS))
    s = rows5[-1] if rows5 else None
    p5, r5 = (s[1], s[2]) if s else (None, None)
    cap = capacity_5h(p5, r5, now, r7)
    reach = max_reachable(weekly, ratio.k, cap)
    dist = reach - target
    slack = weekly + ratio.k * cap - target  # marge brute non plafonnée, base de l'ETA
    rate, span = trend(rows5, rows7, ratio.k, target, r7, now, cfg["trend_hours"])
    eta = None
    if rate is not None and slack > 0 and rate >= IDLE_APPROACH and weekly < target:
        eta = slack / rate * 3600.0
        if eta >= r7 - now:
            eta = None  # pas franchi avant le reset au rythme actuel
    conf, why = ratio.confidence, ""
    if s is None or now - max(s[0], w[0]) > STALE_S:
        conf, why = "faible", "dernier relevé ancien"
    if weekly >= target:
        state = "green"
        why = why or "objectif déjà atteint"
    elif dist < 0:
        state = "red"
    elif dist < cfg["orange_margin_pp"] or (eta is not None and eta < cfg["orange_eta_h"] * 3600):
        state = "orange"
    else:
        state = "green"
    return Ponr(state, target, weekly, reach, dist, slack, ratio.k, cap, rate, eta, span, conf, why)
