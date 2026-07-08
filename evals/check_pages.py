"""Self-check for evals/dataset/pages/*.html against the page briefs in
evals/INJECTION_SPEC.md (BLUEPRINT.md §7, Phase 1b-i). Per page, asserts:
(a) every specified verbatim string (injected violation + distractor) is
present, (b) every furniture element the brief explicitly removes is
absent, (c) the Markets footer matches the brief.

Not an answer-key derivation tool -- verdict labeling for every
(page x jurisdiction x rule) cell is a separate, later step under the
three-actor protocol in INJECTION_SPEC.md. This script only checks that
the pages were built as briefed.
"""
import html
import re
import sys
from pathlib import Path

PAGES_DIR = Path(__file__).parent / "dataset" / "pages"

FURNITURE = {
    "rg_notice": "Please gamble responsibly.",
    "age": "18+",
    "help": "Help available at GambleSupport.example",
    "gbr_tagline": "Take time to think.",
    "mlt_licence": "Licensed by the MLT Gaming Authority (MGA/EX/001/2026)",
    "gbr_licence": "Licensed by the GBR Gambling Commission (GC-EX-2026)",
    "deu_licence": "Licensed under the DEU State Treaty (DE-EX-2026)",
    "deu_deposit_limit": "A cross-operator monthly deposit limit of €1,000 applies.",
}

# Per-page expectations, derived from evals/INJECTION_SPEC.md page briefs.
# "present"/"absent" list furniture keys explicitly stated in the brief as
# present or removed; "strings" are the verbatim injection + distractor
# strings quoted in the brief.
PAGE_SPECS = {
    "p01.html": {
        "markets": "Markets: MLT, GBR",
        "present": ["rg_notice", "age", "help", "gbr_tagline", "mlt_licence"],
        "absent": ["gbr_licence"],
        "strings": [
            "100% up to €200 + 50 Free Spins",
            "35x wagering applies",
            "Minimum deposit €20",
            "Offer valid for 30 days",
            "Spins credited after first deposit",
            "Your winnings, your way.",
        ],
    },
    "p02.html": {
        "markets": "Markets: MLT, DEU",
        "present": ["rg_notice", "age", "help", "mlt_licence"],
        "absent": ["deu_licence", "deu_deposit_limit"],
        "strings": [
            "100% up to €150, 30x wagering, min €10",
            "Top-rated by players.",
        ],
    },
    "p03.html": {
        "markets": "Markets: MLT, GBR, DEU",
        "present": [
            "rg_notice", "age", "help", "gbr_tagline",
            "mlt_licence", "gbr_licence", "deu_licence", "deu_deposit_limit",
        ],
        "absent": [],
        "strings": [
            "€50 Free Bet — no deposit needed",
            "5x wagering, valid 14 days, min deposit not required.",
            "Boosted odds 3.50 on tonight's match!",
            "Offer ends soon!",
            "Bet on 200+ markets",
        ],
    },
    "p04.html": {
        "markets": "Markets: GBR",
        "present": ["rg_notice", "age", "gbr_licence"],
        "absent": ["help"],
        "strings": [
            "Zappy the Wizard — a favourite with students and streamers alike!",
            "Colourful graphics the whole community enjoys.",
        ],
    },
    "p05.html": {
        "markets": "Markets: MLT",
        "present": ["rg_notice", "age", "help", "mlt_licence"],
        "absent": [],
        "strings": [
            "Big games, every day.",
        ],
    },
    "p06.html": {
        "markets": "Markets: MLT, GBR, DEU",
        "present": [
            "rg_notice", "age", "help", "gbr_tagline",
            "mlt_licence", "gbr_licence", "deu_licence", "deu_deposit_limit",
        ],
        "absent": [],
        "strings": [
            "200% up to €300 — see terms",
            "35x wagering",
            "Risk-free first bet — refund if you lose",
            "Our editors' pick.",
        ],
    },
    "p07.html": {
        "markets": "Markets: MLT, DEU",
        "present": ["rg_notice", "age", "help", "mlt_licence"],
        "absent": ["deu_licence", "deu_deposit_limit"],
        "strings": [
            "Join our Live Roulette and Blackjack tables with real dealers, streamed 24/7.",
            "Real dealers, real time.",
        ],
    },
    "p08.html": {
        "markets": "Markets: MLT, GBR, DEU",
        "present": ["rg_notice", "age", "help"],
        "absent": [],
        "strings": [
            "Following this staking plan guarantees long-term profit.",
            "Turn betting into your side income.",
            "Improve your understanding of the odds.",
        ],
    },
    "p09.html": {
        "markets": "Markets: GBR, MLT",
        "present": ["rg_notice", "age", "help", "gbr_tagline", "gbr_licence", "mlt_licence"],
        "absent": [],
        "strings": [
            "50% up to €100, 20x wagering, min deposit €10, valid 7 days",
            "Last chance — bonus ends in 02:14:33!",
            "Don't miss our newsletter — sign up today.",
        ],
    },
    "p10.html": {
        "markets": "Markets: GBR",
        "present": ["rg_notice", "age", "help", "gbr_tagline", "gbr_licence"],
        "absent": [],
        "strings": [
            "Claim your FREE £10 bet",
            "Minimum deposit £10 required to unlock.",
            "No promo code needed.",
        ],
    },
    "p11.html": {
        "markets": "Markets: MLT, GBR",
        "present": ["rg_notice", "age", "help", "gbr_tagline", "mlt_licence", "gbr_licence"],
        "absent": [],
        "strings": [
            "Risk-Free Week: play casino all week, lose nothing — we refund net losses up to €50.",
            "Refund paid as withdrawable cash.",
        ],
    },
    "p12.html": {
        "markets": "Markets: GBR",
        "present": ["gbr_licence"],
        "absent": ["rg_notice", "age", "help", "gbr_tagline"],
        "strings": [
            "Terms apply — see full T&Cs.",
        ],
    },
}


def extract_text(raw_html: str) -> str:
    """Strip tags, decode entities, and collapse whitespace (including the
    line-wraps inside a single source paragraph) -- close enough to what a
    page-reading tool would hand an agent (the shipped verifier's
    read_page pattern)."""
    stripped = re.sub(r"<[^>]+>", " ", raw_html)
    unescaped = html.unescape(stripped)
    return re.sub(r"\s+", " ", unescaped)


def check_page(name: str, spec: dict) -> list[str]:
    path = PAGES_DIR / name
    if not path.exists():
        return [f"{name}: file missing"]
    text = extract_text(path.read_text(encoding="utf-8"))
    errors = []

    if spec["markets"] not in text:
        errors.append(f"Markets footer '{spec['markets']}' not found")

    for key in spec["present"]:
        if FURNITURE[key] not in text:
            errors.append(f"expected furniture '{key}' ({FURNITURE[key]!r}) missing")

    for key in spec["absent"]:
        if FURNITURE[key] in text:
            errors.append(f"furniture '{key}' ({FURNITURE[key]!r}) present but should be absent")

    for s in spec["strings"]:
        if s not in text:
            errors.append(f"required string not found: {s!r}")

    return errors


def main() -> int:
    total_errors = 0
    for name, spec in PAGE_SPECS.items():
        errors = check_page(name, spec)
        if errors:
            total_errors += len(errors)
            print(f"{name}: FAIL ({len(errors)} issue(s))")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"{name}: PASS")

    print()
    if total_errors:
        print(f"check_pages: FAIL -- {total_errors} issue(s) across {len(PAGE_SPECS)} pages")
        return 1
    print(f"check_pages: PASS -- all {len(PAGE_SPECS)} pages OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
