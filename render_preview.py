#!/usr/bin/env python3
"""Local preview render of this repository's GitHub page, saved as screenshot.png.

The bounty wants screenshot.png to be a capture of the repository's page on
GitHub once it is published. Until the repository is pushed, this script makes
the faithful stand-in the same way the kit's own starter capture was made:
README.md is rendered by GitHub's Markdown API, set into a frame drawn like a
GitHub repository page (header, file list, About sidebar, README box) and
screenshotted with headless Chromium at 1280 wide, 1x, light.

After the repository is published, replace screenshot.png with a real capture
of its page and this script is only a record of how the placeholder was made.

Deterministic for a fixed README.md: same input, same page, same pixels.
"""

import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OWNER = "fachruz"
REPO = "make-fun-guide"
BOUNTY_URL = "https://make.fun/bounty/bring-the-humans-02"
WIDTH = 1280
HEIGHT = 8600  # 1280 x 8600 = 11,008,000 px, under the 16,000,000 cap

CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1f2328; background: #ffffff; }
.topbar { background: #010409; color: #f0f6fc; padding: 12px 24px; display: flex;
          align-items: center; gap: 14px; font-size: 14px; }
.topbar .mark { width: 30px; height: 30px; border-radius: 50%; background: #f0f6fc;
                color: #010409; font-weight: 700; display: flex; align-items: center;
                justify-content: center; font-size: 15px; }
.topbar .search { border: 1px solid #3d444d; border-radius: 6px; color: #9198a1;
                  padding: 4px 10px; width: 300px; }
