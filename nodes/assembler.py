"""Converts one checker VIOLATION finding into the shipped
ai-claim-verification-agent's native case format (target.html + source
pages) -- the contract adapts to the shipped agent, not the other way
around (BLUEPRINT.md §5; policy/ADJUDICATION_POLICY.md §12, §14).

Deliberately blind, per policy §2: the assembled case carries no answer-
key markers, no checker rationale/transcript, and no sibling findings --
only the rule text and a fresh read of the page, which is everything a
verifier re-deriving the claim from scratch needs and nothing more.
"""
from __future__ import annotations

from agents.checker.pages import read_page
from contracts.schemas import ComplianceRule, ViolationFinding


def build_claim_text(finding: ViolationFinding, rule: ComplianceRule) -> str:
    """The claim the shipped agent is asked to SUPPORT / CONTRADICT /
    call UNVERIFIABLE (policy §14): a positive assertion that the page
    violates the rule on the cited evidence.
    """
    return (
        f'{finding.page_path} violates rule {rule.rule_id} on evidence: '
        f'"{finding.evidence_excerpt}"'
    )


def _html_page(title: str, paragraphs: list[str]) -> str:
    body = "\n".join(f"<p>{p}</p>" for p in paragraphs)
    return f"<html><head><title>{title}</title></head><body>\n{body}\n</body></html>"


def assemble_case(finding: ViolationFinding, rule: ComplianceRule) -> dict[str, str]:
    """Return {relative_filename: html_content} for exactly one case
    directory under the shipped repo's evals/dataset/: one target.html
    (the claim, as its sole paragraph) and two source pages -- the rule
    text alone, and a fresh read of the checked page (never the
    checker's own evidence_excerpt/rationale, never other findings).
    """
    claim = build_claim_text(finding, rule)
    target_html = _html_page(f"Adjudication claim: {finding.rule_id}", [claim])

    rule_source_html = _html_page(
        f"Rule {rule.rule_id} ({rule.jurisdiction})", [rule.rule_text]
    )

    _page_title, page_paragraphs = read_page(finding.page_path)
    page_source_html = _html_page(finding.page_path, page_paragraphs)

    return {
        "target.html": target_html,
        "source_rule.html": rule_source_html,
        "source_page.html": page_source_html,
    }
