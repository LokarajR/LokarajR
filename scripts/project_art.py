"""Draw one animated SVG per project. Each picture acts out what the project does.

    python scripts/project_art.py      # writes assets/projects/*.svg

Animations are SVG-native (SMIL), so they play inside GitHub READMEs, where
scripts do not run. Standard library only; output is deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "projects"
W, H = 400, 240
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED = "#e6edf3", "#8b949e"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
RED, GREEN = "#f85149", "#3fb950"


def card(title: str, tag: str, footer: str, accent: str, body: str, desc: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{title}: {desc}">
<title>{title}</title>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{BG}" stroke="{BORDER}"/>
<rect x="0.5" y="0.5" width="6" height="{H - 1}" rx="3" fill="{accent}"/>
<text x="22" y="32" font-family="{SANS}" font-size="16" font-weight="700" fill="{TEXT}">{title}</text>
<text x="{W - 20}" y="32" text-anchor="end" font-family="{MONO}" font-size="10" fill="{accent}">{tag}</text>
{body}
<text x="22" y="{H - 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{footer}</text>
</svg>
"""


def doc(x, y, w=26, h=32, stroke=MUTED, fill=PANEL, lines=3):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" stroke="{stroke}"/>'
    for i in range(lines):
        s += f'<path d="M{x + 5} {y + 8 + i * 7}h{w - 10}" stroke="{stroke}" stroke-width="1.5"/>'
    return s


# --------------------------------------------------------------- the eight pictures

def driver() -> str:
    a = "#a371f7"
    body = f"""
<rect x="26" y="56" width="170" height="140" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
<circle cx="40" cy="68" r="4" fill="{RED}"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/></circle>
<text x="50" y="72" font-family="{MONO}" font-size="9" fill="{MUTED}">CAM 01</text>
<circle cx="110" cy="112" r="17" fill="{MUTED}"/>
<path d="M78 196c0-34 14-52 32-52s32 18 32 52z" fill="{MUTED}"/>
<rect x="130" y="104" width="10" height="18" rx="2" fill="{a}"/>
<path d="M60 168h100" stroke="{BORDER}" stroke-width="6" stroke-linecap="round"/>
<rect x="86" y="88" width="62" height="44" rx="4" fill="none" stroke="{a}" stroke-width="2" stroke-dasharray="5 3">
  <animate attributeName="opacity" values="0;1;1;0" dur="3s" repeatCount="indefinite"/></rect>
<text x="88" y="84" font-family="{MONO}" font-size="9" fill="{a}">texting · right<animate attributeName="opacity" values="0;1;1;0" dur="3s" repeatCount="indefinite"/></text>
<rect x="30" y="60" width="162" height="2" fill="{a}" opacity="0.6"><animate attributeName="y" values="60;192;60" dur="3s" repeatCount="indefinite"/></rect>
<text x="214" y="70" font-family="{MONO}" font-size="9" fill="{MUTED}">SPLIT BY DRIVER</text>"""
    rows = (("train", 6, "#58a6ff"), ("val", 2, "#a371f7"), ("test", 3, GREEN))
    for i, (name, n, c) in enumerate(rows):
        y = 82 + i * 22
        body += f'<text x="214" y="{y + 10}" font-family="{MONO}" font-size="9" fill="{MUTED}">{name}</text>'
        for j in range(n):
            body += (f'<g transform="translate({246 + j * 22} {y})"><circle cx="7" cy="5" r="4" fill="{c}"/>'
                     f'<path d="M1 14c0-5 3-7 6-7s6 2 6 7z" fill="{c}"/></g>')
    body += f"""
<rect x="214" y="156" width="164" height="40" rx="8" fill="{PANEL}" stroke="{a}"/>
<text x="296" y="174" text-anchor="middle" font-family="{SANS}" font-size="15" font-weight="700" fill="{TEXT}">0.90 F1</text>
<text x="296" y="189" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">drivers it never saw</text>"""
    return card("Distracted Driver", "COMPUTER VISION", "no driver appears in two splits", a, body,
                "camera frame classifying a driver texting; the data is split so no driver is shared between train, validation and test; 0.90 macro F1 on unseen drivers")


