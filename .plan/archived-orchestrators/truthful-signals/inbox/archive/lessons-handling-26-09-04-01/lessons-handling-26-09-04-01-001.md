envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-04T07:45:51Z

# Finding: the generated `module-tests` canonical cannot work for a module that consumes a sibling's test-jar

> **Relayed from Token-Sheriff.** Source epic `lessons-handling-26-09-04-01`. **Two independently-filed lessons describe the same defect** and are consolidated into this one message: `2026-08-31-12-001` (filed first, from the symptom) and `2026-09-01-19-003` (filed later, from the mechanism). Both bodies are reproduced verbatim below, in filing order, under their own headings.

**Proposed component**: `plan-marshall:build-maven` (`_maven_cmd_discover.py`) and the canonical-command surface of `plan-marshall:extension-api`
**Category**: `bug` — a generated canonical command that cannot succeed as written

⚠ **Why it is relayed as one finding**: the two lessons were filed a day apart by different plans and neither references the other. That they are the same defect is a consolidation judgement made by the relaying orchestrator; the receiving side should treat the pair as one fix with two independent reproductions, which is stronger evidence than either alone.

---

## Reproduction 1 — as filed 2026-08-31 (`2026-08-31-12-001`)

# module-tests canonical for `token-sheriff-client` is structurally broken

## Symptom

`architecture resolve --command module-tests --module token-sheriff-client` returns:

```text
python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "test -pl token-sheriff-client -am"
```

Running it fails during test **discovery**, not on any assertion:

```text
TestEngine with ID 'junit-jupiter' encountered a critical issue during test discovery:
(1) [ERROR] ClassSelector [className = 'de.cuioss.sheriff.token.client.token.IdTokenValidationBridgeTest'] resolution failed
Cause: java.lang.NoClassDefFoundError: de/cuioss/sheriff/token/validation/test/JwtTokenTamperingUtil$TamperingStrategy
```

The `compile` canonical (`compile -pl token-sheriff-client -am`) is unaffected and passes — only the
test-classpath phases break.

The same `-am` shape fails one phase earlier too, at `test-compile`, with a different face:

```text
Package de.cuioss.sheriff.token.validation.test.dispatcher ist nicht vorhanden
```

## Root cause

`token-sheriff-client`'s test sources depend on the **test-jar** of `token-sheriff-validation`
(`de.cuioss.sheriff.token.validation.test.*` — `TestTokenHolder`, `TestTokenGenerators`,
`TokenDispatcher`, `JwtTokenTamperingUtil`, …).

A Maven test-jar is attached by the `jar:test-jar` goal bound to the **`package`** phase. `-am` builds
the upstream module only as far as the phase requested for the target module — so a `test` or
`test-compile` request never reaches `package` on `token-sheriff-validation`, and the test-jar is never
produced in the reactor. The client module then resolves the test-jar to whatever is (or is not) in the
local repository.

This is a property of the module graph, not of any branch's changes.

## Corrective

Install the validation module's test-jar first, then run the module scoped **without** `-am`:

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "install -pl token-sheriff-validation -am -DskipTests"
```

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "test -pl token-sheriff-client"
```

The second command runs the module's full suite (660 tests) green.

