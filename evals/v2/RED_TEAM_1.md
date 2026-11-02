# Red team 1: gate v2 before code

Date: 2026-11-02

Scope: working-tree versions of `evals/eval_config.yaml` (gate v2.0),
`evals/v2/SCENARIO_SPEC.md`, `evals/v2/RULESET_V1_1.md`, `BLUEPRINT.md`
§7 and its 2026-11-02 amendment, and the `STATE.md` open loops. Checked
against `rulesets/*.json`, `evals/answer_key.yaml`, the 12 July pages,
`evals/provenance/*`, `evals/ADJUDICATION_LOG.md`, `evals/EVAL_RESULTS.md`,
`policy/ADJUDICATION_POLICY.md`, `agents/checker/pages.py`,
`contracts/schemas.py`, `evals/run_eval.py`, `evals/dev_score.py` and the
eval-gate skill (with its build-checks reference). No holdout was opened,
listed or searched (this includes the folder `evals/v2/holdouts/`, see
RT1-10). No model, network call or pipeline was run. Only keyless local
Python was used (`python -I`, from the repo root).

Known and accepted items (D1-D10 fixed in P2, private holdouts by signed
exception, blind labeler of another model family, same family authors
pages and runs the checker) are not raised again.

---

## RT1-01: An error or a skipped rule counts as a correct answer on non-violation cells

Severity: High

What breaks: If the expected answer is COMPLIANT or NOT_APPLICABLE, the
case passes when the system does "not assert". A task that FAILED, went
to DEAD_LETTER, or never produced a finding also "does not assert". So a
crash, a timeout or a rule that was never checked gives a free pass on
10 to 17 of the 30 cases, and a free "clean" mark on every non-violation
off-target cell. A system that turns "unsure" into an error is rewarded.
This also contradicts the config's own line that FAILED and DEAD_LETTER
tasks count as misses, and the eval-gate skill's rule that an error
inside the automation is a miss. Component A does not close the gap: A2
checks that DONE tasks have one finding per rule, but it does not check
that every rule of every target market was assigned to a task in the
run, and it puts no limit on FAILED tasks.

Evidence:
- `evals/eval_config.yaml:89`: `expected_compliant_or_na: "not asserted"`.
- `evals/eval_config.yaml:90`: the "always a miss" list applies only "on
  an expected violation".
- `evals/eval_config.yaml:122`: "FAILED or DEAD_LETTER tasks count as
  misses in B" (contradicts line 89).
- `evals/eval_config.yaml:95-96`: off-target material errors are only a
  CONFIRMED false alarm or an unasserted key VIOLATION.
- `evals/eval_config.yaml:58-63`: no per-run coverage check.

Proposed resolution: (1) For every primary cell, whatever the expected
verdict, a FAILED or DEAD_LETTER task or a missing finding is a miss
(categories TASK_FAILED, DEAD_LETTER, and a new NO_DECISION). (2) In the
off-target guardrail, a non-violation cell with no DONE finding is a
material error. (3) Add an A2 check: every rule of every target market
of every page is assigned to exactly one task in each run.

Disposition hint: change the test

---

## RT1-02: A long or misplaced excerpt passes evidence grading

Severity: High

What breaks: Evidence grading only asks that the excerpt overlaps a key
span by at least min(15, span length) characters. There is no upper
limit on excerpt length, so an excerpt that is the whole page text (or a
whole section) always passes for any text-type violation. Second, the
rule accepts "some occurrence" of a key span, so if the span text occurs
twice on the page (short spans such as "free spins" or "ends soon"), an
excerpt that quotes the wrong place still passes. Third, for a key with
several spans (the spec's own example: "free" in a heading plus the
deposit condition in a list), overlap with any one span passes, so
quoting only the deposit condition passes although it does not show the
"free" claim. The public claim says "with valid evidence".

