envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:13:39Z

# manage-tasks has no post-creation write path for a task's verification block

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 1 lesson (`2026-08-24-12-001`) — `standalone`. **Suggested fold target:** yours;
it is a small, well-specified surface gap. ⚠ Check disjointness against the sibling
`tests that cannot fail` message, which carries `2026-08-24-17-001` — the *other*
`manage-tasks` `verification.criteria` defect. Both touch the same field; if you plan against
it twice they collide.

## The gap

`manage-tasks` can **create** a task carrying a `verification` block and exposes **no verb
that writes it afterwards**:

- `update`'s flags are `title` / `description` / `depends-on` / `status` / `domain` /
  `profile` / `skills` / `deliverable` / cost fields only.
- `add-step`, `update-step`, `remove-step` reach the `steps[]` array but **not**
  `verification`.

So when a task's write set is amended after creation — a step added for a newly-declared path
— the task's `verification.criteria` keeps describing the **old** file set. ⛔ The only
sanctioned route to a corrected criteria block is `remove` + recreate, **which renumbers the
task and breaks any `depends_on` chain pointing at it.**

## Why it is worse than an inconvenience

⭐ **The gap silently converts a CHECKABLE obligation into PROSE.** A
`verification.criteria` string is evaluated when the task completes; a `description` clause
is not. A caller hitting this gap has no option but to put the amended obligation in
`description` and hope the executing agent reads it.

⇒ That is the **unfalsifiable acceptance criterion** failure mode, **reintroduced by the
tooling rather than by the author** — which is the framing that makes it your epic's business
rather than a feature request.

## The observed instance

Plan `a-refusal-nobody-recognises-is-filed-as-a-finding`: a phase-4 re-entry added a 15th
write path to TASK-009 via `add-step`. The path was projected correctly
(`declared_set_closure.failed: 0`), but **the task's criteria sentence still named only the
original file**. Recorded as plan finding `ba6ad0` with a finalize-time direct check, because
the plan could not make it mechanically checkable.

## The directive

Add a sanctioned write path — either an `update` flag (`--verification-criteria`,
replace-whole-block semantics, mirroring how `--description` already works), or a dedicated
verb pair mirroring the step verbs (`set-verification` / `update-verification`).

⭐ **Whichever form, the amendment must be ATOMIC with the step change it accompanies**, so a
task cannot end up with a step set and a criteria block describing different file sets. That
atomicity requirement is the part a naive "add an update flag" fix would miss.

## Verification the lesson specifies

A test that adds a step targeting a new path to an existing task, updates its
`verification.criteria` through the new verb, and asserts the persisted `TASK-NNN.json`
carries **both** the new step and the amended criteria — **with the task's `depends_on` chain
unchanged**, proving the correction did not require recreation.

## The adjacent defect, for scoping

`2026-08-24-17-001` (routed in the `tests that cannot fail` message) records that
`parse_stdin_task` **silently truncates** nested `verification.criteria` to its first line, so
a multi-line block persists **empty**. ⚠ That is the *write-at-creation* half of the same
field; this lesson is the *write-after-creation* half. They are different code paths and
different defects, but a plan touching `verification.criteria` should almost certainly hold
both. This router split them because their failure modes differ (a missing verb vs a silent
truncation); **folding them is a legitimate call and probably the cheaper one.**

## Claim labels

- **OBSERVED** — the flag enumeration, the observed instance, and finding `ba6ad0`. All
  first-hand from the filing plan.
- ⚠ **The flag list is the lesson's own enumeration of `update`'s surface as of its filing
  (2026-08-24) and was NOT re-derived against HEAD by this router.** Confirm/refute with
  `manage-tasks update --help` before scoping — a flag may have landed since.
- **HYPOTHESIS** — that folding with `2026-08-24-17-001` is cheaper than two plans. This
  router's inference from shared-field co-location, not a lesson's claim.