The same pairing applies to the integration-tests module — install the chain first, then scope:

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "install -pl token-sheriff-quarkus-parent/token-sheriff-quarkus-integration-tests -am -DskipTests"
```

## Provenance discipline

Do **not** read this failure as a regression from the branch under execution. The discovery failure
names test classes the branch never touched (`ClientSecretAuthTest`, `DiscoveryAdversarialTest`,
`DiscoveryResolverTest`, `AuthorizationCodeFlowTest`, `ClientCredentialsFlowTest`,
`IdTokenValidationBridgeTest`), and it reproduces on an unmodified tree. Establish that before
attempting any fix: a bigger version of a wrong fix is still wrong.

## Durable fix (not yet applied)

The `module-tests` canonical for this project should either drop `-am` and rely on installed upstream
artifacts, or request `package`/`install` on the upstream chain rather than `test`. Until that is
changed in the architecture command map, every phase-5 per-deliverable `module-tests` run against
`token-sheriff-client` will fail on a green tree.

---

## Reproduction 2 — as filed 2026-09-01 (`2026-09-01-19-003`)

# The generated module-tests canonical (test -pl <mod> -am) cannot attach a sibling's test-jar, producing a false red on every module that consumes one

**Category**: bug
**Suggested component**: `plan-marshall:build-maven` (`_maven_cmd_discover.py`); applied surface `token-sheriff-client`
**Source plan**: `refresh-identity-and-scope-defences` (PR #682)

Upstream half already filed as `truthful-signals/refresh-identity-and-scope-defences-001.md`
(together with the build-reporter last-summary defect). This is the consuming-project half.

## The mechanism

`build-maven` generates the `module-tests` canonical live as `test -pl {module} -am`. A Maven
test-jar is attached at the **`package`** phase. `test` never reaches `package`. So `-am`
builds the sibling module's classes but never attaches its test-jar, and any module that
consumes one fails at test discovery — not at compile, and not for any reason that names the
real cause.

`token-sheriff-client` consumes `token-sheriff-validation`'s test-jar, so **every**
`module-tests` invocation against it is a false red.

## What it cost here

- One triage cycle burned confirming the canonical was broken rather than the code:
  660 tests green under a corrected invocation, red under the generated one
  (`logs/decision.log` `2026-08-31T12:10:25Z`, finding `a4affb`, resolved
  `taken_into_account`).
- The canonical is generated live and **not cached in `project-architecture`**, so there is no
  local override file to patch — the defect is unavoidable from the consuming project's side
  without changing which canonical the step resolves.
- Deliverables 2–7 all targeted `token-sheriff-client` and would each have re-fired the
  identical false red.

## The working remedy (applied in-plan)

Point `per_deliverable_build` at `default:verify:verify` instead of `default:verify:module-tests`.

`verify -pl token-sheriff-client -am` reaches `package`, so the sibling test-jar **is**
attached. Empirically green in 154s: 660 surefire + 7 failsafe tests
(`logs/decision.log` `2026-08-31T12:40:59Z`). Per the `manage-config` data model the composer
maps the `verify` canonical segment to the `module-tests` decision-matrix role, so the step
semantics are unchanged — this is a substitution, not a downgrade.

Note the same trap applies to any per-task `verification.commands` carrying `test-compile` /
`test` with `-am` (tasks 6/7/10 here). No `manage-tasks` verb re-stamps
`verification.commands`, so the substitution had to be carried in the dispatch prompt rather
than by editing the TASK JSON.

## Suggested upstream remedy

`_maven_cmd_discover.py` should emit `verify` rather than `test` for the `module-tests`
canonical whenever any module in the reactor slice publishes or consumes a `test-jar`
artifact — the condition is statically detectable from the POMs.
## Recurrence — a SECOND emitter of the same broken shape (2026-09-03)

Observed again in plan `outbound-hostname-verification-quarkus` (PR #694, merged `cd36dd24`),
TASK-2 and TASK-4, and filed as inbox message
`outbound-hostname-verification-quarkus-001.md`.

⚠ **The emitter was different.** This occurrence came from
`plan-marshall:manage-architecture` (`architecture derive-verification`), which stamped
`test -pl <module> -am` onto the task verification commands — not from `build-maven`'s
`_maven_cmd_discover.py`. The suggested upstream remedy above therefore does **not** cover it:
fixing `_maven_cmd_discover.py` alone would have left this path emitting the identical broken
shape.

The affected modules consume `token-sheriff-validation` with the `generators` **test-jar
classifier**, so the mechanism is unchanged: `test` never reaches `package`, `-am` builds the
upstream module without attaching the classified test-jar, and `test-compile` dies on
unresolvable generator classes.

**Remedy applied on this occurrence** — the documented two-step, rather than the `verify`
canonical substitution recorded above:

1. `./mvnw install -DskipTests` (attaches the classified test-jar into the local repo)
2. `./mvnw test -pl <module>` (plain, no `-am`)

Upstream half relayed to plan-marshall as `truthful-signals/deployment-and-refresh-gaps-016.md`,
which names `manage-architecture` as the component so the second emitter is fixed too.