Evidence:
- `evals/eval_config.yaml:108-109` (parts and overlap rules).
- `contracts/schemas.py:109`: `evidence_excerpt: str`, no length limit.
- `evals/v2/SCENARIO_SPEC.md:24-27` (multi-span keys allowed).
- `evals/eval_config.yaml:185` ("with valid evidence").

Proposed resolution: (1) Add a length rule: the total length of excerpt
parts may be at most max(200, 2 x the longest key span) characters, or
at least half of the excerpt's characters must fall inside key span
occurrences. (2) Self-check: every key span occurs exactly once in the
normalized page text (or the key gives the occurrence index). (3) A
multi-span key marks one core span; overlap with the core span is
required.

Disposition hint: change the test

---

## RT1-03: Missing-term violations have no clear evidence type

Severity: High

What breaks: Many rules are about a term that is missing from an offer
that is on the page: one offer has no expiry (MLT-BT-02), a boost has no
base odds (DEU-BT-02), wagering or minimum deposit is only behind a link
(GBR-BT-01, MLT-BT-01, MLT-BT-03). The spec has only two evidence types.
`absent` needs fixed "required content" strings, but a missing expiry
has no fixed string, so the key author must use `text` with the offer as
the span. A good system will naturally answer `ABSENT: no expiry for
offer 2`. That is graded ABSENT_ON_TEXT, a miss. So a good system can
fail several violation cases for a format reason. Two of the 8 July
violation primaries are this kind (p02 MLT-BT-02, p03 DEU-BT-02), so the
holdout will likely have several too.

Evidence:
- `evals/v2/SCENARIO_SPEC.md:23-30` (only `text` and `absent`).
- `evals/eval_config.yaml:110` (ABSENT on a text-type cell is a miss).
- `evals/v2/SCENARIO_SPEC.md:157-158` (p02, p03 primaries).

Proposed resolution: Add a third evidence type `missing_term`. The key
gives the span of the offer that lacks the term. The decision passes if
it is asserted and the excerpt either starts with `ABSENT:` or overlaps
the offer span. Update spec §1, §4, the self-check and A3 (the offer
span must be visible to the reader).

Disposition hint: change the test

---

## RT1-04: The mix rules force many cases onto one kind of check

Severity: High

What breaks: The GEO_ELIGIBILITY category has only 3 rules in total
(DEU-GE-01, GBR-GE-01, MLT-GE-01). All three are the same check: "show
this market's licence line". The spec requires at least 5 cases per
category and allows at most 2 per rule, so at least 5 of the 30 cases
must be licence-line cases. In the same way, GBR-PC-01, MLT-PC-01 and
DEU-PC-02 have word-for-word the same text, so up to 6 cases can test
one reading. Independence rule 2 exists so that "one rule-reading
weakness cannot move many cases at once", but here one weakness (or one
easy check) can move 5 or 6 cases, while only 2 misses are allowed. The
binomial claim treats the 30 cases as independent; these clusters make
the real sample smaller.

Evidence:
- `rulesets/*.json` (printed with keyless Python): GEO has 3 rules;
  PC-01 family text is identical in three files.
- `evals/v2/SCENARIO_SPEC.md:44-45` (category minimum 5; at most 2 per
  rule_id) and `:58-59` (purpose of rule 2).

Proposed resolution: Define a "rule family" (rules with the same first
sentence, or the same check: the three GE-01 rules, the three
"guaranteed or risk-free" rules, the RG notice rules) and cap 2 cases per
family. Lower the GEO category minimum to 2 (or apply category minimums
per family).

Disposition hint: change the test

---

## RT1-05: Ruleset v1.1 notes make some July cells debatable; the "0 of 288" table misses them

Severity: Medium

What breaks: Some notes are wider than the v1.0 reading, and the July
check table does not look at the cells they touch:
- GBR-RG-02 note defines an offer as "a bonus, free bet, odds boost,
  cashback or other promotional incentive". The GBR checker sees this.
  p03 has an "Odds Boost" section with no wagering, minimum deposit or
  expiry, so p03 GBR-BT-01 (key COMPLIANT) becomes arguable.
