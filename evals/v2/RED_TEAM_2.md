# Red team 2: the build before its first gated run

Date: 2026-11-03

Scope: the working tree of branch `repair/v2` as it is (HEAD `3d812eb`
plus uncommitted changes in `agents/checker/harness.py`,
`agents/planner/harness.py`, `evals/run_eval.py`, `nodes/verifier.py`,
`nodes/verifier_runner.py`, `tests/test_p2_repairs.py`, and the new files
`evals/PREFLIGHT.md` and `tests/test_p3_storage.py`). Checked against the
gate (`evals/eval_config.yaml` 2.0), `evals/v2/SCENARIO_SPEC.md`,
`policy/ADJUDICATION_POLICY.md`, `BLUEPRINT.md` §7 and its amendment,
`STATE.md` (open loops and the P2 entry), `evals/PREFLIGHT.md` and
`evals/v2/RED_TEAM_1.md`.

Build files read: `orchestrator/`, `agents/` (checker, planner,
`outcome.py`), `nodes/`, `intake/`, `gate/cli.py`, `contracts/schemas.py`,
`evals/run_eval.py`, `evals/check_holdout.py`, `evals/dev_score.py`,
`tests/`. For the verifier I read only the pinned commit's files
(`git show d444b13c…:agent/*.py` in the sibling checkout's object store;
nothing checked out or changed there). I also read the installed
`claude_agent_sdk` 0.2.110 `types.py` for its error fields.

Not opened, listed or searched: anything under the private holdout
folder, `evals/v2/holdouts/` (including `H2.sha256`), `~/.claude/plans`
and `config.local.yaml`.

What I ran (keyless, no model call, no network, no `--real`, no verifier
subprocess):
- `python -m pytest -q -p no:cacheprovider`: 142 passed, exit 0.
- Stub July series with a new temp `holdout_root` under `%TEMP%`:
  `python -I evals/run_eval.py --dataset july --runs N --holdout-root <temp>`
  for N = 3, 1 and -1.
- Two probe scripts in my scratchpad (`python -B -I`, outside the repo):
  they import the repo modules, replace a stub function in memory, and
  write only under the temp dir.
- `git status --short` before and after: unchanged (only this file is
  new). The allowed pytest and runner commands may refresh gitignored
  `__pycache__` folders.

Known and accepted items are not raised again (D1-D10, private holdouts,
same model family, managed machine-policy hooks, verifier user-level settings,
planner match by page_path + rule_id, no real-model run yet). Resolved
RT1 findings are not raised again.

---

## RT2-01: A gated series can PASS with 0 runs, and with 1 run the off-target guardrail can never fail

Severity: High

What breaks: The runner never checks that a series has exactly 3 runs.
`--runs` is passed straight through, also with `--gated`. With
`--runs -1` (or any number below 1) no run happens at all: every case
"passes" because there is no run to fail, and the result is PASS. With
`--runs 1` a cell can never be wrong "in at least 2 of 3 runs", so no
page is ever unclean and the guardrail is switched off. With
`--runs 2` both runs must be wrong. The gate says one series is 3 runs
and a case passes only if it is right in all 3. A typo or a short test
run with `--gated` would write an official PASS file to `evals/results/`.

Evidence:
- `evals/run_eval.py:741` `runs = runs or config[...]["runs_per_case"]`
  (only 0 or None falls back to 3); `:809` `for k in range(1, runs + 1)`;
  `:508-510` a case starts as passed and only a run can fail it;
  `:536` `if len(material) >= 2`; `:856`, `:864-872` `main` checks
  `--gated` only for `--real` and a holdout name, never the run count.
- Gate: `evals/eval_config.yaml:26` (3 full-workflow runs), `:94-95`,
  `:111`, `:140` (PASS needs a completed series).
- Commands (stub, July, temp `holdout_root`), console output:
  - `--runs 3`: `component B: 5 cases passed, 7 failed, 10 unclean pages`, `RESULT: FAIL`
  - `--runs 1`: `component B: 5 cases passed, 7 failed, 0 unclean pages`, `RESULT: FAIL`
  - `--runs -1`: `component A: 3 passed, 0 failed, 0 not run`,
    `component B: 12 cases passed, 0 failed, 0 unclean pages`, `RESULT: PASS`, exit 0;
    its `results.json` has `"run_db_names": []`.
