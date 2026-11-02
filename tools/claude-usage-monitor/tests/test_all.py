import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from claude_usage import cli, install, metrics, store, tokens  # noqa: E402

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

    def test_commands_with_empty_db(self):
        for cmd in ("status", "report", "forecast", "history", "tokens", "doctor"):
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


if __name__ == "__main__":
    unittest.main()