- MLT-BT-02 note: "Each offer on the page is checked". The same p03
  Odds Boost states no expiry, so p03 MLT-BT-02 (key COMPLIANT) becomes
  arguable.
- GBR-BT-02 note changes "an offer" to "any item the page calls free".
  p04 has a "free-spins round triggered by three or more scatter
  symbols" and mentions deposits, so p04 GBR-BT-02 (key NOT_APPLICABLE)
  becomes arguable. It also conflicts with the applicability rule "no
  bonus on page, bonus-terms rules N/A".
- DEU-RG-02 note lists "sports betting" as a real-money product. p08
  says "Turn betting into your side income", so p08 DEU-RG-02 (key
  NOT_APPLICABLE) becomes arguable.
The table row values themselves are right (checked: every listed cell
matches `evals/answer_key.yaml`), and the rule count (11 changed, 13
unchanged, first sentences word for word) is right.

Evidence:
- `evals/v2/RULESET_V1_1.md:44, 53, 59, 65` (notes) and `:78, 83, 85,
  87` (table rows that do not discuss p03 boost, p04, p08).
- `evals/dataset/pages/p03.html` ("Odds Boost" section),
  `p04.html` ("free-spins round"), `p08.html` ("Turn betting into your
  side income").
- `evals/provenance/PAGE_AUTHOR_PROMPT.md` (rule-level N/A semantics).

Proposed resolution: Narrow the wording before signature: GBR-BT-02 "any
offer the page calls free"; MLT-BT-02 "each bonus offer"; DEU-RG-02
"promotion of a named operator, a specific product, or an offer; general
betting content that names none is not covered"; state in GBR-RG-02 that
the definition is for this rule only, or check GBR-BT-01 against it. Add
p03 GBR-BT-01, p03 MLT-BT-01/02, p04 GBR-BT-02 and p08 DEU-RG-02 to the
table with the reason they do not change.

Disposition hint: change the test

---

## RT1-06: The off-target guardrail will likely decide the result, and it is not sized

Severity: Medium

What breaks: A page is unclean if any of its non-primary cells has a
material error in any of 3 runs. A page has about 7 to 23 non-primary
cells. The why-80 reasoning covers only the primary decisions. Simple
model (independent errors per cell per run, 30 pages): with 15
non-primary cells, a 0.5% per-cell error rate passes the guardrail only
about 60% of the time; 1% passes about 4% of the time. July (one run)
had 8 errors in 184 judged cells on 5 of 12 pages; even after the reader
fix, 2 of 12 pages (p06, p10) stay unclean in a single run. Also, these
cells were not designed, only blind-labelled, so key noise lands here.
Finally, sibling rules count twice: a missed GBR-PC-01 primary also
makes MLT-PC-01 and DEU-PC-02 on the same page off-target errors, so one
mistake is both a failed case and an unclean page.

Evidence:
- `evals/eval_config.yaml:91-102`. The stated support (24 of 30 clean
  gives a one-sided 95% lower bound of about 64%) is correct: computed
  0.643.
- Computed with keyless Python: n=15 cells, p=0.005 gives P(at most 6
  unclean) = 0.60; p=0.01 gives 0.04; n=10, p=0.01 gives 0.30.
- `evals/EVAL_RESULTS.md` July miss analysis and the 2026-11-02 note.

Proposed resolution: Owner decision before freeze, one of: (a) count an
off-target cell as a material error only if it is wrong in at least 2 of
3 runs, and exclude cells that share the primary's trigger (sibling
rules); (b) widen to at most 9 of 30 unclean (about 53% supported);
(c) make the guardrail report-only. Write the expected error rate and
the reason next to the threshold.

Disposition hint: change the test

---

## RT1-07: The 3 runs are not required to be independent

Severity: Medium

What breaks: The gate needs 3 runs per case. Nothing says each run
starts from an empty ledger and audit database. The system is built to
be idempotent (FI-6: a rerun on identical input makes no new findings),
and A2 itself checks that a resume on the same DB makes zero model calls.
If two runs share a DB or a result cache, runs 2 and 3 copy run 1, and
the "right in all 3 runs" rule tests nothing.