- No test covers the run count (no test passes `runs` other than 1 or 2
  to `run_series`; none passes `--runs` to `main`).

Smallest fix: code. Refuse `runs < 1` always, and refuse `--gated` (and
`gated=True` in `run_series`) unless `runs == runs_per_case`; add a
keyless test for both.

Disposition: changed the build. `run_series` refuses `runs < 1` (usage error, exit 64) and a gated series whose run count is not `runs_per_case`. Tests: `tests/test_p3_storage.py::test_rt2_01_*`.

---

## RT2-02: An official result can record a commit that is not the code, config or manifest that ran

Severity: High

What breaks: The series record takes `git rev-parse HEAD` as `commit`,
but nothing checks that the working tree is clean. A gated series run
with uncommitted changes (code, `evals/eval_config.yaml` thresholds, the
manifest file, or an untracked test file that A1 then runs) is recorded
as if it ran "the frozen commit". `config_sha256` is recorded but never
compared with the frozen gate fingerprint, and the manifest is read from
the working tree, not from the commit. The gate's series is "A1 and A3
on the frozen commit, then 3 full-workflow runs of that commit". The
tree is in exactly this state today.

Evidence:
- `evals/run_eval.py:717-719` (`_git_head`), `:746-747` (commit and
  config hash recorded), `:772-778` (manifest read from the working-tree
  path); no `git status` call anywhere in the runner.
- Gate: `evals/eval_config.yaml:26`, `:40-41` (A1 "on the frozen
  commit"), `:149` (only the verifier checkout is checked for a clean
  tree). Frozen gate fingerprint recorded in `STATE.md` (P2 entry):
  `d386930e…`.
- My stub run's `results.json`: `"commit": "3d812eb3dd45c7dfa8b7dc72b92cb886d84e50cc"`,
  while `git diff --stat HEAD` shows `6 files changed, 81 insertions(+),
  16 deletions(-)`, including `evals/run_eval.py` itself, plus two
  untracked files (`tests/test_p3_storage.py` is run by A1).

Smallest fix: code. For `--gated`, refuse to start (usage error, before
any score) unless `git status --porcelain` is empty, so commit, config
and manifest are all pinned by the recorded commit; keyless test with a
dirty temp repo or a patched status call.

Disposition: changed the build. A gated series refuses to start unless `git status --porcelain` is empty (gitignored files excluded), so the recorded commit is the code, gate and manifest that ran. Test: `test_rt2_02_gated_series_needs_a_clean_tree`.

---

## RT2-03: A retired holdout can be run again as official, and a pages-only manifest leaves the key unpinned

Severity: Medium

What breaks: (1) The gate retires a holdout after any completed official
series, PASS or FAIL. The runner counts earlier result files but still
starts a new gated series on the same holdout, so the maintainer could rerun
H2 until it passes and each run would write an official result file.
(2) `verify_manifest` decides "pages-only or full" from the manifest
itself. If a future holdout's committed manifest lists only `pages/`,
the series starts and `key.yaml`, `briefs.md` and `adjudication.md` can
change without any INVALID RUN. The gate requires the full manifest
before the first run. (H2's manifest is reported in STATE as full, 33
files; I did not open it.)

Evidence:
- `evals/run_eval.py:751` (`earlier_series_count` is recorded only);
  `:772-778` (no check of the manifest mode).
- `evals/check_holdout.py:335` `pages_only = all(... startswith("pages/") ...)`.
- Gate: `evals/eval_config.yaml:156` (manifest immutable), `:157`
  (retirement), `:201` (full manifest before the first run).
- Probe (temp dir): pages-only manifest written, then `key.yaml` changed;
  `check_holdout.verify_manifest(...)` returned `[]` (match).

Smallest fix: code. For `--gated`, refuse a holdout that already has an
`evals/results/<H>-*.json`, and require that the manifest lists
`key.yaml`, `briefs.md` and `adjudication.md`; keyless tests for both.

