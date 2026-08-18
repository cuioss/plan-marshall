# Run report — 010-runtime-seam-neutrality (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/runtime-seam-neutrality-osuaxx` (harness-assigned; kept as-is per the lane contract)    **PR:** see the landing record below    **Outcome:** completed

## Skills loaded

Loaded by reading the bundle source path — the `plan-marshall` plugin is not installed in this cloud
session, so `Skill: {bundle}:{skill}` notation was not attempted.

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, `.claude/skills/`) — first action of the run |
| `plan-marshall:ref-code-quality` | bundle path |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `plan-marshall:persona-implementer` | bundle path (production code) |
| `pm-dev-python:python-core` | bundle path (Python production code) |
| `pm-dev-python:pytest-testing` | bundle path (Python tests) |

No skill was unobtainable by either route.

Epic context read alongside: `doc/plans/multiplattform/reference/principles.md` (the governing
cross-cutting principles, §6 in particular).

## Deliverables

| # | Deliverable | Commit | Verification state |
|---|---|---|---|
| D4 | Parameterized OpenCode dispatch | `ecccbbe` | Red-first demonstrated, then green |
| D3 | Registration consolidated | `29c58d6` | Both lockstep invariants demonstrated red against deliberate mismatches, then green |
| D1 | Target-opaque install op | `e43e2e7` | New guard mutation-tested; existing Claude install behaviour unchanged in effect |
| D2 | Target-neutral ABC docstrings | `12fa439` | Zero-hit search re-run at verification time |

**D1 — Target-opaque install op.** `runtime_base.project_install_hook` now states intent only. Its
docstring carries no Claude hook-event name, no `CLAUDE_CODE_*` string, and no settings-file path;
the only `.json` in it is `marshal.json`, plan-marshall's own file. The signature's `target` is the
target identifier, and the Claude settings-path resolution — including the absolute-path
test/recovery override — moved into `_claude_runtime_impl`, documented there and advertised by
neither the ABC nor the router help.

The two Claude-named booleans `overwrite_statusline` / `overwrite_env_disable` were named in the
plan's Problem §1 as part of the coupling, and D1's goal statement requires the `statusLine` command
to appear only in the Claude implementation — so a rename was mandatory. They became one
`overwrite: Sequence[str]` of **target-defined conflict keys**. That shape was chosen over two
renamed booleans because two booleans would still hardcode *two* conflict points in the shared ABC,
which is principle 6's "core-owned target table" in miniature; the sequence lets a third target with
different conflict points need no ABC change at all. Claude defines `statusline` and `env-disable`
and rejects anything else with `unknown_overwrite_key` **before any write**, because silently
ignoring a typo would answer "conflict preserved" to a caller who explicitly asked to overwrite.

Existing Claude install behaviour is pinned by the pre-existing test bodies, which pass unchanged in
effect: the ~60 call sites that pass an absolute `tmp_path` still work, because the recovery override
survives inside the Claude implementation. Only the two `overwrite_*=True` call sites changed shape.

**A refuted plan claim.** The plan labelled as HYPOTHESIS: *"No caller outside `platform-runtime`
constructs the Claude settings path for the install op."* This is **refuted**.
`marshall-steward/references/menu-healthcheck.md` invoked
`project install-hook --target .claude/settings.local.json` — a **relative** path, which the
implementation has been rejecting with `unknown_target` since the `candidate.is_absolute()` guard
was introduced. That documented invocation could not have worked. It now passes `--target claude`
and reads the resolved file from the response's `settings_path`; two neighbouring prose statements
in the same file that asserted the write would land in `./.claude/settings.local.json` were
corrected with it, since `--target claude` may resolve to `.claude/settings.json` instead.

**D2 — Target-neutral ABC docstrings.** The hit list was re-derived by search rather than taken from
the plan: eleven `On Claude` hits and eleven `On OpenCode` hits, spanning `layout_skill_roots`,
`layout_bundle_cache_root`, `session_capture`, `session_push_title_token`, `session_bind`,
`session_resolve_plan`, `session_doctor`, `session_teardown`, `session_reload_directive`,
`metrics_capture`, and `metrics_normalized_tokens` — plus `subagent_dispatch`'s inline
"``Task:`` on Claude, ``task`` on OpenCode". A case-sensitive search for both phrases over
`runtime_base.py` now returns **0**.

