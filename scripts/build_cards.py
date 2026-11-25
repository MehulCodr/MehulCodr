#!/usr/bin/env python3
"""Build the animated SVG cards for the GitHub profile README.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_cards.py

The token is only used to read your public contribution calendar for the
activity and contribution cards. Without a token those two cards are skipped
and the existing files are left as they are.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import urllib.request
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = "MehulCodr"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cards"

# Colours from the portfolio (mehulcodr.github.io).
PAPER = "#F8F7F3"
INK = "#201C2A"
MUTED = "#5F596A"
LINE = "#DDD9E4"
ACCENT = "#4E35C8"
LILAC = "#D5BCFF"
LILAC_2 = "#AD91FF"
PANEL = "#1B1824"
PANEL_LINE = "#3A3447"
PANEL_MUTED = "#9C95AC"
WHITE = "#FDFCFF"

FONT_B64 = base64.b64encode((ROOT / "fonts" / "space-grotesk.woff2").read_bytes()).decode()

STYLE = f"""<style><![CDATA[
@font-face{{font-family:'SG';src:url(data:font/woff2;base64,{FONT_B64}) format('woff2');font-weight:300 700}}
text{{text-rendering:geometricPrecision}}
.d{{font-family:'SG',system-ui,sans-serif;font-weight:500;letter-spacing:-1.6px}}
.b{{font-family:'SG',system-ui,sans-serif;font-weight:400}}
.s{{font-family:'SG',system-ui,sans-serif;font-weight:600;letter-spacing:.4px}}
.m{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.8px}}
.in{{opacity:0;animation:rise .8s cubic-bezier(.16,1,.3,1) var(--t,0s) both}}
.fade{{opacity:0;animation:fade .7s ease var(--t,0s) both}}
.pop{{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .35s ease-out var(--t,0s) both}}
.grow{{transform:scaleY(0);transform-box:fill-box;transform-origin:bottom;animation:grow .9s cubic-bezier(.15,1,.3,1) var(--t,0s) both}}
.wide{{transform:scaleX(0);transform-box:fill-box;transform-origin:left;animation:wide .9s cubic-bezier(.15,1,.3,1) var(--t,0s) both}}
.trace{{stroke-dasharray:1400;stroke-dashoffset:1400;animation:trace 2.4s ease var(--t,0s) both}}
.bob{{animation:bob 6s ease-in-out 3s infinite}}
.nudge{{animation:nudge 2.8s ease-in-out 4s infinite}}
.blink{{animation:blink 1s steps(1) 3s infinite}}
.spin{{transform-box:fill-box;transform-origin:center;animation:spin 14s linear infinite}}
.pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-in-out infinite}}
@keyframes rise{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:none}}}}
@keyframes fade{{to{{opacity:1}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.4)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes grow{{to{{transform:scaleY(1)}}}}
@keyframes wide{{to{{transform:scaleX(1)}}}}
@keyframes trace{{to{{stroke-dashoffset:0}}}}
@keyframes bob{{50%{{transform:translateY(-7px)}}}}
@keyframes nudge{{0%,75%,100%{{transform:none}}87%{{transform:translate(5px,-5px)}}}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes pulse{{50%{{transform:scale(1.6);opacity:.25}}}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}}}}
]]></style>"""


# ---------------------------------------------------------------- helpers

def text(x, y, s, size, fill, cls="b", t=None, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    if t is None:
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" class="{cls}"{a}{extra}>{escape(s)}</text>'
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" class="{cls} in"{a}'
            f' style="--t:{t:.2f}s"{extra}>{escape(s)}</text>')


def rect(x, y, w, h, fill, rx=0, cls=None, t=None, extra=""):
    c = f' class="{cls}"' if cls else ""
    st = f' style="--t:{t:.2f}s"' if t is not None else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{c}{st}{extra}/>'


def path(d, stroke, width=1.5, cls=None, t=None, extra=""):
    c = f' class="{cls}"' if cls else ""
    st = f' style="--t:{t:.2f}s"' if t is not None else ""
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{c}{st}{extra}/>')


def card(name, w, h, body, label, bg=PAPER, border=LINE):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}">\n<title>{escape(label)}</title>\n'
        f'<defs><clipPath id="c"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24"/></clipPath></defs>\n'
        f"{STYLE}\n"
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24" fill="{bg}" stroke="{border}" stroke-width="2"/>'
        f'<g clip-path="url(#c)">{"".join(body)}</g></svg>\n'
    )
    (OUT / f"{name}.svg").write_text(svg)
    print(f"wrote cards/{name}.svg ({len(svg)//1024} KB)")


def pill(x, y, label, fg, bg, t=None, size=10):
    w = len(label) * size * 0.62 + 20
    return (rect(x, y, round(w, 1), 22, bg, 11, "fade" if t is not None else None, t)
            + text(round(x + w / 2, 1), y + 15, label, size, fg, "m", t, "middle")), w


def arrow(x, y, color, t):
    return path(f"M{x} {y+14}L{x+14} {y} M{x+5} {y}H{x+14}V{y+9}", color, 1.8, "nudge", t)


# ---------------------------------------------------------------- cards

def hero():
    b = []
    b.append(text(56, 54, "MG / MEHULCODR", 15, INK, "m", 0.05))
    b.append(text(944, 54, "AI RESEARCH ENGINEER @ OXYZEN · DTU CSE '28", 13, MUTED, "m", 0.1, "end"))
    b.append(path("M56 74H944", LINE, 1.3))
    b.append(rect(57, 104, 11, 11, ACCENT, 3, "pop", 0.2))
    b.append(text(80, 115, "HI, I'M", 15, INK, "m", 0.22))
    b.append(text(50, 222, "Mehul", 108, INK, "d", 0.34))
    b.append(text(50, 320, "Gupta.", 108, INK, "d", 0.48))
    b.append(rect(58, 336, 128, 6, ACCENT, 3, "wide", 0.8))
    b.append(text(58, 377, "I build AI systems that hold up in practice.", 20, MUTED, "b", 0.62))

    # terminal panel
    px, py, pw, ph = 612, 98, 336, 288
    b.append(rect(px, py, pw, ph, PANEL, 22, "fade", 0.3))
    for i in range(1, 13):
        b.append(path(f"M{px+i*26} {py+46}V{py+ph-14}", PANEL_LINE, 0.6, extra=' opacity=".35"'))
    for i, c in enumerate(["#FF7A85", "#FFC96B", "#7EE0A4"]):
        b.append(f'<circle cx="{px+24+i*16}" cy="{py+24}" r="5" fill="{c}"/>')
    b.append(text(px + pw - 20, py + 28, "agent — ~/repo", 11, PANEL_MUTED, "m", None, "end"))
    b.append(path(f"M{px} {py+44}H{px+pw}", PANEL_LINE, 1))

    lines = [
        ("$ agent ask \"where is auth handled?\"", WHITE),
        ("› retrieving repo context…", PANEL_MUTED),
        ("› src/auth/session.py:42", LILAC),
        ("› src/api/routes.py:118", LILAC),
        ("✓ answer · 2 citations", "#7EE0A4"),
        ("$ agent fix --tests", WHITE),
        ("✓ 80/80 tests passing", "#7EE0A4"),
        ("? run git commit  [y/n]", "#FFC96B"),
    ]
    tx = px + 22
    for i, (s, col) in enumerate(lines):
        y = py + 72 + i * 25
        b.append(text(tx, y, s, 12.5, col, "m", 1.0 + i * 0.28))
    cy = py + 72 + 7 * 25
    b.append(f'<rect x="{tx + len(lines[-1][0]) * 7.95 + 6:.1f}" y="{cy-11}" width="8" height="14" rx="1" fill="{WHITE}" '
             f'opacity="0"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.01;.5;.51;1" '
             f'dur="1s" begin="3.2s" repeatCount="indefinite"/></rect>')

    # floating badge
    b.append(f'<g class="bob">{rect(560, 368, 164, 40, ACCENT, 20, "pop", 3.4)}'
             f'<circle cx="582" cy="388" r="4" fill="#7EE0A4" class="pulse"/><circle cx="582" cy="388" r="4" fill="#7EE0A4"/>'
             f'{text(596, 392, "RAG · EVALS · AGENTS", 10, WHITE, "m", 3.5)}</g>')
    card("hero", 1000, 420, b, "Hi, I'm Mehul Gupta. I build AI systems that hold up in practice.")


def link_tile(name, idx, kicker, title, sub, bg, fg, sub_fg, glyph, t0, border=None):
    b = [rect(1, 1, 318, 191, bg, 23)]
    b.append(text(24, 38, f"0{idx}", 14, fg, "m", t0))
    b.append(text(24, 80, kicker, 11, sub_fg, "m", t0 + 0.05))
    b.append(text(22, 127, title, 40, fg, "d", t0 + 0.12))
    b.append(text(24, 158, sub, 14, sub_fg, "b", t0 + 0.2))
    b.append(glyph)
    b.append(arrow(272, 160, fg, t0 + 0.3))
    card(name, 320, 193, b, title, bg, border or bg)


def links():
    gh = (rect(230, 20, 68, 66, WHITE, 18)
          + path("M246 40L232 53L246 66 M282 40L296 53L282 66", ACCENT, 3)
          + path("M259 70L269 36", ACCENT, 3))
    li = (rect(230, 20, 68, 66, INK, 18)
          + f'<rect x="243" y="45" width="7" height="27" rx="2" fill="{LILAC}"/>'
          + f'<circle cx="246.5" cy="35" r="4.5" fill="{LILAC}"/>'
          + path("M259 72V54 M259 59c0-6 4-9 9-9s9 3 9 10v12", LILAC, 6.5))
    em = (rect(230, 20, 68, 66, LILAC, 18)
          + path("M243 38H285V68H243Z M243 40L264 56L285 40", INK, 2.6))
    link_tile("github", 1, "FIND ME ON", "GitHub", "Code, agents & experiments", ACCENT, WHITE, "#D9D0FF", gh, 0.9)
    link_tile("linkedin", 2, "CONNECT ON", "LinkedIn", "Research, work & updates", PAPER, INK, MUTED, li, 1.0, LINE)
    link_tile("email", 3, "SAY HELLO", "Email", "Research, projects & ideas", INK, WHITE, PANEL_MUTED, em, 1.1)


def focus():
    T = 1.6
    b = [text(56, 52, "02 / WHAT I WORK ON", 14, MUTED, "m", 0.2)]
    b.append(text(53, 112, "AI that shows its work.", 48, INK, "d", T))
    b.append(text(56, 140, "Agents, evaluations and retrieval, built to be checked rather than trusted.",
                  16, MUTED, "b", T + 0.12))
    items = [
        ("AGENT SYSTEMS", "Coding agents that cite the code.", "PYTHON · TOOL USE · GIT", "#ECE6FF"),
        ("LLM EVALUATION", "Sandboxed, rubric-graded evals.", "DOCKER · RUBRICS · BATCH", "#F1EEE4"),
        ("RETRIEVAL", "Answers with traceable sources.", "RAG · FAISS · EMBEDDINGS", "#E3EEF0"),
    ]
    for i, (title, desc, tags, bg) in enumerate(items):
        x = 56 + i * 302
        t = T + 0.25 + i * 0.15
        b.append(rect(x, 162, 284, 158, bg, 18, "fade", t))
        b.append(rect(x + 18, 180, 32, 30, PANEL, 9, "pop", t + 0.05))
        ix, iy = x + 34, 195
        if i == 0:
            b.append(path(f"M{ix-5} {iy-6}l-6 6 6 6 M{ix+5} {iy-6}l6 6 -6 6", LILAC, 2))
        elif i == 1:
            b.append(path(f"M{ix-8} {iy+7}V{iy+1} M{ix-2} {iy+7}V{iy-4} M{ix+4} {iy+7}V{iy-7}", LILAC, 2.4))
            b.append(path(f"M{ix+8} {iy-2}l2 2 4-5", "#7EE0A4", 1.6))
        else:
            b.append(f'<circle cx="{ix-2}" cy="{iy-1}" r="6" fill="none" stroke="{LILAC}" stroke-width="2"/>')
            b.append(path(f"M{ix+3} {iy+4}l5 5", LILAC, 2.4))
        b.append(text(x + 62, 200, f"0{i+1}", 11, INK, "m", t + 0.08))
        b.append(path(f"M{x+18} 222H{x+266}", INK, 0.8, extra=' stroke-opacity=".15"'))
        b.append(text(x + 18, 248, title, 16, INK, "s", t + 0.12))
        b.append(text(x + 18, 274, desc, 14, MUTED, "b", t + 0.17))
        b.append(text(x + 18, 302, tags, 10, INK, "m", t + 0.22))
    card("focus", 1000, 344, b, "What I work on: agent systems, LLM evaluation and retrieval")


def wrap(s, n):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + [cur]


def project(idx, kind, title, desc, tags, stat, stat_label, visual, repo, dark=False, bg=PAPER, t0=0.2):
    fg, mute, line = (WHITE, PANEL_MUTED, PANEL_LINE) if dark else (INK, MUTED, LINE)
    b = [text(56, 52, f"PROJECT 0{idx} / {kind}", 13, LILAC if dark else ACCENT, "m", t0)]
    b.append(text(944, 52, f"{repo}", 12, mute, "m", t0 + 0.05, "end"))
    b.append(path("M56 72H944", line, 1))
    b.append(text(53, 128, title, 46, fg, "d", t0 + 0.15))
    for i, ln in enumerate(wrap(desc, 62)):
        b.append(text(56, 162 + i * 22, ln, 15, mute, "b", t0 + 0.25 + i * 0.05))
    x = 56
    for j, tg in enumerate(tags):
        p, w = pill(x, 236, tg, fg, "#2D2838" if dark else "#ECE9F2", t0 + 0.4 + j * 0.06)
        b.append(p)
        x += w + 8
    b.append(text(944, 148, stat, 84, fg, "d", t0 + 0.3, "end"))
    b.append(text(944, 172, stat_label, 11, mute, "m", t0 + 0.38, "end"))
    b.append(visual(fg, mute, t0 + 0.5))
    b.append(arrow(918, 236, fg, t0 + 0.6))
    card(f"project-{idx}", 1000, 282, b, f"{title}: {desc}", bg, bg if dark or bg != PAPER else LINE)


def tests_visual(fg, mute, t):
    out = []
    for k in range(80):
        r, c = divmod(k, 40)
        out.append(rect(round(642 + c * 7.6, 1), 196 + r * 9, 6, 6, "#7EE0A4", 1.5, "pop", t + k * 0.012))
    return "".join(out)


def factors_visual(fg, mute, t):
    hs = [30, 22, 34, 16, 26, 20]
    out = []
    for i, h in enumerate(hs):
        out.append(rect(670 + i * 48, 220 - h, 34, h, ACCENT if i % 2 == 0 else LILAC_2, 5, "grow", t + i * 0.08))
    return "".join(out)


def trace_visual(fg, mute, t):
    ys = [30, 26, 29, 21, 24, 17, 19, 12, 15, 9, 6]
    pts = [(644 + i * 30, 192 + y) for i, y in enumerate(ys)]
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    out = [path(d, ACCENT, 2.2, "trace", t)]
    for i, (x, y) in enumerate(pts):
        out.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{ACCENT}" class="pop" style="--t:{t+0.2*i:.2f}s"/>')
    out.append(text(644, 244, "2016", 10, mute, "m"))
    out.append(text(944, 214, "2026", 10, mute, "m", None, "end"))
    return "".join(out)


def projects():
    project(1, "AGENT SYSTEMS", "AI Coding Agent",
            "A terminal agent that retrieves repository context with file and line citations. It runs on "
            "three model providers and asks before any shell or Git operation.",
            ["PYTHON", "RAG", "GEMINI", "OPENAI", "OLLAMA"], "80", "AUTOMATED TESTS PASSING",
            tests_visual, "MehulCodr/aiagent", dark=True, bg=PANEL)
    project(2, "REAL-TIME APPS", "DevCollaborator",
            "A shared developer workspace with live task updates and @mentions. Heuristics plus Gemini "
            "estimate task complexity and match developers by fit and availability.",
            ["NODE.JS", "SOCKET.IO", "MONGODB", "GEMINI"], "6", "FACTORS FOR DEVELOPER MATCHING",
            factors_visual, "MehulCodr/devcollab-backend")
    project(3, "ADMISSIONS GUIDANCE", "JoSAA Counselling Assistant",
            "An admissions guide that cites its sources and runs Monte Carlo simulations to estimate the "
            "uncertainty in recommendations drawn from historical JoSAA cutoffs.",
            ["RAG", "FAISS", "MONTE CARLO", "PYTHON"], "521K+", "CUTOFF RECORDS, 2016–2026",
            trace_visual, "KrishBnsl/inlui", bg="#EEE9FC")


def background():
    T = 0.2
    b = [text(56, 52, "04 / BACKGROUND", 14, MUTED, "m", T)]
    b.append(text(53, 110, "Experience & education.", 44, INK, "d", T + 0.1))
    b.append(path("M66 146V392", LINE, 2))
    b.append(path("M66 146V392", ACCENT, 2, "trace", T + 0.3))
    entries = [
        (150, "JUL 2026 — PRESENT", "AI Research Engineer · Oxyzen",
         ["Built a Docker sandbox to evaluate LLMs on 50 financial",
          "due-diligence tasks with a provider-neutral pipeline. Wrote",
          "rubrics for 10 tasks; batch workflows target 52% lower cost."]),
        (300, "2024 — 2028", "B.Tech CSE · Delhi Technological University",
         ["Computer Science and Engineering, 9.79 / 10 CGPA.",
          "Python · C++ · C · Java · JavaScript"]),
    ]
    for k, (y, when, role, desc) in enumerate(entries):
        t = T + 0.5 + k * 0.5
        b.append(f'<circle cx="66" cy="{y}" r="7" fill="{PAPER}" stroke="{ACCENT}" stroke-width="2.5" class="pop" style="--t:{t:.2f}s"/>')
        b.append(text(88, y + 5, when, 12, ACCENT, "m", t))
        b.append(text(88, y + 36, role, 21, INK, "s", t + 0.08))
        for i, ln in enumerate(desc):
            b.append(text(88, y + 62 + i * 21, ln, 14, MUTED, "b", t + 0.14 + i * 0.04))

    px = 600
    b.append(rect(px, 34, 346, 372, PANEL, 22, "fade", T + 0.2))
    b.append(text(px + 24, 66, "HIGHLIGHTS", 12, LILAC, "m", T + 0.4))
    b.append(f'<g class="spin" style="transform-origin:{px+318}px 60px">'
             + path(f"M{px+318} 50V70 M{px+308} 60H{px+328} M{px+311} 53l14 14 M{px+325} 53l-14 14", LILAC, 1.6) + "</g>")
    stats = [("9.79", "CGPA / 10"), ("2000+", "LEETCODE KNIGHT"), ("1400+", "CF SPECIALIST"), ("2,989", "JEE MAIN AIR")]
    for i, (num, lab) in enumerate(stats):
        r, c = divmod(i, 2)
        x, y = px + 24 + c * 154, 88 + r * 104
        t = T + 0.6 + i * 0.12
        b.append(rect(x, y, 142, 92, "#262132", 14, "fade", t))
        b.append(text(x + 14, y + 52, num, 36, WHITE, "d", t + 0.05))
        b.append(text(x + 14, y + 76, lab, 9.5, PANEL_MUTED, "m", t + 0.1))
    for i, s in enumerate(["Selected for Amazon ML Summer School", "IEEE Vihaan 2025 hackathon finalist"]):
        t = T + 1.2 + i * 0.12
        y = 320 + i * 30
        b.append(text(px + 24, y + 6, "✦", 14, LILAC, "b", t))
        b.append(text(px + 46, y + 6, s, 14, WHITE, "b", t))
    card("background", 1000, 440, b, "Experience at Oxyzen, B.Tech at DTU, and highlights")


# ---------------------------------------------------------------- live data

def fetch_calendar(token):
    q = ("query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{"
         "totalContributions weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"l": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def stats(days):
    today = dt.date.today()
    counts = [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for d in days]
    counts = [c for c in counts if c[0] <= today]
    longest = run = 0
    for _, n in counts:
        run = run + 1 if n else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i][1] == 0:
        i -= 1  # today not counted yet
    while i >= 0 and counts[i][1]:
        cur += 1
        i -= 1
    active = sum(1 for _, n in counts if n)
    byday = defaultdict(int)
    for d, n in counts:
        byday[d.strftime("%A")] += n
    busiest = max(byday, key=byday.get) if byday else "—"
    months = defaultdict(int)
    for d, n in counts:
        months[(d.year, d.month)] += n
    keys = sorted(months)[-12:]
    return cur, longest, active, busiest, [(dt.date(y, m, 1).strftime("%b").upper(), months[(y, m)]) for y, m in keys]


def activity(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest, active, busiest, months = stats(days)
    T = 0.2
    b = [text(56, 52, "05 / ACTIVITY / LAST 12 MONTHS", 14, LILAC, "m", T)]
    b.append(text(944, 52, "LIVE GITHUB DATA", 12, LILAC, "m", None, "end"))
    b.append(text(53, 114, "Shipping, steadily.", 54, WHITE, "d", T + 0.15))
    b.append(path("M56 140H944", PANEL_LINE, 1))
    base, top = 286, 168
    for k in range(1, 4):
        y = base - k * (base - top) / 3
        b.append(path(f"M56 {y:.0f}H600", "#2E2939", 1, extra=' stroke-dasharray="4 8"'))
    mx = max([n for _, n in months] + [1])
    bw, gap = 36, 9.5
    pts = []
    for i, (lab, n) in enumerate(months):
        x = 62 + i * (bw + gap)
        h = max(6, round((base - top) * n / mx))
        hot = n == mx
        b.append(rect(round(x, 1), base - h, bw, h, ACCENT if hot else "#5B4E86", 8, "grow", T + 0.4 + i * 0.06))
        b.append(text(round(x + bw / 2, 1), base + 24, lab, 10.5, PANEL_MUTED, "m", None, "middle"))
        if hot:
            b.append(text(round(x + bw / 2, 1), base - h + 20, str(n), 12, WHITE, "m", T + 1.3, "middle"))
        pts.append((x + bw / 2, base - h))
    d = "M" + " L".join(f"{x:.1f} {y-10:.1f}" for x, y in pts)
    b.append(path(d, LILAC, 1.6, "trace", T + 0.9, ' stroke-opacity=".6"'))

    tiles = [(str(cal["totalContributions"]), "CONTRIBUTIONS"), (f"{cur}d", "CURRENT STREAK"),
             (f"{longest}d", "LONGEST STREAK"), (str(active), "ACTIVE DAYS")]
    for i, (num, lab) in enumerate(tiles):
        r, c = divmod(i, 2)
        x, y = 636 + c * 158, 160 + r * 92
        t = T + 0.6 + i * 0.12
        b.append(rect(x, y, 146, 80, "#262132", 14, "fade", t))
        b.append(text(x + 14, y + 44, num, 32, WHITE, "d", t + 0.05))
        b.append(text(x + 14, y + 66, lab, 9.5, PANEL_MUTED, "m", t + 0.1))
    b.append(path("M56 340H944", PANEL_LINE, 1))
    b.append(text(56, 372, f"BUSIEST DAY: {busiest.upper()}", 12, LILAC, "m", T + 1.4))
    b.append(text(944, 372, f"UPDATED {dt.date.today():%d %b %Y}".upper(), 12, PANEL_MUTED, "m", T + 1.4, "end"))
    card("activity", 1000, 400, b, "Monthly GitHub activity with streaks and active days", PANEL, PANEL)


def contributions(cal):
    levels = {"NONE": "#ECE9F2", "FIRST_QUARTILE": LILAC, "SECOND_QUARTILE": LILAC_2,
              "THIRD_QUARTILE": "#7559E0", "FOURTH_QUARTILE": ACCENT}
    T = 0.2
    b = [text(56, 52, "06 / CONTRIBUTION MAP", 14, INK, "m", T)]
    b.append(text(53, 108, "The purple squares.", 52, INK, "d", T + 0.15))
    b.append(text(944, 94, f"{cal['totalContributions']}", 62, INK, "d", T + 0.3, "end"))
    b.append(text(944, 114, "CONTRIBUTIONS / 365 DAYS", 11, MUTED, "m", None, "end"))
    weeks = cal["weeks"]
    x0, y0, step = 70, 146, 16.2
    last_month = None
    for wi, w in enumerate(weeks):
        x = x0 + wi * step
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last_month and first.day <= 7:
            b.append(text(round(x, 1), y0 - 8, first.strftime("%b").upper(), 9.5, MUTED, "m"))
            last_month = first.month
        for d in w["contributionDays"]:
            y = y0 + d["weekday"] * step
            b.append(rect(round(x, 1), round(y, 1), 12, 12, levels.get(d["contributionLevel"], "#ECE9F2"),
                          3, "pop", T + 0.5 + wi * 0.022 + d["weekday"] * 0.01))
    for i, lab in [(1, "M"), (3, "W"), (5, "F")]:
        b.append(text(44, y0 + i * step + 10, lab, 10, MUTED, "m"))
    lx = 944 - 5 * 16 - 80
    b.append(text(lx - 8, 288, "LESS", 10, MUTED, "m", None, "end"))
    for i, c in enumerate(levels.values()):
        b.append(rect(lx + i * 16, 278, 12, 12, c, 3))
    b.append(text(lx + 5 * 16 + 4, 288, "MORE", 10, MUTED, "m"))
    card("contributions", 1000, 318, b, "GitHub contribution calendar for the last year")


def main():
    OUT.mkdir(exist_ok=True)
    hero()
    links()
    focus()
    projects()
    background()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        cal = fetch_calendar(token)
        activity(cal)
        contributions(cal)
    else:
        print("No GITHUB_TOKEN; skipped activity and contribution cards.")


if __name__ == "__main__":
    main()