Evidence:
- `evals/eval_config.yaml:25, 84-85` (3 runs) and `:57` (resume makes
  zero model calls).
- `BLUEPRINT.md` §6 FI-6 (dedup on content hash).
- `evals/run_eval.py:336` (DB path depends only on run_id).

Proposed resolution: Config rule: each official run uses a new, empty
ledger DB and audit DB and no local result cache. A2 check: every check
task in every run has at least one model call recorded in that run's
audit DB. Record each run's DB file name in the series record.

Disposition hint: change the test

---

## RT1-08: Result rules leave paths that are not classified or can be mislabelled

Severity: Medium

What breaks:
- A bug in system code that crashes or hangs the runner looks like a
  "runner crash" or "the runner's own timeout", so it becomes INVALID
  RUN with a free rerun, not FAIL.
- "Provider rate limit" is INVALID, but a rate limit hit by an agent
  that loops is a system fault.
- It is not said whether an INVALID run is redone alone or the whole
  series restarts, or that the decision is made before any score is
  read. Seeing partial scores and then calling a run invalid is a
  re-roll.
- NOT ENOUGH CASES is "fewer than 30 valid cases", but "valid case" is
  not defined. If the owner later rules one case wrong, a FAIL could be
  turned into NOT ENOUGH CASES.
- A1 and A3 run before the series. If one fails, no class applies,
  because FAIL requires "series completed".
- A manifest mismatch is INVALID with "no extra approval". After a run,
  editing a holdout page and committing a new manifest would silently
  change cases.

Evidence: `evals/eval_config.yaml:113-125`, `:38-39`, `:65`; the
eval-gate skill §6 and §7 (a wrong case is corrected only by a recorded
owner decision; the old result stays).

Proposed resolution: (1) Any exception or hang raised while code under
`orchestrator/`, `agents/`, `nodes/`, `intake/` or `gate/` is running is
inside the automation: the run completes as scored, non-terminal tasks
fail A2, result FAIL. INVALID only for errors raised in runner or
grader code, auth failure, or a provider error code logged before any
task starts. (2) INVALID is decided from exit codes and logged error
types only, before scoring; the whole series restarts. (3) Define a
valid case: listed in the manifest committed before the first run and
passing the self-check. A case ruled wrong after a run does not change
that run's result. (4) A1 or A3 failure before the series is recorded
as FAIL for that commit. (5) The manifest is immutable after the first
run; a changed holdout gets a new holdout ID by owner decision.

Disposition hint: change the test

---

## RT1-09: Sanitized results can reveal holdout answers; no place for the miss analysis

Severity: Medium