def hybrid_rag() -> str:
    a = "#58a6ff"
    srcs = ("WEB", "NEWS", "WIKI", "PAPERS", "PMC")
    body = ""
    for i, s in enumerate(srcs):
        y = 56 + i * 32
        body += doc(22, y, 22, 26, lines=2)
        body += f'<text x="50" y="{y + 17}" font-family="{MONO}" font-size="9" fill="{MUTED}">{s}</text>'
        body += (f'<circle r="3" fill="{a}"><animateMotion dur="2.4s" begin="{i * 0.4}s" repeatCount="indefinite" '
                 f'path="M90 {y + 13} C140 {y + 13} 150 136 196 136"/></circle>')
    body += f"""
<circle cx="214" cy="136" r="26" fill="{PANEL}" stroke="{a}" stroke-width="2"/>
<text x="214" y="133" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{TEXT}">NLI</text>
<text x="214" y="145" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{TEXT}">verify</text>
<rect x="262" y="62" width="58" height="26" rx="5" fill="{PANEL}" stroke="{BORDER}"/>
<text x="291" y="79" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{TEXT}">0.25%</text>
<rect x="326" y="62" width="58" height="26" rx="5" fill="{PANEL}" stroke="{BORDER}"/>
<text x="355" y="79" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{TEXT}">0.50%</text>
<text x="323" y="104" text-anchor="middle" font-family="{SANS}" font-size="18" font-weight="700" fill="{RED}">≠<animate attributeName="opacity" values="0.2;1;0.2" dur="1.4s" repeatCount="indefinite"/></text>
<path d="M240 136h22" stroke="{MUTED}"/>
<rect x="262" y="118" width="122" height="78" rx="6" fill="{PANEL}" stroke="{a}"/>
<text x="272" y="136" font-family="{MONO}" font-size="9" fill="{a}">ANSWER</text>
<path d="M272 148h96M272 158h80" stroke="{MUTED}" stroke-width="2"/>
<text x="272" y="182" font-family="{MONO}" font-size="10" fill="{RED}">⚠ sources disagree</text>"""
    return card("Hybrid RAG", "RETRIEVAL · REASONING", "shows the conflict instead of hiding it", a, body,
                "five keyless sources stream into an NLI verification step that flags two sources reporting different figures; the answer warns that sources disagree")


def private_docs() -> str:
    a = GREEN
    body = f"""
<rect x="40" y="58" width="190" height="120" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
<path d="M24 184h222l-14 12H38z" fill="{BORDER}"/>
{doc(58, 74)}{doc(92, 74)}{doc(126, 74)}{doc(160, 74)}{doc(194 - 2, 74, 24)}
{doc(58, 120)}{doc(92, 120)}{doc(126, 120, stroke=a)}{doc(160, 120)}
<rect x="54" y="70" width="34" height="40" rx="4" fill="none" stroke="{a}" stroke-width="2">
  <animate attributeName="x" values="54;88;122;156;122" dur="4s" repeatCount="indefinite"/>
  <animate attributeName="y" values="70;70;70;70;116" dur="4s" repeatCount="indefinite"/></rect>
<text x="122" y="172" font-family="{MONO}" font-size="9" fill="{a}">p.14<animate attributeName="opacity" values="0;0;0;0;1" dur="4s" calcMode="discrete" repeatCount="indefinite"/></text>
<g transform="translate(274 66)">
  <path d="M0 18a34 34 0 0 1 48 0M8 26a22 22 0 0 1 32 0M16 34a10 10 0 0 1 16 0" fill="none" stroke="{MUTED}" stroke-width="3" stroke-linecap="round"/>
  <path d="M-4 -2L52 46" stroke="{RED}" stroke-width="3" stroke-linecap="round"/>
</g>
<text x="298" y="128" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">no network</text>
<rect x="282" y="152" width="32" height="24" rx="4" fill="{a}"/>
<path d="M288 152v-7a10 10 0 0 1 20 0v7" fill="none" stroke="{a}" stroke-width="3"/>
<text x="298" y="190" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">your files stay</text>"""
    return card("Private Docs RAG", "OFFLINE RETRIEVAL", "every answer cites page, slide or cell", a, body,
                "a laptop scanning its own documents with no network connection and returning a citation to page 14")


