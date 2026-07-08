"""Local-HTML-only page access, scoped to evals/dataset/pages/. Mirrors
ai-claim-verification-agent's agent/pages.py path-containment pattern
(BLUEPRINT.md §3 no-network + FI-7 path-escape rejection).
"""
from html.parser import HTMLParser
from pathlib import Path

from .config import PAGES_ROOT


class PathOutsideDatasetError(ValueError):
    pass


class _ParagraphExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.paragraphs = []
        self._in_title = False
        self._in_p = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag == "p":
            self._in_p = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "p":
            if self._buf:
                self.paragraphs.append("".join(self._buf).strip())
            self._in_p = False
            self._buf = []

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._in_p:
            self._buf.append(data)


def resolve_page_path(rel_path: str) -> Path:
    """Resolve a path relative to evals/dataset/pages/, rejecting any
    escape attempt (FI-7)."""
    candidate = (PAGES_ROOT / rel_path).resolve()
    if not candidate.is_relative_to(PAGES_ROOT):
        raise PathOutsideDatasetError(
            f"Path {rel_path!r} resolves outside evals/dataset/pages/ -- rejected."
        )
    if not candidate.exists():
        raise FileNotFoundError(f"No such file under evals/dataset/pages/: {rel_path}")
    return candidate


def read_page(rel_path: str) -> tuple[str, list[str]]:
    """Return (title, paragraphs) for an HTML file under evals/dataset/pages/."""
    path = resolve_page_path(rel_path)
    parser = _ParagraphExtractor()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.title, parser.paragraphs
