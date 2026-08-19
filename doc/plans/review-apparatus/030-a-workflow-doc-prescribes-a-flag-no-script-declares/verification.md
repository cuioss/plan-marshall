# Verification — 030-a-workflow-doc-prescribes-a-flag-no-script-declares

**Landed as:** PR #1157, squash commit `3c7a1cc8`
**Verdict:** verified-with-gaps

Every deliverable landed and every named symbol, test class and doc edit the report claims still
exists in the current tree. The gaps are (a) one newly-introduced false statement at D2's declared
*primary fix site*, false for **ten** `ci` subcommands; (b) a live swallowed failure at
`create-pr.md` Step 4, where a failed `ci pr create` returns exit 0 and the step marks itself `done`
on an absent PR number; (c) the hole that makes (b) possible — the widened exit-code convention keys
on the exit code alone, while both CI providers return **exit 0** with `status: error`; (d) a member
of D0's population that the derivation missed entirely; (e) a silent-drop path D1 left open on the
very flag D1 converted; and (f) a flag-FORM enumeration in `review_completeness.py`'s own prose that
is false for two of its nine list flags.

## Method

Read in full: `plan.md`, `report-01.md`, `git show 3c7a1cc8` (message + full diff for all seven
non-plan paths).

Ground truth taken from the working tree. (`HEAD` has since advanced to `500d8061`; every commit
between `61a43e53` and it touches only `doc/plans/review-apparatus/**`, so no production path moved
— `git diff --name-only 61a43e53..HEAD | grep -v '^doc/plans/'` returns nothing.) Later churn on the
same paths was enumerated with `git log --oneline 3c7a1cc8..HEAD -- <path>` for each of the five
production files and the two test files; `review_completeness.py`, `automatic-review/SKILL.md`,
`phase-6-finalize/SKILL.md`, `branch-cleanup.md` and both test files were all touched again
afterwards (#1165, #1167, #1168, #1211, #1215, #1217, #1232, #1235, #1236, #1239, #1241, #1259,
#1287, #1294 …), so every claim was re-read against the files as they stand rather than against the
landed diff.

Searches run (all rooted at the repository, results quoted in the findings below):

- `grep -rn "Exit-code convention for" marketplace/bundles/` — 42 headings, 3 wide, 39 narrow.
- `grep -rn -- "--enabled-bots" marketplace/ test/`, `grep -rn "enabled_bots" marketplace/ test/`,
  `grep -rn "unfetched_bots" marketplace/ test/` — the three D2 null results.
- `grep -rn "stale_participation_bots\|stale-participation-bots" marketplace/` and the same over
  `test/` — the consumer sweep for the pair-form change.
- `grep -n "MalformedBotFlag\|def parse_participation\|def _split_bots\|def cmd_check"` over
  `review_completeness.py`; `grep -n "class TestMalformedBotFlagRejection\|class
  TestStaleParticipationIsPairForm"` over `test_review_completeness.py`.
- A scripted sweep that re-implements the D0/D3 derivation over every `*.md` under the
  `phase-6-finalize`, `automatic-review`, `workflow-integration-github` and `workflow-pr-doctor`
  skills, classifying each doc as WIDE / NARROW / NONE against its own non-`manage-*` invocations.
- A scripted sweep that runs **every** non-`manage-*` fenced invocation in `branch-cleanup.md`,
  `automatic-review/SKILL.md` and `branch-cleanup-rereview.md` against its real parser with
  placeholders substituted, looking for exit 2 / `unrecognized arguments`.

Ran (nothing else; no full build):

- `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py -o addopts="" -q` → **11 passed**; the same with `-v` to observe what the passing run publishes.
- `uv run python -m pytest test/plan-marshall/automatic-review/test_review_completeness.py -o addopts="" -q -k "Malformed or StaleParticipation"` → **10 passed, 131 deselected**.
- `python3 -c` probes against the live modules with the bundle `scripts/` directories on
  `PYTHONPATH`: `parse_participation` on an inadmissible evidence kind, and
  `ci_base.extract_routing_args(['--plan-id','NO_PLAN','pr','create',…])`.

No repository file was modified by this verification other than this file and `gaps.md`. Two
mutation proofs temporarily edited `automatic-review/SKILL.md` and `branch-cleanup.md`; each was
byte-snapshotted first and restored from that snapshot in a `finally`, and each restore was verified
byte-identical. `git status --porcelain` carries one entry not from this verification — an in-flight
`return True` injected into `github_pr.py:699` (`_reviewed_at_merge_candidate`) by another session's
mutation probe. It was left untouched; it does not reach `review_completeness`, the contract test's
argparse sweep, or any probe run here.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | The population is derived and stated with its derivation method, and a rejected call in any member site fails its step, proven by a test that passes today and fails after | Convention widened past `manage-*` in three docs; obligation derived per-doc by `TestExitCodeConventionCoversEveryScript`; doc SET accepted-with-reason as hand-scoped | Three wide headings present (`automatic-review/SKILL.md:172`, `phase-6-finalize/SKILL.md:44`, `branch-cleanup.md:59`); test present and green (3 parametrized cases), mutation-proven by re-running the mutation. **But** the widened convention keys on the exit code alone while both CI providers return exit 0 on any failure (G3), which leaves a live swallow at `create-pr.md` Step 4 (G2); `branch-cleanup-rereview.md` — loaded and executed *from inside the barrier* — carries no convention at all (G4); and 13 further `phase-6-finalize` docs invoking non-`manage-*` scripts keep the narrow one (G6) | partially met |
| D1 | Both directions tested — a pair fed to the bare-form flag and a bare kind fed to the pair-form flag — each a visible caller error rather than an `absent` verdict | `MalformedBotFlag`; `parse_participation` raises; `_split_bots` rejects pairs; `--stale-participation-bots` made pair-form; `TestMalformedBotFlagRejection`, `TestStaleParticipationIsPairForm` | All symbols and both test classes exist and pass. **But** the pair-form parse still silently drops a pair whose `evidence_kind` is not in the bot's registry `participation_evidence`, resolving that bot to `absent` (G5), and the module's own flag-FORM prose names two pair-form flags where four exist (G8) | met, with a residual silent-drop path |
| D2 | Every prescribed invocation in the derived population parses against its own parser | `execution-context.md` universal replaced by a per-script/per-position statement; `automatic-review/SKILL.md` item 4 rendered as pairs; three null results | All six derived invocations parse (verified by running them), as do the three `## Canonical invocations` blocks the sweep excludes. **But** the replacement text at the declared primary fix site is false for **ten** `ci pr` / `ci issue` subcommands (G1) | met for the parse sweep, defective at the primary fix site |
| D3 | The test exists, its population size is published in its own output, and it fails against a deliberately reintroduced divergence | `TestDocumentedReviewMergeInvocationsParse`, population 6, floor ≥ 4, non-emptiness asserted first, mutation-proven | Test exists and is green; population re-derived independently as exactly 6, and the reintroduced-divergence mutation re-run to failure (exactly the `skill-md-github-pr` case, exit 2). **But** the size is emitted only inside failure messages — a passing run publishes no number, and the derivation can shrink silently (G9) | met, except the "published in its own output" clause |

### D0 — enforce the exit-code convention across the merge-and-review population

**What is in the tree.** All three headings landed and survive:

- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:172` —
  `## Exit-code convention for every script call`, with the widening rationale at `:174`
  ("the producer `github_pr fetch_findings` (the FIND entry-point), the `ci checks
  pull-request-runs` read, and the `review_completeness check` guard are NOT `manage-*`").
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:44` and `:46`.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:59` and
  `:61`, plus the "stricter disposition" carve-out at `:66`.

The enforcement test `TestExitCodeConventionCoversEveryScript`
(`test/plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py:214`) is real, runs
three parametrized cases, and derives each doc's widening *obligation* from that doc's own
non-`manage-*` invocations rather than asserting it. Both directions of its mutation-proof claim are
structurally present: `assert _WIDE_HEADING in text` and `assert _NARROW_HEADING not in text`
(`:272`, `:277`). Re-run: `11 passed`. CONFIRMED.

**Where it falls short of the *Done when*.** The plan's D0 is emphatic: "⛔ **Derive the
population.** It is *every script invocation reachable in the finalize merge-and-review path*" and
"⛔ Do not hand-maintain a list of call sites". The delivered derivation derives *where* inside three
named files, but the file set itself is a literal:

```python
_INVOCATION_DOCS = (_BARRIER_DOC, _REVIEW_DOC)                    # :75
_CONVENTION_DOCS = (_BARRIER_DOC, _REVIEW_DOC, _DISPATCHER_DOC)   # :77
```

The report discloses this ("the doc SET … is named from the plan's own scope definition"), so it is
not a false claim — but the disclosure understates the miss. My independent WIDE/NARROW/NONE sweep
found `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md`
carrying **no exit-code convention section at all** (`grep -n "^## "` over that file returns exactly
one heading, `## Re-review the rebased HEAD (trigger A)`), while invoking two non-`manage-*` scripts:

- `:46` — `plan-marshall:workflow-integration-github:github_re_review re-review …`
- `:55-56` — `plan-marshall:workflow-integration-github:github_pr fetch_findings --pr-number
  {pr_number} --plan-id {plan_id}`

(Both re-derived: `grep -n "^#\|execute-script" branch-cleanup-rereview.md` returns one `## `
heading and eight invocations, two of them non-`manage-*`.)

That file is not a distant relative of the barrier. `branch-cleanup.md:489` says of it: "The full
walkthrough … lives in the same-directory sub-standard `branch-cleanup-rereview.md`. **Load and
execute it here**". It is inside the barrier's own execution, it produces `{declined_bots}` (retained
at `branch-cleanup.md:812` and forwarded at `:833`), and it existed at the landing commit
(`git cat-file -e 3c7a1cc8:…/branch-cleanup-rereview.md` succeeds). CONFIRMED gap — see G4.

The same sweep found 13 further `phase-6-finalize` docs that invoke non-`manage-*` scripts and keep
the narrow heading, several of them squarely in the PR/review path: `workflow/create-pr.md` (`ci`),
`workflow/sonar-roundtrip.md` (`ci`, `sonar`), `standards/output-template.md` (`ci`),
`standards/architecture-refresh.md` (`ci`), plus `standards/ci-verify.md` and
`standards/verdict-currency.md` with no convention at all. The report's justification — "the ~35
other docs carrying the boilerplate convention are **other phases/steps**, out of scope" — is
inaccurate as written: these are the same phase. Re-derived independently by running the landed
test's own `_invoked_notations` / `_is_manage_star` / heading constants over every `*.md` in the four
skills: **3 WIDE, 13 NARROW, 6 NONE** (the six NONE being `branch-cleanup-rereview.md`,
`ci-verify.md`, `verdict-currency.md`, `workflow-integration-github/SKILL.md`,
`workflow-pr-doctor/SKILL.md` and `workflow-pr-doctor/standards/automated-review-lifecycle.md`). See
G6.

**A hole in the widened convention itself.** The widened text keys on the exit code alone —
"`exit_code == 0`: parse the returned TOON and use the value as the step describes" — while `ci`'s
own documented three-tier model returns **exit 0** for an expected error: `ci_base.output_error`
(`:790-798`) prints `status: error` and returns `EXIT_SUCCESS`. Reproduced by running the real router
from a directory with no configured provider:

```
$ ci.py checks pull-request-runs --pr-number 1
status: error
operation: router
error: CI provider not configured. Run /marshall-steward first.
EXIT 0
```

The router is not the only tier that does this, and this is the part the earlier pass understated:
**both providers' `main()` returns 0 unconditionally.** `github_ops.py:1906-1908` and
`gitlab_ops.py:2600-2602` each do `result = dispatch(...)`, print the serialized TOON, and
`return 0` — no branch on `result['status']`. So *every* `ci` verb, not just an unrouted one, reports
failure at exit 0. Reproduced against the real provider script with an emptied `PATH`:

```
$ github_ops.py checks pull-request-runs --pr-number 1
status: unconfigured
operation: pull_request_runs
provider: github
detail: Not authenticated. Run 'gh auth login' first.
EXIT 0

$ github_ops.py pr create --title T --plan-id NO_PLAN --base main
status: error
operation: pr_create
error: Not authenticated. Run 'gh auth login' first.
EXIT 0
```

So the class the plan's Goal names — "a value the surface accepts and misreads … absorbed into a
green result" — survives the widening at every `ci` call site whose step does not *separately*
validate the payload shape. Three sites do: the barrier's `checks pull-request-runs` read
(`branch-cleanup.md:825`, "**Every other shape is an UNKNOWN input**"), its sibling at
`automatic-review/SKILL.md:671`, and the barrier's positive three-field requirement on
`fetch_findings` (`branch-cleanup.md:762-775`). Two do not. The `checks status` snapshot at
`branch-cleanup.md:425-430` says "Parse `overall_status` from the returned TOON. `pending`,
`success`, and `none` all proceed", and a `status: error` return carries no `overall_status` at all,
matching no branch while the convention says the exit-0 value is usable — though that gate is
documented as never hard-blocking, so the consequence there is confined. The one with real
consequence is **`create-pr.md` Step 4** (`:277-289`), which invokes `ci pr create` under the NARROW
convention (`:22`), states only "Read `pr_number` and `pr_url` from the TOON output", then logs
`Created PR #{pr_number}` (`:294`) and records `--outcome done --display-detail "#{pr_number}"`
(`:306-310`). Against the exit-0 failure reproduced above, a failed PR creation is a green step with
an empty PR number, and finalize proceeds to the review-and-merge steps against a PR that does not
exist. The same document branches on `status` for `pr view` at `:69-73`, so this is a local omission,
not a house style. This is D0's population, and D0's own mandate — "⛔ D0's framing must not narrow to
'surface the swallowed rejection'" — names exactly this class. CONFIRMED — see G2 (the live site) and
G3 (the convention hole).

**On "a rejected call … fails its step, proven by a test that passes today and fails after".** No code
path can fail an LLM-executed prose step, and the report says so plainly. What landed is prose plus a
test over the prose. That is a defensible reading of an undeliverable clause, and the widening is a
genuine scope change rather than the restatement the plan's Out-of-scope forbids. Recorded as
partially met rather than refuted.

### D1 — a malformed value is REJECTED, not silently reinterpreted

Every named symbol exists in the current tree:

- `MalformedBotFlag` — `review_completeness.py:313`.
- `parse_participation(raw, flag='--participated-bots')` — `:335`, raising at `:370` on
  `not sep or not bot_kind or not evidence_kind`.
- `_split_bots(raw, flag=…)` — `:1163`, raising at `:1185` on `':' in entry`.
- `--stale-participation-bots` routed through `parse_participation` — `:1219`.
- `MalformedBotFlag` → `status: error` + exit 1 + no `participation_complete`: `cmd_check`
  `:1246`, and `_emit_toon`'s early return for `status == 'error'` means the verdict fields are
  never printed.

The two test classes exist and pass: `TestMalformedBotFlagRejection`
(`test_review_completeness.py:1441`) covers both directions at unit *and* CLI level, and
`TestStaleParticipationIsPairForm` (`:1534`) pins the pair-form acceptance and the bare-kind
rejection. `10 passed` when run. CONFIRMED.

Note that a later refactor (#1241) moved the parse out of `cmd_check` into
`_parse_bot_observations` (`:1196`) and gave `cmd_deficit` the same `MalformedBotFlag` handling
(`:1277`) — the D1 behaviour was extended, not eroded.

**The residual defect.** `--stale-participation-bots` now goes through `parse_participation`, which
applies the *admissibility filter* designed for proving participation:

```python
if evidence_kind in bot_registry.participation_evidence(bot_kind):
    proven[bot_kind] = evidence_kind
```

A stale record whose `evidence_kind` is not a declared publish shape for that bot — or whose
`bot_kind` is not in the registry at all — is therefore **silently dropped**, and the bot falls
through to `absent`. Confirmed by direct execution:

```
admissible pr-agent: ['issue_comment', 'inline']
stale bogus -> {}
stale good  -> {'pr-agent': 'issue_comment'}
nonexistent-bot:issue_comment -> {}
```

`absent` and `participated_stale` are both blocking, so this is not a false pass — but
`branch-cleanup.md` is explicit that they carry *opposite remedies* ("a required bot on
`participated_stale` DID publish … so the productive action is a re-review trigger"), and the
in-code comment at `:1216-1218` asserts the opposite of what the code does: "it takes the same pair
form and **the classifier reads only the bot_kinds**". The classifier does read only the bot_kinds —
but only for the records that survive a filter the comment does not mention. The same omission rides
in the user-facing argparse `help=` string at `:1380-1394`, which says the flag names a bot "whose
observed comment matched a declared `participation_evidence` publish shape" and that "the classifier
reads only the bot_kind", never that a non-admissible kind is dropped. CONFIRMED — see G5.

**It is a residual, not a regression — checked.** The landed diff shows the pre-fix wiring was
`stale_participation_bots=_split_bots(args.stale_participation_bots)`, a *bare-form* parse fed the
producer's pairs, so every stale record became a bot literally named `pr-agent:issue_comment` and was
lost unconditionally. Post-fix the drop needs the producer's emitted `evidence_kind` and the
consumer's registry read to diverge, and both sides read the same registry
(`github_pr.py:953` admits only `_kind in participation_evidence(_bot_kind)` before recording).
The precondition is therefore an unregistered bot or a registry edit between the two reads — narrow,
and strictly better than what it replaced.

**A second stale enumeration, in the module's own prose.** `review_completeness.py:128-134` states
"The list flags split into two FORMS … The two EVIDENCE-TYPED (pair-form) flags —
``--participated-bots`` and ``--stale-participation-bots`` … The remaining list flags are bare-form
(``bot_kind`` tokens only)." That is false for two of the nine list flags: `--refused-causes` and
`--refusal-size-caps` route through `parse_causes` (`:382-422`), which requires `bot_kind:value`
pairs and raises `MalformedBotFlag` on a bare token — confirmed by execution
(`parse_causes('pr-agent', '--refused-causes')` raises; `parse_causes('pr-agent:whatever', …)`
returns `{'pr-agent': 'whatever'}`; `parse_causes` spans `:382-423` and the two cause flags are
declared at `:1415` and `:1434`). The same two-way split is repeated — with both cause flags omitted
rather than misclassified — in the `MalformedBotFlag` docstring (`:316-322`), and the `_split_bots`
rejection message (`:1186-1190`) tells a caller
holding a rejected pair token that pairs "belong on a pair-form flag
(--participated-bots / --stale-participation-bots)" — wrong advice for a `bot_kind:cause` token. And
the module's `deficit` usage line (`:116`) omits `--refusal-size-caps`, which the shared
`_add_bot_observation_flags` factory does declare on `deficit` and which
`automatic-review/SKILL.md:1007` documents. CONFIRMED — see G8.

### D2 — reconcile the prescribed invocations to the live surfaces

**What landed and survives.**

- `marketplace/bundles/plan-marshall/agents/execution-context.md:23` — the universal is gone; the
  cell now reads "Forward `--plan-id {plan_id}` to a script call **only where that script's own
  parser declares it, and in the position that parser requires** — this is per-script, not a
  universal every call obeys."
- `automatic-review/SKILL.md:661` — item 4 now reads "rendered as comma-separated
  `{bot_kind}:{evidence_kind}` pairs. This is the SAME evidence-typed form as `{participated_bots}`".
- The three null results hold *as of the landing*: `unfetched_bots` has zero hits anywhere in
  `marketplace/` or `test/`; `enabled_bots` survives only in retirement/migration text
  (`marshall-steward/scripts/upgrade.py:243` `_LEGACY_BOT_LIST_KEY`,
  `manage-config/standards/data-model.md:289`). CONFIRMED.

**The defect introduced at the primary fix site.** The plan calls the envelope contract "**the primary
fix site for the position class**". The replacement text names `ci` as the exemplar of the
before-the-verb case (`execution-context.md:23`):

> a script that declares `--plan-id` as a **top-level/router flag consumed before the subcommand
> verb** (the `ci` router reads it before `pr`/`checks`, so `--plan-id` goes **before** the verb —
> placing it after the verb is an argparse rejection)

`ci` is the wrong exemplar, because it is *both* cases at once — and the post-verb half is **ten**
subcommands, not six. `ci_base.py:260-275` (`add_body_consumer_args`) declares `--plan-id` with
`required=True` on `pr create`, `pr edit`, `pr reply`, `pr thread-reply`, `issue create` and
`issue comment`; `ci_base.py:1172,1190,1201,1217` call `add_plan_id_arg` on `issue prepare-body`,
`issue prepare-comment`, `pr prepare-body` and `pr prepare-comment`, and the `add_plan_id_arg`
`ci_base` imports is `tools-input-validation/scripts/input_validation.py:385-398`, whose signature is
`(parser, required: bool = True)` — so those four are required too. Re-derived by walking the live
parser tree (`ci_base.build_parser('test')` plus `ci_base.add_pr_create_args`) and collecting every
subparser carrying a `--plan-id` option: **ten, all `required=True`.** For all ten the
canonical form places it **after** the verb — `tools-integration-ci/standards/pr-operations.md:163`:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --plan-id {plan_id} --base main [--head feature/x]
```

and `persona-plan-marshall-agent/standards/tool-usage-patterns.md:133,261,268` say the same. A caller
who follows the new envelope text and moves it left of the verb loses it: the router consumes and
strips it before the subparser ever sees it, confirmed by executing the real function —

```
extract_routing_args(['--plan-id','NO_PLAN','pr','create','--title','T','--base','main'])
-> ('/home/user/plan-marshall', ['pr', 'create', '--title', 'T', '--base', 'main'])
```

— after which `pr create`'s `required=True --plan-id` fails with an argparse rejection. Executed for
all ten verbs (router strip, then parse the returned argv against the real parser): **ten exit-2
rejections, zero survivors**, each `error: the following arguments are required: --plan-id`. The
contract text that was rewritten to stop prescribing argparse rejections now prescribes one, for ten
verbs of the very router it names. The trailing mitigation ("Consult each script's
canonical-invocation block … never append `--plan-id` by rote") does not repair it, because the
parenthetical makes an affirmative claim about `pr` specifically.

No *authored* invocation is currently broken by this: sweeping every `ci` invocation in
`marketplace/bundles/**/*.md` for a router-level `--plan-id` returns exactly three sites
(`tools-integration-ci/SKILL.md:159-160`, `ref-workflow-architecture/standards/dispatch-walkthrough.md:136-137`,
`phase-6-finalize/workflow/sonar-roundtrip.md:73-74`), and all three name verbs that declare no
`--plan-id` of their own (`pr view`, `pr wait-for-comments`) — correct pre-verb placement. The
exposure is exactly the runtime-composed invocation the plan's Notes name as the case the structural
guard does not reach. CONFIRMED — see G1.

The report records finding 2 as "D2 cold-read of the new `--plan-id` cell produces a correct
**pre-verb** placement for the `ci` router. Confirmed — no change." The cold read asked exactly the
question the plan's Verification section specified ("*for a script that accepts `--plan-id` only
before its verb, what does this text tell me to do?*") and got the right answer. The inverse question
— for a `ci` subcommand that declares it *after* the verb — was never asked, and it is the one the
new text gets wrong.

**A consumer site the pair-form change did not reach.** `branch-cleanup.md:830-836` forwards
`--stale-participation-bots "{stale_participation_bots}"` alongside five bare-form flags in one
command, and the surrounding prose (`:810`, `:840-856`) discusses emptiness and quoting at length but
never states which flags take pairs and which take bare kinds. Same at
`automatic-review/SKILL.md:964-997` — the `## Canonical invocations` block, which
`_analyze_manage_invocation.py` treats as source of truth, says "All nine list flags take an OPTIONAL
value" (`:980`) and nothing about token form. The barrier command in fact carries **four** pair-form
flags, not one: `--participated-bots`, `--stale-participation-bots`, `--refused-causes` and
`--refusal-size-caps` (the last two route through `parse_causes`). Since a wrong-form token is now a
hard error, both sites are under-specified. CONFIRMED — see G7.

### D3 — a population-derived test that fails when a documented invocation does not parse

`TestDocumentedReviewMergeInvocationsParse`
(`test_review_merge_invocation_contract.py:288`) exists. Non-emptiness is asserted at import
(`:194`), before any parametrize, exactly as the plan demanded. I re-derived the population with an
independent re-implementation of the same walk and got the same six invocations the report claims
(two `github_pr fetch_findings`, two `ci checks pull-request-runs`, two `review_completeness check`).
I then ran all six against their real parsers with `PATH=''`: exit codes 1, 0, 0, 1, 0, 0 — no exit 2,
no `unrecognized arguments`. CONFIRMED.

I also swept **every** non-`manage-*` fenced invocation in the two population docs plus
`branch-cleanup-rereview.md` against its real parser. The only exit-2 results were three artefacts of
my own placeholder substitution (`--head`, `--strategy`, `--timeout` collapsed to empty by an unknown
placeholder), which is precisely the class the test's docstring says it excludes. **No real
documented divergence survives in those docs** — the narrowing hid nothing that is currently broken.

**Where it falls short.** The plan's Verification is explicit: "**D3's population size is published in
the test output**, so a future reader can tell a passing test from an empty one." The number appears
only inside the assertion messages at `:299` and `:304-309`; `grep -n "print(\|record_property\|capsys"` over the
file returns nothing. A passing `-q` run prints `11 passed`; a passing `-v` run enumerates six
parametrized ids but states no count (re-observed under `--collect-only`: six
`test_documented_invocation_parses` ids, `branch-cleanup-md-{github-pr,ci,review-completeness}` and
`skill-md-{github-pr,ci,review-completeness}`). See G9.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | `parse_participation` now raises `MalformedBotFlag` on a shape violation | ACCURATE | `review_completeness.py:370` |
| 2 | `_split_bots` rejects a colon-bearing pair token | ACCURATE | `review_completeness.py:1185` |
| 3 | `--stale-participation-bots` changed from bare-form to pair-form | ACCURATE | `review_completeness.py:1219`; help text `:1380-1390` |
| 4 | `cmd_check` renders `MalformedBotFlag` as `status: error` + exit 1 + no `participation_complete` | ACCURATE | `:1246`; `_emit_toon` returns before the verdict fields when `status == 'error'` |
| 5 | Tests `TestMalformedBotFlagRejection` (both directions), `TestStaleParticipationIsPairForm` | ACCURATE | `test_review_completeness.py:1441`, `:1534`; 10 passed when run |
| 6 | "Mutation-proof by construction (they assert behaviour that only exists post-fix; the pre-fix code returned `{}`/`absent`)" | ACCURATE | The landed diff shows the pre-fix `parse_participation` did `continue` on a colonless token; `pytest.raises(rc.MalformedBotFlag)` cannot pass against that |
| 7 | The SHAPE check is separate from the evidence SEMANTIC filter; a well-formed pair with inadmissible evidence stays a silent drop | ACCURATE — and this is the finding | `parse_participation` filters on `bot_registry.participation_evidence`; confirmed by execution. Correct for `--participated-bots`, wrong in effect for `--stale-participation-bots` (G5) |
| 8 | `execution-context.md` universal replaced with a per-script, per-position statement | ACCURATE as to the edit; the replacement's `ci` exemplar is FALSE for **ten** `ci pr`/`ci issue` subcommands | `execution-context.md:23` vs `ci_base.py:260-275` + `:1172,1190,1201,1217` and `pr-operations.md:163`; parser tree walked and all ten executed |
| 9 | `automatic-review/SKILL.md` item 4 renders `{stale_participation_bots}` as pairs | ACCURATE | `automatic-review/SKILL.md:661` |
| 10 | "No barrier invocation change needed — it already forwarded the producer's pairs verbatim" | ACCURATE but incomplete | `branch-cleanup.md:810` retains the producer records; nothing at `:830-836` states the form (G7) |
| 11 | Null result: `--enabled-bots` absent from the whole tree, 0 hits in `marketplace/bundles/` | ACCURATE at the landing; **no longer true in the tree** | `review_gate_delta.py:504` declares `--enabled-bots`; that script did not exist at `3c7a1cc8` (`git cat-file -e` fails) — introduced later by #1239 |
| 12 | Null result: `enabled_bots` frontmatter key gone, only retirement/migration references survive | ACCURATE as scoped to the marshal.json CONFIG knob; the evidence list is incomplete | Retirement text at `upgrade.py:69,226-243,406`, `manage-config/standards/data-model.md:289,326`, `marshall-steward/SKILL.md:66,379,387`, `bot-participation-contract.md:42`. Live NON-config uses exist and post-date the landing: `review_gate_delta.py:264` (a parameter), `automatic-review/SKILL.md:1092` and `bot-participation-contract.md:627` (a published figure) |
| 13 | Null result: `complete` / `unfetched_bots` absent; live names are `participation_complete` / `unproven_bots` / `bot_states` | ACCURATE | `grep -rn "unfetched_bots" marketplace/ test/` → 0 hits |
| 14 | Convention widened in `branch-cleanup.md`, `automatic-review/SKILL.md`, `phase-6-finalize/SKILL.md` | ACCURATE | Three wide headings; 39 narrow ones elsewhere |
| 15 | "Widening scoped to the finalize merge-and-review docs (D0's population); the ~35 other docs … are **other phases/steps**, out of scope" | OVERSTATED | 13 narrow + 3 conventionless docs invoking non-`manage-*` scripts are inside `phase-6-finalize` itself, including `workflow/create-pr.md`, `workflow/sonar-roundtrip.md` and `standards/branch-cleanup-rereview.md`. Re-derived independently: 3 WIDE / 13 NARROW / 6 NONE |
| 16 | `TestExitCodeConventionCoversEveryScript` "derives … the three non-`manage-*` families (derived, not hand-listed)" | ACCURATE for the families, OVERSTATED for the population | `:244-248` derives the skill set from the scan; `:75-77` hard-codes the doc set |
| 17 | D0 test "Mutation-proven: reverting a heading to the `manage-*` form fails exactly that doc's case (verified)" | ACCURATE — mutation re-run | Reverting `branch-cleanup.md:59` to the narrow heading failed exactly `…[standards-branch-cleanup.md]` at `:272` (`1 failed, 10 passed`); the file was restored byte-identical from a snapshot |
| 18 | D3 "derives … asserts non-emptiness first, publishes size (6 invocations, floor ≥ 4)" | ACCURATE except "publishes" | Population independently re-derived as exactly 6; floor at `:304`; no output on a passing run (G9) |
| 19 | D3 "Mutation-proven: a reintroduced `--enabled-bots` … made exactly the `skill-md-github-pr` case fail (verified, then reverted)" | ACCURATE — mutation re-run | Appending `--enabled-bots "{enabled_bots}"` to the FIND `fetch_findings` invocation in `automatic-review/SKILL.md` failed exactly `…[skill-md-github-pr]` with `returncode 2` and `github_pr.py: error: unrecognized arguments: --enabled-bots` (`1 failed, 10 passed`); the file was restored byte-identical from a snapshot |
| 20 | Finding 4 fixed in `6cf9ea8`: docstring corrected to "follows the discipline; reimplements a fenced-block walk" | ACCURATE | `test_review_merge_invocation_contract.py:29-33` carries exactly that wording; `test/_shared/_dispatch_roster.py` exists |
| 21 | Finding 7: no reader of `complete`/`unfetched_bots` exists; `_cmd_merge_authorization.py` reads `unproven_bots` | ACCURATE | Zero hits for `unfetched_bots`; `manage-status/scripts/_cmd_merge_authorization.py:21` references `unproven_bots` |
| 22 | Build gate: `./pw verify plan-marshall` SUCCESS, 15896 passed / 1 skipped | UNVERIFIABLE | Not re-run (the task forbids the full build). The two suites this plan owns pass: 11 + 10 |
| 23 | Commits `ff5af02`, `d24e7fc`, `ec02ee1`, `6cf9ea8` | UNVERIFIABLE | `git cat-file -t` → "Not a valid object name" for all four; expected after a squash merge with the branch deleted |
| 24 | Findings 8-11 (CI states, bot reviews, CLA) and the Reviewer-participation table | UNVERIFIABLE | GitHub-side state not reconstructible from the clone |
| 25 | Contract check row "Step 3 Plan directory — `doc/plans/review-apparatus/030-…/plan.md` exists" | ACCURATE | `git diff --name-status --find-renames 3c7a1cc8^ 3c7a1cc8` shows `R100` from the flat `030-….md` into the directory, plus the added report |

**One plan obligation the report never addresses.** The Claim-labels table has **eight** rows; one
is an OBSERVED row the report never touches — "`--in-progress-bots ""` is dropped by the executor so
argparse sees a flag with no argument, while omitting the flag works … **reproduce it once before
building on it**". The report mentions neither the reproduction nor the claim. The cause class is in
fact already closed in the tree — all nine list flags carry `nargs='?'` with `const=''`
(`review_completeness.py:1298`, `_add_bot_observation_flags`), and the executor's stripping is real
and locatable at
`tools-script-executor/templates/execute-script.py.template:1419-1420` (`# Strip empty string args …`
/ `script_args = [a for a in script_args if a]`), documented at `branch-cleanup.md:740-748` — so
nothing is broken; but a required confirm/refute artefact went unreported.

Likewise the plan's Verification asks for an "endorsement trap" hint *if* D0's work touches the
rejection reporting. It did not (no change to `tools-script-executor`), so the condition never fired.
The report does not say so — silence where a one-line "not triggered" belonged. Both are recorded
together as G11.

## Correctness review

1. **`execution-context.md:23` prescribes an argparse rejection for ten `ci` subcommands.** Detailed
   above; CONFIRMED by walking the live parser tree and by executing the router strip plus the real
   parse for all ten — ten exit-2 rejections, zero survivors. Blocker (G1).

2. **The pair-form `--stale-participation-bots` inherits an admissibility filter that silently drops,
   and the code comment denies it.** CONFIRMED by execution. Polarity-selecting in the sense the plan
   warns about — not toward a false pass, but toward the wrong *member* and therefore the wrong
   remedy in an operator-facing prompt. Major (G5).

3. **Fragility in the D3 derivation, not currently firing.** `_documented_invocations` (`:162-185`)
   takes `_EXEC_CALL.search(block)` — the *first* notation in a fenced block — and then passes
   `tokens[notation_idx + 1:]` (`:331`) — *all* remaining tokens — as that script's arguments. A
   fenced block holding two commands would feed the second command's tokens to the first parser as
   arguments. Every block in the current population holds exactly one command, so nothing fails
   today. The `if '[' in block: continue` skip at `:182` is similarly broad — any invocation that
   grows a bracket silently leaves the population, guarded only by the `>= 4` floor while the true
   population is 6. Not a live defect, but it is the mechanism by which the sweep can shrink to
   nothing while staying green, so it is folded into G9 rather than left as a note.

4. **A fail-open in the surrounding path, not in what landed.** `create-pr.md` Step 4 marks the
   step `done` on a `ci pr create` that failed at exit 0 — detailed under D0 above, raised as G2. It
   is not a regression from this plan; it is a member of D0's own population that the three-doc
   derivation did not reach, and it is the sharpest surviving instance of the class the plan exists
   to close.

5. **No fail-open, no non-idempotence, no vacuous test found in what landed.** `_emit_toon` returns
   before the verdict fields on `status: 'error'`, so a malformed flag genuinely cannot emit
   `participation_complete`. The D1 tests assert `pytest.raises(MalformedBotFlag)` against code that
   previously did `continue` — they cannot pass pre-fix. The D0 heading test asserts both the presence
   of the wide heading and the absence of the narrow one, so a half-applied edit fails.

6. **Empty-value handling is intact after the change.** `parse_participation` and `_split_bots` both
   `continue` on an empty token before any shape check, so `--flag ""`, a bare flag, a trailing comma
   and a whitespace-only value all still read as the empty list rather than as a malformed token —
   verified by `test_split_bots_accepts_bare_and_empty` (`test_review_completeness.py:1474`).

## Completeness review

| Consumer kind | Swept? | Result |
|---|---|---|
| Production code reading the changed flags | yes | `cmd_check` and `cmd_deficit` both route through `_parse_bot_observations`; no third caller (`grep -n "def cmd_"`) |
| Test fixtures/stubs feeding bare kinds to the now-pair-form flag | yes | `grep -rn "stale_participation_bots" test/` — the only bare-kind uses are `check_completeness(...)` **library** calls (`test_pre_merge_barrier.py:671`, `test_bot_participation_contract.py:643`), where a list of bot kinds is the correct API. No stale CLI fixture |
| Prose restating the old bare form of `--stale-participation-bots` | yes | None survives. `workflow-integration-github/SKILL.md:132-135` already documented the pair record shape |
| Sites that must state which flags are pair-form now that a wrong form is fatal | yes | **Two misses**: `branch-cleanup.md:830-836` and `automatic-review/SKILL.md:964-997` / `:999-1010` (G7) |
| Docs in the finalize merge-and-review path needing the widened convention | yes | **One miss with no convention at all** (`branch-cleanup-rereview.md`, G4), 13 same-phase docs left narrow plus 5 further conventionless ones (G6) |
| Docs whose fenced invocations should be in D3's parse sweep | yes | `branch-cleanup-rereview.md`'s `fetch_findings` and `github_re_review re-review` are outside it; I ran them anyway and they parse — so the miss is coverage, not a live break (G4) |
| `ci` call sites whose step does not positively validate the returned shape | yes | **Two**: `branch-cleanup.md:425-430` (`checks status`, non-blocking by design) and `create-pr.md:277-289` (`pr create`, marks the step `done` — G2). Three sites do validate: `branch-cleanup.md:762-775`, `:825`, `automatic-review/SKILL.md:671` (G3) |
| Prose-bearing string literals stating a now-false claim | yes | `test_review_merge_invocation_contract.py:18` and `:291` still call `--enabled-bots` "a flag no script/parser declares" while `review_gate_delta.py:504` declares it (G10); `review_completeness.py:128-134`, `:316-322` and the `_split_bots` error template at `:1186-1190` state a two-FORM split that is false for `--refused-causes` / `--refusal-size-caps` (G8); the `--stale-participation-bots` `help=` at `:1380-1394` omits the admissibility drop (G5) |
| Readers of the renamed return fields (`complete` / `unfetched_bots`) | yes | Zero hits tree-wide; the plan's HYPOTHESIS is refuted, as the report says |

## Out-of-scope compliance

| Out-of-scope item | Compliance |
|---|---|
| The executor's `detail=` truncation | **COMPLIANT.** No file under `tools-script-executor` appears in `git show --stat 3c7a1cc8` |
| Building a second consumer for degraded-input signals | **COMPLIANT.** No new consumer; the run report is the coordination channel, as the plan directs |
| Adding prose that restates the exit-code convention | **COMPLIANT, narrowly.** The heading change is a scope change, not a restatement. Two paragraphs were added (`automatic-review/SKILL.md:179`, `branch-cleanup.md:66`), but each *points at* an existing UNKNOWN branch rather than repeating the convention — and both point accurately: `automatic-review/SKILL.md:748-760` really does route `review_completeness check` and the `checks pull-request-runs` read into a loop_back, and `branch-cleanup.md` really does carry two `## UNKNOWN — …` branches |
| Any change to a repository other than this one | **COMPLIANT.** Nine paths, all in this repository |

## Residue status

| Residue item recorded in `report-01.md` | Status now |
|---|---|
| `verify / verify` in_progress at hand-off | **Closed by the landing.** The PR merged as `3c7a1cc8`; the merge queue admits only on a green required context |
| CLA pending for `cuioss-oliver` | **Closed by the landing.** The merge occurred, so the gate cleared or was not required |
| Review coverage 1-of-3 (coderabbit rate-limited, sourcery skipped) | **Closed as disclosed.** A one-run disclosure, not a tracked debt; no artefact in the tree carries it forward |
| Landing confirmation delegated to the orchestrator's collect | **Closed.** `3c7a1cc8` is an ancestor of `HEAD` |

No residue item is still open. Every gap listed in `gaps.md` is newly identified by this
verification, not a carried-forward residue.

## Summary

Counts by severity: **1 blocker, 5 major, 5 minor** — see `gaps.md` (G1–G11). No false report claim:
every symbol, test class, heading and doc edit `report-01.md` names exists in the tree today, both
owned suites pass (11 + 10), and both mutation-proof claims were re-run and hold. Three report
statements are OVERSTATED (the "other phases/steps" justification for the D0 doc set, "publishes
size", and the `enabled_bots` null result as stated tree-wide rather than scoped to the config knob);
three are UNVERIFIABLE for structural reasons (squashed commit ids, GitHub-side state, the full
build).

Bottom line: the plan landed substantially as documented and as designed, and the D1 work in
particular is clean, well-tested and correctly separated from the evidence-admissibility filter. But
the deliverable the plan itself called the *primary fix site for the position cause class* shipped a
replacement text that prescribes an argparse rejection for **ten** `ci` subcommands — the same
failure class the plan exists to close, now written into the envelope contract every dispatched leaf
reads. Alongside it, D0's anti-curation mandate was met in form (the widening *obligation* is
derived) but not in substance (the doc *set* is a literal), and that literal cost the plan two real
members: `branch-cleanup-rereview.md`, which the barrier loads and executes and which carries no
exit-code convention at all; and `create-pr.md`, where a failed `ci pr create` returns exit 0 and the
step marks itself `done` on an absent PR number — the plan's own Goal class, still live in the
finalize path. The exit-code-only keying of the widened convention is what makes that last one
possible, and it is exactly the narrowing D0's text forbade. All are cheap to close and none undoes
what landed.

## Adversarial review

An independent pass re-derived every load-bearing finding above against the tree rather than
accepting it, corrected what it contradicted, and extended the gap set. This section states what was
re-run, precisely enough to re-run again.

### What was re-derived, and how

**Executed against the live modules** (bundle `scripts/` directories on `PYTHONPATH`; probes run
through `uv run python`):

- `ci_base.build_parser('test')` + `ci_base.add_pr_create_args(pr_sub)`, walked recursively for every
  subparser declaring a `--plan-id` option, printing `(path, action.required)`.
- `ci_base.extract_routing_args` on a pre-verb `--plan-id` for each of those subcommands, then
  `parser.parse_args(remaining)` on the returned argv, with `stderr` captured.
- `parse_participation` on an inadmissible evidence kind, an unregistered bot, and an admissible
  pair; `parse_causes` on a bare token and on a pair; `bot_registry.participation_evidence('pr-agent')`.
- `ci.py checks pull-request-runs --pr-number 1` from a directory with no configured provider.
- `github_ops.py checks pull-request-runs --pr-number 1` and
  `github_ops.py pr create --title T --plan-id NO_PLAN --base main`, each with `PATH=''`.

**Test runs:** `test_review_merge_invocation_contract.py` (`11 passed`), the same with
`--collect-only` (six `test_documented_invocation_parses` ids), and
`test_review_completeness.py -k "Malformed or StaleParticipation"` (`10 passed, 131 deselected`).

**Mutations, each byte-snapshotted before the edit and restored from that snapshot in a `finally`,
with the restore verified byte-identical:** the `--enabled-bots` reintroduction in
`automatic-review/SKILL.md`'s FIND `fetch_findings` invocation, and the narrow-heading reversion in
`branch-cleanup.md`. No `git checkout`/`restore`/`stash` was used.

**Sweeps re-implemented from scratch** (not reusing the earlier pass's scripts): the WIDE / NARROW /
NONE classification over every `*.md` in the four skills using the landed test's own
`_fenced_commands` / `_invoked_notations` / `_is_manage_star` logic; and a regex sweep of every `ci`
invocation in `marketplace/bundles/**/*.md` for a router-level `--plan-id` before the verb.

### Verdicts on the findings this document already carried

**UPHELD, unchanged (14).** The blocker's mechanism (`execution-context.md:23` vs `ci_base`, router
strip confirmed by execution); the exit-0 `status: error` return from `ci`; `branch-cleanup-rereview.md`
carrying one `## ` heading and no convention while invoking two non-`manage-*` scripts; the
3 WIDE / 13 NARROW / 6 NONE sweep and every one of its 13 narrow line citations; the 42 / 3 / 39
heading count; the `--stale-participation-bots` admissibility drop, reproduced with identical output;
the D1 symbols and both test classes at their cited lines; the D3 population of exactly 6 and its
six ids; the absence of `print` / `record_property` / `capsys`; the three D2 null results as scoped;
`review_gate_delta.py:504` declaring `--enabled-bots` and not existing at `3c7a1cc8`; the canonical
post-verb forms at `pr-operations.md:163` and `tool-usage-patterns.md:133,261,268`; the landed
diff's seven non-plan paths and the `R100` plan.md rename; `3c7a1cc8` being an ancestor of `HEAD`
with no production path moved since `61a43e53`.

**OVERSTATED, corrected (1).** The claim was stated at **six** `ci` verbs in the body, the
Correctness review and the Summary while the headline said ten. Ten is right, and the body's
derivation was the incomplete one: it counted only `add_body_consumer_args`
(`pr create`, `pr edit`, `pr reply`, `pr thread-reply`, `issue create`, `issue comment`) and missed
the four `add_plan_id_arg` verbs (`pr prepare-body`, `pr prepare-comment`, `issue prepare-body`,
`issue prepare-comment`). `ci_base` imports `add_plan_id_arg` from `input_validation`
(`:385-398`), whose signature is `(parser, required: bool = True)` — so all ten are required, and all
ten were executed to an exit-2 rejection. The blocker is therefore **stronger**, not weaker.

**Understated, corrected (1).** The exit-0 hole was attributed to `ci_base.output_error` at the
router tier. The provider tier does the same thing unconditionally: `github_ops.py:1906-1908` and
`gitlab_ops.py:2600-2602` both `return 0` after `dispatch` with no branch on `result['status']`, so
**every** `ci` verb reports failure at exit 0, not only an unrouted one.

**Corrected in scope (1).** Report-claim 12's `enabled_bots` null result holds for the marshal.json
config knob but not tree-wide as written: `review_gate_delta.py:264`,
`automatic-review/SKILL.md:1092` and `bot-participation-contract.md:627` are live, non-retirement
uses that post-date the landing.

**Upgraded from PLAUSIBLE to ACCURATE (2).** Report-claims 17 and 19 were recorded as
structurally-certain-but-not-re-run. Both mutations were run: the heading reversion failed exactly
`…[standards-branch-cleanup.md]`, and the `--enabled-bots` reintroduction failed exactly
`…[skill-md-github-pr]` with `github_pr.py: error: unrecognized arguments: --enabled-bots`.

**REFUTED (0).** No finding in this document was contradicted by the re-derivation.

**UNVERIFIABLE, unchanged (3).** Report-claims 22 (the full-build figures), 23 (the four pre-squash
commit ids) and 24 (GitHub-side CI, review and CLA state). Each is unverifiable for a structural
reason — no full build was run, the branch was deleted on squash-merge, and the clone carries no
GitHub state — not for want of looking.

**Citation drift corrected (12).** `_documented_invocations` `:170-192` → `:162-185`; the bracket
skip `:187` → `:182`; the derived-skill-set assertion `:262` → `:244-248`; the wide-heading assertion
`:271` → `:272`; `TestDocumentedReviewMergeInvocationsParse` `:287` → `:288`; the size assertions
`:299-306` → `:299` and `:304-309`; the floor `:302` → `:304`; the module prose `:128-133` →
`:128-134`; the `MalformedBotFlag` docstring `:315-322` → `:316-322`; `parse_causes` `:382-422` →
`:382-423`; `github_pr.py:952-953` → `:953`; the canonical blocks `:970-990` / `:1000-1010` →
`:964-997` / `:999-1010`. Every other `path:line` in this document was opened and matched the quoted
text.

**Count corrected (1).** The plan's Claim-labels table has **eight** rows, not seven.

### What the re-derivation added

- **G2 — `create-pr.md` Step 4 marks the step `done` on a failed `ci pr create`.** Neither document
  named it. It is a live instance of the plan's own Goal class inside D0's stated population,
  reachable because the provider returns exit 0 on failure and the step states no `status` branch.
  Reproduced end to end.
- **G3 sharpened** from "the router returns exit 0" to "both providers return exit 0
  unconditionally", with the three validating sites and the two non-validating sites enumerated.
- **G8 broadened** from the module docstring to the three prose-bearing literals that carry the same
  false two-FORM split — including the `_split_bots` rejection message, which is user-facing error
  text that names the wrong flags for a `bot_kind:cause` token — plus the `deficit` usage line's
  omission of `--refusal-size-caps`.
- **G9 absorbed** the D3 derivation fragility the Correctness review had recorded without raising:
  the first-notation / all-remaining-tokens split and the broad `'[' in block` skip are the mechanism
  by which the sweep can shrink while staying green, so they belong with the unpublished size and the
  under-set floor.
- **G11 extended** to cover both unreported obligations (the executor empty-value claim label and the
  never-fired endorsement-trap condition), and its evidence now cites the executor stripping at its
  real source, `execute-script.py.template:1419-1420`, rather than only the doc that describes it.
- **G1 evidence extended** with the sweep establishing that no *authored* `ci` invocation places
  `--plan-id` before a verb that declares it — the three pre-verb sites all name verbs that do not —
  so the exposure is the runtime-composed invocation, exactly as the plan's Notes predicted.

`gaps.md` was renumbered contiguously G1–G11 in severity order (1 blocker, 5 major, 5 minor) and
every cross-reference in this document now points at the renumbered entry.

### What did not change

The verdict stays **verified-with-gaps**. Every deliverable landed, both owned suites pass, both
mutation proofs hold, and no gap here undoes what shipped. The blocker survives and is broader than
first recorded; the single most important correction is that the envelope contract's `ci` claim is
false for **ten** subcommands rather than six, all of them `required=True`, all executed to an exit-2
rejection.
