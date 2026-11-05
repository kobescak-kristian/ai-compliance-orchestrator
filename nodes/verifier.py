"""Subprocess wrapper around the shipped ai-claim-verification-agent, run
as the adjudicator over checker VIOLATION findings (policy/
ADJUDICATION_POLICY.md, superseding the earlier "4th checker" framing in
BLUEPRINT.md §2 step 3 -- see BLUEPRINT.md's Phase 4 amendment note).

Assembles one case per finding (nodes/assembler.py), writes it into the
shipped repo's evals/dataset/ by default, or into a private case_root
outside every Git repository, which nodes/verifier_runner.py points the
shipped agent's DATASET_ROOT at (P3; the shipped code is not changed),
invokes the shipped agent unmodified via nodes/verifier_runner.py as a
subprocess, parses/validates its JSON output at the boundary into an
AdjudicationRecord, and always removes the case directory afterward --
the shipped repo's working tree is checked clean before and after every
run (tests/test_bounds.py::test_verifier_cage, Phase 4 dev-leg report).

Implemented Phase 4, replacing its stub from Phase 2 (BLUEPRINT.md §9).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agents.outcome import SUBSCRIPTION_LIMIT_RE
from contracts.schemas import AdjudicationVerdict, ComplianceRule, ViolationFinding
from intake.local_config import load_local_config
from nodes.assembler import assemble_case
from orchestrator.pipeline import ProviderError, VerifierInvocationError, finding_id_for

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
RUNNER_SCRIPT = REPO_ROOT / "nodes" / "verifier_runner.py"

# D3: a machine-specific verifier checkout (the dedicated pinned clone)
# comes from this env var, else from config.local.yaml, else config.yaml.
REPO_PATH_ENV = "VERIFIER_REPO_PATH"
# D3: when set, the subprocess writes the shipped agent's audit DB here
# instead of inside the verifier checkout (nodes/verifier_runner.py).
AUDIT_DB_ENV = "VERIFIER_AUDIT_DB"
# P3: when set, the subprocess reads its case files from this private
# folder instead of <checkout>/evals/dataset (nodes/verifier_runner.py).
DATASET_ROOT_ENV = "VERIFIER_DATASET_ROOT"
TIMEOUT_S = 600  # D6: wall-clock cap per verifier subprocess
# Decision D1 (2026-11-03): agent sessions run on the
# subscription login only. These variables would make the CLI use API
# billing or a cloud provider instead, so the subprocess never gets them
# and evals/run_eval.py --real refuses to start while one is set.
NON_SUBSCRIPTION_AUTH_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
)
PROVIDER_STATUS_CODES = {401, 403, 429, 529}
_API_STATUS_RE = re.compile(r"api_error_status=(\d+)")
# R2: a budget stop, as verifier_runner reports it (the SDK's error text
# on the exception path, the result subtype on the is_error path).
BUDGET_STOP_RE = re.compile(r"Reached maximum budget|error_max_budget_usd")

# Populated by every verify_finding() call: {finding_id, cost_usd,
# num_turns} -- for dev/eval-leg cost+turns reporting only (BLUEPRINT.md
# §7), never part of the strict AdjudicationRecord contract. Mirrors
# agents/checker/harness.py's last_result convention. R2 (ruling
# 2026-11-03, option B): a budget stop has no result, so its row is
# {finding_id, cost_usd: None, cost_usd_estimated: <the budget cap>,
# num_turns: None}; the cap is an estimated notional cost, not a measured
# value or a guaranteed upper bound, and no turn count is invented.
run_stats: list[dict] = []


def reset_run_stats() -> None:
    run_stats.clear()

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


def resolve_repo_path(config: dict) -> Path:
    override = os.environ.get(REPO_PATH_ENV) or load_local_config().get("verifier_repo_path")
    path = Path(override or config["repo_path"])
    # A relative path is relative to this repo, never to the working
    # directory (real runs execute in the private run directory, P3).
    return (path if path.is_absolute() else REPO_ROOT / path).resolve()


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


def _check_clean_tree(repo_path: Path) -> None:
    """D3: the shipped checkout must have no local change at all."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise VerifierConfigError(f"could not read git status of shipped repo: {result.stderr.strip()}")
    if result.stdout.strip():
        raise VerifierConfigError(
            "shipped repo working tree is not clean -- refusing to run against a modified checkout"
        )


