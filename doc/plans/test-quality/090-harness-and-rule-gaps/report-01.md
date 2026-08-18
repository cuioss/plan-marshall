# Run report — 090-harness-and-rule-gaps (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/harness-rule-gaps-541rjw` (harness-assigned)
**PR:** _pending_    **Outcome:** completed

All six code deliverables (D1–D6) were reached, plus D7's measurements. Two of the plan's own
gating HYPOTHESIS claims were **refuted** by re-derivation and are recorded as such below.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | plugin (`Skill:`) — the run's first action |
| `plan-marshall:ref-code-quality` | bundle path |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `pm-dev-python:python-core` | bundle path (Python production code) |
| `pm-dev-python:pytest-testing` | bundle path (Python tests) |

No skill was unobtainable by both routes.

## Gating checks performed before any edit

**Collision matrix (`README.md` § "The collision matrix").** The parties it names against `090` are
`080`, `100`, `110` and `120`. Evidence, taken from the GitHub MCP `list_pull_requests` surface and
from `git ls-remote`:

| Party | Open PR | In-flight branch | Verdict |
|---|---|---|---|
| `080` | none | none | clear |
| `100` | none | none | clear |
| `110` | none | none | clear |
| `120` | none | none | clear |

The repository had exactly **one** open PR at check time — #1289
(`chore(cloud-plan-lane): forbid git checkout as the mutation-sweep restore`, head
`claude/main-sha-pinned-cwd-0p9af9`), which names no test-quality plan. Six other remote branches
were unmerged; none belongs to a named party. `claude/runtime-seam-neutrality-osuaxx` touches
`script-shared/scripts/marketplace_paths.py` — the same *directory* D1 changes but not a file it
touches, and it belongs to the `multiplattform` epic, which the matrix does not name. Recorded as an
observation, not a collision.

⚠️ **Sequencing observation.** `claude/architecture-orchestration-test-reduction-iuthfe` is already
merged into `main`, so plan `070` has **landed** — this plan did not land before `070` started, as
its § Notes intended. That is an ordering fact, not a collision (the matrix governs concurrent
editing only), and it means `070`'s **B6** half did not have D1's seams available to it.

**`marketplace/bundles/**` exclusivity.** Not separately re-verified beyond the matrix and PR checks
above; no in-flight test-quality work exists to contend for it.

## Deliverables

### D1 — Publish a parser seam on every module that blocks a `parse_ns` conversion — **done** (`149279b`)

**Re-derivation, and what it refuted.** The plan's 27-blocked-site figure is labelled HYPOTHESIS and
gating. Re-derived by probing `parse_ns` against the modules on a pristine `origin/main` worktree:

| Group | `060`'s claim | Re-derived verdict |
|---|---|---|
| `script-shared` build CLI, 15 sites | blocked, no seam | **CONFIRMED.** `parse_ns` raises `ParserSeamNotFound` on both `build/_build_cli.py` and `build/_build_execute_factory.py`: "publishes none of `('build_parser', '_build_parser', '_build_arg_parser')` and has no callable `main()`" |
| `manage-providers`, 12 sites | blocked, no seam | **REFUTED.** The claim is true of the private command modules `060` named (`_list_providers.py`, `_cred_*.py`) but false of the skill: its CLI owner `credentials.py` has a `main()`, so seam 2 already resolved. `parse_ns(..., 'credentials.py', 'list-providers')` returned a namespace on unmodified `main` |

So **15**, not 27, sites were blocked on a genuinely missing seam. The other 12 were blocked on the
tests addressing the private handler module rather than the CLI that owns its parser — a different
defect with a different remedy.

**A broader mechanical derivation was also run and is reported as a lead, not as the blocked set.**
Over the 253 test modules that construct a `Namespace(`, resolving the marketplace modules they reach
by both import styles (`load_script_module` triples **and** plain imports): 148 modules reached, of
which 8 expose a published builder, 33 a `main()`, 5 failed to load, 87 expose neither but sit in a
skill whose front script does, and 15 expose neither in a skill with no seam-bearing front script at
all. ⛔ **That 15 is not the blocked-conversion set**: "a test module imports X" is not "a test module
builds a namespace *for* X", and most of the 15 (`toon_parser.py`, `marketplace_paths.py`,
`extension_base.py`) are pure libraries with no CLI. Resolving a hand-built namespace to the parser
that would produce it is a per-call-site read, which is how `060` produced its list and is not
something this sweep replaces.

