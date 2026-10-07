# PLAN-PR-065: The settings repository accumulates publish PRs and never lands one

epic: review-apparatus
workstream: WS-02

> Staged plan spec — created 2026-09-13 on operator direction, after a first-party read of
> `cuioss/pr-agent-settings` and of this repository's publisher workflow. Three operator rulings were
> taken at staging time and are recorded in § Operator rulings; they are settled, not open.

## Objective

Make `cuioss/pr-agent-settings` a repository that **lands** what is published to it: clear the publish
backlog, stop it regenerating, protect `main` with a check that means something, and reduce its two
working documents to what a reader needs — with the history kept, relocated rather than deleted.

## Why this is one plan and not four

The four asks share one cause. The publisher opens a pull request per source commit and **nothing
merges it**, so: the backlog grows without bound; `packs/` has never existed on `main`, which
structurally blocks `PLAN-PR-039`; and `README.adoc` keeps absorbing the narrative that a landed,
modular doc set would have carried. Fixing the backlog without the publisher is a cleanup that is
stale within days — that is the operator's third ruling below.

## What was OBSERVED first-party at staging (2026-09-13)

- **The repository has exactly ONE commit**: `729165e` (`#15`, the model-ladder promotion from the
  shipped `PLAN-PR-041`). Nothing else has ever landed.
- **Its whole tree is two files**: `.pr_agent.toml` (29,484 B) and `README.adoc` (66,174 B). There is
  **no `.github/` directory, no workflow, and no CI of any kind**, and no `packs/`.
- **Every open pull request is a pack publish**: title `chore(packs): publish reviewer packs from
  cuioss/plan-marshall@{sha}`, head `pr-agent-packs/{sha}`, base `main`, label `skip-bot-review`.
- **The publisher is `.github/workflows/pr-agent-packs-publish.yml` in THIS repository.** It fires on
  push to `main` under `marketplace/bundles/**` / `marketplace/targets/**`, REPLACES `settings/packs`
  wholesale, opens a PR on a per-sha branch — and has **no merge step at all**.
- ⇒ **The open PRs mutually supersede one another**: each carries a complete replacement snapshot, so
  the newest alone reaches the state a fresh publish would produce.
- `README.adoc` is ~1,225 lines over 51 headings; its `== Learnings` section alone spans lines
  108–863 (~755 lines, 62% of the document), and `== Charter: why security-weighted` a further ~228.

⛔ **The open-PR COUNT is not among these observations.** `ci pr list --state open` returned exactly
**30** rows — which is `gh`'s default page size, so it is a PAGE, not a population. The operator
reports 46. D0 derives the real number; ⛔ **no deliverable may cite 30**, and a count that equals a
tool's default limit is evidence of truncation, not of a population.

## Operator rulings (settled at staging — do not re-litigate)

1. **Land the newest, close the rest as superseded.** Not a literal sequential merge-all: that is ~46
   merges of stale snapshots, each conflicting with the next on the same files, arriving at the
   identical tree.
2. **Protect `main` AND give it something to require** — a minimal validation check, so protection
   verifies what lands rather than only blocking direct pushes.
3. **Fix the publisher too.** The plan spans both repositories.

## Deliverables

**D0 — GATE, mutates nothing.** Derive, first-party: (a) the COMPLETE open-PR population with explicit
paging — publish the count with the page size it was read at; (b) a per-PR classification, so a PR that
is **not** a pack publish is named rather than swept into the backlog; (c) the newest pack PR by source
commit; (d) `main`'s current protection and auto-merge settings; (e) whether the `cui-release-bot` App
installation carries the scope D3 needs. ⛔ **HALT and report** if any open PR is not a pack publish, or
if the App lacks `administration: write` — D3 then becomes an operator action rather than a silent
failure.

**D1 — Clear the backlog.** Merge the newest pack PR so `packs/` exists on `main` for the first time.
Close every other open pack PR with a comment naming the PR that superseded it, and delete its branch.
*Done when:* open pack PRs are zero, `packs/` on `main` equals the set the generator emits at that
source commit, and the report enumerates every PR closed with its superseding PR — ⛔ counted from D0's
derived population, never from a page.

**D2 — Give the repository a check worth requiring.** A minimal validation workflow: `.pr_agent.toml`
parses as TOML, `packs/` is non-empty, and every pack file matches the derived-domain naming the
publisher emits. *Done when:* the workflow runs on `pull_request` against `main`, fails on a corrupted
toml and on an empty `packs/`, and both failure modes are exercised.

**D3 — Protect `main`.** Require the D2 check, require pull requests (no direct pushes), require linear
history, and allow the release bot to auto-merge. *Done when:* a direct push to `main` is refused, a PR
failing D2 cannot merge, and the publisher's own PR still lands unattended. ⛔ If D0 found the App
without `administration: write`, this deliverable produces the exact settings for the operator to apply
and says so — it does NOT report itself done.

**D4 — Enable auto-merge, at the repository and in the publisher.** Turn on repository auto-merge, and
have the publisher request it on the PR it opens (`gh pr merge --auto --squash`), so a published set
lands the moment D2 passes. *Done when:* a publish PR reaches `main` with no human action, and the
`skip-bot-review` label still applies at creation time — ⛔ that ordering is load-bearing, per the
workflow's own comment.

**D5 — Stop the per-sha branch accumulating.** With auto-merge armed, a stuck check must not re-open
the same unbounded backlog. Either land the publish on ONE rolling branch, or keep per-sha branches and
delete the branch on merge, plus close any superseded open publish PR when a newer one is opened.
*Done when:* two consecutive publishes leave at most one open publish PR, exercised by a test or a
recorded two-run observation. ⛔ The existing "already match the derived set — nothing to publish"
no-op path must survive unchanged.

