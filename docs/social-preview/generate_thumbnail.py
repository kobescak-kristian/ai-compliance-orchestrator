#!/usr/bin/env python3
"""
LinkedIn post thumbnail — ai-compliance-orchestrator publication announcement.
1200x627, design system mirrored from kobescak-kristian.github.io :root
palette and the site's dark failure-callout block (.failure / .contact).

Fonts (not committed; fetch before running):
  Bricolage Grotesque (variable) + IBM Plex Mono, from
  https://github.com/google/fonts (ofl/bricolagegrotesque, ofl/ibmplexmono)
  into ./fonts/

Every number and label binds to published tables:
  gate thresholds 0.95/0.90 -> ai-compliance-orchestrator evals config
  run id gate-9328e564      -> evals/EVAL_RESULTS.md
Usage: python generate_thumbnail.py [out.png]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 627

# --- site palette (kobescak-kristian.github.io :root) ---
DARK      = "#10201A"   # --dark
DARK_2    = "#16291F"   # --dark-2
DARK_INK  = "#DFE9E2"   # --dark-ink
DARK_MUT  = "#8FA79A"   # --dark-muted
DARK_RULE = "#24382E"   # --dark-rule
AMBER     = "#E5B96B"   # site failure-block accent
STAMP_BR  = "#0E8563"   # --stamp-bright

FDIR = "fonts/"

def brico(size, wght=800):
    f = ImageFont.truetype(FDIR + "BricolageGrotesque.ttf", size)
    try:
        f.set_variation_by_axes([14, 100, wght])  # opsz, wdth, wght
    except Exception:
        pass
    return f

def mono(size, medium=False):
    name = "IBMPlexMono-Medium.ttf" if medium else "IBMPlexMono-Regular.ttf"
    return ImageFont.truetype(FDIR + name, size)

img = Image.new("RGB", (W, H), DARK)
d = ImageDraw.Draw(img)

# subtle grid, mirroring .contact::before (56px cells, low opacity)
grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(grid)
for x in range(0, W, 56):
    gd.line([(x, 0), (x, H)], fill=DARK_RULE, width=1)
for y in range(0, H, 56):
    gd.line([(0, y), (W, y)], fill=DARK_RULE, width=1)
grid.putalpha(grid.split()[3].point(lambda a: int(a * 0.45)))
img = Image.alpha_composite(img.convert("RGBA"), grid)
d = ImageDraw.Draw(img)

M = 84  # left margin

# --- stamp label (site .st pattern: mono, letterspaced, bordered, -1.5deg) ---
label = "G A T E   F A I L E D   ·   P U B L I S H E D   A S - I S"
lf = mono(21, medium=True)
lw = d.textlength(label, font=lf)
pad_x, pad_y = 18, 12
stamp = Image.new("RGBA", (int(lw) + 2 * pad_x + 6, 21 + 2 * pad_y + 8), (0, 0, 0, 0))
sd = ImageDraw.Draw(stamp)
sd.rounded_rectangle(
    [0, 0, stamp.width - 3, stamp.height - 3],
    radius=6, outline=AMBER, width=2)
sd.text((pad_x, pad_y - 2), label, font=lf, fill=AMBER)
stamp = stamp.rotate(1.5, expand=True, resample=Image.BICUBIC)
img.alpha_composite(stamp, (M, 74))
d = ImageDraw.Draw(img)

# --- headline (Bricolage 800, site h1 treatment) ---
h1a = "The system that"
h1b = "failed its own test."
hf = brico(88, 800)
d.text((M, 188), h1a, font=hf, fill=DARK_INK)
d.text((M, 288), h1b, font=hf, fill=DARK_INK)

# thin amber underline under "failed" (site .u highlight gesture)
fw = d.textlength("failed", font=hf)
d.rectangle([M, 288 + 96, M + fw, 288 + 102], fill=AMBER)

# --- evidence lines (mono, bind to published tables) ---
d.text((M, 442), "pre-committed gate  P >= 0.95 · R >= 0.90   |   official run gate-9328e564",
       font=mono(22), fill=DARK_MUT)
d.text((M, 478), "published as-is · thresholds untouched · synthetic rule sets",
       font=mono(22), fill=DARK_MUT)

# --- footer rule + repo path with brand dot ---
d.line([(M, 524), (W - M, 524)], fill=DARK_RULE, width=2)
d.rounded_rectangle([M, 552, M + 16, 568], radius=4, fill=STAMP_BR)
d.text((M + 30, 548), "github.com/kobescak-kristian/ai-compliance-orchestrator",
       font=mono(23, medium=True), fill=DARK_INK)

out = sys.argv[1] if len(sys.argv) > 1 else "orchestrator-flip-post-thumb.png"
img.convert("RGB").save(out, "PNG")
print(f"written {out} ({W}x{H})")
