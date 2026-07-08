"""Pydantic v2 handoff contracts (BLUEPRINT.md §5): ComplianceRule,
CheckTask, ViolationFinding, AccuracyFinding, SeverityReport,
RemediationProposal, and the ledger row schema. Enforced at every
orchestrator boundary; a payload that fails validation is rejected into
a dead-letter table, never silently coerced or dropped -- so every model
here forbids extra fields.

Frozen before any agent code exists (Phase 1a, BLUEPRINT.md §9).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base for every contract: unknown fields are a schema violation,
    not a thing to silently coerce or drop (BLUEPRINT.md §3).
    """

    model_config = ConfigDict(extra="forbid")


class RuleCategory(str, Enum):
    BONUS_TERMS = "BONUS_TERMS"
    RG_MESSAGING = "RG_MESSAGING"
    PROHIBITED_CLAIMS = "PROHIBITED_CLAIMS"
    GEO_ELIGIBILITY = "GEO_ELIGIBILITY"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Verdict(str, Enum):
    COMPLIANT = "COMPLIANT"
    VIOLATION = "VIOLATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AccuracyVerdict(str, Enum):
    """Verbatim from ai-claim-verification-agent's log_finding tool
    (its `verdict` argument, VALID_VERDICTS in agent/tools.py).
    """

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIABLE = "UNVERIFIABLE"


class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class AdjudicationVerdict(str, Enum):
    """The verifier's three adjudication verdicts (policy/ADJUDICATION_
    POLICY.md §3). Maps from the shipped agent's native verdict schema
    per policy §14: SUPPORTED -> CONFIRMED, CONTRADICTED -> REJECTED,
    UNVERIFIABLE -> DISPUTED.
    """

    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class TaskState(str, Enum):
    """Terminal-state machine (BLUEPRINT.md §3): QUEUED -> RUNNING ->
    DONE | FAILED | DEAD_LETTER | ESCALATED.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"
    ESCALATED = "ESCALATED"


class ComplianceRule(StrictModel):
    jurisdiction: str
    rule_id: str
    category: RuleCategory
    severity: Severity
    rule_text: str
    ruleset_version: str


class CheckTask(StrictModel):
    page_path: str
    jurisdiction: str
    ruleset_version: str
    assigned_rules: list[str] = Field(default_factory=list)


class ViolationFinding(StrictModel):
    page_path: str
    jurisdiction: str
    rule_id: str
    ruleset_version: str
    verdict: Verdict
    evidence_excerpt: str
    rationale: str
    task_id: str


class AccuracyFinding(StrictModel):
    """Reuses the shipped verifier's existing verdict schema verbatim
    (claim, verdict, source, evidence) plus task linkage -- the contract
    adapts to the shipped agent, not the other way around
    (BLUEPRINT.md §5).

    Superseded by AdjudicationRecord as of Phase 4 (policy/ADJUDICATION_
    POLICY.md): the verifier adjudicates checker VIOLATION findings
    rather than running as an independent 4th checker. Retained,
    unused, as the Phase 2/3 scaffolding record of that earlier design.
    """

    claim: str
    verdict: AccuracyVerdict
    source: str
    evidence: str
    task_id: str


class AdjudicationRecord(StrictModel):
    """The verifier's ruling on one VIOLATION finding (policy/
    ADJUDICATION_POLICY.md §3, §6). Every verdict -- CONFIRMED, REJECTED,
    or DISPUTED -- writes one of these; rows are retained forever, never
    overwritten (a finding's assertion status changes only through an
    adjudication row).
    """

    finding_id: str
    verdict: AdjudicationVerdict
    citation: str
    model: str
    timestamp: datetime
    run_id: str


class SeverityReport(StrictModel):
    page_path: str
    findings: list[ViolationFinding | AccuracyFinding] = Field(default_factory=list)
    severity_score: float
    rank: int
    computed_from: list[str] = Field(default_factory=list)


class RemediationProposal(StrictModel):
    page_path: str
    rule_id: str
    offending_text: str
    proposed_text: str
    evidence_refs: list[str] = Field(default_factory=list)
    status: ProposalStatus = ProposalStatus.PENDING
    created_by_run_id: str


class LedgerRow(StrictModel):
    """Every task, every stage (BLUEPRINT.md §5). Mirrors the
    orchestrator/ledger.py task_ledger table column-for-column.
    """

    task_id: str
    stage: str
    state: TaskState
    attempt: int
    started_at: datetime | None = None
    ended_at: datetime | None = None
    exit_code: int | None = None
    error_class: str | None = None
    payload_ref: str | None = None
