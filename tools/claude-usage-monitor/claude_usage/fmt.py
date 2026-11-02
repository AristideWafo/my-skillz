import time
from datetime import datetime

DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def dur(sec):
    if sec is None:
        return "?"
    sec = max(int(sec), 0)
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    if d:
        return "%dj%02dh" % (d, h)
    if h:
        return "%dh%02d" % (h, m)
    return "%dmin" % m


def when(ts, now=None):
    """'14:30' si aujourd'hui, sinon 'sam. 11:00'."""
    now = now if now is not None else time.time()
    t, n = datetime.fromtimestamp(ts), datetime.fromtimestamp(now)
    hm = t.strftime("%H:%M")
    return hm if t.date() == n.date() else "%s %s" % (DAYS[t.weekday()], hm)


def full(ts):
    t = datetime.fromtimestamp(ts)
    return "%s %s" % (DAYS[t.weekday()], t.strftime("%d/%m %H:%M"))


def pct(v):
    return "%d%%" % round(v) if v >= 1 or v == 0 else "%.1f%%" % v


def rate(v):
    return "n/d" if v is None else "%+.1f pts/h" % v