Three further target leaks in the same file, outside the `On Claude` hit list but the same
anti-pattern, were cleared under D2's goal (a third implementer reading `runtime_base.py` alone):
the module docstring naming both concrete classes, `project_initial_setup`'s `target` argument
documented as `"claude"` or `"opencode"`, and `metrics_normalized_tokens`' doc-residency example
naming `CLAUDE.md`. A search for `Claude|OpenCode|claude|opencode|CLAUDE` over `runtime_base.py`
now returns zero hits of any kind.

Displaced notes landed in the concrete classes: Claude gained the `hook_not_configured` rationale on
`session_capture`, the transcript-sum note on `metrics_capture`, the transcript paths / record shapes
/ `CLAUDE.md` doc-residency member on `metrics_normalized_tokens`, and the tool-name plus passthrough
note on `subagent_dispatch`; OpenCode gained the reason its `session_capture` declines as `no-op`
rather than `hook_not_configured`, and the "explicit count is always honoured" note on
`metrics_capture`.

**D3 — Registration consolidated.** `platform_runtime.py` declares `_DEFAULT_TARGET`, `_REGISTRY`
and `_TARGET_BOOTSTRAP_LIBS` adjacently as one block; all three argparse defaults and the bare
fallback read the constant. `_TARGET_BOOTSTRAP_LIBS` could only move below the pre-import bootstrap
call once `_bootstrap_glob_discover` guarded on `target is not None` — the pre-import call passes
`None`, so the name is never evaluated at that point. The literal `"claude"` now appears in
`platform_runtime.py` only inside the registration block and the constant definition.

`marketplace_paths.py`'s three fallback returns collapse onto `_DEFAULT_RUNTIME_TARGET`.