def raze() -> str:
    a = "#f0883e"
    env = lambda x, y, c=MUTED: (f'<g transform="translate({x} {y})"><rect width="30" height="20" rx="3" fill="{PANEL}" stroke="{c}"/>'
                                 f'<path d="M0 0l15 11L30 0" fill="none" stroke="{c}"/></g>')
    body = f"""
<text x="22" y="66" font-family="{MONO}" font-size="9" fill="{MUTED}">RAZORPAY WEBHOOKS</text>
<g transform="translate(22 80)">{env(0, 0)}<animateTransform attributeName="transform" type="translate" values="22 80;150 80" dur="2s" repeatCount="indefinite"/></g>
<g transform="translate(28 86)">{env(0, 0)}<animateTransform attributeName="transform" type="translate" values="28 86;150 86" dur="2s" begin="0.3s" repeatCount="indefinite"/></g>
<text x="60" y="122" font-family="{MONO}" font-size="9" fill="{MUTED}">duplicate</text>
<g transform="translate(22 136)">{env(0, 0)}<animateTransform attributeName="transform" type="translate" values="22 136;150 136" dur="5s" repeatCount="indefinite"/></g>
<text x="60" y="170" font-family="{MONO}" font-size="9" fill="{MUTED}">delayed</text>
<g transform="translate(22 176)">{env(0, 0, RED)}<animateTransform attributeName="transform" type="translate" values="22 176;90 176" dur="2.5s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="1;1;0" dur="2.5s" repeatCount="indefinite"/></g>
<text x="104" y="190" font-family="{MONO}" font-size="9" fill="{RED}">lost ✗</text>
<path d="M200 70l34 12v34c0 26-18 42-34 50-16-8-34-24-34-50V82z" fill="{PANEL}" stroke="{a}" stroke-width="2"/>
<text x="200" y="112" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{TEXT}">dedupe</text>
<text x="200" y="124" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{TEXT}">reconcile</text>
<path d="M200 176v14" stroke="{a}" stroke-dasharray="3 3"/>
<text x="200" y="204" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{a}">asks Razorpay ↺</text>
<rect x="258" y="74" width="126" height="96" rx="6" fill="{PANEL}" stroke="{BORDER}"/>
<text x="268" y="92" font-family="{MONO}" font-size="9" fill="{MUTED}">ORDER #1042</text>
<text x="268" y="120" font-family="{SANS}" font-size="15" font-weight="700" fill="{MUTED}">pending<animate attributeName="opacity" values="1;1;0;0" dur="4s" calcMode="discrete" repeatCount="indefinite"/></text>
<text x="268" y="120" font-family="{SANS}" font-size="15" font-weight="700" fill="{GREEN}">paid ✓ once<animate attributeName="opacity" values="0;0;1;1" dur="4s" calcMode="discrete" repeatCount="indefinite"/></text>
<text x="268" y="152" font-family="{MONO}" font-size="9" fill="{MUTED}">demo: 1/5 → 5/5</text>"""
    return card("Raze", "RELIABLE ENGINEERING", "every payment lands exactly once", a, body,
                "duplicate, delayed and lost Razorpay webhooks hit a dedupe and reconcile shield; the order flips from pending to paid exactly once")