Disposition: changed the build. A gated series refuses a holdout that already has `evals/results/<H>-*.json` (retired), and ends as INVALID RUN when the committed manifest does not pin `key.yaml`, `briefs.md` and `adjudication.md`. H2's manifest pins all three (file names checked). Tests: `test_rt2_03_*`.

---

## RT2-04: Some system crashes are classified the wrong way (INVALID RUN vs FAIL)

Severity: Medium

What breaks: Two paths go against the gate's result rules.
(1) A system crash that happens again in the A2 resume check (for
example a data-dependent bug in a stage) escapes from `a2_checks`, which
runs outside the per-run `try`. The outer handler then calls it "runner
or grader code" and the series becomes INVALID RUN. The gate says an
exception inside the automation is scored as is (a FAIL path), and an
INVALID RUN may be rerun with no extra approval, so a system defect
would get free reruns. (2) The provider-error check (`PROVIDER_ERROR`
rows mean INVALID RUN) runs only when `run_once` returns normally. If a
provider error and a later system crash happen in the same run, the run
is scored and the series can FAIL instead of being INVALID.
Also, no keyless test covers `_raised_in_runner` or the provider-error
INVALID path, although A1 must include "D9 ... classification".

Evidence:
- `evals/run_eval.py:664-666` (provider check inside `run_once` only),
  `:820-827` (crash branch scores the run, no provider check), `:397`
  (resume check runs the stages again inside `a2_checks`), `:844-846`
  (outer handler: every exception is "runner or grader code", no
  `_raised_in_runner`).
- Gate: `evals/eval_config.yaml:146-147`, `:151-152`, `:45` (A1 must
  include D9 classification).
- Probe 2 (stub July, `--runs 1`, a stage function whose frame is in
  `orchestrator/pipeline.py`):
  - crash once, no provider error: `FAIL` (correct)
  - crash once, plus one `ProviderError` in the check stage: `FAIL`
    (gate: INVALID RUN)
  - crash every time: `INVALID RUN: exception in runner or grader code:
    RuntimeError` (gate: scored as is)
- `grep` of `tests/` for `_raised_in_runner`, `provider error rows`,
  `PROVIDER_ERROR` in `test_run_eval.py`: no hit.

Smallest fix: code and test. Check provider rows in the crash branch
too; in `resume_check` catch system exceptions and count them as resume
failures (or classify them with `_raised_in_runner`); add keyless tests
for the three cases above.

Disposition: changed the build. A system-code crash in the resume check now fails that A2 row and the run is scored as is (a runner-code crash stays INVALID RUN); the provider-error rule is applied after a crashed run too. Tests: `test_rt2_04_*`.

---

## RT2-05: A provider overload can be scored as a miss instead of INVALID RUN

Severity: Medium

What breaks: The gate makes provider auth, rate-limit and overload
errors an INVALID RUN. The build recognises them only from a few
signals. The SDK's assistant error types have no "overload" value; an
overload most likely arrives as `server_error` (inference), and the
build treats `server_error` without a ResultMessage as an agent error,
which is scored as a miss. On the verifier side, the error is
recognised only when the shipped agent ends with `is_error` and a
numeric `api_error_status`; the shipped harness raises
`RuntimeError("No ResultMessage received ...")` in the other case, so the
stderr has no status and the task ends as `VERIFIER_FAILED`, a miss.
Under a 3-run official series with about 500 agent sessions, one such
event can turn an infrastructure problem into a scored FAIL.

Evidence:
- `agents/outcome.py:12` (`authentication_failed`, `rate_limit`,
  `billing_error` only), `:28-30` (no ResultMessage plus any other
  assistant error raises `AgentRunError`).
- `tests/test_p2_repairs.py:291` asserts `(None, ["server_error"]) ->
  AgentRunError`.
- Installed SDK 0.2.110 `types.py`: `AssistantMessageError` is
  `authentication_failed, billing_error, rate_limit, invalid_request,
  server_error, unknown`.
- `nodes/verifier.py:192-202` (needs `api_error_status=<digits>` in
  stderr); `nodes/verifier_runner.py:75-84` (prints the status only when
  `result.is_error`); pinned verifier `agent/harness.py`
  `run_case_result` raises `RuntimeError` when no ResultMessage arrives.

