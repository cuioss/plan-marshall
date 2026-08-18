> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The finalize step contract states its ordering, its carriage and its re-fire currency truthfully

**Epic:** truthful-signals
**Branch prefix:** `fix` — every deliverable repairs a shipped signal that asserts more than the tree
supports, or a guard that passes against the defect it names.

## Problem

The finalize-step contract is described in four places at once — implementor frontmatter, the
`extension-api` ext-point standards, the `phase-6-finalize` dispatcher and its per-step standards,
and the user-facing configuration pages — and each of those surfaces has drifted from the others in
the same direction: **towards claiming coverage that is not there.** Four ceremony gates that were
migrated onto per-step `lane` overrides still have rows in the consumer-facing run-at-all table, and
setting them returns `status: success` while nothing reads the persisted key. A prompt-body
declaration key was added with a both-direction conformance guard that reads a surface 24 of the 26
implementors do not have, so it is vacuous for them; the same commit shipped a dispatcher extension
slot that the guard rejects. Nine hand-written `[DISPATCH]` emission blocks sit at real dispatch
sites in a tree whose own standard calls that shape forbidden and calls the resolve seam "the sole
permitted dispatch-emission shape". And four separate areas — step ordering, the push barrier's
re-fire mapping, the verdict-currency refusal table, and the declared `verdict_inputs` globs — were
each demonstrated, by a recorded mutation, to leave the suite **green** against exactly the defect
the guard over them names. A fifth, the two canonical `destroys` declarations, is an asserted
unpinnedness that D2 re-verifies by mutation before it adds the guard.

The mechanism is common to all of them: **a fact is declared in one place and restated in another,
and nothing derives the second from the first.** `test_step_prompt_fields_contract.py` reads
carriage from `prompt: |` blocks while `ext-point-finalize-step.md:130` names the step's *input
table* as the declaration surface; `test_verdict_currency.py:565` asserts a refusal heading with a
bare substring search over the whole file, so a cross-reference to the other step's section satisfies
it; `test_git_workflow.py:632` opens its test body with its own RE-FIRE/SKIP oracle and then asserts
against that oracle. Each restatement is individually plausible and collectively unbound, which is why
the drift is invisible until someone re-derives the population by hand.

## Goal

Every statement this plan touches about the finalize step contract — an order, a carried prompt-body
field, an emission site, a return signal, a configuration key, a coverage verdict — is either derived
from the frontmatter and code that decide it, or is bound to that substrate by a test that has been
seen RED against the defect it names. No consumer-facing page names a configuration key that does
not resolve, and no guard this plan leaves behind passes against the defect it was written for.

## Deliverables

Each deliverable names the gap ids it closes. The gap bodies — Kind, Severity, Where, What is wrong,
Why it matters, Fix, Done when — are **git-tracked and are required reading before implementing the
deliverable that cites them**: `doc/plans/truthful-signals/{source-plan-dir}/gaps.md`, and the
sibling `verification.md` § "Adversarial review" where the evidence matters. Where a gap body and its
plan's `verification.md` § "Adversarial review" disagree, the adversarial-review section wins.

**Every count in this plan is a lead, not a fact. Re-derive it at the moment of the change** — the
clone this run executes in is not guaranteed to match the tree these gaps were written against.

Deliverables are ordered so the eight `high` gaps land first: D1 gates, D2 carries three highs, D3
two, D4 two, D5 one.

---

### D1 — Derive the four populations this plan rests on, or HALT

*(closes 040/G3)*

Five later deliverables — D2, D3, D5, D7 and D8 — scope themselves by a population that must be
**derivable from the tree**.
Derive all four first, in the run report, naming the exact command used for each. **If (a) or (c)
cannot be derived, stop and report the plan blocked** — do not substitute a hand-maintained list,
because a hand-maintained population is the defect class several of these gaps already are.

