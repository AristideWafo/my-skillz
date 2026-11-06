import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from claude_usage import cli, install, metrics, ponr, store, tokens  # noqa: E402

H = 3600
NOW = 1_800_000_000
R5 = NOW + 2 * H  # reset session dans 2h => fenêtre ouverte depuis 3h
R7 = NOW + 3 * 86400


def win5(points, resets=R5):
    """points: [(secondes avant NOW, pct)]"""
    return [(NOW - a, p, resets) for a, p in sorted(points, reverse=True)]


class Metrics(unittest.TestCase):
    def test_delta_intervals(self):
        w = win5([(3 * H, 0), (2 * H, 10), (H, 25), (300, 40), (0, 45)])
        self.assertAlmostEqual(metrics.delta(w, R5, "five_hour", 300).pts, 5)
        self.assertAlmostEqual(metrics.delta(w, R5, "five_hour", H).pts, 20)
        self.assertAlmostEqual(metrics.delta(w, R5, "five_hour", 5 * H).pts, 45)  # base 0 à l'ouverture
        self.assertEqual(metrics.delta_since_reset(w, R5, "five_hour"), 45)

    def test_delta_unknown_base_is_partial(self):
        w = [(NOW - H, 50, R7), (NOW, 53, R7)]
        d = metrics.delta(w, R7, "seven_day", 5 * H)
        self.assertEqual((d.pts, d.span_s, d.partial), (3, H, True))

    def test_rates(self):
        w = win5([(2 * H, 10), (H, 20), (0, 30)])
        self.assertAlmostEqual(metrics.rate_over(w, R5, "five_hour", H), 10)
        self.assertAlmostEqual(metrics.rate_instant(w), 10)
        self.assertAlmostEqual(metrics.rate_ewma(w), 10)
        self.assertAlmostEqual(metrics.rate_window_avg(w, R5, "five_hour"), 10)  # 30% en 3h

    def test_ewma_favors_recent(self):
        w = win5([(3 * H, 0), (2 * H, 1), (H, 2), (0, 32)])
        self.assertGreater(metrics.rate_ewma(w), metrics.rate_window_avg(w, R5, "five_hour"))

    def test_time_to_exhaustion(self):
        self.assertAlmostEqual(metrics.time_to_exhaustion(50, 10), 5 * H)
        self.assertIsNone(metrics.time_to_exhaustion(50, 0.0))  # pas de division par zéro
        self.assertIsNone(metrics.time_to_exhaustion(50, None))
        self.assertEqual(metrics.time_to_exhaustion(100, 0), 0)

    def test_projection_at_reset(self):
        self.assertAlmostEqual(metrics.project_at_reset(40, 10, NOW, NOW + 2 * H), 60)
        self.assertEqual(metrics.project_at_reset(40, -5, NOW, NOW + H), 40)

    def test_forecast_limit_before_reset(self):
        w = win5([(2 * H, 10), (H, 40), (0, 70)])  # 30 pts/h, reste 30 pts => 1h < 2h
        fc = metrics.forecast(w, R5, "five_hour", NOW)
        self.assertEqual(fc.status, "ok")
        self.assertAlmostEqual(fc.eta_s, H)
        self.assertGreater(fc.pct_at_reset, 100)
        self.assertEqual(fc.pct_floor, 70)

    def test_forecast_limit_not_reached(self):
        w = win5([(2 * H, 10), (H, 12), (0, 14)])
        fc = metrics.forecast(w, R5, "five_hour", NOW)
        self.assertIsNone(fc.eta_s)
        self.assertAlmostEqual(fc.pct_at_reset, 18)

    def test_forecast_insufficient(self):
        self.assertEqual(metrics.forecast([], None, "five_hour", NOW).status, "insufficient")
        self.assertEqual(metrics.forecast(win5([(0, 5)]), R5, "five_hour", NOW).status, "insufficient")
        self.assertEqual(metrics.forecast(win5([(60, 5), (0, 6)]), R5, "five_hour", NOW).status, "insufficient")

    def test_forecast_idle(self):
        fc = metrics.forecast(win5([(2 * H, 20), (H, 20), (0, 20)]), R5, "five_hour", NOW)
        self.assertEqual(fc.status, "idle")
        self.assertIsNone(fc.eta_s)

    def test_forecast_erratic_is_low_confidence(self):
        w = win5([(3 * H, 0), (150 * 60, 1), (120 * 60, 30), (90 * 60, 31), (60 * 60, 60), (30 * 60, 61), (0, 62)])
        self.assertEqual(metrics.forecast(w, R5, "five_hour", NOW).confidence, "faible")

    def test_forecast_stale_last_sample(self):
        w = win5([(3 * H - 1, 5), (2 * H, 15), (H, 25)])
        self.assertEqual(metrics.forecast(w, R5, "five_hour", NOW).confidence, "faible")

    def test_window_change_ignores_old_window(self):
        old = [(NOW - 6 * H, 90, NOW - 2 * H), (NOW - 3 * H, 95, NOW - 2 * H)]
        new = [(NOW - H, 3, R5), (NOW, 8, R5)]
        win, resets = metrics.current_window(old + new, NOW)
        self.assertEqual((resets, [p for _, p, _ in win]), (R5, [3, 8]))

    def test_reset_jitter_same_window(self):
        win, _ = metrics.current_window([(NOW - H, 10, R5), (NOW, 20, R5 + 5)], NOW)
        self.assertEqual(len(win), 2)

    def test_expired_window_yields_nothing(self):
        self.assertEqual(metrics.current_window([(NOW - H, 90, NOW - 10)], NOW), ([], None))

    def test_inconsistent_decrease_dropped(self):
        win, _ = metrics.current_window([(NOW - 2 * H, 30, R5), (NOW - H, 10, R5), (NOW, 35, R5)], NOW)
        self.assertEqual([p for _, p, _ in win], [30, 35])

    def test_missing_data(self):
        self.assertIsNone(metrics.delta([], R5, "five_hour", H))
        self.assertIsNone(metrics.rate_instant([]))
        self.assertIsNone(metrics.rate_ewma([(NOW, 1, R5)]))
        self.assertEqual(metrics.current_window([], NOW), ([], None))
        self.assertEqual(metrics.current_window([(NOW, 5, None)], NOW), ([], None))


