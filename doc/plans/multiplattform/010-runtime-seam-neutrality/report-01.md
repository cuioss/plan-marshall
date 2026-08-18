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
- `UV_HTTP_TIMEOUT=600` was set on every `./pw` call. No `uv.lock` churn appeared at any point;
  deliverable paths were staged explicitly, never `git add -A`.

## Findings

Nine verification rounds ran. Every round found defects in the previous round's fixes. Findings are
recorded per instance below, grouped by round, with disposition.

| Round | Findings | Disposition |
|---|---|---|
| 1 (cold read of the ABC, no concrete runtime in context) | 8 | all fixed — `0a9796b` |
| 2 (full verification) | 5 A-class + 1 B survivor + 4 residuals | 5 fixed, survivor closed with 4 tests — `51fffd7`; 1 further site — `5dbab2f` |
| 3 (audit of rounds 1–2's fixes) | 7 A-class | all fixed — `0af667e` |
| 4 → reported as round 5 | 6 A-class | all fixed — `dca6e6f` |
| 6 (budget ceiling) | 8 A-class | all fixed — `ddf9d23` |
| 7 | 10 A-class | all fixed — `c6f3a3a`, `eb6bd3f` |
| 8 | 13 A-class | all fixed — `5e2e6ac`, `5888f22` |
| 9 (harm-focused) | 3 with consequence, none blocking | F1 fixed; F2/F3 recorded as residue |

**Defects this run introduced and then had to fix — recorded because they are the run's own error
rate, not the plan's.** Four invented rationales in four consecutive rounds: a claim that the runtime
imports "cannot move into this block" (disproved by executing the relocation); a claim that
`marketplace_paths`' fallback "matches the router's" (the router errors instead); a claim that the
two registration dicts had "drifted before" (no such commit exists); a claim that "a comment line
ends an isort group" (ruff's own fix inserts a blank line). Two invented counts: "three edits"
corrected to "four dispositions", itself corrected — there are five, and the fix was to stop counting
and name them. One invented wire format: the `project install-hook` TOON examples were written by
hand and documented an inline list syntax the serializer has never produced, plus a render-event
label that does not exist.

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
and had already hidden a defect.

### The stop record

- **Which exit ended the loop, and when.** The original budget was **6 rounds, declared before the
  first dispatch** (the plan named none, so the run did). It was **exhausted at round 6** — the
  budget exit, not the verifier exit. Everything condition A forbids was fixed regardless, because A
  is not subject to the budget. The operator then granted **five further rounds**; rounds 7–9 ran and
  the operator's grant is not exhausted. **The loop is being stopped by judgment, not by exhaustion**
  — see the residue note below.
- **The verifier's own last answer** (round 9, quoted, not paraphrased): *"No. Nothing false remains
  that a reader or operator would act on."* and *"Ship it. Open the PR now. … Nothing must be fixed
  first."*
- **Evidence stronger than a read.** Round 9 did not re-read: it executed every documented command
  against three throwaway projects (`claude`, `opencode`, an unregistered target) and compared
  outputs. Three of the five `project install-hook` captures reproduce **byte-for-byte**. The
  `unknown_overwrite_key` rejection, the `overwritten` dispositions, the empty-stdout/stderr-outcome
  split of `session render-title`, and the OpenCode decline were all reproduced live. Separately, the
  22-block automated TOON normalisation was proved meaning-preserving by re-parsing all 81 blocks
  before and after: exactly three semantic differences, all of them the deliberate `target:`
  correction.
- **Were the late rounds' findings narrower?** **No — and this is the honest answer, not the
  convenient one.** Rounds 5→8 went 7 → 8 → 10 → 13 A-class findings. Round 7 judged them *wider*
  than earlier rounds', and round 8 agreed. Only round 9, under a deliberately narrowed
  harm-focused charter, returned a short list.
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
- **19 TOON-fenced blocks outside `platform-runtime/standards/` do not round-trip** — mostly
  `marshall-steward` tab-tables mislabelled as `toon`, plus two genuine payloads in
  `error-handling.md`. The new doc-pin's guarantee stops at the platform-runtime standards.
- **`_claude_runtime_impl.py:50` hardcodes `"valid targets are: claude, opencode"`** inside the
  Claude runtime while the router derives the same message from `_REGISTRY`. A target enumeration in
  a concrete runtime — small, but exactly this epic's subject.

## Reviewer participation

_The PR is opened as the final step of this run; reviewer verdicts are recorded against it there, per
the population derived from `automatic-review/standards/{bot_kind}.md` (`coderabbitai`,
`cuioss-review-bot`, `sourcery-ai`)._

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
| 7 PR cycle | **pending at write time** — the PR is opened immediately after this commit, which is why the report cannot carry its number (Step 8 condition 3 requires the report to land *in* the PR) |
| 8 Merge gate | **pending** — conditions 1–3 evaluated after the PR opens |
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

**A contract change was proposed, approved by the operator, and shipped as a separate PR** on
`chore/cloud-plan-lane-round-budget`, cut from `main` and touching only
`.claude/skills/cloud-plan-lane/SKILL.md`.

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
run at round five, which is worse than stopping with survivors disclosed. Six sites restating the
budget rule moved together.

*Validated by this run:* the operator extension at round 6 → 7 is exactly the checkpoint the change
describes, and it worked — it surfaced the decision at the moment it was load-bearing.

**A second lesson this run paid for, not yet proposed as a contract change.** The skill's
verification loop has no mechanism requiring a documentation claim to be *pinned to its producer*.
Every fix for eight rounds was a re-asserted sentence checked by the same reader who wrote it, which
is why the same defect class regenerated. This run built one such mechanism
(`test_contract_doc_toon_is_canonical.py`) and it immediately caught 22 defects no human round had
found. Whether the lane should require that pattern — a machine check between a claim and the code
that makes it true — is worth the operator's consideration, but it is a design question larger than
this run's evidence, so it is recorded rather than proposed.

## Residue

Listed in the Findings section above under "Residue for a later plan", plus the three characterised
survivors S1–S3. The highest-value item is the `health_check` `permissions` detail naming
`settings.local.json` when the check resolved `settings.json` — the one residue where an operator
acting on the output touches the wrong file.