What breaks: The per-case fields `rule_id` and `miss_category` tell the
reader the primary rule of every case, and for failed cases the expected
verdict: NOT_ASSERTED, OFF_PAGE, NO_OVERLAP and ABSENT_ON_TEXT mean
"expected VIOLATION" (ABSENT_ON_TEXT also means text type);
ASSERTED_ON_NON_VIOLATION means "expected COMPLIANT or N/A". The type of
`false_alarm_cells` and `missed_cells` is not given; if they are lists
of rule_ids they publish key verdicts. This matters because the config
retires a holdout only after a FAIL. After a PASS, the eval-gate skill
§8 has a later version rerun the same test, now with these hints public.
Separately, the eval-gate skill requires a miss analysis ("what failed
and the pattern") in every results entry, but the allowlist has no field
for it, so the analysis either breaks the allowlist or is missing.

Evidence: `evals/eval_config.yaml:125, 131-137`; the eval-gate skill
"Results entry" and §8.

Proposed resolution: (1) State that a holdout is retired after any
completed official series, PASS or FAIL; later versions use a fresh
holdout. Or keep `rule_id` and `miss_category` in the private results
only. (2) Define `false_alarm_cells` and `missed_cells` as integer
counts. (3) Add one allowed free-text field `miss_pattern`, written by
the owner, with no page text, spans or rule wording from a page.

Disposition hint: change the test

---

## RT1-10: Holdout text can reach the build workspace

Severity: Medium

What breaks: The official run will create files that hold holdout page
text, excerpts and rationales: the ledger and audit DBs (today written
in the repo root), console output (an A3 failure would print the
missing span), and tracebacks. A later build session in this repo can
read them, so the builder can learn the holdout. The page reader is
caged to `evals/dataset/pages/`, so the easy way to run a holdout is to
copy its pages into a tracked folder. Also, the folder
`evals/v2/holdouts/` already exists, is untracked and is not ignored by
Git, so `git add evals/v2/` stages whatever is in it. (I did not open
it.)

Evidence:
- `evals/run_eval.py:336` (`official_gate_<run_id>.db` in the repo
  root); `evals/dev_score.py` (`AUDIT_DB_PATH`).
- `agents/checker/pages.py` (cage root `PAGES_ROOT` from config,
  currently `evals/dataset/pages/`).
- `git check-ignore -v evals/v2/holdouts` returned exit 1 (not ignored).

Proposed resolution: Config and P2: official runs read pages from
`holdout_root` by switching the cage root through the local setting,
never by copying pages into the repo; they write DBs and logs under
`holdout_root`; the runner prints sanitized output only. Add
`.gitignore` lines `evals/v2/holdouts/*` and
`!evals/v2/holdouts/*.sha256`, and a CI check that fails on any other
file there. Name the gitignored file that holds `holdout_root`.

Disposition hint: change the build (P2)

---

## RT1-11: The grader's text and the system's text can differ, so a correct excerpt can fail

Severity: Medium

What breaks: Three parts read page text: the grader's own extractor,
the system reader (`read_page`), and the checker tool's verbatim check
(D5 fix). The spec does not make them agree on:
- block boundaries: `<li>A</li><li>B</li>` can become "AB" in one and
  "A B" in another, so a quote across two elements fails as OFF_PAGE;
- HTML entities (`T&amp;Cs` on p12), `<title>`, `<nav>`, alt text,
  hidden elements, and bullets a reader may add;
- characters the normalize rule misses: German quotes (U+201E),
  guillemets, the hyphens U+2010 and U+2011, soft hyphen U+00AD and
  zero-width space U+200B (NFKC keeps all of these, tested);
- excerpt habits: quotes wrapped around the excerpt, or "[…]". July
  excerpts already used "...".
Also, NFKC turns "…" into "...", so the order of the normalize steps
matters; the config lists the right order but does not say it binds.

Evidence: `evals/eval_config.yaml:106-108`;
`evals/v2/SCENARIO_SPEC.md:98-102`; keyless test:
`unicodedata.normalize('NFKC', ...)` maps U+2026 to "...", leaves
U+201E, U+00AD, U+200B unchanged and maps U+2011 to U+2010.

Proposed resolution: One shared `normalize()` and one text rule used by
grader, reader and tool: a space at every block-element boundary, none
at inline boundaries, entities decoded, `<title>` and hidden elements
excluded (or included in all three). Normalize steps run in the listed
order. Map all Unicode quote and dash characters, remove format
characters (category Cf), strip quotes around the excerpt and brackets
around "…". Add keyless A1 tests with these inputs.

Disposition hint: change the test

---

## RT1-12: Planner-integrity checks pass when the planner proposes nothing

Severity: Medium

What breaks: Every planner check starts with "every proposal". With zero
proposals, all checks pass, and the public claim still says "all ...
planner-integrity checks passed".

Evidence: `evals/eval_config.yaml:58-63, 186-188`.

Proposed resolution: Add an A2 check: every CONFIRMED VIOLATION finding
has exactly one PENDING proposal.

Disposition hint: change the test

---

## RT1-13: The rule files are not pinned by the gate

Severity: Medium

What breaks: The holdout key is labelled against the signed v1.1 text,
but the system reads `rulesets/*.json`, which can be edited at any time
as a system input while the label still says `v1.1`. After a FAIL, extra
notes could be added that steer the checker toward the next holdout's
readings, and the series record would not show it. Also the config says
`status: FROZEN`, while the ruleset it depends on is only PROPOSED.

Evidence: `evals/eval_config.yaml:9-11, 164` (version string only);
`evals/v2/RULESET_V1_1.md:3-5`.

Proposed resolution: After signature, record the SHA-256 of the three
JSON files in the config. Add `ruleset_sha256` to the series allowlist
and an A2 check that the run used those exact files. Set the status to
"FROZEN on ruleset signature" until the owner signs.

Disposition hint: change the test

---

## RT1-14: A3 would not have caught the July reader defect

Severity: Medium

What breaks: A3 checks only the key spans of text-type violations and
the required strings of absence cells. Compliant and N/A primaries have
no spans, and non-primary content is not checked. On July p09 the
primary is COMPLIANT, so A3 checks nothing there, although the current
reader drops the heading that holds all the offer terms; that defect
caused 3 July false alarms on p09. Also the absence half passes for a
reader that drops everything.

Evidence: `evals/eval_config.yaml:64-70`. Keyless run of
`agents.checker.pages.read_page('p09.html')`: the heading text "20x
wagering, min deposit" is not in the output; `p04.html` list items are
not in the output.

Proposed resolution: A3 also checks every primary trigger, and checks
that every text block of the grader's text appears in the reader's text
(block-level containment, after shared normalization).

Disposition hint: change the test

---

## RT1-15: The independence checks are easy to pass and the claim says "independently authored"

Severity: Low

What breaks: Rule 1 blocks only exact matches: the same normalized
trigger text, or the exact same sequence of tags and class names.
Changing one word or one class name passes. One spec author writes all
30 briefs and one page author writes all pages, so "independently
authored" in the public claim says more than the protocol gives.

Evidence: `evals/v2/SCENARIO_SPEC.md:54-57, 110-114`;
`evals/eval_config.yaml:185`.

Proposed resolution: Add near-duplicate checks (for example word-set
overlap of triggers at or above 0.6 stops the self-check; tag sequence
compared without class names, with an edit-distance limit). Say
"separately briefed" in the claim.

Disposition hint: change the test

---

## RT1-16: Public claim wording mixes the sample and the population

Severity: Low

What breaks: "At least 80% of 30 ... got their predeclared decision
right ... (95% confidence)" describes the 30 cases (a PASS means at
least 28 of 30) and then adds a confidence level that only fits a
statement about the rate. "With valid evidence" is not true for absence
cases (assertion only). The wording does not say how many earlier
series failed, which matters because there is no attempt limit.