def payload(p5=None, p7=None, sid="s1", cost=0.1):
    rl = {}
    if p5 is not None:
        rl["five_hour"] = {"used_percentage": p5, "resets_at": R5}
    if p7 is not None:
        rl["seven_day"] = {"used_percentage": p7, "resets_at": R7}
    d = {"session_id": sid, "cost": {"total_cost_usd": cost},
         "context_window": {"total_input_tokens": 10, "total_output_tokens": 2}}
    if rl:
        d["rate_limits"] = rl
    return d


class Pace(unittest.TestCase):
    def test_pace(self):
        now, resets = 1000000, 1000000 + 2.5 * 3600  # 5h : moitié écoulée
        self.assertAlmostEqual(metrics.pace(60, resets, "five_hour", now), 10)
        self.assertAlmostEqual(metrics.pace(30, resets, "five_hour", now), -20)


class Storage(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "u.db")

    def tearDown(self):
        self.dir.cleanup()

    def test_persistence_between_sessions(self):
        c = store.connect(self.path)
        store.record(c, payload(10, 20), NOW - 600)
        store.record(c, payload(15, 21), NOW)
        c.close()
        c2 = store.connect(self.path)
        self.assertEqual([r[1] for r in store.samples(c2, "five_hour")], [10, 15])
        self.assertEqual([r[1] for r in store.samples(c2, "seven_day")], [20, 21])

    def test_dedup_and_heartbeat(self):
        c = store.connect(self.path)
        self.assertEqual(store.record(c, payload(10, 20), NOW), 3)
        self.assertEqual(store.record(c, payload(10, 20), NOW + 10), 0)
        self.assertEqual(store.record(c, payload(10, 20), NOW + store.HEARTBEAT_S), 2)

    def test_no_rate_limits_no_crash(self):
        c = store.connect(self.path)
        self.assertEqual(store.record(c, {"session_id": "x"}, NOW), 0)
        self.assertEqual(store.record(c, {}, NOW), 0)
        self.assertEqual(store.samples(c, "five_hour"), [])

    def test_collect_errors_logged_not_raised(self):
        c = store.connect(self.path)
        bad = {"rate_limits": {"five_hour": {"used_percentage": "abc"}, "seven_day": {"used_percentage": -3}}}
        self.assertEqual(store.record(c, bad, NOW), 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM errors").fetchone()[0], 2)

    def test_prune_retention(self):
        c = store.connect(self.path)
        store.record(c, payload(10, 20), NOW - 100 * 86400)
        store.prune(c, NOW)
        self.assertEqual(store.samples(c, "five_hour"), [])

    def test_no_prompt_content_stored(self):
        c = store.connect(self.path)
        p = payload(10, 20)
        p["transcript_path"] = "/secret/path"
        p["prompt"] = "mot de passe: hunter2"
        store.record(c, p, NOW)
        dump = "\n".join(c.iterdump())
        self.assertNotIn("hunter2", dump)
        self.assertNotIn("/secret/path", dump)


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        os.environ["CLAUDE_USAGE_HOME"] = self.dir.name
        os.environ["CLAUDE_CONFIG_DIR"] = self.dir.name

    def tearDown(self):
        os.environ.pop("CLAUDE_USAGE_HOME")
        os.environ.pop("CLAUDE_CONFIG_DIR")
        self.dir.cleanup()

    @staticmethod
    def load(path):
        with open(path) as f:
            return json.load(f)

    def run_cli(self, argv, stdin=""):
        old = sys.stdin
        sys.stdin = io.StringIO(stdin)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                rc = cli.main(argv)
        finally:
            sys.stdin = old
        return rc, out.getvalue()

    def test_statusline_without_quota_info(self):
        self.assertEqual(self.run_cli(["statusline"], "{}"), (0, "usage n/d\n"))

    def test_statusline_garbage_stdin(self):
        self.assertEqual(self.run_cli(["statusline"], "pas du json"), (0, "usage n/d\n"))

    def test_statusline_never_fails_when_db_broken(self):
        os.environ["CLAUDE_USAGE_HOME"] = "/dev/null/impossible"
        self.assertEqual(self.run_cli(["statusline"], "{}"), (0, "usage n/d\n"))

    def test_statusline_formats_and_stale_fallback(self):
        now = int(time.time())
        p = {"session_id": "s", "rate_limits": {
            "five_hour": {"used_percentage": 72, "resets_at": now + 6000},
            "seven_day": {"used_percentage": 68, "resets_at": now + 200000}}}
        _, short = self.run_cli(["statusline"], json.dumps(p))
        self.assertTrue(short.startswith("5h 72% (+5) | W 68% (+1) | Reset "), short)
        _, long = self.run_cli(["statusline", "--format", "long"], json.dumps(p))
        self.assertIn("Session 5h: 72% (+5) | Reset: 1h40 | Semaine: 68% (+1)", long)
        _, again = self.run_cli(["statusline"], "{}")  # nouvelle session sans rate_limits
        self.assertTrue(again.startswith("5h 72% (+5) | W 68% (+1)"), again)
        self.assertTrue(short.rstrip().endswith("PONR ?"), short)  # rapport 5h/hebdo pas encore appris
        self.assertIn("PONR: ?", long)

    def test_statusline_ponr_segment_with_history(self):
        now = int(time.time())
        conn = store.connect()
        r7 = now + 20 * H
        for ts, p5, w in ((now - 2 * H, 0, 40), (now - H, 25, 42.5), (now - 60, 50, 45)):
            for lt, pct, r in (("five_hour", p5, now + 3 * H), ("seven_day", w, r7)):
                conn.execute("INSERT INTO limit_samples(ts,source,limit_type,pct,resets_at) VALUES(?,?,?,?,?)",
                             (ts, "t", lt, pct, r))
        conn.commit()
        conn.close()
        _, out = self.run_cli(["statusline"], "{}")
        # k = 0.1 ; capacité 50 + 17h*20 = 390 ; max 45 + 39 = 84 % < 95 % => rouge
        self.assertIn("| PONR 🔴 -11pp", out)
        _, rep = self.run_cli(["ponr"])
        self.assertIn("ROUGE", rep)
        self.assertIn("déjà franchi", rep)
        with open(os.path.join(self.dir.name, "config.json"), "w") as f:
            json.dump({"statusline": False, "weekly_target": 150}, f)
        _, out = self.run_cli(["statusline"], "{}")
        self.assertNotIn("PONR", out)  # désactivable
        _, doc = self.run_cli(["doctor"])
        self.assertIn("ignorées (inconnues ou invalides) : weekly_target", doc)

    def test_report_survives_ponr_failure(self):
        old = ponr.evaluate
        ponr.evaluate = lambda *a, **k: 1 / 0
        try:
            rc, out = self.run_cli(["report"])
        finally:
            ponr.evaluate = old
        self.assertEqual(rc, 0)
        self.assertIn("PONR) : n/d", out)

    def test_ponr_segment_never_shows_minus_zero(self):
        p = ponr.Ponr("red", 95, 50, 94.7, -0.3, -0.3, 0.1, 10, 1, None, 0, "bonne", "")
        self.assertEqual(cli._ponr_segment(p, "short"), "PONR 🔴 -1pp")
        p = p._replace(state="orange", distance=3.4, eta_s=3 * H + 1200)
        self.assertEqual(cli._ponr_segment(p, "short"), "PONR 🟠 +3pp | ETA 3h20")
        self.assertEqual(cli._ponr_segment(p._replace(confidence="faible"), "short"), "PONR 🟠 +3pp")

    def test_commands_with_empty_db(self):
        for cmd in ("status", "report", "forecast", "ponr", "history", "tokens", "doctor"):
            self.assertEqual(self.run_cli([cmd])[0], 0, cmd)

    def test_install_backup_and_uninstall(self):
        sp = install.settings_path()
        with open(sp, "w") as f:
            json.dump({"model": "x"}, f)
        self.run_cli(["install"])  # dry-run
        self.assertNotIn("statusLine", self.load(sp))
        self.run_cli(["install", "--yes"])
        data = self.load(sp)
        self.assertIn("claude-usage", data["statusLine"]["command"])
        self.assertEqual(data["model"], "x")
        self.assertTrue([f for f in os.listdir(self.dir.name) if ".bak-claude-usage-" in f])
        self.run_cli(["uninstall", "--yes"])
        self.assertNotIn("statusLine", self.load(sp))

    def test_install_refuses_foreign_statusline(self):
        sp = install.settings_path()
        with open(sp, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "mon-script"}}, f)
        self.assertEqual(self.run_cli(["install", "--yes"])[0], 1)
        self.assertEqual(self.load(sp)["statusLine"]["command"], "mon-script")
        self.run_cli(["uninstall", "--yes"])
        self.assertIn("statusLine", self.load(sp))


