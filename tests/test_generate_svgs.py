import json
import sys
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_svgs as g  # noqa: E402

CONFIG = {
    "owner": "LokarajR",
    "thesis": "Measured on unseen data.",
    "featured": [
        {"repo": "Vision-Repo", "label": "Vision Project", "pillar": "Vision"},
        {"repo": "Rag-Repo", "label": "RAG Project", "pillar": "Retrieval"},
        {"repo": "Missing-Repo", "label": "Gone", "pillar": "Reliability"},
    ],
}
REPOS = [
    {"name": "Vision-Repo", "fork": False, "pushed_at": "2026-10-23T05:00:00Z", "default_branch": "main"},
    {"name": "Rag-Repo", "fork": False, "pushed_at": "2026-09-09T10:00:00Z", "default_branch": "master"},
    {"name": "Some-Fork", "fork": True, "pushed_at": "2026-12-01T00:00:00Z"},
    {"name": "LokarajR", "fork": False, "pushed_at": "2026-12-02T00:00:00Z"},
    {"name": "Old", "fork": False, "archived": True, "pushed_at": "2026-12-03T00:00:00Z"},
]
RUNS = {"Vision-Repo": None, "Rag-Repo": {"conclusion": "success"}, "Missing-Repo": None}


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # raises if the SVG is not well-formed XML


def texts(svg: str) -> list[str]:
    return ["".join(el.itertext()) for el in parse(svg).iter("{http://www.w3.org/2000/svg}text")]


class Summarize(unittest.TestCase):
    def test_latest_activity_ignores_forks_archived_and_profile_repo(self):
        data = g.summarize(REPOS, RUNS, CONFIG)
        self.assertEqual(data["latest_activity"], "2026-10-23")

    def test_project_fields(self):
        vision, rag, missing = g.summarize(REPOS, RUNS, CONFIG)["projects"]
        self.assertEqual((vision["updated"], vision["ci"], vision["available"]), ("Oct 2026", None, True))
        self.assertEqual((rag["updated"], rag["ci"]), ("Sep 2026", "passing"))
        self.assertEqual((missing["available"], missing["updated"]), (False, None))

    def test_failed_run_is_reported_as_failing(self):
        runs = dict(RUNS, **{"Rag-Repo": {"conclusion": "failure"}})
        self.assertEqual(g.summarize(REPOS, runs, CONFIG)["projects"][1]["ci"], "failing")

    def test_no_repos_at_all(self):
        data = g.summarize([], {}, CONFIG)
        self.assertIsNone(data["latest_activity"])
        self.assertFalse(any(p["available"] for p in data["projects"]))


class Helpers(unittest.TestCase):
    def test_month_year(self):
        self.assertEqual(g.month_year("2026-01-05T00:00:00Z"), "Jan 2026")
        for bad in (None, "", "2026", "2026-13-01", "abcd-ef"):
            self.assertIsNone(g.month_year(bad))

    def test_pages_deploys_do_not_count_as_ci(self):
        self.assertFalse(g.is_repo_workflow({"path": "dynamic/pages/pages-build-deployment"}))
        self.assertFalse(g.is_repo_workflow({}))
        self.assertTrue(g.is_repo_workflow({"path": ".github/workflows/ci.yml"}))

    def test_truncate(self):
        self.assertEqual(g.truncate("short", 10), "short")
        self.assertEqual(g.truncate("a" * 20, 10), "a" * 9 + "…")
        self.assertEqual(g.truncate("  spaced \n out ", 20), "spaced out")


class Render(unittest.TestCase):
    def setUp(self):
        self.data = g.summarize(REPOS, RUNS, CONFIG)

    def test_both_themes_are_valid_svg(self):
        for theme in g.THEMES:
            parse(g.render_card(self.data, theme))
            parse(g.render_header(theme))

    def test_deterministic(self):
        self.assertEqual(g.render_card(self.data, "dark"), g.render_card(self.data, "dark"))
        self.assertEqual(g.render_header("light"), g.render_header("light"))

    def test_special_characters_are_escaped(self):
        data = dict(self.data, thesis='<script>&"quotes"\'</script>', owner="a&b")
        svg = g.render_card(data, "dark")
        parse(svg)
        self.assertNotIn("<script>", svg)
        self.assertIn('<script>&"quotes"\'</script>', texts(svg))

    def test_missing_data_renders_placeholders(self):
        svg = g.render_card({"owner": "x", "thesis": "", "latest_activity": None, "projects": []}, "dark")
        t = texts(svg)
        self.assertIn("No project data available.", t)
        self.assertIn("latest public activity: unavailable", t)

    def test_unavailable_and_ci_states(self):
        t = texts(g.render_card(self.data, "light"))
        self.assertIn("✓ passing", t)
        self.assertIn("unavailable", t)

    def test_card_shows_no_numbers_beyond_dates(self):
        # Only dates belong on the card; no invented metrics.
        for line in texts(g.render_card(self.data, "dark")):
            stripped = line.replace("2026", "").replace("10-23", "")
            self.assertFalse(any(ch.isdigit() for ch in stripped), line)


class Main(unittest.TestCase):
    def test_api_failure_writes_nothing(self):
        def broken_fetch(*_):
            raise urllib.error.URLError("offline")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "c.json"
            cfg.write_text(json.dumps(CONFIG))
            out = Path(tmp) / "assets"
            out.mkdir()
            (out / "system-card-dark.svg").write_text("previous")
            code = g.main(["--config", str(cfg), "--out-dir", str(out)], fetch=broken_fetch)
            self.assertEqual(code, 1)
            self.assertEqual((out / "system-card-dark.svg").read_text(), "previous")
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["system-card-dark.svg"])

    def test_successful_run_writes_both_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "c.json"
            cfg.write_text(json.dumps(CONFIG))
            out = Path(tmp) / "assets"
            code = g.main(["--config", str(cfg), "--out-dir", str(out), "--header"],
                          fetch=lambda *_: (REPOS, RUNS))
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["header-dark.svg", "header-light.svg",
                              "system-card-dark.svg", "system-card-light.svg"])


if __name__ == "__main__":
    unittest.main()