def truthlens() -> str:
    a = "#e3b341"
    body = f"""
<rect x="30" y="58" width="170" height="136" rx="6" fill="{PANEL}" stroke="{BORDER}"/>
<rect x="42" y="70" width="146" height="14" rx="2" fill="{MUTED}"/>
<path d="M42 98h146M42 110h120M42 122h140M42 134h100M42 146h146M42 158h90M42 170h130" stroke="{BORDER}" stroke-width="4"/>
<g><circle cx="0" cy="0" r="22" fill="none" stroke="{a}" stroke-width="3"/><path d="M16 16l16 16" stroke="{a}" stroke-width="5" stroke-linecap="round"/>
  <animateTransform attributeName="transform" type="translate" values="80 110;150 130;90 160;80 110" dur="4s" repeatCount="indefinite"/></g>
<g transform="rotate(-12 300 92)"><rect x="248" y="72" width="104" height="38" rx="4" fill="none" stroke="{RED}" stroke-width="3"/>
<text x="300" y="98" text-anchor="middle" font-family="{SANS}" font-size="17" font-weight="800" fill="{RED}">LIKELY FAKE</text>
<animate attributeName="opacity" values="0;0;1;1" dur="4s" calcMode="discrete" repeatCount="indefinite"/></g>
<rect x="232" y="132" width="152" height="54" rx="10" fill="{PANEL}" stroke="{a}"/>
<text x="244" y="152" font-family="{MONO}" font-size="9" fill="{a}">LLaMA 3 · why:</text>
<path d="M244 164h124M244 174h90" stroke="{MUTED}" stroke-width="2"/>"""
    return card("TruthLens", "NLP · LLM", "scores the article, then explains why", a, body,
                "a magnifying glass scans a news article, a 'likely fake' stamp appears and LLaMA 3 explains the verdict")


def federated() -> str:
    a = "#39c5cf"
    clients = ((70, 80), (70, 170), (330, 125))
    body = f"""
<circle cx="200" cy="125" r="30" fill="{PANEL}" stroke="{a}" stroke-width="2"/>
<text x="200" y="122" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{TEXT}">FedAvg</text>
<text x="200" y="134" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">server</text>"""
    for i, (x, y) in enumerate(clients):
        body += f"""
<rect x="{x - 26}" y="{y - 20}" width="52" height="40" rx="6" fill="{PANEL}" stroke="{BORDER}"/>
<text x="{x}" y="{y - 4}" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{MUTED}">client {i + 1}</text>
<text x="{x}" y="{y + 10}" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{a}">🔒 data</text>
<path d="M{x} {y}L200 125" stroke="{BORDER}" stroke-dasharray="3 4"/>
<circle r="4" fill="{a}"><animateMotion dur="2.2s" begin="{i * 0.5}s" repeatCount="indefinite" path="M{x} {y}L200 125"/></circle>
<circle r="2" fill="{RED}" opacity="0.8"><animateMotion dur="2.2s" begin="{i * 0.5}s" repeatCount="indefinite" path="M{x + 4} {y - 5}L204 119"/></circle>"""
    body += f'<text x="236" y="190" font-family="{MONO}" font-size="9" fill="{RED}">● DP noise added</text>'
    body += f'<text x="236" y="204" font-family="{MONO}" font-size="9" fill="{a}">● clipped gradients</text>'
    return card("Federated Learning", "PRIVACY", "only noised updates leave the client", a, body,
                "three clients keep their data locked and send clipped, noise-added gradients to a FedAvg server")


