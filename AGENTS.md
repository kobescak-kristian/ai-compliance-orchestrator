# AGENTS.md — ai-compliance-orchestrator

Agent-first context router. It points to where repository truth lives.
It is not itself evidence of project state: cite the source it routes
to, never this file.

## Repository purpose

Multi-jurisdiction iGaming compliance surveillance built to demonstrate
bounded multi-agent orchestration: caged checker agents fan out over a
deterministic Python control plane with typed handoffs, a full audit
trail, and a human approval gate. Rule sets are synthetic and no legal
accuracy is claimed. Human overview: `README.md`.

## Authority and conflict handling

| Question | Canonical source |
|---|---|
| What the system is and claims publicly | `README.md` |
| Behavioural contract: invariants, agent tool boundaries, gate definition | `SPEC.md`; `BLUEPRINT.md` for full rationale |
| Why a design decision was made, and what it superseded | `adr/` |
| Verifier / adjudication behaviour, verdicts, scoring treatment | `policy/ADJUDICATION_POLICY.md` |
| Eval thresholds, ground truth, official results | `evals/eval_config.yaml`, `evals/answer_key.yaml`, `evals/EVAL_RESULTS.md` |
| Build status, open loops, change history | `STATE.md` |
| What the implementation actually does | affected source, tests, configuration, and executable schemas inspected together |

When sources disagree:

- An adopted ADR or explicit dated amendment outranks the original text
  it amends.
- Documents state intent; implementation and tests state behaviour. A
  gap between them is a finding to surface, not something to silently
  reconcile.
- `STATE.md` is the status surface. Do not infer current build or phase
  status from historical design documents.
- If canonical sources conflict, surface the conflict and do not resolve
  it by assumption. If the requested task depends on that conflict,
  stop and ask the owner.

`AGENTS.md` is routing guidance, never evidence of implementation or
project state.

## Task routing

These are starting points, not exhaustive reading lists.

| Task class | Start here |
|---|---|
| Understand or explain the system | `README.md`, then `SPEC.md` |
| Control plane: ledger, state machine, pipeline, aggregation | `SPEC.md` non-negotiables; `adr/0001`; `orchestrator/`; `contracts/schemas.py`; relevant failure tests |
| Agent cages: tools, caps, prompts | `SPEC.md` agent boundaries; relevant `agents/<name>/`; `tests/test_bounds.py` |
| Verifier / adjudication node | `policy/ADJUDICATION_POLICY.md`; `adr/0002`; `nodes/`; `config.yaml` |
| Eval dataset, scoring, results | `evals/eval_config.yaml`; `evals/run_eval.py`; `evals/EVAL_RESULTS.md`; `evals/provenance/` where provenance matters |
| Documentation / README / ADR work | relevant artifact first; `.githooks/validate_artifacts.py` for enforced structure |
| CI, hooks, publishing | `.github/workflows/ci.yml`; `.githooks/`; `.publicgate-allow` |
| Current status or open decisions | `STATE.md` |

## Always-on constraints

- The control plane is deterministic Python. No model call may decide
  routing, state transitions, or severity. See `SPEC.md` and `adr/0001`.
- Every model agent runs inside an explicit tool whitelist. Do not widen
  a whitelist or bypass a boundary merely to make a task easier.
- Development and keyless verification paths use stub/no-model
  execution. Do not opt into paid or real-model execution without
  explicit owner authorization.
- The verifier is a reused external agent pinned by commit in
  `config.yaml`. Do not edit that external agent or change its pin
  without an explicit recorded decision.
- Eval gates and scorers are frozen before a judged run and are not
  adjusted after seeing its result.
- Answer-key material such as `evals/answer_key.yaml` and
  `evals/INJECTION_SPEC.md` must never enter model-agent input or
  prompts.
- If canonical design material does not cover a material design
  decision required by the task, stop and ask the owner rather than
  silently creating the policy.
- Git history is evidence and published records are hash-pinned. Never
  rewrite repository history.
- No secrets or machine-local absolute paths in tracked files. Secrets
  belong only in gitignored local secret storage; machine-specific
  values belong in gitignored local configuration.
- This file is an instruction surface, not a security boundary.
  Permissions, hooks, tests, and other mechanical controls remain
  authoritative enforcement mechanisms.

## Verification

- Done means the requested acceptance condition is demonstrated, not
  merely that a file exists.
- When repository dependencies are already installed, the keyless
  stub-mode suite is:

      pytest -v

- Tier 0 artifact structure can be checked with:

      python .githooks/validate_artifacts.py .

- Do not run paid/real-model evaluation or a verifier-subprocess path
  without explicit owner authorization. Such runs can incur cost and
  may create temporary files in the sibling verifier checkout.

## Repository landmarks

- Root `*.db` files are gitignored local run artifacts, not canonical
  project truth.
- `evals/check_pages.py`, `evals/dev_score.py`, and
  `evals/run_eval.py` are standalone evaluation CLIs, not pytest tests.
- Tool-specific instruction files such as `CLAUDE.md` contain
  tool/session mechanics and defer to this file for shared repository
  context.