Smallest fix: code plus gate clarification (maintainer): decide whether
`server_error` and a missing ResultMessage count as provider overload;
record the raw provider error type in `payload_ref` so the decision is
"from logged error types", as the gate asks.

Disposition: pending ruling (gate clarification: do `server_error` and a missing ResultMessage count as provider overload, that is INVALID RUN?). No change made.

Ruling 2026-11-03 (option b; gate text unchanged): INVALID RUN only when the logged provider type or status shows auth failure, rate limit or overload, and a subscription usage-limit message counts as a provider rate limit. `server_error` without such a status and a missing ResultMessage stay agent errors (a miss), with the raw types logged. Changed the build: `agents/outcome.py` (usage-limit message on an error result is a provider error; every agent-error message logs the raw assistant error types, `api_error_status` and, when a ResultMessage exists, the first 300 characters of its error text), `nodes/verifier_runner.py` (prints the error text and errors of an errored run), `nodes/verifier.py` (usage-limit message is a provider error). Remaining gap, accepted: a verifier run that ends without a ResultMessage has no logged type and stays a miss (the shipped verifier is not changed). Tests: `test_d6_outcome_mapping` (new rows), `test_rt2_05_*`.

---

## RT2-06: One agent failure makes component A fail, although the gate says it should not

Severity: Medium

What breaks: The gate says a timeout or FAILED task inside a run is not
an A failure by itself; its cost lands in B as a miss. Three A2 checks
break this rule:
- planner integrity needs exactly one proposal per CONFIRMED finding,
  so one planner timeout, budget stop or agent error fails A and with it
  the whole series (B does not score proposals at all);
- the independence check counts tool-call rows, not model calls, so a
  checker that ends (FAILED or COVERAGE dead-letter) without calling any
  tool fails A;
- the leak check counts "no rows to verify" as a leak, so a run where
  every verifier session failed before its first tool call fails A.
The two gate lines conflict; the build follows the stricter one. With
about 15 confirmed findings per run and 3 runs, one planner flake is
enough.

Evidence:
- Gate: `evals/eval_config.yaml:33-35` versus `:59` and `:65`.
- `evals/run_eval.py:274-278` (missing proposal counted), `:366`,
  `:370-372` (independence from `tool_calls` rows), `:378-382`
  (`RuntimeError` "no rows" counted as a leak).
- Probe (stub July, `--runs 1`, first planner call raises
  `TimeoutError`): `planner_one_pending_proposal_per_confirmed`
  `passed: False, count: 1`, result `FAIL`.

Smallest fix: gate or spec change (maintainer): say whether a terminal FAILED
plan task (and a checker or verifier session with no tool call) is an A
failure or only a recorded diagnostic; then align the three checks and
add keyless tests.

Disposition: pending ruling (the gate lines conflict; the build keeps the stricter reading until it is ruled). No change made.

Clarification 2026-11-03 (gate v2.0 text unchanged; recorded before any judged run): under lines 33-35, an A2 line that needs an artifact of a task (an audit row, a proposal) applies to tasks that ended DONE. A check task that ended FAILED or DEAD_LETTER, or a plan task that ended FAILED, passes A2 when it is terminal, recorded with an error class and stored no finding or proposal; their counts are published as diagnostic rows. Changed the build (`evals/run_eval.py`): independence counts DONE check tasks only (FAILED and DEAD_LETTER check tasks store no finding and are misses in B); the leak check fails on any marker, and on a missing audit DB or no rows only when a DONE task should have logged there (checker and planner DB: a DONE check task; verifier DB: a DONE verify task); planner integrity needs zero proposals for a CONFIRMED finding whose plan task ended FAILED and exactly one for every other, and every stored proposal still passes every planner check. A plan task that ended DONE without a proposal or DEAD_LETTER still fails A. New component A rows `diagnostic_check_tasks_failed_or_dead_letter` and `diagnostic_plan_tasks_failed` (passed is None, count is the number of tasks). Tests: `test_rt2_06_*`.

---

## RT2-07: The leak check reads only tool calls, not what else the agents are given

Severity: Medium