**Seams published**, each with `main()` (or `build_main`) now parsing with the published parser so the
two cannot drift:

| Module | Seam | Call sites unblocked |
|---|---|---|
| `script-shared/scripts/build/_build_cli.py` | `build_parser()` — the shared build-class surface (`run`, `parse`, `coverage-report`, `check-warnings`, `discover`); `build_cli_parser()` extracted from `build_main` | 15 (`060`'s `script-shared` group) |
| `script-shared/scripts/build/_build_execute_factory.py` | `build_parser()` — the `run` surface its `cmd_run` reads, importing the registration rather than restating it | the same 15, addressed at the module under test |
| `manage-providers/scripts/credentials.py` | `build_parser()` extracted from `main()` | 12 — **not previously blocked**; this converts seam 2 (which executes `main()`) into seam 1 |

**No production behaviour changed.** The full accept-set of all four build wrappers plus
`credentials.py` — every flag, `dest`, default, action class, `nargs`, `const`, `type`, `choices`,
`required` and `metavar`, recursively through every subparser — was captured by intercepting each
`main()`'s `parse_args` call, before and after. The two JSON dumps are **byte-identical**.
`argparse_surface.py` was not used: it derives the accept-set by running `--help` through the
generated executor, which this lane may not create.

**Bound worth stating:** a `parse_ns`-derived `run` namespace is the parser's own output and therefore
does **not** carry `build_main`'s post-parse mutations (`--plan-id` → `NO_PLAN`, `resolve_project_dir`
on `project_dir`). Interception happens at the parse, before those run. The hand-built namespaces this
replaces did not carry them either.

### D2 — Let the shared loader address a skill file outside `scripts/` — **done** (`aeb8f7a`)

**Instance set, derived per finding.** Of the 183 whole-tree `test-module-preamble-boilerplate`
findings, **14** resolve a skill-root `extension.py` — read at each finding's `file:line`, since the
sweep names the test module and not the path it resolves. Not two: `060`'s figure was scoped to the
fifteen directories it worked. The 14 sit in 13 test modules across 11 directories.

**Option chosen: widen the loader.** The alternative (exempt the shape in the analyzer) was rejected
with a reason: the shape is a stable marketplace convention — 11 bundles ship
`skills/plan-marshall-plugin/extension.py`, and **9 of the 11 have no `scripts/` directory at all** —
so exempting it would silence the message while leaving 14 hand-rolled `spec_from_file_location`
preambles in the tree, which is the duplication **B7** exists to remove. Widening makes the remedy the
rule already prescribes actually applicable.

Added `get_skill_dir` and `load_skill_module` (skill-root-relative) beside the existing
`get_scripts_dir` / `load_script_module` (scripts-relative), with both loaders sharing one
`_exec_module_from_path` construction. Two explicit functions rather than a fallback inside one: no
skill ships both `scripts/extension.py` and a root `extension.py` today, but a silent fallback would
make resolution depend on which file happened to exist.

The rule's own message, the standards doc, the rule catalog and the provenance table now name the
applicable helper per shape.

⚠️ **The count is unchanged at 183, and that is the correct outcome.** D2's done-when is satisfied by
the first of its two branches — every one of the 14 findings is now *fixable by the documented
remedy*. Converting the call sites is not this plan's to do: the 14 live under `test/pm-dev-*/`,
`test/pm-documents/`, `test/marketplace/`, `test/pm-code-intelligence/`,
`test/plan-marshall/build-gradle/`, `test/plan-marshall/build-npm/`, and one at the root of
`test/plan-marshall/` (`test_plan_marshall_plugin_extension.py`) — none of which this plan's Expected
surface claims. They belong to the
owning slices (`080` for the `pm-*` and `marketplace` directories, `060`'s slice for the `build-*`
ones). This is the same division D1's Out-of-scope states: this plan opens the seam, the owning slice
performs the conversion.