.repohead { background: #f6f8fa; border-bottom: 1px solid #d1d9e0; padding: 14px 24px 0; }
.reponame { font-size: 20px; color: #0969da; }
.reponame b { font-weight: 600; }
.chip { border: 1px solid #d1d9e0; border-radius: 999px; color: #59636e; font-size: 12px;
        padding: 1px 8px; margin-left: 8px; vertical-align: 3px; }
.tabs { margin-top: 12px; font-size: 14px; color: #1f2328; display: flex; gap: 18px; }
.tabs span { padding: 6px 2px; }
.tabs .on { border-bottom: 2px solid #fd8c73; font-weight: 600; }
.wrap { display: flex; gap: 24px; padding: 20px 24px; max-width: 1280px; }
.main { flex: 1; min-width: 0; }
.side { width: 296px; flex: none; }
.filebox, .readmebox { border: 1px solid #d1d9e0; border-radius: 6px; }
.filebox .row, .readmebox .head { background: #f6f8fa; padding: 8px 16px; font-size: 14px;
                                 border-bottom: 1px solid #d1d9e0; }
.filebox table { width: 100%; border-collapse: collapse; font-size: 14px; }
.filebox td { padding: 7px 16px; border-top: 1px solid #eef1f4; }
.filebox td:last-child { color: #59636e; text-align: right; }
.readmebox { margin-top: 20px; }
.readmebox .body { padding: 24px 32px 32px; }
.side h3 { font-size: 14px; margin: 0 0 8px; }
.side p { font-size: 14px; line-height: 1.5; margin: 6px 0; }
.side a { color: #0969da; text-decoration: none; font-size: 14px; }
.topic { display: inline-block; background: #ddf4ff; color: #0969da; border-radius: 999px;
         font-size: 12px; padding: 2px 10px; margin-top: 6px; }
.markdown-body { font-size: 16px; line-height: 1.6; word-wrap: break-word; }
.markdown-body h1 { font-size: 2em; border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; }
.markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; }
.markdown-body h3 { font-size: 1.25em; }
.markdown-body a { color: #0969da; text-decoration: none; }
.markdown-body img { max-width: 100%; }
.markdown-body blockquote { border-left: 4px solid #0969da; background: #ddf4ff;
  margin: 16px 0; padding: 12px 18px; color: #1f2328; }
.markdown-body blockquote h2 { border: none; margin-top: 4px; }
.markdown-body code { background: #eff1f3; border-radius: 6px; padding: .2em .4em;
  font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 85%; }
.markdown-body pre { background: #f6f8fa; border-radius: 6px; padding: 16px; overflow: auto; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body table { border-collapse: collapse; display: block; overflow: auto; }
.markdown-body th, .markdown-body td { border: 1px solid #d1d9e0; padding: 6px 13px; }
.markdown-body tr:nth-child(2n) { background: #f6f8fa; }
.markdown-body details { margin: 10px 0; }
.markdown-body hr { border: none; border-top: 1px solid #d1d9e0; margin: 24px 0; }
"""

FRAME = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body>
<div class="topbar"><div class="mark">GH</div><div class="search">Type / to search</div>
<div>Pull requests</div><div>Issues</div><div>Codespaces</div><div>Marketplace</div></div>
<div class="repohead">
  <div class="reponame">{owner} / <b>{repo}</b><span class="chip">Public</span></div>
  <div class="tabs"><span class="on">Code</span><span>Issues</span><span>Pull requests</span>
  <span>Actions</span><span>Projects</span><span>Security</span><span>Insights</span></div>
</div>
<div class="wrap">
  <div class="main">
    <div class="filebox">
      <div class="row"><b>{owner}</b> — Getting started with make.fun: a guide for newcomers</div>
      <table>
        <tr><td>LICENSE</td><td>MIT license</td></tr>
        <tr><td>README.md</td><td>Guide: getting started with make.fun</td></tr>
        <tr><td>screenshot.png</td><td>This page, captured</td></tr>
      </table>
    </div>
    <div class="readmebox">
      <div class="head">README.md</div>
      <div class="body"><article class="markdown-body">{readme}</article></div>
    </div>
  </div>
  <div class="side">
    <h3>About</h3>
    <p>A getting-started guide to make.fun: put your AI coding agent to work in
       build competitions, step by step.</p>
    <p><a href="{bounty}">{bounty}</a></p>
    <span class="topic">makefun</span>
  </div>
</div>
</body></html>"""


def render_readme(md_text: str) -> str:
    payload = json.dumps(
        {"text": md_text, "mode": "gfm", "context": f"{OWNER}/{REPO}"}
    ).encode()
    req = urllib.request.Request(
        "https://api.github.com/markdown",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "makefun-guide-preview"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read().decode()


def badge_svg(left: str, right: str, color: str = "#0969da") -> str:
    """A shields-style badge drawn locally, as the kit's starter capture drew
    them: the live badge route is only pictured here, never fetched."""
    lw = 7 * len(left) + 12
    rw = 7 * len(right) + 12
    w = lw + rw
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20">'
        f'<rect width="{lw}" height="20" fill="#555"/>'
        f'<rect x="{lw}" width="{rw}" height="20" fill="{color}"/>'
        f'<text x="{lw / 2}" y="14" fill="#fff" font-family="Verdana" '
        f'font-size="11" text-anchor="middle">{left}</text>'
        f'<text x="{lw + rw / 2}" y="14" fill="#fff" font-family="Verdana" '
        f'font-size="11" text-anchor="middle">{right}</text></svg>'
    )
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)


def local_badges(html: str) -> str:
    """Swap the three live make.fun badge images for locally drawn ones, so
    the preview shows the finished page (on GitHub the real badges load).
    GitHub's renderer routes the images through camo.githubusercontent.com
    with the original URL hex-encoded in the path; decode it to match."""
    swaps = {
        "https://make.fun/badge/bring-the-humans-02.svg":
            badge_svg("make.fun", "bring-the-humans-02"),
        f"https://make.fun/badge/bring-the-humans-02/{OWNER}/{REPO}/rank.svg":
            badge_svg("rank", "pending"),
        f"https://make.fun/badge/bring-the-humans-02/{OWNER}/{REPO}/reward.svg":
            badge_svg("reward", "$1,000 USDC", "#1a7f37"),
    }

    def swap(match: "re.Match[str]") -> str:
        url = bytes.fromhex(match.group(1)).decode()
        return f'src="{swaps.get(url, match.group(0))}"'

    return re.sub(r'src="https://camo\.githubusercontent\.com/[0-9a-f]+/([0-9a-f]+)"',
                  swap, html)


def main() -> int:
    md_text = (ROOT / "README.md").read_text()
    readme_html = local_badges(render_readme(md_text))
    html = FRAME.format(css=CSS, readme=readme_html, owner=OWNER, repo=REPO,
                        bounty=BOUNTY_URL)
    frame_path = Path("/tmp/bth02-frame.html")
    frame_path.write_text(html)
    raw_path = Path("/tmp/bth02-raw.png")
    chrome = next(Path.home().glob(
        ".cache/ms-playwright/chromium_headless_shell-*/"
        "chrome-headless-shell-linux64/chrome-headless-shell"))
    subprocess.run(
        [str(chrome), "--headless", "--disable-gpu", "--no-sandbox",
         "--hide-scrollbars", f"--window-size={WIDTH},{HEIGHT}",
         f"--screenshot={raw_path}", frame_path.as_uri()],
        check=True, capture_output=True, timeout=180)
    img = Image.open(raw_path).convert("RGB")
    # Crop trailing blank rows (page background is white below the frame).
    px = img.load()
    last = img.height - 1
    while last > 0 and all(px[x, last] == (255, 255, 255)
                           for x in range(0, img.width, 16)):
        last -= 1
    img = img.crop((0, 0, img.width, min(img.height, last + 41)))
    out = ROOT / "screenshot.png"
    img.save(out, optimize=True)
    print(f"wrote {out}: {img.width}x{img.height} "
          f"({img.width * img.height} px), {out.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
