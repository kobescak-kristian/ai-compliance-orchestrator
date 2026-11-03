# Preflight (gate v2, eval-gate build check c)

Written by hand before each gated series, and again when a series
restarts. It is a checklist, not a code guard. Machine-specific paths
are never written here: `<holdout_root>` and `<verifier clone>` are the
values in the gitignored `config.local.yaml`.

Status of each line: **DONE <date>** with the command and its result, or
**OPEN** (to be done at run time). "Preflight done <date time>" and every
item that needed action go into the first run's results entry.

## 1. Storage map (where a run writes, and whether that is inside Git)

Owner rules: nothing that contains holdout data is written inside a Git
repository or inside a holdout folder; console output is sanitized.

| What | Where | Holds page text? | Inside Git? | How verified |
|---|---|---|---|---|
| Ledger DB, checker and planner audit DB | `<holdout_root>/runs/<dataset>/<series>/run<k>/` | yes | no | storage guard (`guard_output_path`: not in this repo, not in a holdout folder, not in any Git work tree); `tests/test_run_eval.py`, `tests/test_p3_storage.py` |
| Verifier audit DB | `run<k>/verifier_audit.db` (env `VERIFIER_AUDIT_DB`) | yes | no | `tests/test_p2_repairs.py` (fake verifier); probe below |
| Verifier case files | `run<k>/verifier_cases/<case>/`, removed after each call (env `VERIFIER_DATASET_ROOT`) | yes | no | `tests/test_p3_storage.py` (fake verifier); probe below |
| Results file | private run dir; `evals/results/<series>.json` only for `--gated` (sanitized allowlist) | no | the gated file only, sanitized | allowlist tests in `tests/test_run_eval.py` |
| Console | counts, IDs and result class only | no | no | `evals/run_eval.py` `main` |
| CLI session transcripts (checker, planner, verifier) | `~/.claude/projects/<folder named after the run dir>/` (owner decision 2A: real runs execute in the run dir) | yes | no | cwd tests in `tests/test_p3_storage.py`; location: OPEN, metadata check in section 3 |
| Machine-policy hook action records (managed-policy hook `record` on every `mcp__*` call) | `~/.claude/kos-core/records/no-repo.jsonl` when the cwd is the run dir | fragments (tool input up to 200 chars, result up to 120 chars) | no | `~/.claude/kos-core` is not a Git repository (`git rev-parse` exit 128); file: OPEN, section 3 |
| Machine-policy hook session stamps and `loaded` files | `~/.claude/kos-core/stamps/`, `loaded/` | no (metadata) | no | as above |
| Verifier clone `__pycache__` | `<verifier clone>/agent/__pycache__/` | no (verifier code only) | gitignored in the clone | clone `git status --porcelain` stays empty |
| A1 keyless suite temp dirs | system temp | no (fixtures, July pages) | no | tests use `tmp_path` |

Agent context (owner decision 3A): the checker and planner run with
`setting_sources=[]` and `strict_mcp_config=True`, so no user, project or
local settings, no CLAUDE.md and no other MCP server load, whatever the
working directory. The managed machine-policy hooks still run (machine policy, not
changed by this repo). Known limit: the verifier runs as shipped (pinned,
ADR-0002) and still loads user-level settings and the user CLAUDE.md; with
the run dir as cwd it no longer loads this repo's.

## 2. Checklist (build check c, items 1-6)

1. **Infrastructure is ours for the series.** No other Claude Code session
   uses tools on this machine during a run: the machine-policy `record` hook takes a
   shared lock and fails closed for `mcp__*` calls after 10 s, which would
   turn an agent tool call into an error. No other test run on the same
   tools. OPEN.
2. **Credentials.** The Claude login used by the Agent SDK works and does
   not expire before the series ends. OPEN (checked by the dry run, item 5).
3. **Limits.** Agent sessions per run: one per check task, one per
   verified finding, one per proposal. About 120 per dev-suite run; about
   500 per official attempt (3 runs), plus one rerun. Check the plan's
   usage limits against that. OPEN.
