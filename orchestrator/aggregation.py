"""Deterministic severity aggregation (BLUEPRINT.md §2 step 4, §3):
collects findings per page and ranks pages by a severity score computed
strictly from rule metadata (each ComplianceRule's severity class) --
never decided by a model. No LLM calls originate here.
"""
from __future__ import annotations

from contracts.schemas import AdjudicationRecord, ComplianceRule, SeverityReport, Verdict, ViolationFinding

SEVERITY_WEIGHTS = {"CRITICAL": 3, "MAJOR": 2, "MINOR": 1}


def compute_severity_score(
    findings: list[ViolationFinding], rules_by_id: dict[str, ComplianceRule]
) -> float:
    """Sum of SEVERITY_WEIGHTS over this page's VIOLATION findings, using
    only the severity class each finding's own rule carries in the
    versioned rule set -- no judgment call, no model in the loop.
    """
    score = 0.0
    for finding in findings:
        if finding.verdict != Verdict.VIOLATION:
            continue
        rule = rules_by_id.get(finding.rule_id)
        if rule is not None:
            score += SEVERITY_WEIGHTS[rule.severity.value]
    return score


def build_severity_reports(
    findings_by_page: dict[str, list[ViolationFinding]],
    rules_by_id: dict[str, ComplianceRule],
) -> list[SeverityReport]:
    """One SeverityReport per page, ranked by descending severity_score
    (rank 1 = most severe). computed_from lists the distinct
    ruleset_versions actually represented in that page's findings, so a
    gap (a jurisdiction that never completed, e.g. FI-4) is visible by
    its absence rather than silently implied as compliant.
    """
    reports = []
    for page_path, findings in findings_by_page.items():
        score = compute_severity_score(findings, rules_by_id)
        computed_from = sorted({f.ruleset_version for f in findings})
        reports.append(
            SeverityReport(
                page_path=page_path,
                findings=findings,
                severity_score=score,
                rank=0,
                computed_from=computed_from,
            )
        )

    reports.sort(key=lambda r: r.severity_score, reverse=True)
    for i, report in enumerate(reports, start=1):
        report.rank = i
    return reports


def build_adjudication_report(records: list[AdjudicationRecord]) -> dict[str, list[AdjudicationRecord]]:
    """Deterministic three-way split of adjudication records (policy/
    ADJUDICATION_POLICY.md §5): CONFIRMED findings are the system's
    assertions; DISPUTED findings are surfaced in their own section,
    never as an assertion; REJECTED findings are excluded from both --
    present in the ledger (and this report, for transparency) but never
    scored or asserted.
    """
    return {
        "confirmed": [r for r in records if r.verdict.value == "CONFIRMED"],
        "disputed": [r for r in records if r.verdict.value == "DISPUTED"],
        "rejected": [r for r in records if r.verdict.value == "REJECTED"],
    }