**One addition beyond D3's stated "Done when".** `marketplace_paths._invoke_layout_op` carried its
own `if target == 'opencode': … else: ClaudeRuntime` branch — a second target→class registration
site in a shared script, and precisely principle 6's forbidden `if target == …`. It now resolves the
class through the router's `_make_runtime`, so the module names no runtime class and enumerates no
target. This is not in D3's literal done-when, but the plan's **Goal** ("adding a runtime target is
one registration edit plus one default constant") is unreachable while adding target X still
requires editing `marketplace_paths.py`. Recorded here as a deliberate, Goal-driven addition rather
than silent scope creep.

**D4 — Parameterized OpenCode dispatch.** The literal `execution-context-level-3` no longer appears
in `opencode_runtime.py`; `subagent_type` echoes the requested `agent`, mirroring the Claude
passthrough. `standards/contract.md` states the passthrough as a cross-target rule.

### Coupling-inventory closure (operator-directed, outside the plan's Expected surface)

The run initially recorded as residue that `reference/coupling-inventory.md` lists this plan's four
couplings under a section it labels **open**, that landing this PR makes those rows false, and that
the document states no convention for retiring a row — so inventing one unilaterally would couple
this PR to an epic-level decision. The operator directed the run to establish the convention and
apply it. Both are done, and both are outside the plan's Expected surface; they are recorded here as
an operator-authorised addition rather than as plan scope.

**The convention** is stated in the inventory's own preamble (`§ Closing a row`), because the
document owns its rows. Its load-bearing rule is that a row is retired **on a re-derivation, never
on a plan's merge status** — a plan can land with a deliverable descoped, so retiring rows on merge
would record work that was never done. The three re-derivation outcomes (finds nothing → delete;
still finds it → keep, narrowed to the residue; cannot be re-derived → treat as not closed, and
rewrite the row first) are tabulated there. A closed row is deleted rather than archived, because a
"formerly open" section would make the work list a changelog, which the repository's documentation
standards forbid; the durable record is the closing plan's run report, which git holds. The one
carve-out is a row closed by *deciding* rather than *removing*: it moves to **Deliberate
non-migrations** or **Confirmed clean** instead of vanishing, so intent is never mistaken for
oversight. The epic README carries a one-line obligation pointing at it, so a plan executor meets it
without the rule being restated.

**The closure.** Each of §A's four rows was re-derived against the tree before deletion, per the
convention applied to itself: the Claude hook-event vocabulary / `statusLine` / `CLAUDE_CODE_*` /
settings-path search over `runtime_base.py` → 0; `On Claude` / `On OpenCode` → 0;
`execution-context-level-3` in `opencode_runtime.py` → 0; `_DEFAULT_TARGET` present and consumed at
every argparse default and fallback, with `marketplace_paths` on `_DEFAULT_RUNTIME_TARGET`. All four
re-derive clean, so all four are deleted. §A held only `010` rows, so it now holds none; per the
convention it keeps its heading and records what was re-derived, since deleting the heading would
leave a reader unable to distinguish a category checked and found clear from one nobody looked at.

No row of this plan's closed clean by decision rather than removal, so nothing moved into the two
intent sections. The plan's one deliberate non-migration (`wait_for` call sites) was already recorded
there before this run.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` returns **11 files** (19 changed in total) —
Python changes are present, so the gate applies. Re-derived at finalisation; the draft said 10,
before the verification rounds added a test file.

- Per-commit gate: every commit touching `*.py` was preceded by a clean gate — `ruff … All checks
  passed!`, `mypy … Success`, `SPDX-header check passed`, plugin-doctor `status: pass` /
  `total_issues: 0` / empty `issues[]`. The plan-directory commit (`a21b353`) is a pure `git mv` and
  needed no gate. **This is a claim about the run's own process, not something the tree records** —
  no artifact preserves a per-commit gate history, so a reader can verify only the head.
- Branch gate: `./pw verify` (all three sub-steps — quality-gate, test-compile, module-tests) run
  over the branch diff at finalisation: **`=== verify: SUCCESS ===`, 20655 passed, 14 skipped**,
  mypy clean over 411 production and 763 test files, plugin-doctor `total_issues: 0`. The draft's
  20565 was measured before the verification rounds added tests and is superseded, not corrected —
  it was true when written.
- Post-merge gate: `origin/main` moved to `b199d94` while the PR was open, making it un-mergeable.
  The base branch was merged in (`ccf1ff0`) and `./pw verify` re-run over the result:
  **`=== verify: SUCCESS ===`, 20 892 passed, 14 skipped**, mypy clean over 413 production and 770
  test files. The rise over 20 655 is `origin/main`'s own new tests, not this branch's. Superseding
  again by the same rule: each figure was true of the tree it measured.
  - The merge's two conflicts were both docstring-only, both in `session_capture`. `origin/main` had
    documented that the session id is APPENDED to `status.metadata.session_ids` rather than replacing
    a scalar — a target-general fact, so it folded into D2's target-opaque phrasing rather than
    displacing it. D2's invariant was re-checked after resolution and still holds: zero occurrences
    of `claude`/`opencode` in `runtime_base.py`, and zero `On Claude:`/`On OpenCode:` pairs anywhere
    under `platform-runtime/scripts/`.
- `UV_HTTP_TIMEOUT=600` was set on every `./pw` call. No `uv.lock` churn appeared at any point;
  deliverable paths were staged explicitly, never `git add -A`.

## Findings

**Eight verification dispatches ran, labelled 1–9 with no round 5.** An earlier draft of this section
said "nine rounds"; that was the highest label, not a count, and the table below has always had eight
rows. Round 4's findings were reported under the label "round 5" and every later label inherited the
off-by-one, which the row label recorded but the surrounding prose never reconciled.

The report **cannot** rule out that a ninth dispatch ran and went unrecorded — nothing in git
distinguishes "eight dispatches mislabelled" from "nine dispatches, one row missing", and the run's
own commit messages disagree (`0af667e` calls itself "a third verification round"; `dca6e6f` calls
itself "a fifth" while auditing "round 4's own corrections"). Eight is what the evidence supports and
is what is claimed here. A tenth dispatch ran after this section was first written and is recorded
below.

Every round **after the first** found defects in the previous round's fixes; round 1 was a cold read
of the ABC with no previous round to audit. Findings are recorded per instance below, grouped by
round label, with disposition.

| Round label | Findings | Disposition |
|---|---|---|
| 1 (cold read of the ABC, no concrete runtime in context) | 8 | all fixed — `0a9796b` |
| 2 (full verification) | 5 A-class + 1 B survivor + 4 residuals | 5 fixed, survivor closed with 4 tests — `51fffd7`; 1 further site — `5dbab2f` |
| 3 (audit of rounds 1–2's fixes) | 7 A-class | all fixed — `0af667e` |
| 4 → reported as round 5 | 6 A-class | all fixed — `dca6e6f` |
| 6 (budget ceiling) | 8 A-class | all fixed — `ddf9d23` |
| 7 | 10 A-class | all fixed — `c6f3a3a`, `eb6bd3f` |
| 8 | 13 A-class | all fixed — `5e2e6ac`, `5888f22` |
| 9 (harm-focused) | 3 with consequence, none blocking | F1 fixed; F2/F3 recorded as residue |
| 10 (run-report accuracy + the unreviewed skill branch) | 12 against this report, 8 against the skill branch | 11 report findings fixed; G1/G2 fixed; G3–G5 characterised in the skill PR |

**Defects this run introduced and then had to fix — recorded because they are the run's own error
rate, not the plan's.**

*Four invented rationales.* An earlier draft called these "four in four consecutive rounds", which
made the error rate read as a bounded burst. Traced to their introducing commits, they are not
consecutive and one was not a round's at all — they span the whole run, starting with the original
deliverable:

| Invented rationale | Introduced by | Found by |
|---|---|---|
| the runtime imports "cannot move into this block" (disproved by executing the relocation) | `51fffd7` — round 2's fix | round 3 |
| `marketplace_paths`' fallback "matches the router's" (the router errors with `unknown_target` instead) | `29c58d6` — **the D3 deliverable, not a round** | round 2 |
| the two registration dicts had "drifted before" (no such commit exists) | `ddf9d23` — round 6's fix | round 7 |
| "a comment line ends an isort group" (ruff raises `I001` and fixes it by inserting a **blank** line) | `c6f3a3a` — round 7's fix | round 8 |

*One invented count, not two.* An earlier draft claimed *"three edits" corrected to "four
dispositions", itself corrected* — a correction chain that never happened. The two are unrelated
claims in different files. "Three edits" was the registration comment's cost-of-adding-a-target and
was **true when written**; `ddf9d23` retired it by moving the imports into the block. The invented
count is `project_install_hook`'s Returns clause, which went three → four → five before the fix was
to stop counting and name the dispositions instead (`installed`, `already_present`, `migrated`,
`already_present_other`, `overwritten`).

*One invented wire format.* The `project install-hook` TOON examples were written by hand and
documented an inline list syntax the serializer has never produced, plus a render-event label that
does not exist.

**The most consequential single finding was in the original change.** `menu-healthcheck.md` told an
operator that on `status: error` the response "names in `settings_path`" the file whose permissions
to check. `toon_error` builds exactly four keys and `settings_path` is not among them. Introduced by
D1 (`e43e2e7`), it survived seven rounds and was found in round 8, three lines from text round 7 had
rewritten.

**Rejected findings, with reasons.** Round 7 proposed that `runtime_base`'s import be split out of
the registration block on the grounds that a comment ends an isort group — rejected on evidence
(ruff raises `I001` and fixes it by inserting a blank line), and the comment now records the real
constraint. Round 8's B2 (removing the placeholder exemption introduces forward-compat fragility for
a future template) was accepted as real but judged the lesser cost: the exemption was one commit old
and had already hidden a defect. **Attribution correction:** an earlier draft credited that second
finding to round 8 while also listing `5e2e6ac` among round 8's fixes — but `5e2e6ac` *is* the
exemption removal, and a round cannot both produce a commit and raise a finding against it. The
finding came from the self-audit inside `5e2e6ac` itself, whose message examines the preceding commit
`c6f3a3a`. Round 8's dispatch is not its source.

### The stop record

- **Which exit ended the loop, and when.** The skill names two exits: (i) the verifier answers that
  nothing remains, and (ii) the declared budget is spent. **The loop ended on exit (i), at the round
  labelled 9**, whose verdict is quoted below. The operator's grant of five further rounds was **not**
  spent — two remained — so exit (ii) was never reached at the end.

  An earlier draft said the loop stopped "by judgment, not by exhaustion". Judgment is not one of the
  two exits, and naming it instead of an exit left the required answer unstated while the contract
  check marked the row done. The accurate statement is exit (i), with grant unspent.

  On the budget's own history: the original budget was **6 rounds, declared before the first dispatch**
  (the plan named none, so the run did). An earlier draft said it was "exhausted at round 6" — that
  does not follow from the table, because the row labelled 6 was the **fifth** dispatch under the
  off-by-one recorded above, so only five of the six were spent when the operator was asked. The ask
  at that boundary was therefore early rather than at exhaustion. Everything condition A forbids was
  fixed regardless, because A is not subject to the budget.

  Two further dispatches ran after this record was first written: the round labelled 10, whose
  findings are folded in above and which is the source of every correction in this bullet, and the
  external review on PR #1291.
- **The verifier's own last answer** (round 9, quoted, not paraphrased): *"No. Nothing false remains
  that a reader or operator would act on."* and *"Ship it. Open the PR now. … Nothing must be fixed
  first."*
- **Evidence stronger than a read.** Round 9 did not re-read: it executed every documented command
  against three throwaway projects (`claude`, `opencode`, an unregistered target) and compared
  outputs. Three of the five `project install-hook` captures reproduce **exactly once the settings
  path is normalised** — an earlier draft said "byte-for-byte", which cannot be literally true and
  overstated the stop record's strongest evidence claim: `contract.md` states that the documented
  captures had the temporary directory rewritten to a readable repository path, so a fresh invocation
  against a throwaway project necessarily emits a different `settings_path` and only the OpenCode
  decline could match unnormalised. Every other field matched without normalisation. The
  `unknown_overwrite_key` rejection, the `overwritten` dispositions, the empty-stdout/stderr-outcome
  split of `session render-title`, and the OpenCode decline were all reproduced live. Separately, the
  22-block automated TOON normalisation was proved meaning-preserving by re-parsing all 81 blocks
  before and after: exactly three semantic differences, all of them the deliberate `target:`
  correction.
- **Were the late rounds' findings narrower?** **No — and this is the honest answer, not the
  convenient one.** The A-class counts **rose**: 7 → 8 → 10 → 13, across the rounds labelled
  **3, 6, 7 and 8**. An earlier draft attributed that sequence to "rounds 5→8", which the table above
  does not support — the round labelled 5 recorded six findings, and 7 is the count for round 3. The
  sequence and the conclusion are unchanged; only the row labels were wrong. Round 7 judged its
  findings *wider* than earlier rounds', and round 8 agreed. Only round 9, under a deliberately
  narrowed harm-focused charter, returned a short list — and narrowing the charter is how that short
  list was obtained, which is a fact about the question asked, not evidence that little remained.
- **What residue to assume remains.** Assume the documentation-truth sweep is **incomplete, not
  exhausted**. Of round 8's thirteen findings, six were introduced by round 7's own fixes or were
  n−1-of-n misses within them — the loop was generating roughly as many defects as it removed. A
  tenth round would audit round 9's prose and find its equivalents. Specifically, assume: (a) more
  reformatted-but-not-re-derived example blocks exist in `contract.md` sections this plan did not
  touch; (b) prose added by rounds 7–9 has not itself been audited; (c) the run's commit messages
  carry uncorrected slips (two known in `dca6e6f`, recorded below).
- **Known-false statements left in pushed commit messages**, uncorrectable without rewriting history:
  `dca6e6f` says "two of the reference implementation's eight outcomes are `write_failed`" (it is one
  outcome, reached from two call sites) and "false for a third of them" (4 of 24 is one sixth).
  `5dbab2f` misattributes an earlier fix to the wrong commit. The tree is correct; the messages are
  not.

### Survivors — behavioural findings left open, each characterised

| # | Finding | (a) proof / (b) bound | Re-put to the verifier in the stopping round? |
|---|---|---|---|
| S1 | `marketplace_paths._invoke_layout_op`'s `except Exception` swallows every failure with no diagnostic; four of five failure exits are uncovered | **(b)** Every reachable failure degrades to `_DEFAULT_SKILL_ROOTS` / `_DEFAULT_BUNDLE_CACHE_ROOTS`, which the lockstep tests pin equal to what the default target's op actually returns — so on Claude the fallback *is* the correct answer. On OpenCode it would silently narrow skill discovery to `.claude/skills`; OpenCode is not a tested runtime. Pre-existing; this branch did not widen it | Yes — round 9: "Not reachable as user harm" |
| S2 | `test_layout_op_resolves_each_registered_target_distinctly` asserts pairwise-distinct roots; a third target legitimately sharing a root list turns it red with no defect | **(b)** Cannot fire with two registered targets, both verified distinct. Fires visibly at target-add time, never silently. Named in the test's own docstring with the remedy | Yes — round 9: "maintenance friction… no user harm" |
| S3 | In a container with no `HOME` and no passwd entry, `claude_runtime.py`'s module-level `Path.home()` makes the whole lockstep file error at collection, so its `pytest.skip` guard never runs | **(b)** Pre-existing (`86d5298`), outside this plan's surface, and **not newly reachable**: `_invoke_layout_op` now imports `claude_runtime` on the OpenCode path too, but OpenCode's own `layout_skill_roots` calls `Path.home()` anyway, so the outcome is identical before and after. Documented in the guard's docstring | Yes — round 9: "No regression" |
| S4 | `OpenCodeRuntime.metrics_capture` reports `status: success` for an explicit `--total-tokens` while persisting nothing. The Claude implementation writes the token cursor and calls `manage-metrics end-phase` before succeeding; the OpenCode one reaches no boundary at all, so the count is acknowledged and lost | **(b)** Pre-existing; this branch rewrote the docstring that asserted the false behaviour and has now corrected it to state what the code does. Fires only when a caller passes an explicit count on an OpenCode project, and OpenCode is not a tested runtime. **Not fixed here** because the persistence boundary is target-neutral in substance but lives in `claude_runtime`, so wiring it up means relocating a helper across the target boundary — a plan, and one that would otherwise add exactly the coupling this epic removes. Inventory row added | Raised by CodeRabbit on PR #1291, confirmed by reading both implementations |
| S5 | `platform-runtime/SKILL.md` restates per-target no-op status in a shared skill body — nine of 24 op rows end in "no-op on OpenCode" | **(b)** D2's declared surface was `runtime_base.py`, so no claim in this report is falsified by it. A third target makes those nine rows silently incomplete rather than merely unstated, which is a documentation defect at target-add time, not a runtime one. Inventory row added | Derived while resolving the `origin/main` merge, which edited one of the nine rows |

### Residue for a later plan (not this plan's surface)

- **`health_check`'s `permissions` check names a file it did not check.** `_claude_runtime_impl`
  resolves `_claude_project_settings_path()` (which prefers `.claude/settings.json`) then hardcodes
  the literal `settings.local.json` in both details. In a project holding only `settings.json` it
  reports on a file that does not exist, and its unhealthy branch misdirects an operator to the wrong
  file. Pre-existing, reproduced by round 9, untouched here. **The one residue with real operator
  consequence — worth an issue.**
- **`prompt_not_found` carries two meanings** — a missing `--prompt-file` and a missing agent file.
  The `message` disambiguates, so it degrades to a wrong diagnostic rather than a wrong action.
- **Four `Runtime` operations document no way to decline** — `project_initial_setup` and
  `health_check` state "(success or error)"; both `layout_*` ops state no status vocabulary. A target
  that cannot implement them has nothing to point at. Contract-shape gap, not a Claude coupling;
  recorded in the inventory's §A as explicitly outside what its detections covered.
- **348 TOON-fenced blocks outside `platform-runtime/standards/` do not round-trip**, across roughly
  130 files. The new doc-pin's guarantee stops at the platform-runtime standards. Worst offenders:
  `manage-architecture/standards/client-api.md` (16), `manage-api.md` (15), `manage-status/SKILL.md`
  (14), `tools-integration-ci/standards/api-contract.md` (13).

  An earlier draft put this at **19** and described it as "mostly `marshall-steward` tab-tables
  mislabelled as `toon`, plus two genuine payloads in `error-handling.md`". That is the
  `marshall-steward` subtotal, not the tree-wide figure — the sweep had been run over one bundle and
  its result written up as though it were the whole. The qualifier is true of the 19 and false of the
  348, and a later plan sized off the old number would have scoped this at about 5% of its real
  extent. Re-derived with the doc-pin's own oracle over every tracked `.md`/`.adoc` outside
  `platform-runtime/standards/`.
- **`_claude_runtime_impl.py:51` hardcodes `"valid targets are: claude, opencode"`** inside the
  Claude runtime while the router derives the same message from `_REGISTRY`. A target enumeration in
  a concrete runtime — small, but exactly this epic's subject.
- **`platform-runtime/SKILL.md` carries D2's coupling one file over.** Nine of the op table's 24 rows
  end in "no-op on OpenCode", two parenthesise Claude-specific behaviour, and the frontmatter names
  both targets. D2's declared surface was `runtime_base.py`, so the report's D2 claim ("the ABC
  docstrings are target-opaque") stays true and bounded — but a reader of the *skill* still gets the
  target-coupled version of the same 24 operations. Derived while resolving the `origin/main` merge,
  which edited one of those nine rows. Added to the inventory's §C rather than fixed here: fixing it
  is a nine-row rewrite plus a no-op-surfacing decision, which is a plan, not a merge resolution.
- **Two structural refactors CodeRabbit raised on PR #1291, both real, both larger than a review fix.**
  (1) *One target-registration source of truth.* `_REGISTRY`, `_TARGET_BOOTSTRAP_LIBS`,
  `_DEFAULT_TARGET` and `_DEFAULT_RUNTIME_TARGET` remain four independent definitions; D3 made them
  adjacent and added lockstep tests, which **detect** drift after the fact but do not **prevent** an
  incomplete registration. The stronger shape is one record per target that owns its class and
  bootstrap libs, with every view derived from the record set. D3's declared goal was "a registration
  is one contiguous edit", which is met; "a registration is structurally impossible to do partially"
  is the next step and is not claimed here.
  (2) *A content-level pin for the terminal-title inventory.* `_DISPLAY_RENDER_ENTRIES` is
  authoritative but its labels are restated in `_claude_runtime_impl` and in four `contract.md`
  blocks. The new doc-pin checks TOON **shape**, so a wrong label or status value passes it — a limit
  its own docstring already states. Generating those blocks from the runtime, or diffing them against
  it, would close the gap the pin deliberately leaves open.
- **`health_check`'s documented examples do not match its serialized output** — the `display` detail
  is built by `_diagnose_display_entries` and never reads "render-title hook entry present", and the
  `hook` check probes both `.claude/settings.json` and `.claude/settings.local.json` rather than the
  one file the examples show. Same family as the first residue item above, and the same fix closes
  both: derive the documented health-check examples from a captured run.
- **The plan's Goal is wider than D2's completion criteria.** `plan.md` says a third target can
  implement or decline *every* `Runtime` operation from `runtime_base.py`; D2's criteria only check
  that target-enumerating text is gone. `project_initial_setup`, `health_check`, `layout_skill_roots`
  and `layout_bundle_cache_root` still document no way to decline (the third residue item above), so
  the Goal as written is not fully met by the criteria as written. Recorded rather than resolved: the
  honest reading is that D2 delivered its criteria and the Goal overreached them.

## Reviewer participation

PR [#1291](https://github.com/cuioss/plan-marshall/pull/1291). Population derived from
`automatic-review/standards/{bot_kind}.md` (`coderabbitai`, `cuioss-review-bot`, `sourcery-ai`).

| Reviewer | Verdict | Reopens? |
|---|---|---|
| `coderabbitai` | **reviewed** on the second push, after a rate-limit window closed the first attempt. **11 actionable comments**, merge risk 🟡 Moderate. Four were real defects confirmed by reading the implementations and are fixed: the install-hook target mismatch, the `push-title-token` no-op/success contract, the unclosed-TOON-fence drop, and the inventory row misassigned to plan 010. Two more were real and are recorded as residue with the reason they are plans rather than review fixes (a single registration record; a content-level pin for the terminal-title inventory). The rest overlap residue this report already carried. Rate-limited again on the fix commit. | yes |
| `sourcery-ai` | **declined on size** — "your pull request is larger than the review limit of 150000 diff characters". Measured: `git diff origin/main...HEAD \| wc -c` = **160 040**, over the limit by ~7%. | no |
| `cuioss-review-bot` | **did not run** — no review, no comment, no check on this PR. | n/a |

Two of the three reviewers therefore contributed **no findings at all**, and this is a coverage gap
rather than a clean bill. Recorded honestly here because a silent reviewer and an approving reviewer
are indistinguishable in the PR UI, and only one of them is evidence.

The `sourcery-ai` refusal is **structural, not transient**: the diff is over its hard limit and every
subsequent commit (the `origin/main` merge, the fixes below) only grows it, so there is no state of
this PR that Sourcery would review. Splitting the PR to get under the limit was not done — the two
largest contributors are the run report (348 lines, a lane-mandated record that cannot be dropped)
and `contract.md` (165/110, the deliverable itself). Dropping neither is possible; the gap stands.

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no token counter to the
  running agent, so no figure is stated rather than an estimated one. Nine verification sub-agents ran;
  their individual usages were reported to the orchestrating session but are not aggregated here,
  because a partial sum presented as a total is the defect this section exists to avoid.
- **Wall-clock:** run start 2026-08-17 ~18:54 UTC (container clone timestamp) through finalisation.
- **Population:** these figures count **this single Claude Code cloud session**. That is **NOT
  comparable** to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary. This session shares neither that
  boundary nor that tree, so the two cannot be reconciled and no parity is implied.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named above; all obtained by bundle path (the plugin is not installed in this session) |
| 2 Branch | **done** — harness-assigned `claude/runtime-seam-neutrality-osuaxx`, kept as-is; pushed before the first edit and after every commit |
| 3 Plan directory | **done** — `doc/plans/multiplattform/010-runtime-seam-neutrality/plan.md`, first-instruction block present and unmodified |
| 4 Implement | **done** — every commit carries the trailer; deliverables addressed |
| 4 Per-commit gate | **done** — see the Build gate caveat: this is a process claim the tree does not record |
| 4 Pushed | **done** — no unpushed commit remains |
| 5 Build gate | **done** — 11 `*.py` files changed; `./pw verify` green at finalisation |
| 6 Verification sub-agent | **done** — nine rounds, stop record above |
| 7 PR cycle | **done** — PR [#1291](https://github.com/cuioss/plan-marshall/pull/1291). The row first read "pending at write time", on the reasoning that the report cannot carry a number that does not exist yet; that is true of the first commit and stops being true once the PR is open, so the row is updated in place rather than left as a snapshot. Review cycle recorded under Reviewer participation: CodeRabbit reviewed on the second push after a rate-limit window, `sourcery-ai` declined on diff size, `cuioss-review-bot` never ran |
| 8 Merge gate | **pending** — conditions 1–3 evaluated after CI settles on the review-fix commit |
| 8 Bridge | **done** — no status or bookkeeping write landed under `doc/plans/` outside this plan's directory. The `coupling-inventory.md` and epic `README.md` edits are operator-directed deliverables, recorded above as outside the plan's Expected surface |
| 9 This check | **done** — this table |
| 9 What have we learned | **done** — below |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a cloud run never performs or records one.

**Re-verified tree claims.** The report's filesystem claims were re-checked at finalisation rather
than carried from the draft: the `*.py` count moved 10 → 11 and the suite total 20565 → 20655, both
because the verification rounds added tests. `.plan/` now holds build artifacts the draft did not
mention — the build gate created them after the draft was written.

## What have we learned (Step 9)

**A contract change was proposed, approved by the operator, and opened as
PR [#1292](https://github.com/cuioss/plan-marshall/pull/1292)** on `chore/cloud-plan-lane-round-budget`,
cut from `main` and touching only `.claude/skills/cloud-plan-lane/SKILL.md`.

An earlier draft of this section said the change was "shipped as a separate PR" while **no PR
existed** — the branch was pushed and nothing more. That is the highest-consequence defect the
run-report audit found, because it is the failure mode that loses work silently: an orchestrator
collecting this report would have filed the contract change as delivered, and it would have sat
unlanded on a branch drifting further behind `main` with nobody looking for it. The lesson is narrow
and worth keeping: *pushed* is not *shipped*, and a report may only claim the step it can name the
artifact for.

*Evidence from this run:* the skill already mandated the multi-round loop, but left the round budget
for the run itself to choose ("otherwise the run does, up front") and made the operator checkpoint
optional and backwards-framed ("a run that wants more rounds MAY ask"). This run declared six —
arbitrarily. The skill's own text warns that the author is the party motivated to stop, then hands
that author the number.

*The change:* the budget is fixed at five unless the plan sets another; a reachable operator is
**asked at the boundary**, and told what they need to decide with (rounds spent, what the last round
found, whether findings are narrowing or merely fewer, and every open survivor). A granted extension
is another five on the same terms. The headless carve-out is preserved and its rationale made
explicit, so a later editor does not simplify it away: an unconditional ask strands every unattended
run at round five, which is worse than stopping with survivors disclosed. **Seven** sites restating the
budget rule moved together (an earlier draft said six; the seventh is the escalation rule in the
closing discipline list).

*NOT validated by this run.* An earlier draft claimed the operator extension at the round 6 → 7
boundary "is exactly the checkpoint the change describes, and it worked". It is not, and the
distinction is the whole point of the change. The change describes **the run asking** — surfacing
rounds spent, what the last round found, and every open survivor, via `AskUserQuestion`, at the
boundary. What actually happened is that **the operator volunteered** further rounds without being
asked. The run never issued the ask, so the mechanism the change introduces was never exercised; what
the run demonstrates is the *absence* the change is meant to fix, not the change working. Calling
that validation would have been the report certifying a mechanism on evidence that does not touch it.

**A second lesson this run paid for, not yet proposed as a contract change.** The skill's
verification loop has no mechanism requiring a documentation claim to be *pinned to its producer*.
Every fix for eight rounds was a re-asserted sentence checked by the same reader who wrote it, which
is why the same defect class regenerated. This run built one such mechanism
(`test_contract_doc_toon_is_canonical.py`) and it immediately caught 22 defects no human round had
found. Whether the lane should require that pattern — a machine check between a claim and the code
that makes it true — is worth the operator's consideration, but it is a design question larger than
this run's evidence, so it is recorded rather than proposed.

## Residue

Listed in the Findings section above under "Residue for a later plan", plus the five characterised
survivors S1–S5. The highest-value item is the `health_check` `permissions` detail naming
`settings.local.json` when the check resolved `settings.json` — the one residue where an operator
acting on the output touches the wrong file.
