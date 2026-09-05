# Exit-Code Convention for Every Script Call

## Purpose

This is the single statement of the exit-code contract that governs every
`python3 .plan/execute-script.py` call in the marketplace — of EVERY notation,
**not only `manage-*`**. Every document that invokes the executor
cross-references this standard; none of them restates it.

The standard lives in `tools-script-executor` because that skill owns the
executor the convention governs. It is a sibling of
[`cwd-policy.md`](cwd-policy.md), [`domain-aware-notation-spec.md`](domain-aware-notation-spec.md),
and [`wait-pattern.md`](wait-pattern.md), which document the other properties of
the same call boundary.

## Why the scope reaches past `manage-*`

Every earlier statement of this convention was scoped to `manage-*` script
calls. A document that invokes `ci`, `github_pr`, `sonar`, `git-workflow`,
`platform_runtime`, or any other non-`manage-*` script was therefore left with
no rule at all — and several of those scripts print `status: error` while
exiting 0 by design. A caller reading only the exit code accepts a failed call
as a usable value, then reads success-payload fields off an error envelope that
does not carry them.

That is the swallowed-rejection gap. The convention below closes it by binding
every notation, not a prefix-selected subset.

## The contract

Unless a step explicitly states otherwise, every executor call carries this
contract:

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause. There is no envelope to preserve on that sub-path — synthesize the error TOON instead, naming the call and carrying the raw stdout verbatim.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Read `status` before anything else. The first clause is the only one that
yields a usable value, and it is reachable only when both halves of its
condition hold.

### Preserving the envelope on the exit-0 error path

The middle clause says to copy the whole envelope rather than a chosen subset
of its fields, and the reason is that there is no stable subset to choose.
Beyond `status` and `error`, the diagnostic fields vary by verb: `ci` verbs
carry `operation`, `error_cause`, and `context`; the plan-resolution envelopes
carry `message` and `plan_id` instead. Neither list is exhaustive. `error` is
sometimes a hard-coded generic string whose real cause sits in one of the other
fields, so dropping them can discard the cause entirely. The envelope's
diagnostic fields are not success payload — the prohibition on reading
success-payload fields off a non-`success` return does not reach them.

The one sub-path with no envelope to preserve is the unparseable stdout, which
is why the clause sends you to synthesize the error TOON there instead. Naming
the call means all three of notation, subcommand, and arguments: without the
arguments the synthesized TOON reports that something failed without recording
what was asked of it, and the raw stdout it carries is the only account of the
cause that exists.

## A zero exit never establishes success for a `ci` call

The middle clause is what the `ci` family makes load-bearing: a `ci` verb
reports failure as `status: error` at exit 0 **by design**, so a caller must
branch on the payload `status` and never on the exit code.

That rule is stated authoritatively in
[`plan-marshall:tools-integration-ci`](../../tools-integration-ci/SKILL.md) §
"A `ci` verb reports failure as `status: error` at exit 0 — by design", which
owns the three-tier model behind it and cites the source locations. It is not
restated here — this standard names the consequence for the contract above and
points at the owning skill for the mechanism.

## Operation-failure carve-out

The middle clause is also how a `manage-*` *operation* failure surfaces. The
`manage-*` scripts follow the canonical output contract
([`pm-plugin-development:plugin-script-architecture`](../../../../pm-plugin-development/skills/plugin-script-architecture/standards/output-contract.md)),
under which `file_not_found`, `field_not_found`, `plan_not_found`, a validation
rejection, or an already-exists verdict exits `0` and carries the verdict in the
stdout TOON `status: error` payload.

A step that issues a call whose *effect* matters — a `qgate add` that must land
a finding, a `read`/`get` that must find a field — MUST detect the rejection by
inspecting the TOON `status`, NOT by testing `exit_code != 0`. Reserving
`exit_code != 0` for crash and argparse detection while reading the TOON for
operation-failure detection are two distinct branches; conflating them (treating
a zero exit as "the write landed") regresses the contract and is forbidden.

## Step-level exceptions

A step MAY carry a **stricter** disposition than "STOP and return an error" —
routing a failed call into an explicit UNKNOWN verdict that blocks a merge, for
example. That is this convention's "unless a step explicitly states otherwise"
at work: a tighter handling of the same failure, never a licence to swallow it.

A step MAY also document a call whose non-zero exit is itself the signal —
`manage-files exists` returning `exists: false`, or `manage-status
get-worktree-path` returning an empty `worktree_path`. Such exceptions are
documented inline in the step that issues them, never inferred.

## How a document references this standard

A document that invokes the executor carries a single cross-reference under an
`## Exit-code convention for every script call` heading, and restates no clause:

```markdown
## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this
document — of EVERY notation, not only `manage-*` — is stated once in
[`tools-script-executor/standards/exit-code-convention.md`](<relative path>); it
is not restated here.
```

The heading is kept so the section remains a navigable anchor and so the
document still declares that the contract binds it. The body is the reference
and nothing more: one body of this text exists in the tree, and every consuming
document points at it.

**Why a reference rather than an inline copy.** A copy at the point of use is
stronger for a reader who never follows the link, and that is a real cost of
this arrangement. It is accepted deliberately: this convention was previously
duplicated across the tree, and the duplicated paragraph produced two multi-site
defects at two consecutive HEADs — a fix landing in some copies and not others.
A pointer that is always correct beats a copy that drifts.
