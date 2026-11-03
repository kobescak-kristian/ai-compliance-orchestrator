"""Local-HTML-only page access, scoped to one cage root (default
evals/dataset/pages/). Mirrors ai-claim-verification-agent's
agent/pages.py path-containment pattern (BLUEPRINT.md §3 no-network +
FI-7 path-escape rejection).

The page text follows the shared text rule (intake/textrule.py, RT1-11):
headings, list items, table cells and every other block are kept (D1).

For a private holdout the runner switches the cage root to the holdout's
pages and sets an alias map, so agents see neutral page names and never a
case ID (evals/eval_config.yaml holdout_markers). Pages are never copied.
Error messages never name the cage root.
"""
from pathlib import Path

from intake.textrule import extract, normalize

from .config import PAGES_ROOT


class PathOutsideDatasetError(ValueError):
    pass


_cage_root: Path = PAGES_ROOT
# {neutral name shown to agents: real file name under the cage root}.
# Empty means no aliasing: names resolve directly under the cage root.
_aliases: dict[str, str] = {}


def configure_cage(root: Path, aliases: dict[str, str] | None = None) -> None:
    """Switch the cage root (and optionally the alias map) for a run."""
    global _cage_root, _aliases
    _cage_root = Path(root).resolve()
    _aliases = dict(aliases or {})


def reset_cage() -> None:
    global _cage_root, _aliases
    _cage_root = PAGES_ROOT
    _aliases = {}


def _outside(rel_path: str) -> PathOutsideDatasetError:
    return PathOutsideDatasetError(f"Path {rel_path!r} resolves outside the page cage -- rejected.")


def resolve_page_path(rel_path: str) -> Path:
    """Resolve a page name inside the cage root, rejecting any escape
    attempt (FI-7). With an alias map set, only alias names resolve."""
    if "\\" in rel_path:
        # Backslash is a path separator on Windows but a literal
        # filename character on POSIX -- the same string escapes on
        # one OS and not the other. The cage treats it as a separator
        # everywhere, so the bound is OS-independent (design decision
        # 2026-07-24, ported from ai-claim-verification-agent commit
        # c3633e6).
        raise _outside(rel_path)
    if _aliases:
        if rel_path not in _aliases:
            raise FileNotFoundError(f"No such page in the page cage: {rel_path}")
        rel_path_on_disk = _aliases[rel_path]
    else:
        rel_path_on_disk = rel_path
    candidate = (_cage_root / rel_path_on_disk).resolve()
    if not candidate.is_relative_to(_cage_root):
        raise _outside(rel_path)
    if not candidate.is_file():
        raise FileNotFoundError(f"No such page in the page cage: {rel_path}")
    return candidate


def read_page(rel_path: str) -> tuple[str, list[str]]:
    """Return (title, text blocks) for a page in the cage, one block per
    block-element boundary (shared text rule)."""
    parsed = extract(resolve_page_path(rel_path).read_text(encoding="utf-8"))
    return parsed.title, list(parsed.blocks)


def read_visible_text(rel_path: str) -> str:
    """Normalized visible text of a page in the cage (shared text rule)."""
    parsed = extract(resolve_page_path(rel_path).read_text(encoding="utf-8"))
    return normalize("".join(parsed.chunks))
