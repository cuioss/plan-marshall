envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=landing
created=2026-08-09T17:52:24Z

# Foreign-repo residue RESOLVED — all four PRs opened

Supersedes the residue item carried in `generic-charter-language-specific-defect-006.md`
(landing) and the foreign-repo candidate-lesson written by `plan-retrospective`. The residue is
now closed on the delivery side; the **lesson** it produced is unaffected and still stands.

## What was wrong

PLAN-PR-022 finished with three of its eight deliverables landed nowhere. D6/D7/D8 targeted four
foreign repositories; all four branches were committed and pushed, and **zero** had a pull
request. Phase 5 recorded the gap correctly and three times — each foreign `[ARTIFACT]` line ends
with the literal words "PR not yet opened" — and every task still reported `done`, because task
done-ness is measured at the commit. That is sound for a host task, where the host PR carries the
commit, and structurally wrong for a foreign one, where nothing does.

## What was done

All four branches were first re-verified against their remotes (`ls-remote`), not against the
run's own claim — each was present at exactly the reported SHA, so the work was durable and only
the PRs were missing.

| Repo | PR | Deliverable |
|---|---|---|
| `cuioss/pr-agent-settings` | [#14](https://github.com/cuioss/pr-agent-settings/pull/14) | D7 — central `[pr_code_suggestions]` block |
| `cuioss/cuioss-organization` | [#237](https://github.com/cuioss/cuioss-organization/pull/237) | D6 — `pr-agent-improve` label gate |
| `cuioss/API-Sheriff` | [#202](https://github.com/cuioss/API-Sheriff/pull/202) | D8 — Java pack + missing `AGENTS.md` |
| `cuioss/TokenSheriff` | [#643](https://github.com/cuioss/TokenSheriff/pull/643) | D8 — Java pack + `AGENTS.md` case rename |

Merge order is stated in each body: **#14 → #237 → #202/#643**. Merging the label gate before the
central config would gate a tool whose config block does not yet exist. The two rollout PRs are
independent of both and may land alone.

## One defect fixed during recovery

D7 set `enable_intro_text = false` under `[pr_code_suggestions]`. That key **does not exist in
that section** at pr-agent v0.39.0 — the section declares 23 keys and it is not among them. It is
real but scoped to `[pr_reviewer]`, which is why a file-scoped grep for it returns a hit that says
nothing about the section being configured. The setting was inert; it is removed in `650a7d4`,
and the resulting gap is recorded rather than papered over, because no key in the section is a
rename of it and the nearest behavioural neighbours are not drop-in equivalents.

The generalisable rule, worth more than the fix: **section-scope every PR-Agent key
verification.** `enable_help_text` alone appears in nine sections of `configuration.toml` with
differing defaults. A grep that reports presence without naming the enclosing section will confirm
a key that is absent from the section actually being configured.

## Queue action

`PLAN-PR-022` may now be stamped shipped on the delivery axis — but the four foreign PRs are
**open, not merged**, and two of them are CI-gated in repositories this epic does not own.
Corroborate each landing against the foreign PR itself before recording it as shipped; absence
from a host-side record proves nothing about a foreign repo.
