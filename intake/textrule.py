"""The one shared text rule (evals/eval_config.yaml evidence_grading,
shared_text_rule; RT1-11): the grader (evals/), the system page reader
(agents/checker/pages.py) and the checker tool's verbatim check (D5) all
import this module, so all three see the same visible text.

Visible text: every element outside script, style, template, comments
and elements with the hidden attribute; title included; one space at
every block-element boundary, none at inline boundaries; HTML entities
decoded. normalize() runs the steps in the order the gate lists them.

Moved here unchanged from evals/check_holdout.py in P2; the text blocks,
the title and the excerpt helpers are the only additions.
"""
from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "li", "main", "nav", "ol", "p", "section", "table", "tbody", "td", "tfoot",
    "th", "thead", "title", "tr", "ul",
}
LAYOUT_TAGS = {
    "heading": {"h1", "h2", "h3", "h4", "h5", "h6"},
    "list": {"li"},
    "table": {"td", "th"},
    "p": {"p"},
}
SKIP_TAGS = {"script", "style", "template"}
# Void elements have no end tag and no text (RT2-08): a hidden one is
# dropped on its own and never opens a skip region.
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}

_SINGLE_QUOTES = (0x2018, 0x2019, 0x201A, 0x201B, 0x2039, 0x203A, 0x0060)
_DOUBLE_QUOTES = (0x201C, 0x201D, 0x201E, 0x201F, 0x00AB, 0x00BB)
_DASHES = (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212, 0xFE58, 0xFE63, 0xFF0D)
_CHAR_MAP = {c: "'" for c in _SINGLE_QUOTES} | {c: '"' for c in _DOUBLE_QUOTES} | {c: "-" for c in _DASHES}
ELLIPSIS = chr(0x2026)

# An evidence_excerpt that starts with this marker reports missing
# content instead of quoting the page (owner correction 2026-11-02).
ABSENT_MARKER = "ABSENT:"


def normalize(text: str) -> str:
    """Normalization shared with evidence grading; steps run in the order
    listed in evals/eval_config.yaml evidence_grading.normalize_steps_in_order."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = text.casefold().translate(_CHAR_MAP).replace("...", ELLIPSIS)
    return re.sub(r"\s+", " ", text).strip()


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _TextExtractor(HTMLParser):
    """All text outside script/style and comments, plus the text of each
    heading, list item, table cell and paragraph element on its own, and
    the page split into text blocks (one per block-element boundary)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.elements: dict[str, list[str]] = {k: [] for k in LAYOUT_TAGS}
        self.body_signature: list[str] = []
        self.blocks: list[str] = []
        self.title = ""
        self._block: list[str] = []
        self._in_title = False
        self._skip = 0
        self._skip_stack: list[str] = []
        self._in_body = False
        self._open: list[tuple[str, list[str]]] = []

    def _flush_block(self) -> None:
        text = _collapse("".join(self._block))
        self._block = []
        if not text:
            return
        if self._in_title:
            self.title = self.title or text
        else:
            self.blocks.append(text)

    def handle_starttag(self, tag, attrs):
        if self._skip:
            if tag == self._skip_stack[-1]:
                self._skip_stack.append(tag)
                self._skip += 1
            return
        if tag in SKIP_TAGS or any(name == "hidden" for name, _ in attrs):
            if tag in VOID_TAGS:
                return
            self._skip_stack.append(tag)
            self._skip += 1
            return
        if tag == "body":
            self._in_body = True
        elif self._in_body:
            cls = dict(attrs).get("class") or ""
            self.body_signature.append(f"{tag}.{cls}")
        if tag in BLOCK_TAGS:
            self.chunks.append(" ")
            self._flush_block()
            if tag == "title":
                self._in_title = True
        for layout, tags in LAYOUT_TAGS.items():
            if tag in tags:
                self._open.append((layout, []))

    def handle_endtag(self, tag):
        if self._skip:
            if tag == self._skip_stack[-1]:
                self._skip_stack.pop()
                self._skip -= 1
            return
        if tag in BLOCK_TAGS:
            self.chunks.append(" ")
            self._flush_block()
            if tag == "title":
                self._in_title = False
        for layout, tags in LAYOUT_TAGS.items():
            if tag in tags:
                for i in range(len(self._open) - 1, -1, -1):
                    if self._open[i][0] == layout:
                        name, buf = self._open.pop(i)
                        self.elements[name].append(normalize("".join(buf)))
                        break

    def handle_data(self, data):
        if self._skip:
            return
        self.chunks.append(data)
        self._block.append(data)
        for _, buf in self._open:
            buf.append(data)

    def close(self):
        super().close()
        self._flush_block()


def extract(html_text: str) -> _TextExtractor:
    parser = _TextExtractor()
    parser.feed(html_text)
    parser.close()
    return parser


def visible_text(html_text: str) -> str:
    return normalize("".join(extract(html_text).chunks))


def excerpt_parts(excerpt: str) -> list[str]:
    """Evidence excerpt cleanup (evidence_grading excerpt_cleanup and
    excerpt_parts): normalize, '[…]' and '(…)' count as the ellipsis,
    the excerpt is split on the ellipsis, surrounding quotation marks are
    stripped and empty parts dropped."""
    text = normalize(excerpt)
    for marker in (f"[{ELLIPSIS}]", f"({ELLIPSIS})"):
        text = text.replace(marker, ELLIPSIS)
    parts = [p.strip().strip("'\"").strip() for p in text.split(ELLIPSIS)]
    return [p for p in parts if p]


def is_absent_excerpt(excerpt: str) -> bool:
    return excerpt.strip().startswith(ABSENT_MARKER)


def excerpt_on_page(excerpt: str, page_text: str) -> bool:
    """True iff the excerpt has at least one part and every part occurs
    in the normalized visible page text (no fuzzy match)."""
    parts = excerpt_parts(excerpt)
    return bool(parts) and all(p in page_text for p in parts)