### D3 — Make a shared-registration collision impossible to introduce silently — **done** (`aeb8f7a`)

**The no-publish escape.** `load_script_module`, `load_skill_module` and `parse_ns` all take
`register: bool = True`. Default behaviour is unchanged; `register=False` returns the module without
touching `sys.modules`. `parse_ns` carries the passthrough because it is the call a test is most
likely to make and it registers exactly as a direct load does.

**The guard quantifies over the live set**, as the plan requires: it walks every `*.py` under `test/`,
finds every call to the three registering helpers, resolves the name each publishes (through
module-level string constants as well as literals), and cross-checks against every plain import in the
tree. Nothing is hard-coded about which modules participate.

⚠️ **Re-derivation refuted the count.** `060` recorded **three** latent registrations. The whole-tree
derivation finds **19 live collisions** — names that are both file-loaded and plainly imported *today*,
not latent at all:

`_architecture_core`, `_build_execute_factory`, `_cmd_effort`, `_config_defaults`, `_cred_edit`,
`_findings_core`, `_github_pr`, `_gradle_cmd_discover`, `_gradle_execute`, `_maven_execute`,
`_pyproject_execute`, `effort_presets`, `finalize_step_presets`, `github_pr`, `manage_terminal_title`,
`plan_logging`, `recipe_scoring`, `review_completeness`, `run_config`.

`060`'s three was a property of the slice it measured, not of the tree. Blast radius varies widely —
`_build_execute_factory` is loaded by one module and plainly imported by 19; `run_config` by 2 and 13.

**Consequence for the guard's shape.** An `assert no collisions` guard would red the build on 19
pre-existing conditions spread across directories this plan may not edit. The guard is therefore a
**growth check** against a pinned baseline — the same shape `010` used to land its rules over a
non-compliant tree. Two arms, reported separately so the failures cannot be confused: a new collision
fails one, and a pinned name that is no longer a collision fails the other, so the baseline cannot rot
into a silent allowance.

**The guard caught a collision in this run's own diff.** The first D1 test module registered
`_build_cli`, which `test_build_execute_factory.py` imports plainly — a 20th collision, created by
this plan. It was **fixed rather than baselined**: every `parse_ns` / `load_script_module` call in both
new D1 test modules now passes `register=False`. That is the worked example of the escape, and the
reason `parse_ns` needed the passthrough.

**Coverage bound, stated rather than hidden.** 88 loader call sites pass a module name that is neither
a literal nor a module-level constant, so the walker cannot resolve them and a collision introduced at
one is invisible to the guard. That count is asserted as a non-growing ceiling with its own test, so
the blind spot is a visible quantity rather than an unstated narrowing.

**Guard placement.** `test/plan-marshall/script-shared/test_conftest_loader_contract.py` — inside a
directory this plan's Expected surface claims, and explicitly **not** at the root of `test/` or of
`test/plan-marshall/`, both of which the partition enumerates by name. ⚠️ **A plan-internal tension,
disclosed:** the Expected surface scopes `test/plan-marshall/script-shared/` to "only where a D1
production change requires its own test", while D3 requires its guard to go "inside an existing
directory this plan's Expected surface already claims". Every claimed test directory is scoped to some
other deliverable, so the two instructions cannot both be satisfied literally. Resolved in favour of
D3's explicit placement rule, because the alternative it forbids (a new module at `test/` or
`test/plan-marshall/` root) is the defect that instruction exists to prevent. The collision matrix
already covers `090` × `100` run 3 for this directory, and that check is clear.

### D4 — Match the citation spellings that actually occur — **done** (`ef1f867`)

Widened `_PLAN_DELIVERABLE_ID_RE` (`deliverable D?\d+`, so `Deliverable 2` matches beside
`deliverable D2`) and `_PR_REFERENCE_RE` (a bare `#NNN` beside `PR #NNN`).

**Then bounded the bare form against measured false positives, not guesses:**