- **(a) The `ext-point-finalize-step` implementor set and its frontmatter facts** — every implementor,
  with `order`, `mutates_source`, `head_dependent`, `post_run_review`, `records_facts`,
  `requires_prompt_fields`, `verdict_inputs`, `reads`, `destroys`. Derive it from the `implements:`
  frontmatter across `marketplace/bundles/**` and `.claude/skills/**` (the mechanism
  `extension_discovery.find_implementors` uses). This is the substrate for D2, D3, D7 and D8.
  ⛔ Do **not** use `test/_shared/_dispatch_roster.py` as the population source — it is a
  heading-bounded Markdown-section and roster-row parser for the `dispatch-inline-split.md` rosters,
  not a frontmatter population source. (This mis-pointer has been rediscovered twice; see 040/G5,
  which is not in this plan's scope.)
- **(b) The tree-wide hand-written `[DISPATCH]` emission population** — every occurrence of a
  `manage-logging work` call carrying a `[DISPATCH]` message under `marketplace/` and `.claude/`,
  split into *dispatch sites* (the file also contains an `effort resolve-target` call inside a fenced
  command block) and *doc-echoes* (it does not). ⛔ Two exclusions the derivation MUST apply, because
  a bare grep gets both wrong: **(i)** `ref-workflow-architecture/standards/dispatch-logging.md` is
  the standard that forbids the shape and quotes it to forbid it (§ "Anti-pattern (forbidden)" and
  the emission-contract prose) — it is never a member of this population and is never edited by D5;
  **(ii)** the split is decided by a fenced, executable `effort resolve-target` command block, **not**
  by the string appearing in prose — the two doc-echoes each mention `manage-config effort
  resolve-target …` inline while describing what the *dispatcher* does, and a string-match split
  misclassifies both as dispatch sites. D5's scope is exactly this split. The gap body records 11
  matches in 7 files, 9 blocks across 5 dispatch-site files — **re-derive it; do not trust those
  numbers**.
- **(c) The per-implementor input-table `Required` row population** — for each implementor doc, the
  rows of any prompt-body-field table under a `Required` column whose key falls outside the generic
  dispatch contract. Parse the table header to locate the `Required` column; never assume a column
  position. This is D3's new assertion surface.
- **(d) The `from _dispatch_roster import` importer set under `test/`** — needed only to settle
  040/G3.

Then close 040/G3: `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md`
§ Deliverables → D2 asserts `_dispatch_roster.py`'s "sole consumers are the phase-6-finalize tests".
Replace that clause with what population (d) actually returns, keeping the paragraph's conclusion
(that the module is a Markdown-section/roster-row parser, not the execution-context workflow roster)
unchanged — that conclusion is independently correct and is not in question.

*Done when:* the run report carries a § Populations section naming each of (a)–(d), the command that
produced it, and its size **as re-derived during this run**; and `040/report-01.md` § D2 asserts no
importer set that the derivation in (d) contradicts.

---

### D2 — Six guards that pass against the defect they name

*(closes 230/G2, 310/G4, 440/G6, 440/G1, 300/G1, 302/G8)*

Every item here is a `vacuous-test`, `vacuous-guard` or `missing-test` gap. **A vacuous-guard gap is
closed only by a test that has been seen RED against the defect it names.** For each of the six, the
run performs the named mutation, records the observed failure (test id and message) in the run
report, restores the file **byte-identically** and confirms `git diff --quiet` before moving on. A
deliverable item whose red was not observed is reported as **not done**, never as done-with-a-caveat.

1. **230/G2 — the era-stamp ordering adjacency has no test.** Add a derivation test asserting, from
   discovered finalize-step frontmatter (never hardcoded), that
   `project:finalize-step-era-stamp-fill.order` lies strictly between `default:create-pr.order` and
   `default:ci-verify.order`, in the discovery-driven style of
   `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`. Then correct
   `doc/plans/truthful-signals/230-.../report-01.md` § D5(a), which cites
   `test_finalize_edge_ordering.py` as deriving this invariant — it derives only the two
   gate-relative edge families and says so in its own prose.
   *Red:* set the era-stamp step's `order` to a value above `ci-verify`'s and observe the new test
   fail.
2. **310/G4 — the push barrier's re-fire mapping is self-asserted.**
   `test/plan-marshall/workflow-integration-git/test_git_workflow.py::test_verdict_token_drives_refire_skip_mapping`
   defines its own `verdict()` oracle three lines above the assertion. **This plan pre-decides the
   gap's option (a)**, so the run makes no mid-run call: add a pure helper
   `push_barrier_action(state) -> 're-fire' | 'skip'` to
   `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`, have
   `cmd_branch_sync_state` include it in its payload as `barrier_action`, have
   `phase-6-finalize/SKILL.md`'s push-barrier item branch on that field rather than on the state
   token, and assert the helper's output per state. Option (a) is chosen over (b) because it removes
   the prose from the decision path entirely rather than teaching a test to parse prose.
   *Red:* make the helper return `re-fire` for `remote_absent_landed` and observe the test fail.
3. **440/G6 — the refusal-table guard is a bare substring search.**
   `test/plan-marshall/phase-6-finalize/test_verdict_currency.py:565` asserts
   `_REFUSAL_HEADING in body` over the whole step doc; both tabled steps carry that phrase twice —
   once as their heading and once inside a cross-reference to the *other* step's section — so
   renaming either heading leaves the guard green. Replace it with a heading-anchored match (an ATX
   heading in that step's own doc), keeping the assertion message and adding the matched heading
   level to it.
   *Red:* rename **only** the `### Verdict-input surface — deliberately undeclared` heading in
   `.claude/skills/finalize-step-plugin-doctor/SKILL.md`, leaving the cross-reference untouched, and
   observe the test fail. Repeat for the `##` heading in
   `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`.
4. **440/G1 — a wildcard-free `verdict_inputs` glob is bound to no existing path.** The
   declaration-conformance block in `test_verdict_currency.py` pins non-emptiness, well-formedness,
   `head_dependent` companionship and the no-`**` rule, but nothing pins that a wildcard-free glob
   names a path that exists. Add a guard that, for every glob in `_declared_surfaces()` containing no
   `*` or `?`, asserts the path exists under the repository root and is git-tracked; wildcard-bearing
   globs are exempt because they legitimately name a family. Name the declaring step and the
   offending glob in the message.
   *Red:* rewrite one declared literal glob to a path that does not exist and observe the failure.
5. **300/G1 — the two canonical `destroys` declarations are unpinned.** Two normative documents
   (`finalize-step-order-bands.md` § "`reads` and `destroys`", `ext-point-finalize-step.md`'s
   `destroys` row) name `archive-plan`'s `destroys: [plan-directory]` and `branch-cleanup`'s
   `destroys: [worktree]` as the anchors of that vocabulary, and nothing asserts either exists.
   Beside `TestNoTwoFinalizeStepsShareAnOrder` in
   `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py`, add a class that
   reads the two step docs' frontmatter directly and asserts each declaration, with the message
   naming the contract the declaration serves.
   *Red:* delete either `destroys:` block and observe the new test fail.
6. **302/G8 — three hand-maintained required-key lists with no binding.** In
   `test/plan-marshall/plan-orchestrator/test_landing_completeness.py`: (a) build `_facts_block`'s
   default dict by iterating `LANDING_REQUIRED_KEYS` rather than by literal, supplying a per-key
   sample value from a small lookup and failing loudly on an unmapped key; (b) add a test parsing the
   `| Key | Value | Source |` table under § "Required machine-readable fact keys" in
   `landing-payload-spec.md` and asserting the extracted key set equals `set(LANDING_REQUIRED_KEYS)`;
   (c) add the same for `emit-landing.md`'s Step 2 enumeration.
   *Red:* remove one key from `LANDING_REQUIRED_KEYS` and observe (b) and (c) both fail.

*Done when:* all six mutations were performed, each produced the named test failing, each file was
restored byte-identically with `git diff --quiet` clean afterwards, and the run report records the
failing test id and message for each. The six tests pass on the unmutated tree.

---

### D3 — Bind the step-specific prompt-body carriage contract to the surface that declares it

*(closes 260/G1, 260/G2, 260/G3, 260/G6, 260/G7)*

`requires_prompt_fields` was added with a both-direction conformance guard, and both directions read
carriage from a step's own `prompt: |` block. Only a small minority of implementors have such a block
(re-derive the exact figure from population (a) and (c) of D1 — do not trust a number here), so for
the rest the ∀-direction is vacuous; and the ∃-direction rejects the very extension slot the same
commit added to the generic dispatch template. Three separate documents also disagree about which
names are "generic contract" names.

**This plan makes the three contract calls at authoring time, so the run never has to.** Each is
recorded here with its reason; the run implements them and does not re-open them.

1. **Call one (260/G2): the generic template IS an admissible carriage site.** Take the gap's option
   (1). Reason: `phase-6-finalize/SKILL.md`'s generic templates already carry the
   `<plus every step-specific field the step declares in requires_prompt_fields>` slot and already
   instruct the dispatcher to forward every declared field; option (2) would delete a capability that
   landed deliberately, and the declaration is not left unbound by option (1) because call two gives
   it a real binding surface. So: `test_no_orphan_prompt_field_declaration` becomes conditional on
   the step having its own `prompt:` block, and a declaring step with no own snippet is compliant.
   Reword **all four** sites that justify the rejection with "the generic template carries only the
   five generic fields and [structurally] cannot send a step-specific one" — the assertion message
   and module docstring in `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`,
   `extension-api/standards/ext-point-finalize-step.md`, and
   `phase-6-finalize/workflow/pre-submission-self-review.md` — and remove the "a step's extras live
   in its own dispatch body" clause from the generic-template paragraph in
   `phase-6-finalize/SKILL.md`, which contradicts the forwarding instruction in the same sentence.
2. **Call two (260/G1): the input table is the third checked surface.** Add a third assertion
   deriving, per implementor, the input-table `Required` rows whose key falls outside the contract
   set (population (c) from D1), and asserting that set equals the step's `requires_prompt_fields`
   declaration. Parse the table header to locate the `Required` column. Then replace the "these two
   quantified directions are the ONLY … detector scope" and "asserts both directions and no third
   scope" statements in `ext-point-finalize-step.md` § "Step-specific prompt-body fields" with the
   three-surface statement that is then true.
3. **Call three (260/G3 + 260/G7): name the dispatcher-supplied inputs, and settle the two competing
   "six fields".** Introduce **one** named exempt set used by every assertion in the module:
   the generic contract names plus `caller_phase` plus the dispatcher-supplied runtime inputs
   `iteration`, `producer` and whitelisted `session_id`. Reason for exempting the runtime inputs:
   they are supplied by the dispatcher to *every* dispatched external step and are not carried by any
   step's own body, so requiring each step to declare them would be pure ceremony and would collide
   with the ∃-direction. Reason for `caller_phase`:
   `ext-point-execution-context-workflow.md` already declares it "the optional 6th-field extension of
   the canonical 5-field contract", so the guard's competing six-name list is the side that is wrong.
   Reflect both in the `requires_prompt_fields` row of `ext-point-finalize-step.md`, in that file's
   generic-contract name list, and in `phase-6-finalize/SKILL.md` § "Interface Contract for External
   Steps", so all three say the same thing. Extend the control test (or add a synthetic sibling) so a
   block carrying `caller_phase` is asserted **not** step-specific.
4. **260/G6 — broken link display text.** In `ext-point-finalize-step.md` § "Step-specific prompt-body
   fields", the opening link's display text is `../../agents/execution-context.md` while its href is
   `../../../agents/execution-context.md`. The href is correct; fix the display text to match, so the
   path a reader copies resolves.

*Done when:* adding a `Required: Yes` non-contract prompt-body row to any finalize-step doc without
the matching `requires_prompt_fields` entry turns a test in
`test_step_prompt_fields_contract.py` **red** (observed, then reverted byte-identically); adding
`requires_prompt_fields: [<field>]` to a generically-dispatched step with no own `prompt:` block
leaves the suite **green**; a synthetic block carrying `caller_phase` is exercised and asserted
not step-specific; `grep -rn "cannot send a step-specific one\|cannot carry a step-specific field"
marketplace/ test/` returns zero hits; and the fixed link's display text resolves to an existing file
when joined to its own directory.

---

### D4 — The consumer-facing finalize configuration surface names only keys that resolve

*(closes 190/G6, 190/G7, 190/G5)*

`doc/user/configuration.adoc`'s `[#run-at-all-gates]` table documents five `plan.phase-6-finalize.*`
keys that do not exist, and its worked-example block runs two of them. The failure is asymmetric and
both halves are bad: `plan phase-6-finalize get --field self_review` errors, while
`set --field self_review --value never` returns `status: success` and persists a key nothing reads.
That is a shipped false signal on the highest-risk gate the page describes.

1. **190/G6 — the four retired ceremony gates.** Delete the `self_review`, `qgate`, `simplify` and
   `steps['default:finalize-step-security-audit'].security_audit` rows, and replace them with one
   sentence beneath the table stating that the four ceremony gates are set through their owning step's
   `lane` override. Name the owning steps and the value transform from the canonical statement in
   `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` (search it for "ceremony gates"
   — it carries both the owning-step map and the `off`/`minimal`/other transform; take the mapping
   from there rather than from this plan, so a later change to it does not leave this page stale), and
   cross-reference the `<<execution-profile-lane-selection>>` section where the `lane` override row
   already lives. Replace the `get --field self_review` line in the worked-example block with
   `plan phase-6-finalize step get --step-id default:pre-submission-self-review`. Leave the
   `deep_lane`, `escalation` and `revalidation` rows untouched — all three resolve and validate.
2. **190/G7 — `plugin_doctor` never existed.** Delete the `plan.phase-6-finalize.plugin_doctor` row
   and change the `set` example in the same block to a knob that exists and round-trips —
   `plan phase-6-finalize set --field finalize_without_asking --value false` is documented in the
   same page's review-gates section. The lint the deleted row named is a project-local finalize step
   whose activation rides the lane/scope machinery, not a phase-level field; it is also meta-project
   only, so it does not belong on a consumer page at all.
3. **190/G5 — `set-lane` rejects a documented value with no route.** The `finalize-steps set-lane
   --lane` verb accepts a three-value subset while the per-element override validator accepts five,
   so `set-lane --lane minimal` exits 2 with a bare argparse rejection. **This plan pre-decides the
   gap's second branch:** keep the narrow write set (its narrowing is defended in
   `_cmd_finalize_steps.py`'s own docstring and is documented as deliberate in `configuration.adoc`'s
   "What `set-lane` accepts" admonition) and replace the bare argparse `choices` rejection with a
   check whose message names the working wider channel — the generic
   `step set --step-id <id> --param lane --value minimal` route. Then point the reader at that
   message from the `configuration.adoc` admonition. Reason for this branch over widening: widening
   the verb would contradict a recorded design rationale, which is a contract change this run may not
   self-approve.

*Done when:* every `Config key` cell in the `[#run-at-all-gates]` table resolves to a key the config
seed emits; every command in the code block that follows the table exits `0` and round-trips its
value through `get`; `grep -n plugin_doctor doc/user/configuration.adoc` returns no hit; and
`finalize-steps set-lane --lane minimal` is rejected by a message containing the string `step set`.

---

### D5 — Drive hand-written `[DISPATCH]` emissions to zero

*(closes 280/G2, 280/G4)*

`ref-workflow-architecture/standards/dispatch-logging.md` states that a caller MUST NOT hand-write a
`manage-logging work "[DISPATCH]"` line, lists that shape under **"Anti-pattern (forbidden)"**, and
declares the resolve seam "the sole permitted dispatch-emission shape". Population (b) from D1 is the
set of surviving violations, split into dispatch sites and doc-echoes.

1. **280/G2 — the dispatch sites.** For each file in the *dispatch-site* half of population (b), add
   `--workflow {the doc's own workflow notation} --plan-id {plan_id} --caller plan-marshall:{calling-skill}`
   to the `effort resolve-target` call that already precedes the dispatch, delete the hand-written
   emission block, and reword the surrounding prose to say the resolve seam emits the line. Two
   landed migrations are the templates to copy — `plan-marshall/workflow/execution.md` and the
   `phase-6-finalize/SKILL.md` dispatch block, both of which already pass the three flags. Also:
   - Delete or restate the two `planning.md` sentences that instruct the reader to "emit the
     standardized pre-dispatch attempt log line and the post-resolve dispatch log line", one of which
     cites `dispatch-logging.md` § Emission contract as authority for a shape that section forbids.
   - Reword the re-fire loops (the `outline_prompt` re-dispatch, the `until_clean` q-gate auto-loops,
     the `refine_prompt` re-dispatch) from "re-dispatch via the same `Task:` envelope" to "re-run the
     resolve (which re-emits) and re-dispatch" — a re-fired step that skips the resolve contributes
     one trail line for N firings, which is the retry blindness this migration exists to remove.
   - Where a resolve passes neither `--role` nor `--phase` (the `--default` site), **confirm the
     emitted label by executing the resolver before landing**: with all three absent the seam falls
     back to the literal `default`, so pass an explicit `--role` if today's hand-written label must be
     reproduced.
2. **280/G4 — the two finalize doc-echoes.** `phase-6-finalize/workflow/lessons-capture.md` and
   `phase-6-finalize/workflow/adr-propose.md` each say "The dispatcher emits the standardized
   `[DISPATCH]` work-log line **at the call site**", carry a heading naming that emission, and show
   the command block the standard now forbids. That dispatcher was migrated to the seam. In both
   files replace the sentence with "passes the dispatch context to its `effort resolve-target`, so
   the resolve seam emits the `[DISPATCH]` work-log line and the paired decision-log record, per
   firing", and delete the heading and its command block. Keep the cross-reference to
   `dispatch-logging.md`. These two files contain **no** `effort resolve-target` call, so do not try
   to add flags to one — that instruction is uncarryable here and was corrected in 280's own
   adversarial review.

*Done when:* the population-(b) derivation, **re-run after the edits**, returns zero matches across
`marketplace/` and `.claude/`; every `effort resolve-target` in the former dispatch-site files carries
`--workflow`; and no sentence in `plan-marshall/workflow/planning.md` instructs a hand-written
`[DISPATCH]` emission.

---

### D6 — The `baseline-reconcile` return contract, stated where its consumers read it

*(closes 310/G3, 310/G5, 310/G8)*

Three return signals were added — a fail-closed `merge_base_unresolved` skip, a `head_unresolved`
skip, and a `probe_mutated_head` error — and no skill or standards document mentions any of them
(the tokens occur only inside the script itself; re-derive that). All the consumer blocks instruct
"if the script exits non-zero → STOP", but the wrapper prints the payload through a helper that
always returns 0, so that instruction never fires; each block then parses a `classification` field
the skipped and errored payloads do not carry.

1. **310/G3 — document the signals and branch on `status`.** (a) Add the three reasons, with their
   behaviour, to the Step 3d "Skip Conditions Summary" table in
   `phase-2-refine/standards/refine-workflow-detail.md`. (b) In
   `phase-6-finalize/standards/finalize-step-sync-baseline.md` and at **both** `baseline-reconcile`
   call sites in `phase-6-finalize/standards/branch-cleanup.md` (the pre-rebase classifier and the
   § "Re-run the classifier against the current head" block), replace "if the script exits non-zero →
   STOP" with an explicit `status` branch: `status: error` → STOP and return the error TOON to the
   dispatcher; `status: skipped` → force the decision to `needs_user` and log the `reason`; only
   `status: success` proceeds to parse `classification`. (c) Add a **Return** block to the
   `baseline-reconcile` section of `workflow-integration-git/SKILL.md`, which today carries no return
   documentation at all — list the success fields, every skip reason including the pre-existing
   activation skips, and the typed errors. The sibling `branch-sync-state` section in the same file
   is the shape to copy.
2. **310/G5 — delete the dead disjunct.** Both threshold rules read
   `classification == overlap_no_content_conflict AND (auto_reconcilable == false OR {threshold} ==
   no_overlap_only)`. The classifier sets `auto_reconcilable` to exactly that classification test, so
   the first disjunct is unreachable inside a branch already conditioned on it — both docs even say
   so in a trailing parenthetical. Reduce both rules to the reachable condition, keep the explanatory
   sentence, keep `auto_reconcilable` in the payload, and add one sentence to the new Return block
   stating that it is derived and never downgrades an auto-resolvable overlap.
3. **310/G8 — narrow the non-mutation sentence to what the probe guarantees.**
   `finalize-step-sync-baseline.md` claims the probe "performs only `fetch + diff + merge-tree`". It
   also runs a stale-base-branch auto-update **before** the fetch, ungated by `--no-emit`, which
   persists a rewritten `base_branch` into `references.json` and emits a decision-log entry. Rewrite
   the clause to enumerate the real side-effect set: it never moves the branch ref and never touches
   the working tree; its only persisted write is that stale-`base_branch` auto-update, which fires
   only when the configured base branch no longer resolves on origin. Add `base_branch_updated` and
   `original_base_branch` to the new Return block, and state there that `--no-emit` suppresses Q-Gate
   findings but **not** the `references.json` update.

*Done when:* each of the three signal tokens appears in at least one authoritative skill document;
all three finalize consumer blocks branch on `status` before they parse `classification`;
`grep -rn "auto_reconcilable == false" marketplace/` returns zero hits; and no document claims the
probe "performs only fetch + diff + merge-tree" or that it writes nothing.

---

### D7 — Declare the finalize-step facts the contract advertises and no step carries

*(closes 300/G3, 302/G4, 302/G3)*

Three declaration keys are advertised by the contract and carried by nobody, so the properties they
were built to make checkable remain runtime accidents.

1. **300/G3 — apply the `reads` key.** A tree-wide search for a `reads:` frontmatter declaration
   returns zero (re-derive it). Concrete un-declared reads are documented in prose: the inline
   `emit-landing` step reads `record-metrics`' recorded facts and runs before `archive-plan`, which
   `destroys: [plan-directory]`; `print-phase-breakdown` reads the generated metrics. Add
   `reads: [metrics]` to `finalize-step-print-phase-breakdown.md` and `emit-landing.md`, and
   `reads: [worktree]` to any step whose body genuinely inspects the linked worktree — **verify each
   by reading the step body before declaring, and declare nothing a step does not actually read.**
   Use only the vocabulary tokens fixed by `finalize-step-order-bands.md`. Then update that file's
   vocabulary paragraph to cite a real `reads` declaration rather than only the two `destroys`
   anchors.
2. **302/G4 — `emit-landing` must declare `work_performed`.** Its Error Handling table has an
   `--outcome done` branch reachable without the step having performed its characteristic work (the
   inbox write returns an error → log and mark `done`), which is exactly the contract's stated
   trigger for declaring `work_performed`. Add `records_facts: [work_performed]` to the frontmatter,
   `--fact work_performed=true` to the Step 4 `mark-step-done` call and `--fact work_performed=false`
   to the Error Handling row's `done` call — spell that call out rather than leaving it prose. Add a
   row for `default:emit-landing` to the Declared-obligations table in `ext-point-finalize-step.md`
   with its consumer question ("did this run actually emit a landing?").
3. **302/G3 — give `pr` and `merge_state` a typed producer.** `landing-payload-spec.md`'s Source
   column says `pr` comes from "`create-pr` / CI" and `merge_state` from "`branch-cleanup` facts";
   neither fact exists, and the producer doc accordingly instructs deriving both by parsing prose.
   **This plan pre-decides the gap's preferred branch — wire the producers**, because the
   `records_facts` both-direction conformance test then holds them, whereas the documentation-only
   branch leaves two of the eight required landing keys re-derived from free text. Add
   `records_facts: [pr_number]` to `create-pr.md` with a `--fact pr_number=` at its terminal call
   site, and add `merge_state` to `branch-cleanup.md`'s declared `records_facts` union, recorded at
   each `--outcome done` branch that determines it (the union is a step-level declaration and each
   branch records only its honest subset — that reconciliation rule is already stated in
   `branch-cleanup.md` and must not be restated). Then correct
   `landing-payload-spec.md`'s Source cells to name the new facts, and correct the corresponding
   derive-from-prose instruction in `emit-landing.md`.

*Done when:* at least one step declares `reads:`, every declared token matches a `destroys` token or a
documented producer, and `finalize-step-order-bands.md`'s vocabulary paragraph cites a real
declaration; `emit-landing.md` declares `work_performed` and every `--outcome done` call site in its
body records it; `create-pr` and `branch-cleanup` declare and wire facts supplying `pr` and
`merge_state`; and the `records_facts` conformance suite passes with all three steps in its derived
population.

---

### D8 — Finalize standards that state more than the tree supports

*(closes 160/G2, 160/G4, 160/G9, 230/G1, 300/G2, 300/G4, 300/G8, 300/G9, 330/G1, 410/G1, 410/G4,
440/G2, 440/G3)*

Thirteen statements across the finalize standards, the ordering-band contract, the routing contract
and two composer fixtures each assert a rule, a population or a number that has moved. Each is
individually small; they are one deliverable because the fix shape is identical — **make the
statement true against the substrate that decides it, or reduce it to a pointer at the document that
owns it.** Take them in this order; the first three share one file and the third is a prerequisite of
the second.

- **160/G9** — the `display_detail` sizing paragraph in
  `phase-6-finalize/standards/pre-push-quality-gate.md` sends the reader to a document that states no
  ceiling and whose only mention of the field points back to a sibling of the sizing paragraph's own
  file. Repoint the link to the sibling that actually states the constraint (`external-step-contract.md`
  § "Required termination"), keeping the "do not restate the number here" discipline.
- **160/G4** — the module-tests honest-degradation branch (`whole_tree_available == false`) routes to
  Mark Step Complete (Success) while the default Branch A detail string still claims the module-tests
  dimension is green. Add a third `--display-detail` variant that does **not** contain the word
  "green" for that dimension, reference it from that branch, and document Branch A's default string as
  inapplicable on that path. Size it against its worst-case placeholder expansion, against the ceiling
  the now-correct pointer from 160/G9 leads to.
- **160/G2** — the parity population is called "derived, not hand-listed" in
  `pre-push-quality-gate.md` and "the derived set of dimensions" in `_gate_coverage.py`'s docstring,
  while `parity_population` returns a literal tuple of cells with hand-written notes and no
  production consumer reads it. **This plan pre-decides the gap's option (b):** relabel it honestly in
  both places as a *recorded* derivation, naming the commit it was derived at, and add at least one
  test that re-checks a cell against its substrate (e.g. asserting the `spdx-paths` note matches the
  actual SPDX path list the whole-tree quality gate builds). Reason for (b) over "make it genuinely
  derived": building new derivation machinery for an artifact with no production consumer is a
  capability change, and this plan's boundary is the truthfulness of the statement.
- **230/G1** — `phase-6-finalize/standards/push.md`'s "Finalize-internal re-stale (known-safe)" bullet
  names `era-stamp-fill` and `lessons-capture`; `lessons-capture` declares `mutates_source: false`.
  Replace the hardcoded pair with the discriminator plus correct examples: membership is a step whose
  authoritative doc declares `mutates_source: true` **and** whose `order` is greater than
  `default:pre-push-quality-gate`'s, because the ledger entry the re-stale is measured against is
  written by that gate. Derive both the discriminator's operands and the examples from population (a);
  do **not** substitute `finalize-step-lessons-housekeeping` or `finalize-step-sync-baseline` — both
  are ordered below the build and would be a fresh wrong example.
- **300/G2** — the Settle band row in `extension-api/standards/finalize-step-order-bands.md` promises
  "the guaranteed insertion room is in the major-step gaps above it" and names ranges that are all
  above `push`, so none of them can hold a pre-push step. Split the band explicitly into a pre-push
  sub-region and a post-push sub-region, state that the pre-push sub-region has **no** guaranteed
  insertion room today and that the sanctioned remedy for a new pre-push step is a deliberate re-space
  of the sub-cluster (the doc's own second alternative), and correct the stated occupancy to what
  population (a) returns.
- **300/G4** — the same file declares it "does **not** restate or alter that discriminator" and then
  restates the `mutates_source` obligation in three band rows. Reduce each to a pointer at the
  document that owns it, keeping only the numeric allocation in this file, which is what the file's
  own scope statement already claims.
- **330/G1** — `phase-6-finalize/standards/emit-landing.md`'s `post_run_review` paragraph still says
  the step "writes only under `.plan/`" and that the post-run guard reports "any dirty TRACKED path
  outside `.plan/`". The guard's exemption is keyed on git trackedness, not on the path prefix. Mirror
  the wording already applied to the two sibling docs (`workflow/lessons-capture.md` and
  `standards/finalize-step-preference-emitter.md` — read the corrected paragraph in the latter and
  match it).
- **440/G2** — `phase-6-finalize/SKILL.md` § Resumability states the head-dependent re-entry decision a
  second time, and is wrong in three places: the section's lead sentence, the `done | differs from live
  HEAD` table row, and the closing summary all prescribe an unconditional re-fire that the Step 3 table
  has narrowed to a verdict-currency classifier consult. Replace the row's action cell with a pointer
  to Step 3, extend the lead sentence's cross-reference so it defers the **action** as well as the
  membership, and qualify the closing summary. Leave the `matches` and `field absent` rows alone.
- **440/G3** — two operator-facing sentences in `phase-6-finalize/standards/branch-cleanup.md`'s
  pre-merge review-completeness barrier assert an unconditional rebase and an authoritative CI wait;
  on the `use_merge_queue == true` path the same document skips the rebase and downgrades the wait.
  Route both by `use_merge_queue`, matching the conditional form the rest of the document uses.
- **410/G1** — § (e) of `phase-6-finalize/standards/disposition-to-hint-routing.md` opens by requiring
  a **recognized** reviewer `bot_kind` validated against the registry-derived set and closes by
  instructing the emitter to exclude findings "without a `bot_kind`" — a presence-only test. The
  emitter is an LLM-executed prose contract, so that paragraph *is* its implementation. Rewrite the
  closing sentence to the recognized-identity form, changing nothing else in the section.
- **410/G4** — § (d) of the same file asserts, unqualified, that "`default` only ever means
  *unattributed*, never *cross-cutting*". True of the disposition→hint routing path; false of the
  `default` bucket, which has a second, still-live producer that a sibling contract in the same skill
  directory routes cross-cutting lessons-capture facts to. Scope the claim to a disposition
  recurrence, append one sentence naming the other producer with a cross-reference to it, and apply
  the same scoping to the `_UNATTRIBUTED_MODULE` comment in
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` and to
  `.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md`. **Leave
  `phase-6-finalize/workflow/lessons-capture.md` unchanged** — confirming that route is retained, not
  silently retired, is half of what this item settles.
- **300/G8** — `test/plan-marshall/manage-execution-manifest/test_declared_step_contract_regression.py`
  annotates the preference-emitter row of `_CONFIG_DECIDED_SEED` with a stale order. The annotations
  are load-bearing: the literal's own comment says it is deliberately scrambled so a reader can check
  the sequence assertions by reading these numbers. Correct the annotation to the order the step's
  standards doc declares. No assertion and no seed position changes.
- **300/G9** — `manage-execution-manifest.py`'s sort-rationale comment names the same step with the
  same stale order as a current fact. Rewrite the parenthetical so it names the order the step carried
  **at the time of the incident** with an explicit past-tense marker and, if it states a current
  order, states the one the standards doc declares. Keep the surrounding explanation unchanged.

*Done when:* each of the thirteen items' own *Done when* condition, as written in its source
`gaps.md` entry, holds — the run report records the check it ran for each, one line per gap id. In
particular: `grep -rn "auto_reconcilable == false"`-style absence checks are re-run after the edit,
not asserted; the `push.md` bullet names no step whose authoritative doc declares
`mutates_source: false` and no step ordered at or below the pre-push quality gate; the Settle band's
occupancy figures match population (a); and no sentence in `phase-6-finalize/SKILL.md` § Resumability
prescribes an unconditional re-fire.

## Out of scope

Every exclusion carries its reason, because with no operator watching, the written boundary is the
only thing standing between this run and mid-run drift.

- **302/G7 (register `default:emit-landing` in the tracked `.plan/marshal.json` registry) and
  302/G5 (classify it in the dispatched/inline roster).** Excluded **together**, because they are
  bidirectionally coupled: the closure test asserts `classified == registered` in both directions, so
  landing the roster row without the registry key turns it red as a *ghost row*, and landing the
  registry key without the roster row turns it red as an *unclassified step*. G7 needs a write to
  `.plan/marshal.json` — that file is git-tracked, but `cloud-plan-lane` states this lane **never
  touches `.plan/`** and must never write there, and the regeneration route (`/marshall-steward`)
  needs the generated executor a fresh clone does not carry. The contract wins over this plan, so the
  pair is left for a local run. Do **not** land G5 alone as a "safe half" — it is the half that turns
  the suite red.
- **410/G2 (assess the existing `default`-bucket hints against the D2 attribution gate).** Excluded
  for the same reason: its remedy edits `.plan/project-architecture/default/enriched.json`, inside the
  `.plan/` tree this lane may not write to, and the alternative branch (a grandfather note) still
  requires reading and adjudicating that store's contents to name entries by index. 410/G4, which
  makes the scoping claim that item depends on correct, **is** in scope as part of D8 — so the
  excluded work gets easier, not harder.
- **440/G4 (take D4's before/after re-fire measurement).** Excluded because it requires running two
  real finalizes over the same plan shape on a machine that holds plan state under `.plan/`, and
  a cloud clone has no plan state and no finalize to measure. This is the same wall the original run
  hit; authoring it again would author a stall.
- **230/G4 (implement D2's unified-barrier fold and its D5(b) test).** Excluded on two independent
  grounds. It is blocked on 230/G3's attribution measurement, whose substrate is the archived plan
  corpus under `.plan/` — absent from every clone, including a normal developer checkout. And its
  second blocker is explicitly a judgement call: reversing `ci-verify.md`'s documented
  triage-CI-first rationale, which this run may not self-approve.
- **Every gap in the source directories that this plan does not name.** The gap files carry more
  entries than the 41 assigned here; only the ids listed in the deliverable headings are in scope. In
  particular the *zero-emission* dispatch sites (280/G3, 280/G7) are a different defect from D5's
  wrong-shape sites and are not in this plan's set, so D5's closing sweep is scoped to the
  hand-written-emission population and does not claim the dispatch-site population is complete.
- **Widening the `set-lane` verb's accepted value set (190/G5's first branch), and building a genuinely
  derived `parity_population` (160/G2's option (a)).** Both are capability changes to a contract whose
  current narrowing is defended in a recorded rationale. This plan takes the other branch of each and
  says so in D4 and D8; the widening remains available to a later plan with an operator to authorize
  it.
- **Any plugin-cache sync.** A lane plan that edits `marketplace/bundles/` neither performs a sync nor
  records one as owed — the merged bundle source is authoritative and `/sync-plugin-cache` is a
  machine-local build step reading a git-ignored tree.

## Expected surface

Re-derive this list against the diff at verification time; a file changed that is not here is
collateral and must be explained in the run report.

**Tests**

- `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py` (or a sibling module) — D2.1
- `test/plan-marshall/workflow-integration-git/test_git_workflow.py` — D2.2
- `test/plan-marshall/phase-6-finalize/test_verdict_currency.py` — D2.3, D2.4
- `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — D2.5
- `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` — D2.6
- `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py` — D3
- `test/plan-marshall/manage-execution-manifest/test_declared_step_contract_regression.py` — D8
- `test/plan-marshall/build-pyproject/` — a parity-cell substrate test for D8 / 160/G2

**Scripts**

- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — D2.2
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py` and
  `.../manage-config.py` — D4.3
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — D8 (docstring)
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — D8
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — D8 (comment only)

**Contracts and standards**

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — D3, D7
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/finalize-step-order-bands.md` — D7, D8
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — D2.2, D3, D8
- `.../phase-6-finalize/standards/pre-push-quality-gate.md` — D2.3 (mutation target), D8
- `.../phase-6-finalize/standards/push.md` — D8
- `.../phase-6-finalize/standards/branch-cleanup.md` — D6, D7, D8
- `.../phase-6-finalize/standards/finalize-step-sync-baseline.md` — D6
- `.../phase-6-finalize/standards/emit-landing.md` — D7, D8
- `.../phase-6-finalize/standards/finalize-step-print-phase-breakdown.md` — D7
- `.../phase-6-finalize/standards/disposition-to-hint-routing.md` — D8
- `.../phase-6-finalize/workflow/create-pr.md`, `.../pre-submission-self-review.md` — D3, D7
- `.../phase-6-finalize/workflow/lessons-capture.md`, `.../adr-propose.md` — D5.2
- `.../phase-2-refine/standards/refine-workflow-detail.md` — D6
- `.../phase-3-outline/standards/outline-workflow-detail.md` — D5.1
- `.../plan-marshall/workflow/planning.md`, `.../planning-outline.md` — D5.1
- `.../workflow-pr-doctor/SKILL.md` — D5.1
- `.../workflow-integration-git/SKILL.md` — D6
- `.../plan-orchestrator/standards/landing-payload-spec.md` — D7
- `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — D2.3 (mutation target, restored)
- `.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md` — D8

**Documentation**

- `doc/user/configuration.adoc` — D4
- `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md` — D1
- `doc/plans/truthful-signals/230-finalize-retriggers-ci-after-it-has-already-gone-green/report-01.md` — D2.1
- `doc/plans/truthful-signals/510-.../plan.md` and `report-NN.md` — the lane's own artifacts

## Claim labels

Every confirm/refute artifact below is **git-reachable from a fresh clone**. No claim rests on
`.plan/` state, an orchestrator ledger, or a machine-local record.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 190/G6 reproduces: the four retired ceremony-gate rows are live in the run-at-all table | OBSERVED | `doc/user/configuration.adoc` — `[#run-at-all-gates]` rows `plan.phase-6-finalize.self_review`, `.qgate`, `.simplify`, `steps['default:finalize-step-security-audit'].security_audit`, plus the `get --field self_review` line in the following code block |
| 190/G7 reproduces: the `plugin_doctor` row and its `set` example are live | OBSERVED | `doc/user/configuration.adoc` — `plan.phase-6-finalize.plugin_doctor` row and the `set --field plugin_doctor --value always` example |
| 230/G2 reproduces: no test derives the era-stamp/ci-verify adjacency | OBSERVED (asserted absence, verified) | `.claude/skills/finalize-step-era-stamp-fill/SKILL.md` `order: 21`; `phase-6-finalize/standards/ci-verify.md` `order: 22`; `phase-6-finalize/workflow/create-pr.md` `order: 20`; `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py` — the only `ci-verify` occurrence is prose inside the floor test's docstring, no assertion |
| 260/G1 reproduces: the guard reads carriage only from `prompt:` literal blocks, never from the input table | OBSERVED | `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py` — `_step_specific_fields`, `_prompt_blocks`; `extension-api/standards/ext-point-finalize-step.md` § "Step-specific prompt-body fields" naming the input table as the declaration surface |
| 260/G2 reproduces: the extension slot and the ∃-direction contradict | OBSERVED | `phase-6-finalize/SKILL.md` generic-template paragraph (`<plus every step-specific field …>` slot, "a floor, not a ceiling", "the dispatcher MUST forward every declared field", "a step's extras live in its own dispatch body") vs `test_step_prompt_fields_contract.py::test_no_orphan_prompt_field_declaration` and its assertion message |
| 280/G2 reproduces: hand-written `[DISPATCH]` blocks survive at real dispatch sites | OBSERVED | `plan-marshall/workflow/planning-outline.md`, `.../planning.md`, `workflow-pr-doctor/SKILL.md`, `phase-6-finalize/workflow/pre-submission-self-review.md`, `phase-3-outline/standards/outline-workflow-detail.md` — each carries a `manage-logging work --message "[DISPATCH]…"` block; `ref-workflow-architecture/standards/dispatch-logging.md` § "Anti-pattern (forbidden)" forbids the shape |
| 310/G4 reproduces: the re-fire mapping test defines its own oracle | OBSERVED | `test/plan-marshall/workflow-integration-git/test_git_workflow.py::test_verdict_token_drives_refire_skip_mapping` — the local `def verdict(state)` three lines above the assertion it checks |
| 440/G6 reproduces: the refusal guard is a bare substring check | OBSERVED | `test/plan-marshall/phase-6-finalize/test_verdict_currency.py::test_every_tabled_refusal_carries_its_section` — `assert _REFUSAL_HEADING in body` over the whole doc; the phrase occurs twice in each tabled step's doc |
| No gap in this plan's set was already closed at authoring time | OBSERVED | Every gap listed in a deliverable heading was opened at its cited file and symbol and reproduces; the per-gap artifacts are the `Where` clauses of the source `gaps.md` entries |
| Population (a) — the implementor set and its frontmatter — is derivable from `implements:` frontmatter | HYPOTHESIS | D1 settles it: the derivation either returns a non-empty set carrying the named keys, or the plan HALTS |
| Population (c) — input-table `Required` rows outside the contract set — is derivable by a header-aware table scan | HYPOTHESIS | D1 settles it; the gap body reports exactly one hit today (`default:pre-submission-self-review` / `candidates`), so the new assertion is expected to start green — **re-derive, do not trust that count** |
| `.plan/marshal.json` and `.plan/project-architecture/default/enriched.json` are git-tracked but out of this lane's reach | OBSERVED | `.gitignore` negates `!.plan/marshal.json`; `git ls-files .plan/` lists both. `cloud-plan-lane` § Superseded-rules table states the lane never touches `.plan/`, and its closing rules forbid writing there. The exclusion is a contract boundary, not an invisibility |
| The expected surface is the union of the source gaps' `Where` clauses | HYPOTHESIS | The verification diff review settles it: any file changed that is not listed is collateral and must be explained |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half. The
three absences this plan builds on — no test derives the era-stamp adjacency, no step declares
`reads:`, `default:emit-landing` appears in neither roster — were each verified by search at
authoring time and **must be re-verified before the deliverable that depends on them is implemented**.

## Verification

Beyond each deliverable's own *Done when*:

1. **The red-first ledger (D2, and D3's declaration guard).** The run report carries a table with one
   row per mutation: the file mutated, the mutation, the test id that failed, the failure message,
   and the restore confirmation (`git diff --quiet` clean, bytes identical). **A guard whose red was
   not observed is reported as not done.** This is the one verification the plan cannot substitute
   anything for: five of these six guards were each demonstrated green against their own defect
   before this plan existed.
2. **Cold reads — four deliverables whose value is what a later reader DOES with the text.** Dispatch
   the pre-PR verification sub-agent (`cloud-plan-lane` § Step 6) with an *interpretation* brief, not
   a conformance brief: give the reader the changed text with no context from this plan, and have it
   report **which reading it took**. Record the answer verbatim; a wrong reading is a wording failure
   however complete the text looks.
   - **D4** — hand the reader the rewritten `[#run-at-all-gates]` section and ask: *"An operator wants
     to switch off the finalize self-review. What exact command do they run?"* A correct reading names
     a `step set … --param lane` route against `default:pre-submission-self-review`. A reading that
     produces `plan phase-6-finalize set --field self_review …` means the replacement sentence failed.
   - **D3** — hand the reader the rewritten § "Step-specific prompt-body fields" and ask: *"I am
     writing a finalize step that needs one extra prompt-body field. Where do I declare it, where do I
     carry it, and does the generic dispatch template suffice?"* A correct reading says the input
     table declares it, `requires_prompt_fields` records it, and the generic template does carry it.
   - **D6** — hand the reader the new **Return** block and one consumer's rewritten branch and ask:
     *"The command exited 0 and printed `status: skipped, reason: merge_base_unresolved`. What do you
     do next?"* A correct reading forces `needs_user` and does not parse `classification`.
   - **D8 / 440-G2** — hand the reader § Resumability alone and ask: *"A head-dependent step has a
     `done` record and HEAD has moved. Re-fire or skip?"* A correct reading consults the
     verdict-currency classifier rather than answering unconditionally.
3. **Absence re-verification.** Before implementing D7.1, D2.1 and (if it were in scope) any
   roster work, re-run the searches behind the three asserted absences named under Claim labels and
   record the result. An absence that has since been closed is recorded in the report and the
   corresponding item is dropped, not re-implemented.
4. **Population re-derivation at the point of claim.** Every count this plan's report states — the
   implementor set size, the `[DISPATCH]` match count, the input-table `Required` row count, the
   registry key count — is re-derived at the moment it is written, with the command shown. **No number
   is carried across from this plan file.**
5. **Build gate.** This plan changes Python (`git-workflow.py`, `_cmd_finalize_steps.py`,
   `manage-config.py`, `_gate_coverage.py`, `manage-execution-manifest.py`, `audit.py`, and several
   test modules), so the conditional build gate fires: run `./pw verify` per the lane contract and
   report its result. A docs-only subset does not exempt the run — the gate is decided on the actual
   diff.
6. **Collateral check.** Diff the changed-file list against § Expected surface and explain every
   file outside it.

## Notes

- **Provenance.** This plan carries 41 gaps drawn from twelve landed plans in this epic —
  040, 160, 190, 230, 260, 280, 300, 302, 310, 330, 410, 440. Each source directory's `gaps.md` and
  `verification.md` are git-tracked under `doc/plans/truthful-signals/{dir}/` and are the authority
  for the defect; this plan restates only enough to scope the work. Where a gap body and its
  `verification.md` § "Adversarial review" disagree, the adversarial-review section wins — it records
  which claims were upheld, refuted, re-severitied or added, and several gap bodies carry clauses that
  section corrected in place.
- **Two traps the source reviews already sprang, recorded so this run does not spring them again.**
  (i) `test/_shared/_dispatch_roster.py` is a Markdown-section parser, not a population source — two
  plans in this epic reached for it and both paid to discover otherwise. (ii) 280/G2's original fix
  instructed adding `--workflow` to an `effort resolve-target` call in seven files, two of which
  contain no such call; that instruction was uncarryable and those two files are D5.2's doc-echoes,
  not D5.1's dispatch sites.
- **`.plan/` is git-ignored and absent from this clone**, with the two exceptions named under Claim
  labels, which this lane still may not write to. Nothing in this plan asks the run to open a `.plan/`
  path; if a source `gaps.md` entry names one, that is context for a local run, not an instruction
  here.
- **Coherence.** The 41 gaps do cohere: every one of them is a statement about, or a guard over, the
  finalize step contract — what order a step runs at, what its dispatch carries, what its return
  signals mean, and when a recorded verdict is still current. The five excluded gaps are excluded for
  runtime reasons (a `.plan/` write, a measurement needing plan state, a contract reversal), not for
  thematic ones.
- **Sequencing.** D1 gates D2, D3, D5, D7 and D8 — do not start those before its populations are
  derived and reported. D2 and D3 both touch `phase-6-finalize/SKILL.md`; D6, D7 and D8 all touch
  `branch-cleanup.md`. Land in deliverable order to keep those edits from colliding.
- **The one number worth stating, as a lead.** Eight of the 41 gaps are `high`, and every one of them
  is closed by D2, D3, D4 or D5. If the run must stop early, stopping after D5 leaves no `high` gap
  open — **re-derive that mapping from the deliverable headings rather than trusting this sentence.**