class Tokens(unittest.TestCase):
    def test_scan_dedupes_streaming_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "proj"))

            def line(out):
                return json.dumps({"timestamp": "2026-10-29T10:00:00Z", "message": {"id": "m1", "usage": {
                    "input_tokens": 2, "output_tokens": out,
                    "cache_creation_input_tokens": 5, "cache_read_input_tokens": 7}}})
            with open(os.path.join(d, "proj", "a.jsonl"), "w") as f:
                f.write(line(10) + "\n" + line(50) + '\nnot json "usage"\n')
            t = tokens.scan(0, root=d)
            self.assertEqual((t["messages"], t["output"], t["cache_read"]), (1, 50, 7))


K = 0.1  # pts hebdo par pt 5h dans les scénarios


def learned(now, r7, w_end=45.0):
    """Fenêtre 5h passée (0->50 entre -15h et -13h, expirée à -10h) puis inactivité : k = 0.1."""
    r5 = now - 10 * H
    rows5 = [(now - 15 * H, 0, r5), (now - 14 * H, 25, r5), (now - 13 * H, 50, r5)]
    rows7 = [(now - 15 * H, w_end - 5, r7), (now - 14 * H, w_end - 2.5, r7), (now - 13 * H, w_end, r7),
             (now, w_end, r7)]  # session ouverte maintenant : relevé hebdo frais
    return rows5, rows7