def surveillance() -> str:
    a = "#db61a2"
    body = f"""
<g transform="translate(26 92)"><rect width="52" height="34" rx="6" fill="{PANEL}" stroke="{a}" stroke-width="2"/>
<circle cx="26" cy="17" r="9" fill="none" stroke="{a}" stroke-width="2"/><path d="M52 10l14-8v30l-14-8" fill="{PANEL}" stroke="{a}" stroke-width="2"/></g>
<text x="30" y="146" font-family="{MONO}" font-size="9" fill="{MUTED}">motion → clip</text>
<path d="M150 118a18 18 0 0 1 34-10a16 16 0 0 1 28 14a14 14 0 0 1-6 28h-54a16 16 0 0 1-2-32z" fill="{PANEL}" stroke="{MUTED}" stroke-width="2"/>
<text x="180" y="138" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{TEXT}">GCP</text>
<text x="180" y="170" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{MUTED}">Pub/Sub · Video AI</text>
<rect x="250" y="80" width="64" height="76" rx="4" fill="{PANEL}" stroke="{BORDER}"/>
<circle cx="282" cy="104" r="9" fill="{MUTED}"/><path d="M266 150c0-22 7-34 16-34s16 12 16 34z" fill="{MUTED}"/>
<rect x="260" y="88" width="44" height="64" fill="none" stroke="{GREEN}" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" dur="3s" repeatCount="indefinite"/></rect>
<text x="260" y="170" font-family="{MONO}" font-size="9" fill="{GREEN}">person<animate attributeName="opacity" values="0;0;1;1" dur="3s" repeatCount="indefinite"/></text>
<g transform="translate(336 100)"><rect width="40" height="28" rx="3" fill="{PANEL}" stroke="{a}" stroke-width="2"/><path d="M0 0l20 14L40 0" fill="none" stroke="{a}" stroke-width="2"/>
<animate attributeName="opacity" values="0;0;0;1" dur="3s" repeatCount="indefinite"/></g>
<text x="338" y="146" font-family="{MONO}" font-size="9" fill="{a}">alert</text>
<circle r="4" fill="{a}"><animateMotion dur="3s" repeatCount="indefinite" path="M94 109L150 126L250 118L336 114"/></circle>"""
    return card("Cloud Surveillance", "VISION · CLOUD", "camera → cloud → person → email", a, body,
                "a camera records on motion, the clip flows through Google Cloud, a person is detected and an email alert is sent")


def ast_similarity() -> str:
    a = "#79c0ff"

    def tree(ox):
        n = [(ox + 60, 70), (ox + 30, 110), (ox + 90, 110), (ox + 15, 150), (ox + 45, 150), (ox + 90, 150)]
        e = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5)]
        s = "".join(f'<path d="M{n[i][0]} {n[i][1]}L{n[j][0]} {n[j][1]}" stroke="{BORDER}" stroke-width="2"/>' for i, j in e)
        for k, (x, y) in enumerate(n):
            s += (f'<circle cx="{x}" cy="{y}" r="9" fill="{PANEL}" stroke="{a}" stroke-width="2">'
                  f'<animate attributeName="fill" values="{PANEL};{a};{PANEL}" dur="3s" begin="{k * 0.4}s" repeatCount="indefinite"/></circle>')
        return s

    body = tree(30) + tree(250) + f"""
<text x="90" y="182" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">your code</text>
<text x="310" y="182" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">GPL repo</text>
<text x="200" y="110" text-anchor="middle" font-family="{SANS}" font-size="22" fill="{a}">⇄</text>
<rect x="160" y="128" width="80" height="10" rx="5" fill="{PANEL}" stroke="{BORDER}"/>
<rect x="160" y="128" width="0" height="10" rx="5" fill="{a}"><animate attributeName="width" values="0;68;68" dur="3s" repeatCount="indefinite"/></rect>
<text x="200" y="156" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">similarity</text>"""
    return card("AST Similarity", "PROGRAM ANALYSIS", "compares syntax trees to flag reuse", a, body,
                "two syntax trees are compared node by node and a similarity bar fills to flag possible GPL code reuse")


ART = {
    "driver": driver, "hybrid-rag": hybrid_rag, "private-docs-rag": private_docs, "raze": raze,
    "truthlens": truthlens, "federated": federated, "surveillance": surveillance, "ast": ast_similarity,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in ART.items():
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8", newline="\n")
    print(f"wrote {len(ART)} project SVGs to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