def check_verifier_checkout(config: dict | None = None) -> Path:
    """Pin and clean-tree check (D3); also the runner's real-mode
    preflight. Returns the resolved checkout path."""
    config = config or load_verifier_config()
    repo_path = resolve_repo_path(config)
    _check_pinned_commit(repo_path, config["pinned_commit"])
    _check_clean_tree(repo_path)
    return repo_path


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
    max_budget_usd: float | None = None,
    config: dict | None = None,
    audit_db_path: str | Path | None = None,
    case_root: str | Path | None = None,
) -> dict:
    """Adjudicate one VIOLATION finding through the shipped agent,
    unmodified, as a subprocess. Returns a raw dict -- signature-
    compatible with nodes.verifier_stub.stub_verifier -- that
    orchestrator.pipeline.run_verify_stage validates into an
    AdjudicationRecord at the boundary (same real-agent-returns-raw-
    dict / orchestrator-validates convention as agents.checker.harness.
    real_checker). Raises VerifierConfigError / VerifierInvocationError
    on any failure -- there is no partial or silently-degraded result.
    audit_db_path, when given, redirects the shipped agent's audit DB
    out of its checkout (D3); case_root, when given, does the same for
    the case files, which hold the page text (P3).
    """
    config = config or load_verifier_config()
    repo_path = check_verifier_checkout(config)

    model = model or config["models"]["dev"]
    max_budget_usd = max_budget_usd if max_budget_usd is not None else config["max_budget_usd"]["dev"]

    case_id = f"phase4_adj_{uuid.uuid4().hex[:12]}"
    dataset_root = Path(case_root).resolve() if case_root is not None else repo_path / "evals" / "dataset"
    case_dir = dataset_root / case_id

    try:
        env = {k: v for k, v in os.environ.items() if k not in NON_SUBSCRIPTION_AUTH_ENV}
        if audit_db_path is not None:
            env[AUDIT_DB_ENV] = str(audit_db_path)
        if case_root is not None:
            env[DATASET_ROOT_ENV] = str(dataset_root)
        files = assemble_case(finding, rule)
        _write_case_files(case_dir, files)

        try:
            result = subprocess.run(
                [sys.executable, str(RUNNER_SCRIPT), str(repo_path), case_id, run_id, model, str(max_budget_usd)],
                capture_output=True, text=True, check=False, timeout=TIMEOUT_S, env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"verifier subprocess timed out after {TIMEOUT_S}s for finding {finding_id_for(finding)}"
            ) from exc
        if result.returncode != 0:
            status = _API_STATUS_RE.search(result.stderr)
            if status and int(status.group(1)) in PROVIDER_STATUS_CODES:
                raise ProviderError(
                    f"verifier provider error api_error_status={status.group(1)} for finding "
                    f"{finding_id_for(finding)}"
                )
            if SUBSCRIPTION_LIMIT_RE.search(result.stderr):
                raise ProviderError(f"verifier provider subscription usage limit for finding {finding_id_for(finding)}")
            if BUDGET_STOP_RE.search(result.stderr):
                run_stats.append(
                    {
                        "finding_id": finding_id_for(finding),
                        "cost_usd": None,
                        "cost_usd_estimated": max_budget_usd,
                        "num_turns": None,
                    }
                )
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

        run_stats.append(
            {
                "finding_id": finding_id_for(finding),
                "cost_usd": payload.get("cost_usd"),
                "num_turns": payload.get("num_turns"),
            }
        )

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

        return {
            "finding_id": finding_id_for(finding),
            "verdict": _VERDICT_MAP[shipped_verdict],
            "citation": f"{evidence_source}: {evidence_note}",
            "model": model,
            "timestamp": datetime.now(timezone.utc),
            "run_id": run_id,
        }
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
