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

# A document asserts something about a site outside itself, and nothing checks the assertion

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

A documented `{a|b|c}` enum in a `## Canonical invocations` block is **not commentary**. The
plugin-doctor `manage-invocation-invalid` analyzer reads that block as **source of truth**, so a block
that diverges from the live argparse `choices` is an **incorrect oracle**, not merely stale docs. A
reader — human or agent — following the documented contract and meeting a real value the block omits
would classify it as an invented value under this project's own *"never invent script subcommands"*
rule, and would be wrong.

⛔ **The original motivating instance is REFUTED, and that is the most important thing in this plan.**
The founding claim was that `manage-metrics` SKILL.md listed six of eleven `DISPATCH_TERMINATION_CAUSES`
values. Re-verified against the implementing source: the script defines **11** and **all 11 appear in
the SKILL.md**. It was closed by an earlier commit, not by any plan.

⭐ **The refutation strengthens this plan rather than weakening it.** The one instance anybody had
actually looked at turned out to be fine — which is exactly why the population sweep and the
mechanical guard are the deliverables that matter. **A class cannot be retired from the sample that
motivated it.**

⛔ **And there is a lesson in *how* it was caught.** The same premise was labelled `OBSERVED` here and
`HYPOTHESIS` in a twin plan in another epic. Only the twin carried a named confirm/refute artifact,
and only the twin's run caught the refutation on contact instead of rewriting a correct file to match
a dead premise. **A claim copied into a second plan does not inherit the first plan's verification,
and an inherited `OBSERVED` is the more dangerous half.**

The surviving subject is the **class**: a document asserting something about a site outside itself,
with nothing checking the assertion. Instances span far past argparse — a central standard claiming N
siblings bind an obligation when one did; an ADR cited as accepted while its recorded status is
`Proposed`; a skill body gaining an authoring-time `MUST` while its activation description still
scopes it to interactive use; a standard describing a suppression without naming where it is
enforced; a thin-pointer skill breaking its own no-duplication rule three lines after stating it.
**In every case the assertion has no named, checkable referent — exactly the thing a `HYPOTHESIS` is
required to have.**

## Goal

A cross-document claim carries a named, checkable referent, and a mechanical guard fails
`quality-gate` when a documented enum, a documented count, or a documented registration diverges from
the live source it claims to describe.

## Deliverables

1. **D1 — GATE: derive the population.** Mutates nothing. Compare every documented `{a|b|c}` enum in
   every `manage-*` canonical block against its live argparse `choices`, and report the divergent set.
   *Done when:* the **divergent count** and the **number of blocks examined** are reported as **two
   separate numbers**, and the swept population is stated.
   ⛔ **The known instances are a SAMPLE, not an enumeration.** Two live drifts were reported by
   another run and are **leads to confirm, not established facts**: `manage-findings` SKILL.md
   documenting fewer types than `FINDING_TYPES` defines, and `manage-lessons` SKILL.md documenting
   fewer categories than `LESSON_CATEGORIES` defines. Confirm each at its named symbol.
   ⭐ **Key the derivation on surface-change events, not only on a static doc scan.** The divergence is
   usually not *authored* — it is **left behind when a surface widens**, so the real population is
   *"every doc that documented the old form"*, which a per-skill sweep will miss.
   ⛔ **STOP CONDITION.** If the population cannot be derived mechanically, halt and report it. Do
   **not** substitute a hand-listed set of scripts to check — a hand-maintained population is the
   defect class this plan closes, reproduced inside the fix.
2. **D2 — The structural guard.** A plugin-doctor rule failing `quality-gate` when a documented enum
   in a canonical block diverges from the live argparse `choices`. The comparison is mechanical and
   the data is already introspectable — the same class of deterministic check the argument-naming
   cluster already performs for flag names.
   *Done when:* the rule ships, is **population-derived from the script inventory** (never a hardcoded
   list), and **publishes the population size it examined**.
   ⚠ **Mind the declared-versus-derived distinction** — it is this plan's worked example. In the
   `record-dispatch-boundary` case, `choices=` **is** derived from the source tuple and is therefore
   *not* a mirror, while the hand-listed values in the argparse `description=` string **are**. A guard
   that cannot tell them apart will either miss drift or invent it.
3. **D3 — Extend the same mechanism one surface outward: README versus `plugin.json`.** A bundle
   README that states a skill count while `plugin.json` registers a different number is the identical
   shape, and it is mechanically checkable.
   *Done when:* the rule compares each bundle README's enumeration against its `plugin.json`
   registration and fails on divergence.
   ⭐⭐ **This is the elevation that makes D3 worth its cost: three of the known undercounts hide a
   *security* skill** (`javascript-security`, `python-security`, `plugin-security`). A README
   undercount is cosmetic right up until the omitted skill is the one a reader would go looking for.
