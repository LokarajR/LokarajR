import datetime as dt
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import leetcode_heatmap as h  # noqa: E402

TODAY = dt.date(2026, 10, 25)  # a Sunday
SVG = "{http://www.w3.org/2000/svg}"


class Heatmap(unittest.TestCase):
    def test_parse_calendar_uses_utc_days(self):
        raw = json.dumps({"1760572800": 3, "1760659200": 1})  # 2025-10-16, 2025-10-17 UTC
        self.assertEqual(h.parse_calendar(raw), {"2025-10-16": 3, "2025-10-17": 1})
        self.assertEqual(h.parse_calendar(""), {})

    def test_levels(self):
        self.assertEqual([h.level(n, 16) for n in (0, 1, 4, 5, 12, 16)], [0, 1, 1, 2, 3, 4])
        self.assertEqual(h.level(3, 0), 0)

    def test_render_counts_only_the_last_year(self):
        counts = {"2026-10-24": 5, "2026-01-02": 2, "2024-01-01": 99}
        svg = h.render(counts, TODAY, "someone")
        root = ET.fromstring(svg)
        self.assertIn("7 LeetCode submissions", "".join(root.itertext()))
        days = [r for r in root.iter(f"{SVG}rect") if r.find(f"{SVG}title") is not None]
        self.assertEqual(len(days), 365)  # 52 full weeks plus today's Sunday
        self.assertEqual(days[-1].find(f"{SVG}title").text, "0 on 2026-10-25")
        self.assertEqual(days[-2].find(f"{SVG}title").text, "5 on 2026-10-24")

    def test_empty_calendar_renders(self):
        ET.fromstring(h.render({}, TODAY, "someone"))

    def test_deterministic_and_escaped(self):
        a = h.render({"2026-10-01": 1}, TODAY, "<x&y>")
        self.assertEqual(a, h.render({"2026-10-01": 1}, TODAY, "<x&y>"))
        ET.fromstring(a)


if __name__ == "__main__":
    unittest.main()