| Bound | What it excludes | Why |
|---|---|---|
| `(?<=[^\w#\-])` | `plan-marshall#123`; `pre-#812`; a comment's own `#` delimiter | The reference analyzer already owns the first. `pre-#812` is a schema-state literal the corpus asserts on. Comment segments arrive from `tokenize` with the delimiter attached |
| `#\d{2,}` on the bare form only | `#1`, `#2`, `#3` enumerations | One-digit bare numbers are intra-document enumeration. Affordable because `PR #7` still matches through the prefixed alternative, which carries no digit bound |

**Whole-tree counts** (`doctor-marketplace.py test-conventions --test-root test/`):

| Stage | `test-docstring-historical-prose` |
|---|---:|
| pristine `origin/main` | 81 |
| widened, unbounded | 308 |
| **widened + bounded (shipped)** | **282** |

**No true positive stopped being reported.** Every one of the 81 pristine findings is present in the
final set — zero `file:line` pairs disappeared and no file's count decreased. The 26 findings the
bounds removed are fully accounted for, and split cleanly in two: **10** one-digit bare numbers (`#1`
×4, `#2` ×5, `#3` ×1), and **16** numbers inside a hyphenated compound (`pre-#812` ×11, `pre-#515`
×2, `post-PR-#474` ×2, `post-#854` ×1). The 16 were listed individually with their source lines and
read; the 10 were classified by matched text rather than read one by one.

**False-positive rate, measured by a cold reader.** Two independent sub-agents, each given only the
findings and their surrounding source — no plan, no diff, no task context — and asked per finding
whether it is a citation of history or the test's own data:

| Sample | Matcher state | CITATION | DATA | FP rate |
|---|---|---:|---:|---:|
| 10, spread across both new spellings | widened, unbounded | 6 | 4 | **40%** |
| 10, freshly drawn, offset from the first | widened + bounded (shipped) | 8 | 2 | **20%** |

The two false positives that survive are shape-indistinguishable from real citations and are the
stated residue: `#118` (an upstream `cui-open-rewrite` designation for a WARN log format the parser
under test consumes) and `#1078` (provenance for where a fixture body was copied from).

**`this plan` is deliberately left unmatched, on a measured rate.** Population: 79 prose segments the
phrase would newly add. A third cold read of 10, told that `plan` is also a domain noun here, returned
**7 CITATION / 3 DATA — a 30% FP rate**, worse than the 20% the shipped widenings measure at. The
phrase names the plan *record under test* often enough that shape cannot separate the two senses.

Six test cases added to `test_test_conventions_rule6.py`, each **mutation-proven**: reverting the
matchers to their pre-widening spellings, un-narrowing the bare form, removing the preceding-character
bound, and "simplifying" the digit bound onto both alternatives each turn a distinct subset red.

### D5 — Generalise the citation-versus-datum fix to the sibling rule — **measured; rule left unchanged** (`00c6fa7`)

**The rule reports 0 findings over `marketplace/bundles/**` today**, so a false-positive rate over its
live findings is 0 of 0 and would tell the operator nothing. The informative measurement is the
suppression accounting over all 159 lesson-ID-shaped tokens in that tree:

| Reason the token is not reported | Count |
|---|---:|
| Path allowlist (shipped default-suppression config) | 124 |
| Markdown fenced code block | 19 |
| Markdown inline-code span (the exemption **already** implemented) | 16 |
| **In a literal span that only the sibling's exemption would reach** | **0** |

**Decision: do not import the exemption.** It would remove **zero** false positives on the corpus this
rule governs, while adding a way to hide a real citation inside backticks in a Python file. The tree's
one Python literal-span occurrence — `analyze-logs.py`'s "Generalised from the prior phase-5-only
reader … (lesson `2026-05-20-12-002`)" — is itself a narrative citation, i.e. exactly what the import
would wrongly exempt.

The rule's **behaviour is unchanged**; its module docstring now carries the measured basis so the
question is not reopened without new evidence. (The plan's own framing that the sibling "still matches
on shape alone" is **partly refuted**: the markdown path already carries the inline-code exemption.
The gap is Python-only, and it is deliberate and documented.)

### D6 — Stop `test/conftest.py` naming a helper by a path that is about to move — **done** (`cc13884`)