Evidence: `evals/eval_config.yaml:88, 183-188`.

Proposed resolution: "N of 30 synthetic scenarios (at most 2 failed)
got their predeclared decision right in all 3 runs, with evidence
checked for text violations. This supports a pass rate of at least 80%
(one-sided 95%) for scenarios drawn under this spec. Earlier series:
k, all recorded."

Disposition hint: change the test

---

## RT1-17: The July development suite cannot use "the same grading"

Severity: Low

What breaks: The spec says the July set uses the same runner and
grading as the holdout and its key is "unchanged". But the July key has
no primary, spans, evidence type or required content, so evidence
grading and A3 (which the config says is reported on the July key)
cannot run. Also, the primaries are said to come from `PAGE_BRIEFS.md`,
but the briefs do not name primaries: the p06 "risk-free is not free"
boundary is in the P11 brief, and p10's brief distractor is "No promo
code needed", not the expiry reminder. 5 of the 12 primaries (p01, p06,
p09, p10, p11) are cells the July run missed. The values themselves
match the key exactly (checked all 12).

Evidence: `evals/answer_key.yaml` top-level keys are `version, status,
derivation, total_cells, violations, pages`;
`evals/v2/SCENARIO_SPEC.md:147-169`; `evals/eval_config.yaml:70`;
`evals/provenance/PAGE_BRIEFS.md`.