4. **D4 — Fix what the sweeps confirm.** Correct the live divergences D1 and D3 surface.
   *Done when:* each confirmed divergence is fixed, and each unconfirmed lead is recorded as refuted
   with its evidence. The known leads to check: the four bundle READMEs whose counts disagree with
   `plugin.json`; the false *"not registered in plugin.json"* sentence still believed present in two
   READMEs; and a `skills:` example naming `pm-dev-java-cui:cui-logging-enforce`, a skill that does not
   exist under that name — **copying that example fails to load**, which makes it the highest-severity
   item in the group.
5. **D5 — Retire the confirmed cross-document contradictions.** Four bounded items, each already
   spot-verified and each an instance of this exact class:
   - Unqualified `standards/…` references in `recipe-cui-logging-enforce`'s fix sequence, where the
     skill has **no `standards/` directory of its own** and the targets belong to a sibling skill the
     same file qualifies correctly elsewhere.
   - Four superseded per-type `change-{bug_fix,enhancement,feature,tech_debt}.md` files sitting beside
     the consolidated `change-types.md`, referenced by nothing. *Where a copy exists, delete the copy.*
   - Two `standards/` documents referenced by no SKILL.md — wire in or remove.
   - `AGENTS.md` instructing a `Co-Authored-By` trailer that contradicts the repository convention,
     **and** `AGENTS.md` and `CLAUDE.md` listing **different** forbidden Bash constructs for the same
     one-command rule. Two authoritative sources, one rule.
   *Done when:* each is fixed or explicitly refuted with evidence.
6. **D6 — Tests, each verified to FAIL pre-fix.**
   - (a) The guard flags a block with a deliberately truncated enum.
   - (b) The guard **passes** on a correct block.
   - (c) The guard's population is **non-empty** and contains a known-good member — **the
     positive-population assertion**, without which a glob that matches nothing looks identical to one
     that matches everything correctly.
   - (d) The README-vs-`plugin.json` check flags a deliberately miscounted README and passes a correct
     one.
   *Done when:* all four hold, and the report states that each was seen to fail before it passed.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables, **at the split presumption**.
**No split.** D1–D3 build one mechanism and D4–D5 are its first application; splitting would ship a
guard with nothing proven to be caught by it, or a set of doc fixes with nothing preventing their
recurrence — and recurrence-prevention is the entire point, given that the founding instance had
already been fixed by hand once. ⚠ If D1's population turns out to be very large, **D4 may be narrowed
to the confirmed set and the remainder reported as residue** rather than inflating the run.

## Out of scope

- ⛔ **The refuted `manage-metrics` six-of-eleven fix. DO NOT IMPLEMENT IT.** All eleven values are
  already documented at both sites. Editing that file to "add the missing five" would corrupt a
  correct document to match a dead premise — which is precisely the failure the twin plan's label
  prevented.
- **The `--enabled-bots` argparse rejection.** It was folded here and then **retracted**: no
  `--enabled-bots` CLI flag exists anywhere in the bundles. Every occurrence is the retired
  `enabled_bots` **config knob** in migration prose. No canonical block advertises the flag, so there
  is nothing for this rule to catch — the two agents that hit it had read a **stale plugin cache** and
  invoked a retired flag against a current script. ⚠ **Guard against the inverse error:** the
  stale-cache explanation invalidates an *artifact*; it must never *acquit a defect*. Here it acquits
  nothing real, because the flag's absence from source was verified directly rather than inferred from
  the story.
- **The `--participated-bots` zero-value rejection.** A distinct defect in the same script, owned by
  another epic. ⛔ **Both rejections log as `failure_kind=argparse_rejection` and are therefore
  indistinguishable in the record** — so D1's population derivation must never treat that log
  signature as identifying.
