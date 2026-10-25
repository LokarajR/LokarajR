import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import chess  # noqa: E402
import chess_game as g  # noqa: E402


class Moves(unittest.TestCase):
    def setUp(self):
        self.start = g.new_state()

    def test_legal_move_is_applied(self):
        new, msg = g.apply_title(self.start, "chess|move|e2e4|0", "alice")
        self.assertEqual(new["ply"], 1)
        self.assertEqual(new["last"], {"uci": "e2e4", "san": "e4", "user": "alice"})
        self.assertIn("@alice played **e4**", msg)

    def test_illegal_move_is_rejected(self):
        new, msg = g.apply_title(self.start, "chess|move|e2e5|0", "alice")
        self.assertIsNone(new)
        self.assertIn("isn't a legal move", msg)

    def test_stale_link_is_rejected(self):
        new, msg = g.apply_title(self.start, "chess|move|e2e4|3", "alice")
        self.assertIsNone(new)
        self.assertIn("board changed", msg)

    def test_garbage_titles_are_rejected(self):
        for title in ("", "hello", "chess|move|e2e4", "chess|move|e2e4|0; rm -rf /", "chess|move|z9z9|0"):
            self.assertIsNone(g.apply_title(self.start, title, "alice")[0], title)

    def test_bad_username_is_not_echoed(self):
        _, msg = g.apply_title(self.start, "chess|move|e2e4|0", "<script>")
        self.assertIn("@someone", msg)

    def test_promotion_defaults_to_queen(self):
        state = {"fen": "8/P7/8/8/8/8/8/k6K w - - 0 1", "ply": 5, "last": None, "game": 1}
        new, _ = g.apply_title(state, "chess|move|a7a8|5", "bob")
        self.assertEqual(chess.Board(new["fen"]).piece_at(chess.A8).symbol(), "Q")

    def test_new_game_only_when_over(self):
        self.assertIsNone(g.apply_title(self.start, "chess|new", "bob")[0])
        mate = {"fen": "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
                "ply": 4, "last": None, "game": 2}
        new, _ = g.apply_title(mate, "chess|new", "bob")
        self.assertEqual((new["fen"], new["ply"], new["game"]), (chess.STARTING_FEN, 0, 3))


class CapturesAndPlayers(unittest.TestCase):
    def test_players_are_counted_per_move(self):
        s = g.new_state()
        s, _ = g.apply_title(s, "chess|move|e2e4|0", "alice")
        s, _ = g.apply_title(s, "chess|move|e7e5|1", "bob")
        s, _ = g.apply_title(s, "chess|move|g1f3|2", "alice")
        self.assertEqual(s["players"], {"alice": 2, "bob": 1})
        html = g.players_html(s)
        self.assertLess(html.index("@alice"), html.index("@bob"))
        self.assertIn("×2", html)

    def test_old_state_without_players_uses_last_mover(self):
        old = {"fen": chess.STARTING_FEN, "ply": 1, "game": 1,
               "last": {"uci": "f2f4", "san": "f4", "user": "LokarajR"}}
        self.assertEqual(g.players_of(old), {"LokarajR": 1})

    def test_new_game_clears_players(self):
        self.assertEqual(g.new_state(2)["players"], {})

    def test_captures_record_piece_and_capturer(self):
        s = g.new_state()
        for i, (mv, who) in enumerate([("e2e4", "alice"), ("d7d5", "bob"), ("e4d5", "carol"), ("d8d5", "dave")]):
            s, _ = g.apply_title(s, f"chess|move|{mv}|{i}", who)
        self.assertEqual([(c["piece"], c["by"]) for c in s["captures"]], [("bp", "carol"), ("wp", "dave")])
        html = g.captures_html(s, "game/img/")
        white_part, black_part = html.split("Black captured")
        self.assertIn("cap-bp.svg", white_part)
        self.assertIn("@carol", white_part)
        self.assertIn("@dave", black_part)
        self.assertLess(html.index("cap-bp.svg"), html.index("@carol"))  # name under the piece

    def test_en_passant_capture_is_a_pawn(self):
        s = {"fen": "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "ply": 0, "last": None, "game": 1}
        new, _ = g.apply_title(s, "chess|move|e5d6|0", "erin")
        self.assertEqual(new["captures"], [{"piece": "bp", "by": "erin", "san": "exd6"}])

    def test_no_captures_yet(self):
        self.assertEqual(g.captures_html(g.new_state(), "game/img/").count("none yet"), 2)

    def test_side_block_is_separate_from_board(self):
        s = g.new_state()
        self.assertNotIn("Players", g.readme_block(s))
        side = g.side_block(s)
        self.assertTrue(side.startswith(g.SIDE_START) and side.endswith(g.SIDE_END))
        self.assertIn("White captured", side)

    def test_replace_block_requires_markers(self):
        self.assertEqual(g.replace_block("a<!--S-->x<!--E-->b", "<!--S-->", "<!--E-->", "Y"), "aYb")
        with self.assertRaises(SystemExit):
            g.replace_block("no markers", "<!--S-->", "<!--E-->", "Y")

    def test_captured_image_is_valid_svg(self):
        ET.fromstring(g.captured_svg("bq"))


class Rendering(unittest.TestCase):
    def test_every_square_image_is_valid_svg(self):
        for code in ["x", "wk", "bp"]:
            for shade in "ld":
                for mark in g.MARKS:
                    ET.fromstring(g.square_svg(code, shade, mark))

    def test_start_board_links_only_movable_white_pieces(self):
        html = g.board_html(g.new_state(), "game/img/", "game/select/")
        self.assertEqual(html.count("<img "), 64)
        self.assertEqual(html.count('href="game/select/'), 10)  # 8 pawns + 2 knights
        self.assertIn('href="game/select/e2.md"', html)
        self.assertNotIn('href="game/select/e1.md"', html)  # king is blocked

    def test_select_page_links_targets_to_issues(self):
        page = g.select_page(g.new_state(), chess.E2)
        self.assertEqual(page.count("issues/new?title=chess%7Cmove%7Ce2e"), 2)  # e3, e4
        self.assertIn("chess%7Cmove%7Ce2e4%7C0", page)

    def test_board_is_deterministic(self):
        s = g.new_state()
        self.assertEqual(g.readme_block(s), g.readme_block(s))


if __name__ == "__main__":
    unittest.main()
