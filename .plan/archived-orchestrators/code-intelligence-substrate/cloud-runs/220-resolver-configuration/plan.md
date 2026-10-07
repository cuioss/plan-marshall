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

# Configure which derivation resolvers run, per machine

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

The derivation seam admits several simultaneously-active resolvers, and sibling plans supply
several more. **Nothing yet decides which resolvers run for which files** in a given checkout.

That binding is **machine-specific**: a resolver may depend on locally-installed tooling, so the same
project can legitimately have different active resolvers on different machines. It therefore belongs
in the machine-local run configuration, behind an operator-facing surface, rather than in a
version-controlled project file.

## Goal

An operator can see which resolvers were discovered, which are active and for which files, and change
that binding — persisted machine-locally — while **an unconfigured project keeps working with a real
default**.

## Deliverables

1. **D1 — a resolver-configuration menu** in the configuration wizard: list discovered resolvers, show
   which are active and for which file patterns, enable and disable them, and set precedence.
   *Done when:* the menu lists a discovered resolver and a change round-trips through it.
2. **D2 — a resolver section in the run-configuration schema**, persisted in the machine-local run
   configuration, mapping file pattern (or language) to resolver.
   *Done when:* the section persists and reloads, following the existing keyed-section pattern rather
   than a new store.
3. **D3 — precedence when several resolvers claim the same file, and a documented default for an
   unconfigured project.**
   ⛔ **The default MUST be a working default, not an empty binding.** A design where resolvers only
   run once configured would **reintroduce the zero-edge defect as a configuration failure instead of
   a derivation one** — the same broken outcome, one layer up.
   *Done when:* an unconfigured project still derives edges, asserted by test.
4. **D4 — retire the dead ignore-file negation** for a run-configuration path that does not exist, and
   drop the stale wording from the comment that introduces it.
   ⛔ **Surgical: that one negation and the comment wording only.** The neighbouring negations are
   **LIVE and load-bearing** — dozens of tracked files depend on them — and **MUST NOT be touched.**
   ⭐ This is folded in here because this plan establishes the correct store, so it is also the right
   place to remove the rule that misdirects readers to a non-existent one.
   *Done when:* the dead rule is gone and the before/after check in Verification shows no change to
   what git tracks.
5. **D5 — documentation.** The new menu, what it binds, and where it persists, in the user-facing
   configuration page; the new keyed section in the run-configuration schema standard, **stating
   explicitly that the store is machine-local.** ⛔ Ship docs **in this plan**.

Five deliverables — at the split guard's edge; evaluate before implementing.

## Out of scope

- **Writing new resolvers.** Excluded — sibling plans supply them; this plan binds them.
- **A project-shared (version-controlled) resolver binding.** Excluded: the binding is
  machine-specific by nature, because resolver availability depends on locally-installed tooling.
- **Touching the live ignore-file negations** beside the dead one. ⛔ Excluded absolutely — dozens of
  tracked files depend on them, and this is the single highest-risk line in the plan.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/marshall-steward/` — the new configuration menu.
  **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — the new keyed
  section. **OBSERVED.**
- `.../manage-run-config/standards/run-config-standard.md` — schema documentation. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/extension-api/` — the seam reads the binding to decide
  which resolvers activate. **HYPOTHESIS**, verify at outline.
- `.gitignore` — the dead negation and its introducing comment (D4). **OBSERVED.** ⛔ The neighbouring
  negations are out of bounds.
- `doc/user/configuration.adoc` — **OBSERVED**, the file exists.
- `test/plan-marshall/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The machine-local run-configuration store is the right home, and it is git-ignored | **OBSERVED** | ⛔ **Re-derive in the clone with `git check-ignore -v`.** Note the store itself is **not present** in a fresh clone — that is expected; **do not read its absence as an argument against it.** |
| A negation exists for a run-configuration path under the project-local directory, and **that file does not exist and is not tracked** | **OBSERVED** | ⛔ **Re-verify with `git ls-files`.** ⚠ **Carried deliberately as a lesson: a `.gitignore` entry describes a RULE, never the EXISTENCE of a file.** Reading that rule as proof of a live shared file once nearly produced an escalation over a non-existent conflict. |
| The neighbouring negations are live, with dozens of tracked files depending on them | **OBSERVED by enumeration, not by sampling** | ⛔ **Re-enumerate before editing anything in that file.** This is D4's safety boundary. |
| The run-configuration skill already persists keyed sections, and its store resolves against the main checkout regardless of caller directory | **OBSERVED** | The run-config script in the clone. A resolver section follows the existing pattern. |
| The configuration wizard has a menu structure a new entry can be added to without restructuring | **HYPOTHESIS** | ⛔ **The wizard's menu implementation was NOT read** when this was staged — the claim is inferred from its described role. **Read the dispatch before scoping D1.** |
| File pattern is the right binding key, rather than language, module, or build system | **HYPOTHESIS** | Confirm against the existing resolvers at outline. ⚠ Two of them split by **file extension inside one module**, which is evidence for pattern-keying and against module-keying — **but it is a single data point.** |
| Removing the dead negation changes nothing about what git tracks | **HYPOTHESIS** | ⚠ **An ignore-file edit is the kind of change that looks inert and is not.** See Verification — the check is cheap and **mandatory.** |

An asserted **absence** ("the negated file does not exist") is verified exactly as an asserted
presence — and here the absence is the entire justification for D4, so verify it first.

## Verification

- **D4 is verified by a before-and-after diff of git's own view.** Run the ignore-check over the
  neighbouring live paths and a working-tree status **before** the edit and **after** it, and diff the
  results. ⛔ **Identical output is the pass condition**; anything else means the surgical boundary was
  crossed.
- **D3 is verified on an unconfigured project**: edges must still be derived with no configuration
  present. A test that only exercises the configured path passes against the exact regression this
  deliverable exists to prevent.
- **D1 is verified by a round-trip**, not by the menu rendering: change a binding, reload, confirm it
  persisted to the machine-local store.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Sequencing.** There is nothing to configure until resolvers exist. ⚠ **Landing this before any
  real resolver exists would ship a menu that configures a single resolver — technically correct,
  practically untestable.** Best paired with, or sequenced after, the plans that supply resolvers.
- **Disjointness.** Surface-disjoint from the resolver-supplying plans (wizard plus run-config versus
  the build and plugin bundles), so concurrent execution is permissible. ⚠ **The run-configuration
  skill is widely consumed** — check for any sibling plan staged against it first.
- **Coordination.** Two other plans in this epic need a configuration surface for language-server
  settings. ⛔ **They must land inside this surface rather than forking a parallel one** — this plan
  is what makes that possible.