`_routing_namespaces`' docstring now identifies the helper by **role** ("the shared build-test helper
module … to reach the factory's `compute_command_key`") rather than by path, and states why: the
mechanism belongs to `load_script_module`, not to any one caller, so the explanation survives a rename
or a second caller.

Done-when, verified: `grep -rn 'build_test_helpers' test/conftest.py` returns **nothing**; no path
under `test/plan-marshall/` appears in the docstring; both recorded facts survive in substance — the
`sys.modules` re-registration (point 1) and the consequence that patching a module object is silently
partial (point 2 and the `__globals__` paragraph).

### D7 — Report the measured deltas and the severity ladder — **done** (this report)

**Per-rule whole-tree `test-conventions` counts**, pristine `origin/main` → this branch:

| Rule | Before | After | Δ |
|---|---:|---:|---:|
| `unique-fixture-basenames` | 1 | 1 | 0 |
| `subprocess-pythonpath` | 15 | 15 | 0 |
| `identifier-validator-corpus` | 0 | 0 | 0 |
| `test-module-line-budget` | 317 | 317 | 0 |
| `test-helper-module-misnamed` | 0 | 0 | 0 |
| `test-module-preamble-boilerplate` | 183 | 183 | 0 |
| `test-docstring-historical-prose` | 81 | 282 | **+201** |
| **total** | **597** | **798** | **+201** |

The single delta is D4's widening; it is a rule seeing more of what was always there, not a
regression. `error_count` is unchanged at 16, so `status` is unaffected.

**The severity ladder — reported, not acted on.**

| Rule | `010` baseline | Current severity | Current count | At zero? |
|---|---:|---|---:|---|
| `test-module-line-budget` | 315 | `warning` | 317 | No |
| `test-module-preamble-boilerplate` | 382 | `warning` | 183 | No |
| `test-docstring-historical-prose` | 254 | `warning` | 282 | No |
| `test-helper-module-misnamed` | 1 | **`error`** | 0 | Already flipped |

**No flip performed.** The plan's HYPOTHESIS — that no rule other than the already-flipped one is at
zero — is **confirmed**. Severities read from the `RuleDescriptor` table in
`_analyze_test_conventions.py`; baselines from `rule-provenance.md`.

**Collected test count** (`pytest test/ --collect-only -q`): **20805 → 20854 (+49)**. This plan adds
tests and removes none.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **9 files**, so the gate applies.

`./pw verify` — clean: `ruff` "All checks passed!", `mypy` "Success: no issues found in 413 source
files" (production) and 771 (test-compile), "SPDX-header check passed", plugin-doctor `status: pass` /
`total_issues: 0`, and **20840 passed, 14 skipped in 380.81s**.

⚠️ **`test-compile` caught one error the narrower calls did not** — exactly the class the lane
contract warns about. `mypy` rejected `keywords['register'].value` because an `isinstance` narrowing on
`keywords.get('register')` does not reach the subscript. Both `./pw quality-gate` and a scoped
`pytest` run were green while it was red. Fixed by factoring the predicate into one
`_opts_out_of_registration` helper, which also removed a duplicated reading of that argument.

`uv run python -m pytest <file> -o addopts=""` was used throughout for red/green iteration
(order-of-seconds per run); `./pw verify` was run once, unchanged, as the gate.

## Findings