4. **No governance rule deploy, tool upgrade, SDK or CLI upgrade during the
   series.** Record the versions at start: `claude-agent-sdk` 0.2.110,
   bundled CLI 2.1.191 (2026-11-03). OPEN at series time.
5. **Dry run.** One dry case through the full real path, runner exit 0 (not
   a result).
   - Stub dry run: DONE 2026-11-03.
     `python evals/run_eval.py --dataset july --holdout-root <temp dir>`:
     exit 0. Files written only under `<temp dir>/runs/july/<series>/`
     (`results.json`, `run1..3/ledger.db`); repository `git status`
     unchanged.
   - Stub fixture-holdout series: DONE 2026-11-03.
     `python -m pytest -q -p no:cacheprovider
     tests/test_run_eval.py::test_stub_holdout_series_writes_only_under_runs`:
     1 passed, exit 0. A synthetic 30-case holdout with its manifest, 2
     stub runs through the alias cage: output only under
     `<temp>/runs/H9/`, holdout files unchanged, repository `git status`
     unchanged, no case ID in any ledger row.
   - Real dry run (1 July page, `--runs 1`, Haiku): OPEN, needs the owner's
     paid-run authorization.
6. **Blueprint reliability table.** N/A: `BLUEPRINT.md` has no "Reliability
   and security defaults" table (it predates that template).

Model availability (gate `model_routing`): `claude-haiku-4-5-20251001` and
`claude-sonnet-4-6` are listed Active with no retirement date in the
claude-api reference cached 2026-10-06. Not checked live. OPEN: confirmed
by the dry run for Haiku, and before the official series for Sonnet.

## 3. Keyless checks (DONE 2026-11-03) and run-time metadata checks (OPEN)

DONE 2026-11-03:
- Verifier clone at the pin and clean: `check_verifier_checkout()` through
  `config.local.yaml` returned the clone; `git -C <verifier clone> rev-parse
  HEAD` = `d444b13c3ba07b9f4798d3298ec3bfc92da5a960`; `git status --porcelain
  --ignored` empty; the clone has no remote.
- Storage-redirect probe (a private script, `python -B -I`): it imported the
  pinned `agent` package from the clone and applied the same assignments as
  `nodes/verifier_runner.py`. `case_paths`, `resolve_dataset_path` and
  `read_page` resolved under a temporary private root, an escape was
  rejected, `AUDIT_DB_PATH` pointed under the private root, nothing was
  written in the clone. No `run_case_result`, no model call. The script
  was a one-off outside the repository and is not kept; to repeat the
  probe, run these steps again by hand. The same redirect is covered on
  every test run by the fake verifier in `tests/test_p3_storage.py`.
- H2: `python -I evals/check_holdout.py <holdout_root>/H2 --verify-manifest
  evals/v2/holdouts/H2.sha256`: "manifest: match", "Holdout self-check:
  PASS", exit 0, 296 cells. Hashing and structure checks only.
- H1: `python -I evals/check_holdout.py <holdout_root>/H1`: "Holdout
  self-check: PASS", exit 0, 384 cells.

OPEN, run in the authorized dev preflight on public data (July or D10
pages), metadata only: before and after the real dry run, list path, size
and modification time (never contents) under `~/.claude/projects`,
`~/.claude/kos-core`, this repository and the verifier clone. Pass when:
- new transcript files appear only under the project folder named after
  the run dir;
- machine-policy hook records grow only in `no-repo.jsonl`;
- nothing new appears in this repository or in the clone (its
  `__pycache__` excepted);
- `verifier_cases/` is empty after the run.
- RT2-07 (public data only): in the dry run's July transcript, check
  whether the working directory reaches the model's context; the result
  goes to the owner's RT2-07 ruling.
For a holdout run (P4) the same listing is taken, and holdout transcripts
are never opened.