What breaks: The gate check is "no answer-key or holdout marker in any
agent input or output". The build checks only the `tool_calls` payloads
(tool input and tool response) in the audit DBs. It never checks the
system prompt, the user prompt, or context that the CLI adds to a
session. By code reading our prompts hold no marker (fact). But since
P3 (decision 2A) every real agent session, including the
verifier subprocess, runs with its working directory at
`<holdout_root>/runs/<H>/<series>/run<k>`, and that path contains the
`holdout_root` marker. Whether the CLI puts the working directory into
the model's context with a custom system prompt is not verified
(inference). If it does, every session has a marker in its input and
the A2 check still passes.

Evidence:
- `evals/dev_score.py:79-81` (`SELECT id, payload FROM tool_calls`);
  `agents/checker/audit.py` `audit_hook` stores only `tool_input` and
  `tool_response`.
- `evals/run_eval.py:658` (`contextlib.chdir(ctx.run_dir)` in real
  mode); the verifier subprocess inherits that cwd
  (`nodes/verifier.py:184-187`, no `cwd=`).
- Gate: `evals/eval_config.yaml:61`, `:79`.
- `evals/PREFLIGHT.md` §3 plans only a metadata listing of transcripts
  (path, size, time), which cannot show this.

Smallest fix: dev case (in the authorized real dry run on July, check
whether the model is told its working directory), or code: run agent
sessions in a neutral per-run directory whose path holds no
`holdout_root` marker.

Disposition: pending ruling. Facts: our prompts hold no marker (code reading); whether the CLI tells the model its working directory is not verified. Proposed: check it in the authorized real dry run on a July page (transcript of public data); if the directory reaches the model, the maintainer decides between a neutral per-run agent directory (amends decision 2A) and accepting it. No change made.

Ruling 2026-11-03: approved as proposed. No change now; the check is made in the real July dry run (not yet authorized), and a neutral per-run directory follows only if the path reaches the model.

---

## RT2-08: A hidden void element hides the rest of the page from the reader and the grader

Severity: Low

What breaks: The shared text rule skips elements with the `hidden`
attribute. The code puts every such tag on a skip stack and waits for
its end tag. A void element (`<input hidden>`, `<img hidden>`,
`<br hidden>`) has no end tag, so everything after it disappears for
the checker, the verifier copy and the grader at the same time. A3 and
the self-check compare the same extractor with itself, so they cannot
see it (the self-check fails only if a key span is after it). The blind
labeler and a human reader still see the text, so off-target cells
would be scored against text the system never got.

Evidence:
- `intake/textrule.py:93-96`.
- Probe: page `<h1>Offer</h1><input type='hidden' name='t' hidden><p>100% risk-free bet</p><footer>Markets: GBR</footer>`:
  `visible_text` = `'offer'`, `blocks` = `['Offer']`.

Smallest fix: code: do not push void elements on the skip stack; add
the case to the RT1-11 shared-text-rule test.

Disposition: pending ruling. The fix is in the shared text rule, which is also the grader (RT1-11), and the gate and scorer are frozen. No change made.

Ruling 2026-11-03: fix approved; it brings the code in line with the frozen `shared_text_rule` text (no judged run exists yet; the H2 manifest hashes files, not extracted text). Changed the build: `intake/textrule.py` drops a hidden void element on its own and never opens a skip region for it. Probe page above now gives `'offer 100% risk-free bet markets: gbr'`. Test: the RT1-11 shared-text-rule test (`test_shared_text_rule_same_text_for_grader_reader_and_tool`) gained a hidden `<input>` and `<img>` before trailing text. H2 manifest check and self-check rerun: "manifest: match", "Holdout self-check: PASS". A3 on H2 rerun (keyless, counts only): `a3_grader_blocks_in_reader`, `a3_triggers_and_spans_in_reader` and `a3_absent_content_not_in_reader` passed, 0 failures each, 30 cases.

---

## RT2-09: A3 checks the reader function, not the text the agents get; the verifier's copy drops the page title

Severity: Low

What breaks: A3 compares `pages.read_page` with the grader, but both
call the same `extract()` on the same file, so the block check passes by
design. It does not check the `fetch_page` text the checker receives, or
the page copy the verifier receives. That copy drops the page `<title>`
(the alias name is put in its place). The checker and the grader see
the title. A violation shown only in the title (for example an
off-target "risk-free" claim) can be flagged by the checker but not
confirmed by the verifier, so it becomes a missed violation (inference
about verifier behaviour).

