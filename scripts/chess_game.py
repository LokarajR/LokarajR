"""Community chess for the profile README, played by clicking on the board.

How a move works (GitHub READMEs cannot run code, so each click is a link):

    1. README board        click a piece of the side to move
    2. game/select/e2.md   the same board with that piece's legal targets marked
    3. click a target      opens a pre-filled issue "chess|move|e2e4|<ply>"
    4. workflow            `chess_game.py move` validates it, updates the board,
                           and the issue is answered and closed

    python scripts/chess_game.py render   # rebuild images, pages and README board
    python scripts/chess_game.py move     # apply ISSUE_TITLE by ISSUE_USER (workflow)

The ply number in every link means a stale link from an old position is
rejected instead of being applied to a different board.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import chess

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
IMG = GAME / "img"
SELECT = GAME / "select"
STATE = GAME / "state.json"
README = ROOT / "README.md"
OWNER = "LokarajR"
START, END = "<!-- CHESS:START -->", "<!-- CHESS:END -->"

SQ = 44
LIGHT, DARK = "#ebecd0", "#779556"
SELECTED, LAST = "#f6f669", "#baca44"
GLYPH = {"k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}
NAME = {"k": "king", "q": "queen", "r": "rook", "b": "bishop", "n": "knight", "p": "pawn"}
MARKS = ("n", "s", "t", "l")  # normal, selected, target, last move
TITLE_RE = re.compile(r"^chess\|move\|([a-h][1-8][a-h][1-8][qrbn]?)\|(\d{1,4})$")
NEW_RE = re.compile(r"^chess\|new$")
USER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


# ------------------------------------------------------------------ state

def new_state(game: int = 1) -> dict:
    return {"fen": chess.STARTING_FEN, "ply": 0, "last": None, "game": game, "players": {}}


def players_of(state: dict) -> dict:
    """Moves per player. Games started before this was tracked fall back to the last mover."""
    if "players" in state:
        return dict(state["players"])
    last = state.get("last")
    return {last["user"]: 1} if last else {}


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return new_state()


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_title(state: dict, title: str, user: str) -> tuple[dict | None, str]:
    """Return (new_state, message). new_state is None when the request is rejected."""
    user = user if USER_RE.match(user or "") else "someone"
    title = (title or "").strip()
    board = chess.Board(state["fen"])

    if NEW_RE.match(title):
        if not board.is_game_over():
            return None, "A game is still in progress, so a new one can't start yet."
        return new_state(state.get("game", 1) + 1), f"@{user} started game {state.get('game', 1) + 1}."

    m = TITLE_RE.match(title)
    if not m:
        return None, "That issue title isn't a chess move. Use the links on the board."
    uci, ply = m.group(1), int(m.group(2))
    if ply != state["ply"]:
        return None, "The board changed since that link was made. Open the profile and try again."
    if board.is_game_over():
        return None, "The game is over. Start a new one from the profile."
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves and len(uci) == 4:
        move = chess.Move.from_uci(uci + "q")  # auto-queen
    if move not in board.legal_moves:
        return None, f"`{uci}` isn't a legal move in this position."
    san = board.san(move)
    board.push(move)
    players = players_of(state)
    players[user] = players.get(user, 0) + 1
    new = {"fen": board.fen(), "ply": state["ply"] + 1, "game": state.get("game", 1),
           "last": {"uci": move.uci(), "san": san, "user": user}, "players": players}
    return new, f"@{user} played **{san}**. Thanks for playing!"


# ------------------------------------------------------------------ images

def piece_code(piece: chess.Piece | None) -> str:
    if piece is None:
        return "x"
    return ("w" if piece.color == chess.WHITE else "b") + piece.symbol().lower()


def square_svg(code: str, shade: str, mark: str) -> str:
    fill = {"s": SELECTED, "l": LAST}.get(mark, LIGHT if shade == "l" else DARK)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SQ}" height="{SQ}" viewBox="0 0 {SQ} {SQ}">',
           f'<rect width="{SQ}" height="{SQ}" fill="{fill}"/>']
    if code != "x":
        colour, kind = code[0], code[1]
        style = ('fill="#ffffff" stroke="#1f1f1f" stroke-width="1.4" paint-order="stroke"'
                 if colour == "w" else 'fill="#1f1f1f" stroke="#1f1f1f" stroke-width="0.6"')
        out.append(f'<text x="22" y="34" text-anchor="middle" font-size="34" {style} '
                   f'font-family="\'DejaVu Sans\', \'Segoe UI Symbol\', \'Apple Symbols\', '
                   f'\'Noto Sans Symbols 2\', serif">{GLYPH[kind]}︎</text>')
    if mark == "t":
        out.append('<circle cx="22" cy="22" r="19" fill="none" stroke="#1f1f1f" stroke-opacity="0.35" stroke-width="4"/>'
                   if code != "x" else '<circle cx="22" cy="22" r="7" fill="#1f1f1f" fill-opacity="0.3"/>')
    out.append("</svg>")
    return "".join(out) + "\n"


def image_name(code: str, shade: str, mark: str) -> str:
    return f"{code}-{shade}-{mark}.svg"


CAP = 22


def captured_svg(code: str) -> str:
    """A small piece with no square behind it, for the captured-pieces row."""
    style = ('fill="#ffffff" stroke="#1f1f1f" stroke-width="1" paint-order="stroke"'
             if code[0] == "w" else 'fill="#1f1f1f" stroke="#8b949e" stroke-width="0.6" paint-order="stroke"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CAP}" height="{CAP}" viewBox="0 0 {CAP} {CAP}">'
            f'<text x="11" y="18" text-anchor="middle" font-size="19" {style} '
            f'font-family="\'DejaVu Sans\', \'Segoe UI Symbol\', \'Apple Symbols\', \'Noto Sans Symbols 2\', serif">'
            f'{GLYPH[code[1]]}︎</text></svg>\n')


def write_images() -> int:
    IMG.mkdir(parents=True, exist_ok=True)
    pieces = [c + k for c in "wb" for k in GLYPH]
    n = 0
    for code in ["x"] + pieces:
        for shade in "ld":
            for mark in MARKS:
                (IMG / image_name(code, shade, mark)).write_text(square_svg(code, shade, mark), encoding="utf-8")
                n += 1
    for code in pieces:
        (IMG / f"cap-{code}.svg").write_text(captured_svg(code), encoding="utf-8")
        n += 1
    return n


START_COUNT = {"p": 8, "n": 2, "b": 2, "r": 2, "q": 1}


def captured(board: chess.Board, colour: bool) -> list[str]:
    """Pieces of `colour` no longer on the board, most valuable first.
    A promotion can make a count go up; that is clamped at zero."""
    out = []
    for kind in "qrbnp":
        missing = START_COUNT[kind] - len(board.pieces(chess.PIECE_SYMBOLS.index(kind), colour))
        out += [("w" if colour else "b") + kind] * max(0, missing)
    return out


# ------------------------------------------------------------------ board html

def issue_url(title: str) -> str:
    body = "Just press **Submit new issue**. The board updates itself in a minute or so."
    return (f"https://github.com/{OWNER}/{OWNER}/issues/new?title={quote(title, safe='')}"
            f"&body={quote(body, safe='')}")


def board_html(state: dict, img_prefix: str, select_prefix: str, selected: int | None = None) -> str:
    """One line of linked images per rank, white at the bottom. No table, so no gaps."""
    board = chess.Board(state["fen"])
    last = state.get("last") or {}
    last_sq = set()
    if last.get("uci"):
        mv = chess.Move.from_uci(last["uci"])
        last_sq = {mv.from_square, mv.to_square}
    movers = {m.from_square for m in board.legal_moves}
    targets = {}
    if selected is not None:
        for m in board.legal_moves:
            if m.from_square == selected and m.to_square not in targets:
                targets[m.to_square] = m
    over = board.is_game_over()

    rows = []
    for rank in range(7, -1, -1):
        cells = []
        for file in range(8):
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            shade = "l" if (file + rank) % 2 else "d"
            mark = "s" if sq == selected else "t" if sq in targets else "l" if sq in last_sq else "n"
            name = chess.square_name(sq)
            alt = f"{name} " + (f"{'white' if piece.color else 'black'} {NAME[piece.symbol().lower()]}" if piece else "empty")
            img = f'<img src="{img_prefix}{image_name(piece_code(piece), shade, mark)}" width="{SQ}" height="{SQ}" align="top" alt="{alt}">'
            href = None
            if sq in targets:
                m = targets[sq]
                uci = m.uci()[:4] + ("q" if m.promotion else "")
                href = issue_url(f"chess|move|{uci}|{state['ply']}")
            elif not over and sq in movers and sq != selected:
                href = f"{select_prefix}{name}.md"
            cells.append(f'<a href="{href}">{img}</a>' if href else img)
        rows.append("".join(cells))
    return "<br>\n".join(rows)


def status_line(state: dict) -> str:
    board = chess.Board(state["fen"])
    last = state.get("last")
    lastbit = f" · last: <b>{last['san']}</b> by @{last['user']}" if last else ""
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"<b>Checkmate. {winner} wins!</b>{lastbit}"
    if board.is_game_over():
        return f"<b>Draw.</b>{lastbit}"
    side = "White" if board.turn == chess.WHITE else "Black"
    check = " · <b>check!</b>" if board.is_check() else ""
    return f"<b>{side} to move</b> · game {state.get('game', 1)}, move {state['ply'] // 2 + 1}{check}{lastbit}"


def readme_block(state: dict) -> str:
    board = chess.Board(state["fen"])
    side = "white" if board.turn == chess.WHITE else "black"
    hint = (f'<a href="{issue_url("chess|new")}">Start a new game</a>' if board.is_game_over()
            else f"Click a {side} piece, then click where it should go.")
    return (f"{START}\n<p>{status_line(state)}</p>\n"
            f"<p>\n{board_html(state, 'game/img/', 'game/select/')}\n</p>\n"
            f"{captures_html(board, 'game/img/')}\n{players_html(state)}\n"
            f"<p><sub>{hint} Anyone can play: each move is a GitHub issue, "
            f"checked for legality by <a href=\"scripts/chess_game.py\">a workflow</a>.</sub></p>\n{END}")


def captures_html(board: chess.Board, img_prefix: str) -> str:
    def row(codes: list[str]) -> str:
        if not codes:
            return "<sub>none yet</sub>"
        return "".join(f'<img src="{img_prefix}cap-{c}.svg" width="{CAP}" height="{CAP}" align="top" '
                       f'alt="{"white" if c[0] == "w" else "black"} {NAME[c[1]]}">' for c in codes)
    return (f"<p><sub><b>White captured</b></sub><br>{row(captured(board, chess.BLACK))}<br>"
            f"<sub><b>Black captured</b></sub><br>{row(captured(board, chess.WHITE))}</p>")


def players_html(state: dict) -> str:
    players = sorted(players_of(state).items(), key=lambda kv: (-kv[1], kv[0].lower()))
    if not players:
        return "<p><sub><b>Players</b></sub><br><sub>be the first to move</sub></p>"
    names = " · ".join(f'<a href="https://github.com/{u}">@{u}</a>' + (f" ×{n}" if n > 1 else "")
                       for u, n in players)
    return f"<p><sub><b>Players</b></sub><br>{names}</p>"


def select_page(state: dict, sq: int) -> str:
    board = chess.Board(state["fen"])
    piece = board.piece_at(sq)
    name = chess.square_name(sq)
    what = f"{'White' if piece.color else 'Black'} {NAME[piece.symbol().lower()]} on {name}"
    return (f"<p align=\"center\"><b>{what}</b>: click a marked square to move there.</p>\n\n"
            f"<p align=\"center\">\n{board_html(state, '../img/', '', selected=sq)}\n</p>\n\n"
            f"<p align=\"center\"><sub>Opens a pre-filled issue; just press <b>Submit</b>. "
            f"<a href=\"https://github.com/{OWNER}\">← back to the board</a></sub></p>\n")


def render(state: dict) -> None:
    write_images()
    SELECT.mkdir(parents=True, exist_ok=True)
    for old in SELECT.glob("*.md"):
        old.unlink()
    board = chess.Board(state["fen"])
    if not board.is_game_over():
        for sq in sorted({m.from_square for m in board.legal_moves}):
            (SELECT / f"{chess.square_name(sq)}.md").write_text(select_page(state, sq), encoding="utf-8")
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README is missing the CHESS:START / CHESS:END markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(head + readme_block(state) + tail, encoding="utf-8")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "render"
    state = load_state()
    if cmd == "render":
        save_state(state)
        render(state)
        return 0
    if cmd == "move":
        new, message = apply_title(state, os.environ.get("ISSUE_TITLE", ""), os.environ.get("ISSUE_USER", ""))
        out = os.environ.get("CHESS_MESSAGE_FILE")
        if out:
            Path(out).write_text(message + "\n", encoding="utf-8")
        print(message)
        if new is None:
            return 2
        save_state(new)
        render(new)
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