Proposed resolution: Commit a July primary-evidence file (spans copied
from the verbatim strings in the briefs, evidence type, required
content) before P2 code. Change "from PAGE_BRIEFS.md" to "chosen in P1,
including 5 July miss cells". Report July numbers as regression only.

Disposition hint: change the test

---

## RT1-18: Small consistency gaps between the documents

Severity: Low

What breaks:
- Spec §3 and the ruleset risk note point to a "§9 test-scope
  statement", but `SCENARIO_SPEC.md` ends at §8.
- A1 lists "regression tests for D1 and D3-D9", but its words name the
  scorer fix (D2) and do not name D3 (verifier pin) or D5 (evidence
  check).
- "holdout markers" for the extended leak check are not defined.
- Three NOT_APPLICABLE primaries are required, but grading treats N/A
  the same as COMPLIANT, so that mix rule tests nothing extra (v1 had a
  separate N/A gate).

Evidence: `evals/v2/SCENARIO_SPEC.md:61-63`;
`evals/v2/RULESET_V1_1.md:100`; `evals/eval_config.yaml:43, 55, 89,
97`; `STATE.md` defect list D1-D10.

Proposed resolution: Point to the eval-gate skill §9 handoff statement
(or add §9). Fix the D-list. Define holdout markers (for example the
case IDs and key file name). Say in the config that N/A primaries test
"not flagged" only.

Disposition hint: change the test

---

## RT1-19: An absence case can be written with a paraphrased required line

Severity: Low

