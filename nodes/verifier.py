"""Subprocess wrapper around the shipped ai-claim-verification-agent, run
as the adjudicator over checker VIOLATION findings (policy/
ADJUDICATION_POLICY.md, superseding the earlier "4th checker" framing in
BLUEPRINT.md §2 step 3 -- see BLUEPRINT.md's Phase 4 amendment note).

Assembles one case per finding (nodes/assembler.py), writes it into the
shipped repo's evals/dataset/ (the only path its own harness can read
from -- REPO_ROOT-relative inside that repo, not configurable from here),
invokes the shipped agent unmodified via nodes/verifier_runner.py as a
subprocess, parses/validates its JSON output at the boundary into an
AdjudicationRecord, and always removes the case directory afterward --
the shipped repo's working tree is checked clean before and after every
run (tests/test_bounds.py::test_verifier_cage, Phase 4 dev-leg report).

Implemented Phase 4, replacing its stub from Phase 2 (BLUEPRINT.md §9).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from contracts.schemas import AdjudicationRecord, AdjudicationVerdict, ComplianceRule, ViolationFinding
from nodes.assembler import assemble_case
from orchestrator.pipeline import VerifierInvocationError, finding_id_for

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
RUNNER_SCRIPT = REPO_ROOT / "nodes" / "verifier_runner.py"

# Policy §14: the shipped agent's native verdict schema maps onto this
# policy's three adjudication verdicts. Fixed, not configurable per run.
_VERDICT_MAP = {
    "SUPPORTED": AdjudicationVerdict.CONFIRMED,
    "CONTRADICTED": AdjudicationVerdict.REJECTED,
    "UNVERIFIABLE": AdjudicationVerdict.DISPUTED,
}


class VerifierConfigError(VerifierInvocationError):
    """config.yaml missing/malformed, or the shipped repo's actual HEAD
    does not match pinned_commit (policy §12) -- fails loudly rather
    than silently drifting onto an unpinned version of the shipped
    code. A VerifierInvocationError subclass so run_verify_stage's
    single except clause maps both to the same task-atomic FAILED.
    """


def load_verifier_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["verifier_agent"]


def _check_pinned_commit(repo_path: Path, pinned_commit: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise VerifierConfigError(f"could not read HEAD of shipped repo at {repo_path}: {result.stderr.strip()}")
    actual = result.stdout.strip()
    if actual != pinned_commit:
        raise VerifierConfigError(
            f"shipped repo HEAD {actual!r} does not match pinned_commit {pinned_commit!r} in config.yaml -- "
            "refusing to run against an unpinned version of the shipped agent"
        )


def _write_case_files(case_dir: Path, files: dict[str, str]) -> None:
    case_dir.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (case_dir / name).write_text(content, encoding="utf-8")


def verify_finding(
    finding: ViolationFinding,
    rule: ComplianceRule,
    run_id: str,
    *,
    model: str | None = None,
    config: dict | None = None,
) -> AdjudicationRecord:
    """Adjudicate one VIOLATION finding through the shipped agent,
    unmodified, as a subprocess. Raises VerifierConfigError /
    VerifierInvocationError on any failure -- there is no partial or
    silently-degraded result.
    """
    config = config or load_verifier_config()
    repo_path = Path(config["repo_path"]).resolve()
    _check_pinned_commit(repo_path, config["pinned_commit"])

    model = model or config["models"]["dev"]
    max_budget_usd = config["max_budget_usd"]["dev"]

    case_id = f"phase4_adj_{uuid.uuid4().hex[:12]}"
    case_dir = repo_path / "evals" / "dataset" / case_id

    try:
        files = assemble_case(finding, rule)
        _write_case_files(case_dir, files)

        result = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT), str(repo_path), case_id, run_id, model, str(max_budget_usd)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise VerifierInvocationError(
                f"verifier subprocess exited {result.returncode} for finding "
                f"{finding_id_for(finding)}: {result.stderr.strip()}"
            )

        try:
            payload = json.loads(result.stdout)
            raw_findings = payload["findings"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise VerifierInvocationError(
                f"verifier subprocess produced schema-invalid output for finding "
                f"{finding_id_for(finding)}: {exc}"
            ) from exc

        if len(raw_findings) != 1:
            raise VerifierInvocationError(
                f"verifier subprocess returned {len(raw_findings)} findings for finding "
                f"{finding_id_for(finding)}, expected exactly 1"
            )

        raw = raw_findings[0]
        try:
            shipped_verdict = raw["verdict"]
            evidence_source = raw["evidence_source"]
            evidence_note = raw["evidence_note"]
        except KeyError as exc:
            raise VerifierInvocationError(
                f"verifier subprocess output missing required field for finding "
                f"{finding_id_for(finding)}: {exc}"
            ) from exc

        if shipped_verdict not in _VERDICT_MAP:
            raise VerifierInvocationError(
                f"verifier subprocess returned unknown verdict {shipped_verdict!r} for finding "
                f"{finding_id_for(finding)}"
            )

        return AdjudicationRecord(
            finding_id=finding_id_for(finding),
            verdict=_VERDICT_MAP[shipped_verdict],
            citation=f"{evidence_source}: {evidence_note}",
            model=model,
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
        )
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