def usage(now, r7, hours, rate5, w0=30.0, step=900):
    """Usage continu à rate5 pts 5h/h ; nouvelle fenêtre 5h dès la fin de la précédente."""
    rows5, rows7 = [], []
    t = start = now - int(hours * H)
    p5, w = 0.0, w0
    while t <= now:
        if t >= start + 5 * H:
            start, p5 = t, 0.0
        rows5.append((t, p5, start + 5 * H))
        rows7.append((t, w, r7))
        dp = min(rate5 * step / H, 100 - p5)
        p5, w, t = p5 + dp, w + K * dp, t + step
    return rows5, rows7


class Ponr(unittest.TestCase):
    def test_capacity_rolling_windows(self):
        self.assertAlmostEqual(ponr.capacity_5h(40, NOW + 2 * H, NOW, NOW + 12 * H), 60 + 200)
        self.assertAlmostEqual(ponr.capacity_5h(40, NOW - H, NOW, NOW + 10 * H), 200)  # fenêtre expirée
        self.assertAlmostEqual(ponr.capacity_5h(None, None, NOW, NOW + 5 * H), 100)  # reset 5h inconnu
        self.assertAlmostEqual(ponr.capacity_5h(0, NOW + 4 * H, NOW, NOW + 2 * H), 40)  # reset hebdo avant le 5h : 20 pts/h max
        self.assertAlmostEqual(ponr.capacity_5h(90, NOW + 4 * H, NOW, NOW + 2 * H), 10)
        self.assertEqual(ponr.capacity_5h(0, NOW + H, NOW, NOW - 1), 0)
        self.assertAlmostEqual(ponr.capacity_5h(120, NOW + H, NOW, NOW + H), 0)  # 5h saturé

    def test_max_reachable_capped(self):
        self.assertEqual(ponr.max_reachable(90, 0.1, 1000), 100)
        rows5, rows7 = learned(NOW, NOW + 100 * H)
        p = ponr.evaluate(rows5, rows7, NOW)
        self.assertEqual(p.max_reach, 100)
        self.assertAlmostEqual(p.distance, 5)
        self.assertAlmostEqual(p.slack, 45 + 200 - 95)

    def test_exchange_ratio(self):
        rows5, rows7 = learned(NOW, NOW + 30 * H)
        r = ponr.exchange_ratio(rows5, rows7, NOW)
        self.assertAlmostEqual(r.k, K)
        self.assertEqual(r.confidence, "moyenne")
        self.assertIsNone(ponr.exchange_ratio(rows5[:1], rows7, NOW).k)

    def test_ratio_uses_stepwise_weekly_and_skips_5h_resets(self):
        # Hebdo écrit seulement quand il change (dédoublonnage) ; intervalle à cheval sur un reset 5h ignoré.
        r7 = NOW + 30 * H
        rows5 = [(NOW - 4 * H, 0, NOW - 2 * H), (NOW - 3 * H, 30, NOW - 2 * H),
                 (NOW - H, 0, NOW + 4 * H), (NOW - 1800, 20, NOW + 4 * H)]
        rows7 = [(NOW - 4 * H, 10, r7), (NOW - 3 * H, 13, r7), (NOW - 1800, 15, r7)]
        r = ponr.exchange_ratio(rows5, rows7, NOW)
        self.assertAlmostEqual(r.k, (3 + 2) / 50.0)

    def test_external_session_jump_counted_in_both_limits(self):
        # Usage hors Claude Code : saut simultané des deux % entre deux relevés.
        r5, r7 = NOW + 3 * H, NOW + 30 * H
        rows5 = [(NOW - H, 10, r5), (NOW - 1800, 60, r5), (NOW, 62, r5)]
        rows7 = [(NOW - H, 40, r7), (NOW - 1800, 45, r7), (NOW, 45.2, r7)]
        self.assertAlmostEqual(ponr.exchange_ratio(rows5, rows7, NOW).k, K)

    def test_ratio_ignores_inconsistent_decrease(self):
        r5, r7 = NOW + 3 * H, NOW + 30 * H
        rows5 = [(NOW - 3 * H, 0, r5), (NOW - 2 * H, 30, r5), (NOW - H, 20, r5)]
        rows7 = [(NOW - 3 * H, 10, r7), (NOW - 2 * H, 13, r7), (NOW - H, 13, r7)]
        self.assertAlmostEqual(ponr.exchange_ratio(rows5, rows7, NOW).k, K)

    def test_comfortably_achievable(self):
        p = ponr.evaluate(*learned(NOW, NOW + 60 * H), now=NOW)
        self.assertEqual(p.state, "green")
        self.assertGreater(p.eta_s, 12 * H)

    def test_approaching_by_eta(self):
        p = ponr.evaluate(*learned(NOW, NOW + 30 * H), now=NOW)
        self.assertEqual(p.state, "orange")  # distance plafonnée 5 pp mais la marge brute fond à ~2 pp/h
        self.assertAlmostEqual(p.slack, 10)
        self.assertTrue(1.5 < p.approach_rate < 2.5, p.approach_rate)
        self.assertTrue(4 * H < p.eta_s < 7 * H, p.eta_s)

    def test_at_point_of_no_return(self):
        p = ponr.evaluate(*learned(NOW, NOW + 25 * H), now=NOW)
        self.assertAlmostEqual(p.distance, 0)
        self.assertEqual(p.state, "orange")

    def test_unreachable(self):
        p = ponr.evaluate(*learned(NOW, NOW + 20 * H), now=NOW)
        self.assertAlmostEqual(p.max_reach, 85)
        self.assertAlmostEqual(p.distance, -10)
        self.assertEqual(p.state, "red")
        self.assertIsNone(p.eta_s)

    def test_red_needs_unreachable_not_high_usage(self):
        rows5, rows7 = usage(NOW, NOW + 50 * H, 4, 25)  # 5h saturé, mais beaucoup de temps
        p = ponr.evaluate(rows5, rows7, NOW)
        self.assertGreaterEqual(rows5[-1][1], 99)
        self.assertNotEqual(p.state, "red")

    def test_target_already_reached(self):
        rows5, rows7 = learned(NOW, NOW + 10 * H, w_end=96)
        p = ponr.evaluate(rows5, rows7, NOW)
        self.assertEqual(p.state, "green")
        self.assertIn("atteint", p.reason)
        self.assertIsNone(p.eta_s)  # pas de point de non-retour pour un objectif déjà atteint

    def test_configurable_target(self):
        rows5, rows7 = learned(NOW, NOW + 20 * H)
        self.assertEqual(ponr.evaluate(rows5, rows7, NOW).state, "red")
        p = ponr.evaluate(rows5, rows7, NOW, ponr.config({"weekly_target": 80}))
        self.assertEqual((p.state, round(p.distance)), ("orange", 5))  # atteignable mais marge qui fond
        self.assertEqual(ponr.evaluate(rows5, rows7, NOW, ponr.config({"weekly_target": 50})).state, "green")

    def test_config_validation(self):
        cfg = ponr.config({"weekly_target": 150, "orange_margin_pp": "x", "orange_eta_h": True, "trend_hours": 6})
        self.assertEqual(cfg["weekly_target"], 95)
        self.assertEqual(cfg["orange_margin_pp"], 2)
        self.assertEqual(cfg["orange_eta_h"], 12)
        self.assertEqual(cfg["trend_hours"], 6)
        self.assertTrue(cfg["statusline"])
        self.assertFalse(ponr.config({"statusline": False})["statusline"])
        self.assertEqual(ponr.config(None), ponr.DEFAULTS)

    def test_approach_rate_follows_consumption(self):
        r7 = NOW + 40 * H
        full = ponr.evaluate(*usage(NOW, r7, 6, 20), now=NOW).approach_rate
        half = ponr.evaluate(*usage(NOW, r7, 6, 10), now=NOW).approach_rate
        idle = ponr.evaluate(*learned(NOW, r7), now=NOW).approach_rate
        self.assertLess(abs(full), 0.3)  # chaque fenêtre 5h remplie : aucune capacité perdue
        self.assertLess(full, half)
        self.assertLess(half, idle)

    def test_insufficient_history_no_eta(self):
        p = ponr.evaluate(*usage(NOW, NOW + 30 * H, 1, 20), now=NOW)
        self.assertIsNotNone(p.k)
        self.assertIsNone(p.approach_rate)
        self.assertIsNone(p.eta_s)

    def test_ratio_not_measurable(self):
        r7 = NOW + 30 * H
        p = ponr.evaluate([(NOW - 600, 3, NOW + H), (NOW, 5, NOW + H)], [(NOW - 600, 40, r7), (NOW, 40.2, r7)], NOW)
        self.assertEqual((p.state, p.weekly), ("unknown", 40.2))

    def test_missing_or_invalid_resets(self):
        rows5, _ = learned(NOW, NOW + 30 * H)
        self.assertEqual(ponr.evaluate(rows5, [(NOW, 40, None)], NOW).state, "unknown")
        self.assertEqual(ponr.evaluate(rows5, [(NOW - H, 40, NOW - 1)], NOW).state, "unknown")  # hebdo expiré
        self.assertEqual(ponr.evaluate([], [], NOW).state, "unknown")
        _, rows7 = learned(NOW, NOW + 30 * H)
        rows5 = [(t, p, None) for t, p, _ in rows5]  # resets 5h absents
        self.assertEqual(ponr.evaluate(rows5, rows7, NOW).state, "unknown")  # k non mesurable sans resets 5h

    def test_weekly_reset_boundary(self):
        old5, old7 = learned(NOW, NOW - 5 * H, w_end=90)  # semaine précédente, close il y a 5h
        r7 = NOW - 5 * H + 7 * 86400
        new5, new7 = usage(NOW, r7, 3, 10, w0=0)
        p = ponr.evaluate(old5 + new5, old7 + new7, NOW)
        self.assertLess(p.weekly, 5)
        self.assertLessEqual(p.trend_s, 3 * H)  # aucune distance calculée sur l'ancienne semaine
        self.assertEqual(p.state, "green")

    def test_large_gap_between_observations(self):
        r7 = NOW + 30 * H
        rows5, rows7 = learned(NOW - 8 * H, r7)
        rows7 = rows7[:-1]  # dernier relevé il y a 21h
        p = ponr.evaluate(rows5, rows7, NOW)
        self.assertAlmostEqual(p.capacity, 600)  # fenêtre 5h expirée pendant le trou : capacité depuis maintenant
        self.assertEqual(p.confidence, "faible")


if __name__ == "__main__":
    unittest.main()