What breaks: The self-check stops only if the exact required string is
present. A page that carries a paraphrase ("Regulated in Malta, licence
MGA/EX/001/2026") passes the check as an absence case, while a good
checker sees a licence reference and answers COMPLIANT. The blind
labeler will probably catch it, but the check does not.

Evidence: `evals/v2/SCENARIO_SPEC.md:92-93`.

Proposed resolution: For each absence case, the key also lists core
tokens (licence number, "18+", help resource name) and the self-check
stops if any appears.

Disposition hint: change the test

---

## RT1-20: The v1.1 notes repeat July distractor wording

Severity: Low

What breaks: The notes name no page, but some examples are close to
July text: "a calm reminder that an unused offer will expire" (p10),
urgency on "a newsletter sign-up" (p09), "lose nothing" backed by a
refund (p11). July results after v1.1 will improve partly because the
rules now describe those exact pages, so they are not independent
evidence that the repair works. The gate is not affected because July is
not gated.

Evidence: `evals/v2/RULESET_V1_1.md:47, 50`; pages p09, p10, p11.

Proposed resolution: Keep the notes; say in the test-scope statement
that July numbers after v1.1 are regression evidence only.

Disposition hint: no change (known limit)

---

## RT1-21: Holdout author isolation rests on instructions only

Severity: Low

What breaks: The spec says no author or labeler sees earlier results or
miss notes, and that authors work only in the private folder. Nothing
mechanical enforces this: an author session started inside this repo
reads `STATE.md` and `EVAL_RESULTS.md` at boot, and any build session
can read `holdout_root` if it chooses to.

Evidence: `evals/v2/SCENARIO_SPEC.md:110-114, 128-131`; this repo's
`CLAUDE.md` boot rule.

Proposed resolution: Author and labeler sessions start in the private
folder with no repo open; the private adjudication file records the
start folder of each session. State the rest as a named limit.

Disposition hint: no change (known limit)

---

Findings: 21; changed the build: 1; changed the test: 18; no change: 2

---

## Resolution (builder, 2026-11-02, before any holdout was authored)

The red team's line above is its own proposal. Below is what the builder
did. Files: `evals/eval_config.yaml`, `evals/v2/SCENARIO_SPEC.md`,
`evals/v2/RULESET_V1_1.md`, `evals/check_holdout.py`,
`tests/test_check_holdout.py`, `evals/v2/july_primaries.yaml`,
`.gitignore`.

| Finding | Resolution | Disposition |
|---|---|---|
| RT1-01 | Primary not decided (FAILED, DEAD_LETTER, no finding) is a miss for every expected verdict; an undecided off-target cell is a material error; A2 coverage check added | changed the test |
| RT1-02 | Core span (first span) must be overlapped; every span occurs exactly once (self-check); length cap max(200, 2 x core span) | changed the test |
| RT1-03 | New evidence type `missing_term`: `ABSENT:` or overlap with the offer span passes | changed the test |
| RT1-04 | Rule families (computed from the rule files) capped at 2 cases; GEO minimum lowered to 2, other categories stay at 5 | changed the test |
| RT1-05 | v1.1 notes narrowed (offers only for "free"; odds boost is not a bonus offer for BT rules; DEU-RG-02 needs a named operator, product or offer; GBR-RG-02 definition "for this rule"); the named cells added to the July table | changed the test |
| RT1-06 | Not changed by the builder: the approved reading stays in the config. Owner decision requested at the P1 stop (count a cell only if wrong in at least 2 of 3 runs; do not score sibling cells). Both readings are reported as diagnostics | resolved: changed the test (owner ruling 2026-11-02, see below) |
| RT1-07 | Fresh ledger and audit DB per run; A2 check that each task has a model call in its own run | changed the test |
| RT1-08 | INVALID only for runner or grader code errors, provider auth, rate-limit or overload errors, manifest or pin mismatch at start; decided before scoring; whole series reruns; valid case defined; A1 or A3 failure is FAIL for that commit; manifest immutable after first run | changed the test |
| RT1-09 | Holdout retired after any completed series; off-target fields are integer counts; owner-approved `miss_pattern` field added | changed the test |
| RT1-10 | `.gitignore` keeps everything except `*.sha256` out of `evals/v2/holdouts/`, and ignores `config.local.yaml`; P2 switches the cage root to `holdout_root`, writes DBs and logs there, sanitizes console output | changed the build (P2) |
| RT1-11 | Normalize extended (all quotes and dashes, format characters removed, fixed order); one shared text rule; P2 makes grader, reader and tool share one module; A1 test with these inputs required | changed the test |
| RT1-12 | A2: every CONFIRMED VIOLATION has exactly one PENDING proposal | changed the test |
| RT1-13 | Config status is "frozen on owner sign-off"; rule-file SHA-256 recorded after signature; A2 check and allowlist field added | changed the test |
| RT1-14 | A3 also checks every text block of the grader's text and every primary trigger | changed the test |
| RT1-15 | Near-duplicate trigger check (60% shared words) and class-free tag-sequence check added; claim says "separately briefed" | changed the test |
| RT1-16 | Public claim wording rewritten as proposed (sample count, rate claim, evidence only for text violations, earlier series count) | changed the test |
| RT1-17 | `evals/v2/july_primaries.yaml` added with spans, evidence types and layouts, checked by a keyless test against the pages and the v1.0 key; wording "chosen in P1, 5 July miss cells" | changed the test |
| RT1-18 | §9 now points to the eval-gate skill; A1 D-list rewritten; holdout markers defined; N/A primaries stated as "not flagged" only | changed the test |
| RT1-19 | `absent_tokens` required for absent cases and checked | changed the test |
| RT1-20 | Recorded as a known limit in `RULESET_V1_1.md` and the config | no change (known limit) |
| RT1-21 | Recorded as a known limit in the spec §6 | no change (known limit) |

Owner ruling on RT1-06 (2026-11-02): an off-target material error counts
toward the guardrail only when the same cell is wrong in at least 2 of 3
runs; all non-primary cells stay scored (no sibling cells left out);
one-off errors are reported as a diagnostic. Written into
`evals/eval_config.yaml`. RT1-06 is now "changed the test".
Findings: 21; changed the build: 1; changed the test: 18; no change: 2