Evidence:
- `evals/run_eval.py:204-207`, `:216`; `agents/checker/pages.py:73-77`.
- `nodes/assembler.py:51-52` (`_page_title` unused,
  `_html_page(finding.page_path, page_blocks)`); pinned verifier
  `agent/pages.py` reads only `<title>` and `<p>`.

Smallest fix: code: put the page title into the verifier's source page
as its first paragraph, and add a keyless test that the verifier case
text contains the title and every grader block.

Disposition: changed the build. `nodes/assembler.py` puts the page title in as the first paragraph of the verifier's page copy. Test: `test_rt2_09_verifier_page_copy_carries_the_page_title`.

---

## RT2-10: The checker can read any page in the cage, not only its own

Severity: Low

What breaks: `fetch_page` accepts any page name in the cage root. For a
holdout run all 30 aliases (`page01.html` ... `page30.html`) resolve, and
for July all 12 pages. The tool docstring says a tool call cannot name
another task's data. An injected line such as "also read page07.html"
or a simple mistake can make the checker judge the wrong page. The
verbatim check limits quotes to its own page, but verdicts can still be
influenced.

Evidence:
- `agents/checker/tools.py:3-5` (claim), `:104-110` (`pages.read_page(args["path"])`,
  no comparison with `task.page_path`).
- `evals/run_eval.py:163-167`, `:785` (all aliases in one cage).

Smallest fix: code: `fetch_page` rejects any path other than
`task.page_path`; keyless test.

Disposition: changed the build. `fetch_page` rejects (and logs as denied) any page other than the task's own. Test: `test_rt2_10_checker_reads_only_its_own_page`.

---

## RT2-11: Cost and turns in the results are wrong

Severity: Low

What breaks: The results file reports `cost_usd` and `turns`
(allowlisted, a recorded diagnostic). The verifier's cost and turns are
never added, so the total misses one session per verified finding.
When a checker or planner session times out, the harness does not
update `last_result`, so the runner adds the previous session's cost and
turns a second time. This is the same kind of telemetry gap as the July
record.

Evidence:
- `evals/run_eval.py:627-650` (only checker and planner add to
  `stats`; `verifier_fn` adds nothing); `nodes/verifier.py:213-219`
  (`run_stats`, never read by the runner).
- `agents/checker/harness.py:80-86`, `agents/planner/harness.py:93-99`
  (`last_result = result` after the `fail_after` block); runner
  `finally` at `evals/run_eval.py:630-634`, `:644-648`.
- Gate: `evals/eval_config.yaml:170`, `:183`.

Smallest fix: code: reset `last_result` to None at the start of each
session, and add the verifier's `run_stats` to the run totals.

Disposition: changed the build. Both harnesses reset `last_result` at the start of a session; the runner adds the verifier's `run_stats` to the run totals. Tests: `test_rt2_11_*`.

---

## Interaction sweep

