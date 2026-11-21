# Markdown Trust Surface

The marketplace's second attack surface is not code — it is **prose the model executes**. Every skill, command, agent, and ingestion doc is markdown that a language model loads and treats as instructions. Two distinct risks live here: (1) a new surface that ingests attacker-influenceable external text and lets the model consume it without passing the deterministic containment boundary, and (2) prose — authored or interpolated — that can be read as an instruction-injection vector or that erodes the isolation between read-only and write-capable contexts. This standard frames both against the existing `plan-marshall:untrusted-ingestion` contract.

The conceptual foundations live in the centralized persona; this standard owns only the marketplace framing and cross-references upward.

| Foundation | Home |
|------------|------|
| Drawing the data-flow diagram and placing the ingestion trust boundary (STRIDE Tampering / Spoofing / Elevation decomposition) | [`threat-modeling-stride.md`](../../../../plan-marshall/skills/persona-security-expert/standards/threat-modeling-stride.md) |
| Trust-boundary architecture, fail-closed handling, why a reader's output is untrusted on emission | [`input-validation-trust-boundaries.md`](../../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| Least privilege, complete mediation, fail-securely behind the reader/writer split | [`secure-design-principles.md`](../../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |

## The existing containment boundary

**Maps to:** CWE-77 (Command/Instruction Injection) · OWASP A03 Injection · ASVS V5

Every untrusted-external-content ingestion surface in the marketplace already loads `plan-marshall:untrusted-ingestion` and conforms to its **reader / orchestrator / writer isolation** contract:

- The **reader** is a read-only `execution-context-reader-{level}` variant. It performs semantic extraction ONLY — parsing practices/findings from raw external text (web pages, GitHub issue/PR/comment bodies, Sonar issue messages) into a CANDIDATE struct. It has `WebSearch, WebFetch, Read, Grep` only — no write, edit, execute, or skill-loading tools.
- The candidate struct is **NOT trusted on emission**. The orchestrator/writer runs the deterministic `plan-marshall:untrusted-ingestion:validate_struct` script on it, which enforces the output schema (`additionalProperties:false` + `maxLength` + `maxItems` + `pattern`), length-caps/truncates, and performs the WebFetch domain-allowlist check.
- The **orchestrator/writer** is a write-capable `execution-context-{level}` variant that consumes ONLY the script-validated, clamped struct — never the raw bytes, never an unvalidated candidate.

Security does not rest on the reader behaving — it rests on the deterministic script being the only path from untrusted bytes to a write-capable context.

## Risk 1 — A new ingestion surface that bypasses the boundary

The dominant failure mode is **surface drift**: a new feature reads attacker-influenceable external text (a new provider, a new web source, a new issue/comment shape) and consumes it directly in a write-capable or skill-loading context, without dispatching through the read-only reader and the `validate_struct` gate. Such a surface re-opens the prompt-injection channel the contract exists to close.

Review any new content-ingestion surface against these questions:

- Does it read text the marketplace does not author — web pages, GitHub bodies, Sonar messages, or any other attacker-influenceable source?
- If so, is the raw text extracted by a **read-only reader** (no write/edit/execute/skill tools), or is it consumed directly by a write-capable context?
- Does the candidate struct pass `plan-marshall:untrusted-ingestion:validate_struct` (schema + length-cap + domain-allowlist) before any write-capable context sees it?
- Does the write-capable context consume ONLY the `status: success` validated, clamped struct — never the raw bytes?

A "no" to the reader-isolation or the validator question is a finding: the new surface must be wired through the untrusted-ingestion contract, not around it.

## Risk 2 — Trust-boundary erosion and injection-susceptible prose

**Maps to:** CWE-1427 (Improper Neutralization of Input Used for LLM Prompting) · OWASP A03 Injection · ASVS V5

Even without a new ingestion surface, prose can erode the boundary:

- **Granting the reader more than it needs.** Adding a write, edit, execute, or skill-loading capability to a reader surface collapses the isolation — the reader becomes a write-capable context consuming untrusted bytes. Reader tool surfaces stay `WebSearch, WebFetch, Read, Grep`.
- **Restating deterministic checks as reader prose.** The schema-enforcement, length-capping, and domain-allowlist logic are deterministic checks the validator script performs. Re-implementing them as reader instructions ("the reader should reject overly long fields…") moves a containment control out of the deterministic boundary and into prose the attacker's text shares context with — the control then depends on the model behaving.
- **Interpolating untrusted text into executable instructions.** Authoring a doc that splices external text into instructions the model will act on, or whose phrasing can be coerced into executing attacker-supplied directives, is an injection vector. Untrusted text is data to be extracted and validated, never instructions to be followed.

## Where this profile is consumed downstream

This skill adds the `plan-marshall-plugin-dev` **security profile and skill** only. An external complement — the in-flight `ws05-security-skill-resolver` plan — is what later adds the resolver verb that consumes each domain's `skills_by_profile.security` set and the `finalize-step-security-audit` Step 1 wiring that layers this profile into the security-audit pipeline. That resolver and finalize-step wiring are explicitly **out of scope here** and MUST NOT be implemented or modified from this skill; this note records the integration direction only.

## Review checklist

- Any new surface reading attacker-influenceable external text routes through a read-only reader and the `validate_struct` boundary before a write-capable context consumes it.
- No reader surface holds write/edit/execute/skill-loading tools.
- Deterministic containment checks (schema, length, domain-allowlist) stay in the validator script, not in reader prose.
- No doc interpolates untrusted external text into instructions the model will execute.