- **The retried-step attempt-identity gap.** A separate open defect belonging to the finalize phase.
  Two findings, one incident: resolve them as a set, but do not merge them into this plan's surface.

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — the new analyzer (D2, D3).
- `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` and
  `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — the two reported enum drifts, if
  D1 confirms them.
- `marketplace/bundles/*/README.md` and `marketplace/bundles/*/.claude-plugin/plugin.json` — the
  count-versus-registration surface (D3, D4).
- `marketplace/bundles/pm-dev-java-cui/**` — the non-existent skill name in a `skills:` example, and
  the unqualified `standards/` references.
- `marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/standards/**` — the four
  superseded per-type files.
- `AGENTS.md`, `CLAUDE.md` — the two governance contradictions.
- `test/**` — tests.
- **Open-ended:** whatever additional SKILL.md files D1 surfaces.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The `manage-metrics` six-of-eleven divergence **no longer exists** | OBSERVED | `manage-metrics.py` § `DISPATCH_TERMINATION_CAUSES` and `manage-metrics/SKILL.md` — ⛔ **re-verify before touching that file**; the plan's instruction is to leave it alone |
| The plugin-doctor `manage-invocation-invalid` analyzer reads the canonical block as source-of-truth | OBSERVED | that analyzer's own source, plus the § Canonical invocations convention stated across bundles |
| `manage-findings` documents fewer types than `FINDING_TYPES` defines | HYPOTHESIS | that SKILL.md versus the `FINDING_TYPES` constant — **another run's finding, spot-verified by that run, not independently** |
| `manage-lessons` documents fewer categories than `LESSON_CATEGORIES` defines | HYPOTHESIS | that SKILL.md versus the `LESSON_CATEGORIES` constant — same provenance caveat |
| Four bundle READMEs state skill counts that disagree with `plugin.json`, three of them hiding a security skill | HYPOTHESIS | each README versus its `plugin.json`. ⛔ **Re-derive every count**; the reported numbers are leads |
| Two READMEs still contain the false *"not registered in plugin.json"* sentence | HYPOTHESIS | those files — an asserted **presence**, cheap to check |
| A `skills:` example names `pm-dev-java-cui:cui-logging-enforce`, which does not exist | HYPOTHESIS | that README, and the bundle's actual skill list. An asserted **absence** on the skill side — verified as a presence |
| The `record-dispatch-boundary` mirror set is **five**, not three, and the contract test reads only one document | HYPOTHESIS | the `description=` string, the standards doc's restated enum, and the test's own site-parsing helper. ⭐ **This is D2's worked example** — get it right and the declared/derived distinction is settled |
| Cluster C19 holds 18 corpus instances of doc-contract divergence | HYPOTHESIS | ⛔ a router's count over a corpus **not reachable from this clone**. Treat as a **floor and a sample**, never as an enumeration |
| The five PR-#1115 instances (standard's sibling count, ADR status, description-vs-body, unnamed enforcement site, thin-pointer self-violation) | HYPOTHESIS | each at its own document. They are quoted here to define the **class**, and none needs to be fixed by this plan to justify it |
| Nothing already checks README counts against `plugin.json` | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — search plugin-doctor's existing rules before building D3 |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D6(c), the positive-population assertion, is the single most important test here.** This
  project's recurring failure is a detector that reports clean because it examined nothing. A guard
  whose glob matches zero files is indistinguishable from a guard whose every match passed — unless
  the population size is asserted to be non-empty and to contain a known member.
- ⛔ **The guard's rule text is text-whose-value-is-what-a-reader-does**, so it gets a **cold read**:
  show the Step 6 verification sub-agent a `choices=` derived from a source tuple and a `description=`
  string that hand-lists the same values, and ask which is a mirror that can drift. The correct answer
  is **the `description=` only**. If it flags the derived `choices=`, D2 will manufacture false
  positives on every correctly-written script.
- Report the swept population and the divergent count **separately** in the run report. A count of
  blocks examined is a **volume**, not a coverage number.
- **Every D4/D5 item that turns out to be already-fixed must be reported as refuted with its
  evidence**, not silently dropped — two items from the source review were already fixed at authoring
  time, and recording that is what stops them being re-filed a third time.
- Python, doc, and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing — several sibling plans in this epic also add plugin-doctor detectors** (the
  inert-thinking-directives plan, the migration-shim plan, and possibly the invented-flags plan).
  **Serialize against whichever is in flight — same analyzer surface.** The config-knob-surfacing plan
  is the same *documentation-completeness* class but a **different bundle**, so it is disjoint and may
  run in parallel.
- ⚠ **An adjacent plan in this epic is the same archetype one layer down**: a finalize step declares a
  required prompt-body field while the generic dispatch template has no slot to carry it — declaring
  and satisfying as two unlinked edits. **Decide at outline whether to absorb it.** For: one
  enforcement rule ("a declaration without a producer is a build error") could close both. Against: a
  merged plan spans two bundles. The `records_facts` frontmatter shipped elsewhere in this project,
  with its no-orphan-declaration and no-undeclared-record guards in both directions, is the reference
  implementation for either choice.
- ⭐ **The standing remedies, restated so they are not re-derived.** Never state a consumer count
  produced by looking — derive it from the population via a structured query and **state the query**,
  so the claim is reproducible. Every set-guarding detector is **population-derived**. And **when a fix
  widens the population, re-check the detector's anchor** — a detector built against the old, narrower
  domain is silently wrong against the new one. One run hit that hazard **twice on a single
  signature**.
- ⭐⭐ **The rule this plan exists to establish, in one line:** *scope the guard to the directive, or
  scope the directive to the guard — never state a directive the guard cannot see.* An honest note
  that a guard covers only part of a population is the right first move and is on-theme, but **honesty
  is not enforcement**.
- A related density observation, filed as context rather than as work: one run produced **seven
  argparse rejections across six distinct components**. No single component is the culprit, so it is
  not a defect anywhere — but an incomplete canonical block is one of the mechanisms that produces
  that density, and D2 reduces it.
- ⛔ **Do not go looking for the orchestrator spec, the inbox messages, the lessons corpus, or
  `doc/review-26-07-04.md`.** The first three live under `.plan/` and are absent from this clone; the
  review document is being retired and its still-valid findings are already transcribed above.
  Everything needed is in this file.