| Interaction | Handled? | Covered by | Needs |
|---|---|---|---|
| Same page in two markets | Yes: one check task and one verify task per page and market; rule IDs carry the market | `tests/test_failures.py::test_fi3_orchestrator_killed_and_restarted` (p01 MLT + GBR); stub July series | nothing |
| Two findings for one rule | Yes: tool refuses the repeat; stage dead-letters the task (COVERAGE) | `test_p2_repairs.py::test_d4_tool_rejects_foreign_and_repeated_rule`, `::test_d4_stage_dead_letters_task_without_full_coverage` | nothing |
| One sentence triggers rules in two markets | Yes by structure: two findings, two verifications, two proposals with the same offending text (distinct by rule_id) | none | keyless test |
| Distractor next to the real trigger | Grading yes (core-span overlap, length cap); model behaviour unknown | `test_run_eval.py::test_grade_evidence_categories`, `::test_grade_evidence_too_long` | dev case |
| Terms split between a heading and a paragraph | Yes: one space at the block boundary; `...` joins in excerpts | `test_p2_repairs.py::test_shared_text_rule_same_text_for_grader_reader_and_tool`, `::test_d1_reader_shows_headings_and_lists` | dev case |
| Absence violation next to a text violation | Yes: `ABSENT:` skips only the verbatim check; text cells keep full grading | `test_run_eval.py::test_a2_absent_rule_both_ways`, `::test_a3_passes_true_absence_and_flags_present_content` | nothing |
| Verifier failure on one of two findings of a task | Yes per policy §12: whole verify task FAILED, both findings unasserted (counted as NOT_ASSERTED) | single-finding only: `test_p2_repairs.py::test_d6_verify_stage_maps_errors` | keyless test |
| Proposal for a finding later disputed | Yes: plan only on CONFIRMED; adjudication rows never overwritten; A2 flags it | `test_run_eval.py::test_a2_planted_proposal_for_disputed_finding`, `test_failures.py::test_adjudication_log_append_only_no_overwrite` | nothing |
| Resume after a crash between stages | Pipeline resume yes; the runner scores a crashed run as is, but a repeated crash in the resume check becomes INVALID RUN (RT2-04) | `test_failures.py::test_fi3_orchestrator_killed_and_restarted` (check stage only) | fix |
| Approval fired twice | Yes: UPDATE scoped to PENDING, second call is a no-op | `test_run_eval.py::test_human_gate_round_trip_idempotent_and_no_planner_path` | nothing |
| Two errors in one task | Yes: the first error wins (circuit breaker, then outcome; schema before coverage) | `test_failures.py::test_fi1_budget_turn_cap`, `::test_fi2_schema_invalid_payload` | nothing |
| Two errors in one run (provider error, then a system crash) | No: scored as FAIL, gate says INVALID RUN (RT2-04) | none | fix |
| Injected instruction on a page | Checker: page delimited, prompt rule. Verifier: page copy not delimited (shipped agent). Planner: excerpt shown raw. Checker can fetch other pages (RT2-10) | `test_p2_repairs.py::test_d8_fetch_page_delimits_page_content`, `::test_d8_assembler_escapes_html` | dev case; fix (RT2-10) |
| Planner fails for one confirmed finding | Fails component A (RT2-06) | probe only | fix (after ruling) |
| Checker or verifier ends without any tool call | Fails component A (RT2-06) | none | fix (after ruling) |
| Gated series with a run count other than 3 | No (RT2-01) | none | fix |
| Same holdout run again after a completed official series | No (RT2-03) | none | fix |
| Excerpt made of small `...` fragments | Grading yes (one part must overlap the core span by 15 characters); the verbatim and planner on-page checks accept any fragments | `test_run_eval.py::test_grade_evidence_categories` | nothing |
| Void element with the hidden attribute | No: rest of page hidden on both sides (RT2-08) | none | fix |
| Evidence only in the page title | Checker and grader see it; the verifier copy does not (RT2-09) | none | fix |
| Same page shown under two names | Yes: one alias per key entry; self-check refuses a page with no key entry or a mismatched ID | `test_check_holdout.py::test_planted_mistake_stops_and_writes_nothing`, `test_p2_repairs.py::test_cage_alias_map_hides_case_ids_and_root` | nothing |

Disposition of the sweep rows:
- keyless test, added: one sentence triggers rules in two markets (`test_sweep_one_sentence_triggers_rules_in_two_markets`); verifier failure on one of two findings fails the whole task, neither asserted (`test_sweep_verifier_failure_on_one_of_two_findings_fails_the_whole_task`);
- dev case, listed for the D10 batch (public development pages; their briefs and keys are written when D10 is authorized, keys by the three-actor protocol): a distractor next to the real trigger; terms split between a heading and a paragraph; an injected instruction on a page (RT2-10 is fixed);
- fix, done: RT2-01, RT2-03, RT2-04, RT2-09 rows;
- ruling: RT2-06 rows (planner failure, session with no tool call) and RT2-08 (hidden void element). Ruled 2026-11-03 and fixed (see RT2-06 and RT2-08).

RT2-05 to RT2-08 were ruled on 2026-11-03: RT2-05, RT2-06 and RT2-08 changed the build; RT2-07 is checked in the real July dry run.
Findings: 11; changed the build: 10; changed the test: 0; no change: 1; pending ruling: 0