**D6 — Modularise the documentation.** Introduce a `doc/` module. `README.adoc` keeps only what a
reader needs to USE the repository: purpose, what it is, which PR-Agent, configuration precedence,
adding a repository, see-also. `== Learnings` and `== Charter: why security-weighted` move to
`doc/`, **verbatim**, with a pointer left at each origin naming the destination. *Done when:*
`README.adoc` is materially smaller, every relocated section is reachable from it by an explicit link,
and ⛔ **nothing is deleted** — a section is moved or it stays.

**D7 — A decision log, not an archive.** `doc/decisions.adoc` carries only decisions that still bind,
each as: the decision, its consequence, and what it forecloses. Historic narrative that records no
binding decision moves to the relocated learnings of D6 rather than into the log. *Done when:* every
entry states a consequence a reader can act on, and the log is linked from `README.adoc`.

**D8 — Reduce `.pr_agent.toml` to configuration.** Rationale and history in comments move to `doc/`;
the live configuration stays. ⛔ **Do not touch the model ladder** — `gemini-3.7-flash` leader,
`3.6-flash` first fallback — settled by the shipped `PLAN-PR-041` (`#15`). *Done when:* the file
parses identically to its pre-change effective configuration, proven by a value-level comparison and
not by reading the diff.

**D9 — Prove the drift guard and discharge `PLAN-PR-039`'s precondition.** `PLAN-PR-038` shipped a
drift guard asserting the published set equals the derived set; with nothing ever published it has
never had a population to check. *Done when:* the guard is exercised against the now-landed `packs/`
and reports a real comparison, and the run records that `PLAN-PR-039`'s *"resolve declared pack keys
against the artifacts published to `cuioss/pr-agent-settings`"* precondition is now satisfied.

Ten deliverables — under the 12 ceiling, with headroom for what D0 returns.

## Expected Surface

- OBSERVED: `.github/workflows/pr-agent-packs-publish.yml` — D4/D5: auto-merge and the branch strategy
- HYPOTHESIS: `marketplace/targets/pr_agent/target.py` — D9: the drift guard's producer side (verify-at-outline)
- HYPOTHESIS: `marketplace/targets/README.md` — D9: the publish contract's documentation site
- FOREIGN (`cuioss/pr-agent-settings`, verify-at-outline — no path in this checkout resolves it):
  `README.adoc` (D6), `.pr_agent.toml` (D8), `doc/` (D6/D7, created), `packs/` (D1, created),
  `.github/workflows/` (D2, created), and `main`'s branch-protection settings (D3, not a file).

⚠ **The foreign half is deliberately declared as `FOREIGN` rather than as a resolvable path.** It
cannot be compared by the disjointness gate at all, and stating that is what keeps the gate's silence
about it from reading as a checked negative (ADR-019). The local entries are what make this spec
`declarative`.

## Claim Labels

- OBSERVED (first-party, 2026-09-13): the repository holds one commit and two files, with no `.github/`
  and no `packs/`. Confirm/refute at `cuioss/pr-agent-settings` § `git log` and its root tree.
- OBSERVED (first-party, 2026-09-13): every open PR read is a pack publish on a `pr-agent-packs/{sha}`
  branch, and each REPLACES `packs/` wholesale. Confirm/refute at
  `.github/workflows/pr-agent-packs-publish.yml` § "Replace the published packs directory".
- OBSERVED (first-party, 2026-09-13): the publisher has no merge step. Confirm/refute at the same file
  § "Open the publish pull request" — it ends at `gh pr create`.
- HYPOTHESIS: the true open-PR count is 46 — operator-reported, and the read that would have settled it
  returned a 30-row page. Confirm/refute at D0 (verify-at-outline). ⛔ A count equal to a default page
  size is truncation evidence, not a population.
- HYPOTHESIS: the `cui-release-bot` App installation can set branch protection — it is minted with
  `contents: write` and `pull-requests: write` for this repository, and protection needs
  `administration: write`. Confirm/refute at D0 against the installation's permissions
  (verify-at-outline). ⛔ An asserted absence here would be as wrong as an asserted presence: derive it.
- HYPOTHESIS: `packs/` landing discharges `PLAN-PR-039`'s only foreign precondition — confirm/refute at
  `PLAN-PR-039` § Objective and § Dependencies (verify-at-outline).

## Dependencies and Sequencing

- ⛔ **`PLAN-PR-039` is BLOCKED until D1 lands** — it resolves declared pack keys against artifacts that
  have never existed on `main`. This plan is its precondition; do not emit `PLAN-PR-039` first.
- ⭐ **Does not overlap the `automatic-review` family.** Its local surface is the publisher workflow and
  the pr-agent target, so it is pairable with the WS-01/WS-03 plans — the only staged spec of which
  that is currently true.
- ⛔ Internal order: **D0 → D1 (land) → D2 → D3/D4/D5 (make it stay landed) → D6/D7/D8 (documents) →
  D9.** Protection before auto-merge, or auto-merge lands against no check.
- ⚠ Do NOT re-litigate the settled `PLAN-PR-038`/`PLAN-PR-039` architecture (epic.md § Standing
  Constraints): packs are generated, published as artifacts, selected via `.github/project.yml`, read
  from the default branch, and `security` is not a selectable pack.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-065-the-settings-repo-accumulates-and-never-lands.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source and to the FOREIGN repository
`cuioss/pr-agent-settings` named in the Expected Surface. It creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