Every finding, per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | D1 re-derivation | `060`'s "27 blocked on a missing seam" is **wrong**: `manage-providers`' 12 were never seam-blocked — `credentials.py` resolves seam 2 on unmodified `main` | Recorded; D1 scoped to the 15 genuinely blocked, and the `credentials.py` change reported as a seam **upgrade**, not an unblock |
| F2 | D2 derivation | `060`'s "two that remain" is a slice figure; the whole-tree skill-root `extension.py` set is **14 findings** | Recorded; D2 sized against 14 |
| F3 | D3 derivation | `060`'s "three latent" registrations is a slice figure; the tree carries **19 live collisions** | Recorded; guard shaped as a growth check against a pinned baseline of 19 |
| F4 | D3 guard, on this run's own diff | The first D1 test module registered `_build_cli`, colliding with `test_build_execute_factory.py`'s plain import — a 20th collision created by this plan | **Fixed**, not baselined: `register=False` at every new call site |
| F5 | Own mutation sweep | `register=False` was **unpinned** — mutating `_exec_module_from_path` to ignore it left the whole suite green | **Fixed**: three guards added (default registers, `register=False` does not, `parse_ns` forwards it), each mutation-proven |
| F6 | Own mutation sweep | The first probe module for those guards (`sensible_number`) is itself plainly imported, so the control created a real collision | **Fixed**: probe switched to `credentials.py`, which nothing plain-imports |
| F7 | `./pw test-compile` | `keywords['register'].value` fails mypy; green under `quality-gate` and scoped pytest | **Fixed** by factoring `_opts_out_of_registration` |
| F8 | Beyond-diff sweep (D4) | Four docs restated the matched spellings or the figure derived from them: `doctor-test-conventions.md` ×2, `rule-catalog.md` ×2 | **Fixed**; the `285 prose / 876 data` figure re-derived to **282 / 904** |
| F9 | Beyond-diff sweep (D2) | Five sites restated the remedy the rule prescribes, two of them naming `load_script_module`'s `spec_from_file_location` call, which this change moved into `_exec_module_from_path` | **Fixed** in the analyzer message, its docstring, the standards doc, the rule catalog and the provenance table |
| F10 | D5 measurement | The plan's premise that the sibling rule "still matches on shape alone" is partly wrong — markdown already carries the inline-code exemption | Recorded; D5's decision rests on the corrected picture |
| F11 | Sequencing | Plan `070` has already landed, so this plan did **not** land before `070` started as its § Notes intended; `070`'s **B6** half ran without D1's seams | Recorded; out of this run's control |
| F12 | D3 guard coverage | 88 loader call sites pass a non-literal, non-constant module name and are invisible to the guard | **Disclosed** and pinned as a non-growing ceiling with its own test |

### Stop record

**Round budget: 4 verification rounds**, declared here before the first dispatch. The plan states no
budget, so the run declares one.

_The exit, the verifier's last answer, and any survivors are recorded here after the loop._

## Reviewer participation

_Filled in after the PR's reviewers report._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not recorded with a trusted source; the session has no clock the run may read
  (`Date.now()`-equivalents are unavailable and no start timestamp was captured). Reported as
  unavailable rather than estimated.
- **Population:** n/a for the figures above. ⛔ Had a figure been available it would count **this
  single Claude Code cloud session's usage**, which is **not** comparable to a plan-marshall
  `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under a per-task billing
  boundary this session does not share.

## Contract check (Step 9)

_Filled in as the final pre-merge commit._

## What have we learned (Step 9)

_Filled in as the final pre-merge commit._

## Residue

| Item | Where it goes |
|---|---|
| The 14 skill-root `extension.py` preambles are now fixable but **not fixed** | The owning slices — `080` (`test/pm-dev-*/`, `test/pm-documents/`, `test/marketplace/`, `test/pm-code-intelligence/`), `060`'s slice (`test/plan-marshall/build-gradle/`, `build-npm/`), and `test/plan-marshall/test_plan_marshall_plugin_extension.py` |
| The 15 `script-shared` `parse_ns` conversions D1 unblocks | `070` / `080` per the plan's Out of scope; `060`'s slice for its own residue |
| The 12 `manage-providers` sites — convertible via `credentials.py`, and never seam-blocked | Same owners; the remedy is to target the CLI owner, not the private handler module |
| **19 live `sys.modules` registration collisions**, pinned not fixed | Each owning slice; the guard prevents a 20th |
| 88 loader call sites the guard cannot resolve statically | Any slice touching them: hoist the argument to a module-level constant |
| `test-docstring-historical-prose` at 282, `test-module-preamble-boilerplate` at 183, `test-module-line-budget` at 317 — none at zero, so no further flip is licensed | `100` for the line budget; the reduction slices for the other two |
| `identifier-validator-corpus`'s empty registry; the `broken-relative-link` fragment gap | Out of scope by the plan; already in the epic README's residue table |
