/**
 * plan-marshall guard plugin — tool.execute.before enforcement of R1-R6.
 *
 * V2 plugin (`Plugin.define` with `ctx.tool.hook("execute.before")`). The
 * opencode host loads every module under `{plugin,plugins}/*.{ts,js}` in the
 * project config directory. This plugin registers a
 * `ctx.tool.hook("execute.before")` hook that inspects each tool invocation against the six
 * plan-marshall hard-rule bypass classes and THROWS to block the execution,
 * appending one audit line to `.plan/temp/guard.log` per blocked invocation.
 *
 * The plugin's decision table is mirrored as a behavioral contract in
 * `test/plan-marshall/platform-runtime/test_opencode_enforcement.py`, which
 * EXECUTES this module under node rather than grepping its source. Keep the
 * two in lock-step when the table changes.
 *
 * DECISION TABLE (authoritative — mirrored in the D4 runtime matrix):
 *
 *   Guarded tools: bash (R1, R2, R4, R5, R6), edit/write/patch/apply_patch (R3).
 *   Every other tool passes through untouched.
 *
 *   R1 — shell-chaining constructors (bash): the command, with single-quoted
 *   regions stripped and double-quoted regions stripped except for command
 *   substitution, contains `&&`, `||`, `;`, `|`, `$(`,
 *   a backtick, any unquoted `&` or `(`, or a newline  => block. `$(` and backticks
 *   inside double quotes still block because Bash executes them there.
 *
 *   R2 — shell file operations, mutation class (bash): the command's first token,
 *   after stripping the shell wrappers (with options), leading `NAME=value`
 *   assignments, quotes, and path qualification, is one of
 *   {rm mv cp touch mkdir rmdir truncate tee chmod chown ln dd}  => block.
 *   Read-side probes (ls cat head tail grep find) are NOT in this guard class:
 *   the two-tier permission map governs them (global deny, orchestrator
 *   small-ops carve-out under ask). Shell spawns `sh`/`bash`/`source` also block.
 *
 *   R3 — direct edits to the generated executor path (edit/write/patch/apply_patch):
 *   the target resolves under `.plan/execute-script.py` — via filePath, or via
 *   every `*** Add/Update/Delete File:` / `*** Move to:` marker (plus legacy
 *   bare add/update/move/delete targets) in apply_patch patchText  => block.
 *
 *   R4 — hard-coded build commands bypassing `python3 .plan/execute-script.py`
 *   (bash): route builds through the executor only. Block when:
 *     - first token is `./pw` unless its verb is explicitly allowed
 *       (only `./pw generate*` and `./pw --*` pass; a missing verb blocks);
 *     - first token is a bare build tool {mvn mvnw gradle gradlew make cmake ant
 *       uv}; or a JS runner {npm npx bun pnpm yarn} followed by
 *       {test run build};
 *     - first token is an interpreter and the basename of the second
 *       token is `build.py` (`python3 ./build.py` included);
 *     - `python(3) -m {pytest mypy ruff}`; a bare {pytest mypy ruff}.
 *   R4 is UNCONDITIONAL. The executor permit stays exempt under R4 and R5.
 *
 *   R5 — direct interpreter calls bypassing the executor (bash): block when the
 *   first token is an interpreter (python/python3 or a versioned spelling such
 *   as python3.12) and the invocation is -c, a script path (any second token not
 *   starting with -), or -m with any module — the allow set is executor-only, so
 *   every -m form refuses. R5 applies in EVERY session in this repository, root
 *   sessions included, matching the Claude hook — there is no plan-context gate.
 *   Two exemptions apply: the executor permit, and the SHARED allow-list of
 *   documented non-executor invocations read from `r5-allowlist.json`. An
 *   allow-list entry is a REPOSITORY-RELATIVE path matched EXACTLY against the
 *   invocation's path resolved against the repository root — never a basename
 *   and never a suffix — so a copy of an allow-listed script outside the
 *   repository never matches.
 *
 *   R6 — a raw `git commit` while the enclosing plan is in phase `6-finalize`
 *   => block. Every plan commit must pass through the gate-bearing
 *   `git-workflow commit` verb, which sanctions an open loop-back fix task, a
 *   review-rubric section-6 record, or a phase-6 settle-band step. Outside
 *   `6-finalize`, or with no plan state present, a raw commit is untouched.
 *
 * TOKENISATION PARITY: the R5 branch tokenises with a quoting-aware splitter
 * (`shellSplit`) matching the Python hook's `shlex.split`, strips the SAME
 * wrapper set, and lowercases the program token for the interpreter check, so
 * the two decision tables agree on the interpreter surface.
 */
import { appendFileSync, mkdirSync, readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { Plugin } from "@opencode/plugin"

// ---- R1: shell-chaining constructors (declared set, mirrored by D4) ----
function hasChainingConstructor(command) {
  let inSingle = false
  let inDouble = false
  let escaped = false
  let unquoted = ""
  let doubleQuotedSubstitution = false
  for (let i = 0; i < command.length; i++) {
    const ch = command[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (ch === "\\" && !inSingle) {
      escaped = true
      continue
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      continue
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble
      continue
    }
    if (!inSingle && !inDouble) {
      unquoted += ch
      continue
    }
    if (inDouble && !inSingle) {
      if (ch === "`") doubleQuotedSubstitution = true
      if (ch === "$" && command[i + 1] === "(") doubleQuotedSubstitution = true
    }
  }
  if (doubleQuotedSubstitution) return true
  return /&&|\|\||[;|]|\$\(|`|[&()]|\n/.test(unquoted)
}

// ---- R2: shell file operations, mutation class (declared set, mirrored) ----
const MUTATION_FILE_OPS = new Set([
  "rm", "mv", "cp", "touch", "mkdir", "rmdir", "truncate", "tee",
  "chmod", "chown", "ln", "dd", "sh", "bash", "source",
])

// ---- R4: hard-coded build bypasses (declared sets, mirrored) ----
// `./pw` is allowlisted by decision-table prefix, not by verb set: only
// `./pw generate*` and `./pw --*` pass. Every other `./pw` invocation
// blocks, so a new build.py-routed alias cannot bypass R4 by omission.
const BARE_BUILD_TOOLS = new Set(["mvn", "mvnw", "gradle", "gradlew", "make", "cmake", "ant", "uv"])
const JS_RUNNERS = new Set(["npm", "npx", "bun", "pnpm", "yarn"])
const JS_RUNNER_BUILD_VERBS = new Set(["test", "run", "build"])
const PYTHON_DIRECT_RUNNERS = new Set(["pytest", "mypy", "ruff"])

// ---- R5: direct interpreter calls bypassing the executor (declared sets, mirrored) ----
// The allow set is executor-only: every -m form refuses, so no allowed-module
// set exists to declare. The two sets below are the whole R5 population the
// contract test parses: the interpreter names and the always-refuse flags.
// A versioned spelling (python3.12) is recognised by `isPythonInterpreter`.
const PYTHON_INTERPRETERS = new Set(["python", "python3"])
const R5_ALWAYS_REFUSE_FLAGS = new Set(["-c", "-m"])

// Shell wrappers a prefix of which is transparent to the shell: `timeout 5 rm
// file` still runs `rm`, `env python3 -c x` still runs the interpreter. Strip
// them (with their options, option values and inline `NAME=value` assignments)
// before the first-token checks so a blocked invocation cannot be reached by
// prefixing a wrapper. Options a wrapper does not itself consume are skipped
// structurally; `timeout` additionally consumes its mandatory DURATION value.
const SHELL_WRAPPERS = new Set(["command", "env", "sudo", "timeout", "nice", "nohup", "time", "xargs"])

// Per-wrapper options that consume a FOLLOWING value token. Kept PER WRAPPER on
// purpose: `sudo -n` is a flag (non-interactive), so a single shared value set
// would swallow the interpreter behind it, while `nice -n 5` and `xargs -n 5`
// DO take a value.
const WRAPPER_VALUE_OPTS = {
  command: new Set([]),
  env: new Set(["-u", "--unset", "-C", "--chdir"]),
  sudo: new Set(["-u", "--user", "-g", "--group", "-U", "--other-user", "-C", "--chdir", "--directory"]),
  timeout: new Set(["-s", "--signal", "-k", "--kill-after"]),
  nice: new Set(["-n", "--adjustment"]),
  nohup: new Set([]),
  time: new Set([]),
  xargs: new Set([
    "-I", "-n", "-P", "-s", "-d", "-a", "-E", "-L", "-o", "-R", "-S",
    "--max-args", "--max-lines", "--max-chars", "--delimiter", "--arg-file",
    "--replace", "--max-procs", "--eof", "--arg-separator",
  ]),
}

// The base allow-list used when no shared data file can be read. Deliberately
// narrow: the sync engine is the one non-executor invocation that must survive
// even a missing data file, because it is the harness's own deploy step. An
// entry is a REPOSITORY-RELATIVE path (see `repoRelativePath`).
const R5_ALLOWLIST_BASE = ["marketplace/targets/sync.py"]

const ASSIGNMENT_RE = /^[A-Za-z_][A-Za-z0-9_]*=/
const VERSIONED_PYTHON_RE = /^python(\d+(\.\d+)*)?$/

// Phase the raw-commit rule guards, mirroring git-workflow.py's
// `_SOURCE_COMMIT_GATE_PHASE`. Outside it a raw `git commit` is untouched.
const SOURCE_COMMIT_GATE_PHASE = "6-finalize"

// `git` global options that consume a SEPARATE following token, so the
// subcommand walk steps over the option AND its value.
const GIT_VALUE_OPTIONS = new Set([
  "-C",
  "-c",
  "--git-dir",
  "--work-tree",
  "--namespace",
  "--super-prefix",
  "--config-env",
  "--exec-path",
  "--attr-source",
])

// Quoting-aware tokenizer mirroring Python's `shlex.split` (POSIX mode) on the
// shapes R5 sees. Returns null on malformed quoting (an unterminated span or a
// trailing escape), so the caller can fall back to a whitespace split exactly
// as the hook's shlex fallback does.
function shellSplit(command) {
  const tokens = []
  let current = ""
  let started = false
  let i = 0
  const n = command.length
  while (i < n) {
    const ch = command[i]
    if (ch === "\\") {
      if (i + 1 >= n) return null
      current += command[i + 1]
      started = true
      i += 2
      continue
    }
    if (ch === "'") {
      started = true
      i++
      let closed = false
      while (i < n) {
        if (command[i] === "'") {
          closed = true
          i++
          break
        }
        current += command[i]
        i++
      }
      if (!closed) return null
      continue
    }
    if (ch === '"') {
      started = true
      i++
      let closed = false
      while (i < n) {
        if (command[i] === '"') {
          closed = true
          i++
          break
        }
        current += command[i]
        i++
      }
      if (!closed) return null
      continue
    }
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      if (started) {
        tokens.push(current)
        current = ""
        started = false
      }
      i++
      continue
    }
    current += ch
    started = true
    i++
  }
  if (started) tokens.push(current)
  return tokens
}

function whitespaceSplit(command) {
  const trimmed = command.trim()
  return trimmed ? trimmed.split(/\s+/) : []
}

function isAssignment(token) {
  return ASSIGNMENT_RE.test(token)
}

// Strip leading wrapper/assignment prefixes, mirroring the hook's
// `_r5_stripped_tokens`. `env -S <string>`/`--split-string[=]<string>` splices
// the string back through the splitter, because `env -S` runs it as the command.
function stripWrappers(tokens) {
  let i = 0
  while (i < tokens.length) {
    const token = tokens[i]
    if (isAssignment(token)) {
      i++
      continue
    }
    if (!SHELL_WRAPPERS.has(token)) break
    const wrapper = token
    const valueOpts = WRAPPER_VALUE_OPTS[wrapper] || new Set()
    i++
    let spliced = null
    while (i < tokens.length) {
      const option = tokens[i]
      if (isAssignment(option)) {
        i++
        continue
      }
      if (!(option.startsWith("-") && option.length > 1)) break
      if (wrapper === "env" && (option.startsWith("-S") || option.split("=")[0] === "--split-string")) {
        let value
        if (option.includes("=")) {
          value = option.slice(option.indexOf("=") + 1)
          i++
        } else if (option === "-S" || option === "--split-string") {
          i++
          value = tokens[i] ?? ""
          i++
        } else {
          value = option.slice(2)
          i++
        }
        const parts = shellSplit(value)
        spliced = parts === null ? whitespaceSplit(value) : parts
        break
      }
      const base = option.split("=")[0]
      i++
      if (!option.includes("=") && valueOpts.has(base) && i < tokens.length && !tokens[i].startsWith("-")) {
        i++
      }
    }
    if (spliced !== null) return stripWrappers(spliced.concat(tokens.slice(i)))
    if (wrapper === "timeout" && i < tokens.length && !tokens[i].startsWith("-")) {
      i++
    }
  }
  return tokens.slice(i)
}

function commandTokens(command) {
  const split = shellSplit(command)
  const tokens = split === null ? whitespaceSplit(command) : split
  return stripWrappers(tokens)
}

function stripMatchedQuotes(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim()
  if (t.length >= 2 && ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'")))) {
    t = t.slice(1, -1)
  }
  return t
}

// Normalize an executable token for R2/R4 comparison: strip surrounding
// quotes and path qualification (`"rm"`, `'rm'`, `/bin/rm`, `./rm` all
// resolve to `rm`). Executor-permit matching stays exact and separate.
function normalizeToken(raw) {
  if (!raw || typeof raw !== "string") return ""
  const t = stripMatchedQuotes(raw)
  const slash = t.lastIndexOf("/")
  if (slash !== -1) return t.slice(slash + 1)
  return t
}

function basenameOf(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim().replace(/\\/g, "/")
  t = stripMatchedQuotes(t)
  const slash = t.lastIndexOf("/")
  if (slash !== -1) t = t.slice(slash + 1)
  return t
}

function tokenAt(command, index) {
  const tokens = commandTokens(command)
  return tokens[index] ?? ""
}

// Whether a token names a python interpreter, case-insensitively, including a
// versioned spelling (`python3.12`). The hook lowercases the program token the
// same way, so the two guards agree on `PYTHON3` and on `python3.12`.
function isPythonInterpreter(raw) {
  const t = normalizeToken(raw).toLowerCase()
  if (PYTHON_INTERPRETERS.has(t)) return true
  return VERSIONED_PYTHON_RE.test(t)
}

function isExecutorPermit(command) {
  const tokens = commandTokens(command)
  if (tokens.length < 2) return false
  if (basenameOf(tokens[0]).toLowerCase() !== "python3") return false
  const second = stripMatchedQuotes(tokens[1]).replace(/\\/g, "/")
  return second === ".plan/execute-script.py" || second.endsWith("/.plan/execute-script.py")
}

// Resolve a script token to its repository-relative path, or null when it does
// not resolve inside the repository. An ABSOLUTE token is made relative to the
// repository root and refused when it lies outside it; a RELATIVE token is
// normalized (a leading `./` collapsed, `..` segments applied) and refused when
// it escapes the root. Matching then compares this key EXACTLY against an
// allow-list entry, so a basename (or a copy of an allow-listed script outside
// the repository) can never match — the suffix hole PLAN-LB-62 shipped.
function repoRelativePath(raw, root) {
  if (!raw || typeof raw !== "string") return null
  let token = raw.trim().replace(/\\/g, "/")
  const normalizedRoot = (root || "").replace(/\\/g, "/").replace(/\/+$/, "")
  if (token.startsWith("/")) {
    if (!normalizedRoot) return null
    const prefix = normalizedRoot + "/"
    if (!token.startsWith(prefix)) return null
    token = token.slice(prefix.length)
  }
  const parts = []
  for (const segment of token.split("/")) {
    if (segment === "" || segment === ".") continue
    if (segment === "..") {
      if (parts.length === 0) return null
      parts.pop()
      continue
    }
    parts.push(segment)
  }
  return parts.length ? parts.join("/") : null
}

// Whether a second token is on the shared allow-list, matched EXACTLY on its
// repository-relative path (resolved against the repository root).
function isAllowListed(command, entries, root) {
  const tokens = commandTokens(command)
  if (tokens.length < 2) return false
  const relative = repoRelativePath(stripMatchedQuotes(tokens[1]), root)
  if (relative === null) return false
  return entries.includes(relative)
}

// Read the shared allow-list. Project first, then the deployed OpenCode config
// directory; absent (or empty) falls back to the built-in base table.
function loadAllowList(root) {
  const configRoot = process.env.XDG_CONFIG_HOME || path.join(process.env.HOME || "", ".config")
  const candidates = [
    path.join(
      root,
      "marketplace",
      "bundles",
      "plan-marshall",
      "skills",
      "platform-runtime",
      "standards",
      "r5-allowlist.json",
    ),
    path.join(
      configRoot,
      "opencode",
      "skills",
      "plan-marshall-platform-runtime",
      "standards",
      "r5-allowlist.json",
    ),
    path.join(
      configRoot,
      "opencode",
      "skill",
      "plan-marshall-platform-runtime",
      "standards",
      "r5-allowlist.json",
    ),
  ]
  for (const candidate of candidates) {
    try {
      const data = JSON.parse(readFileSync(candidate, "utf8"))
      const entries = data && data.entries
      if (entries && typeof entries === "object") {
        const keys = Object.keys(entries)
        if (keys.length) return keys
      }
    } catch {
      // Try the next candidate.
    }
  }
  return [...R5_ALLOWLIST_BASE]
}

const R5_VALUE_TAKING_SINGLE = new Set(["c", "m", "W", "X"])

function isCMCluster(t) {
  if (!t.startsWith("-") || t.startsWith("--")) return false
  if (t.length < 2) return false
  for (const ch of t.slice(1)) {
    if (R5_VALUE_TAKING_SINGLE.has(ch)) return ch === "c" || ch === "m"
  }
  return false
}

function mModuleOf(secondRaw, thirdRaw) {
  const s = typeof secondRaw === "string" ? secondRaw.trim() : ""
  if (s === "-m") return typeof thirdRaw === "string" ? thirdRaw.trim() : ""
  if (s.startsWith("-m") && s.length > 2 && !s.startsWith("--")) return s.slice(2).trim()
  return ""
}

function isInterpreterBypass(secondRaw) {
  if (!secondRaw || typeof secondRaw !== "string") return false
  const t = stripMatchedQuotes(secondRaw)
  if (!t) return false
  if (R5_ALWAYS_REFUSE_FLAGS.has(t)) return true
  if (isCMCluster(t)) return true
  if (t.startsWith("-")) return false
  return true
}

// ---- R5b: interpreter-option prefix (python3 -u script.py) ----
// isInterpreterBypass inspects only the second token, so an interpreter
// option flag in second position (-u, -W, -X, -B, -E, -I, --, bare -)
// hides the script path, -c or -m behind it. Scan every later token with
// the same fail-closed rule: any -c, -m, lone -/--, or non-flag token is a
// bypass. Flag-only tails (python3 --version) and the bare interpreter
// still pass; legitimate work goes through the executor permit.
function hasFlagPrefixedBypass(command) {
  const toks = commandTokens(command).slice(1)
  for (let i = 1; i < toks.length; i++) {
    const t = stripMatchedQuotes(toks[i])
    if (!t) continue
    if (t === "-c" || t === "-m" || t === "-" || t === "--") return true
    if (isCMCluster(t)) return true
    if (!t.startsWith("-")) return true
  }
  return false
}

function targetsExecutor(args) {
  if (!args || typeof args !== "object") return false
  if (normalizedIsExecutorPath(typeof args.filePath === "string" ? args.filePath : "")) return true
  return patchTextTargetsExecutor(typeof args.patchText === "string" ? args.patchText : "")
}

function normalizedIsExecutorPath(raw) {
  if (!raw || typeof raw !== "string") return false
  const normalized = raw.replace(/\\/g, "/")
  return normalized === ".plan/execute-script.py" || normalized.endsWith("/.plan/execute-script.py")
}

// OpenCode's apply_patch tool names its targets in output.args.patchText as
// `*** Add File:` / `*** Update File:` / `*** Move to:` / `*** Delete File:`
// marker lines (plus the legacy bare add/update/move/delete form) rather
// than a filePath. Inspect every operation target (both paths on a move);
// any target resolving under .plan/execute-script.py blocks.
function patchTextTargetsExecutor(patchText) {
  if (!patchText) return false
  const candidates = []
  for (const line of patchText.split("\n")) {
    const op =
      line.match(/^\s*\*+\s+(?:add|update|delete)\s+file:\s*(.+?)\s*$/i) ||
      line.match(/^\s*\*+\s+move\s+to:\s*(.+?)\s*$/i) ||
      line.match(/^\s*(?:add|update|move|delete)\b\s+(.*)$/i)
    if (!op) continue
    const targetPart = op[1]
    const tokenRe = /"([^"]+)"|'([^']+)'|(\S+)/g
    let m
    while ((m = tokenRe.exec(targetPart)) !== null) {
      candidates.push(m[1] ?? m[2] ?? m[3])
    }
  }
  return candidates.some(normalizedIsExecutorPath)
}

// Whether the command is a plain `git commit` invocation — `git` as the
// program, `commit` as the subcommand after any global options.
function isGitCommit(command) {
  if (normalizeToken(tokenAt(command, 0)).toLowerCase() !== "git") return false
  const tokens = commandTokens(command)
  let i = 1
  while (i < tokens.length) {
    const t = stripMatchedQuotes(tokens[i])
    if (GIT_VALUE_OPTIONS.has(t)) {
      i += 2
      continue
    }
    if (t.startsWith("-")) {
      i++
      continue
    }
    return t.toLowerCase() === "commit"
  }
  return false
}

// The enclosing plan's phase, read from the first plan status.json under the
// project root. Empty when no plan state is present or none is readable.
function planPhase(root) {
  const base = path.join(root, ".plan", "local", "plans")
  let entries
  try {
    entries = readdirSync(base)
  } catch {
    return ""
  }
  for (const name of entries.sort()) {
    try {
      const data = JSON.parse(readFileSync(path.join(base, name, "status.json"), "utf8"))
      if (data && typeof data.phase === "string" && data.phase) return data.phase
    } catch {
      // Skip an unreadable or malformed status.
    }
  }
  return ""
}

// R6 — a raw `git commit` in phase 6-finalize is refused: every plan commit
// must pass through the gate-bearing `git-workflow commit` verb.
function isRawFinalizeCommit(command, root) {
  return isGitCommit(command) && planPhase(root) === SOURCE_COMMIT_GATE_PHASE
}

function auditLine(rule, tool, sessionID, callID, detail) {
  return `${new Date().toISOString()} | tool=${tool} | rule=${rule} | session=${sessionID} | call=${callID} | ${detail}`
}

export default Plugin.define({
  id: "plan-marshall-guard",
  async setup(ctx) {
    const root = ctx.location?.directory || "."
    const logPath = path.join(root, ".plan", "temp", "guard.log")
    const allowList = loadAllowList(root)

    function audit(entry) {
      try {
        mkdirSync(path.dirname(logPath), { recursive: true })
        appendFileSync(logPath, entry + "\n", "utf8")
      } catch {
        // An audit failure must never mask the throw that triggered it.
      }
    }

    await ctx.tool.hook("execute.before", async (event) => {
      const tool = event?.tool ?? ""
      const sessionID = event?.sessionID ?? event?.sessionId ?? "?"
      const callID = event?.callID ?? event?.callId ?? event?.id ?? "?"
      const args = (event && (event.input ?? event.args ?? event.params)) || {}
      const command = typeof args.command === "string" ? args.command : ""

      if (tool === "edit" || tool === "write" || tool === "patch" || tool === "apply_patch") {
        if (targetsExecutor(args)) {
          audit(auditLine("R3", tool, sessionID, callID, command || String(args.filePath ?? "")))
          throw new Error(
            "[plan-marshall-guard] R3: direct edits to the generated executor (.plan/execute-script.py) are forbidden; access .plan/ via manage-* scripts only",
          )
        }
        return
      }

      // OpenCode 2 names its shell tool `shell`; OpenCode 1 named it `bash`.
      if (tool !== "shell" && tool !== "bash") return

      if (hasChainingConstructor(command)) {
        audit(auditLine("R1", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R1: shell-chaining constructors (&&, &, ;, |, $(), subshells, process substitutions, backticks, newline) are forbidden; one command per Bash call",
        )
      }

      const token = normalizeToken(tokenAt(command, 0))
      if (token && MUTATION_FILE_OPS.has(token)) {
        audit(auditLine("R2", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R2: shell file operations (mutation class) via Bash are forbidden; use the Read/Edit/Write tools or manage-* scripts",
        )
      }

      if (isRawFinalizeCommit(command, root)) {
        audit(auditLine("R6", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R6: a raw git commit is refused in phase 6-finalize — commit through python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow commit (the gate-bearing path), which sanctions an open loop-back fix task, a review-rubric section-6 record, or a settle-band step",
        )
      }

      if (isExecutorPermit(command)) return

      if (token === "./pw" || basenameOf(tokenAt(command, 0)) === "pw") {
        const verb = tokenAt(command, 1)
        const passes = Boolean(verb && (verb.startsWith("generate") || verb.startsWith("--")))
        if (!passes) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build via ./pw is forbidden; route builds through python3 .plan/execute-script.py",
          )
        }
        return
      }

      if (BARE_BUILD_TOOLS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      if (JS_RUNNER_BUILD_VERBS.has(normalizeToken(tokenAt(command, 1))) && JS_RUNNERS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      if (PYTHON_INTERPRETERS.has(token) || isPythonInterpreter(token)) {
        const second = basenameOf(tokenAt(command, 1))
        const mModule = normalizeToken(mModuleOf(tokenAt(command, 1), tokenAt(command, 2)))
        if (second === "build.py" || (mModule && PYTHON_DIRECT_RUNNERS.has(mModule))) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
          )
        }
        // R5 applies in EVERY session — root sessions included — with no
        // plan-context gate. The allow-list is matched on the repo-relative path.
        if (isAllowListed(command, allowList, root)) return
        if (isInterpreterBypass(tokenAt(command, 1)) || hasFlagPrefixedBypass(command)) {
          audit(auditLine("R5", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R5: direct python interpreter calls (python -c, script paths, python -m) bypassing the executor are forbidden; route builds and checks via python3 .plan/execute-script.py and .plan state via manage-* verbs or the Read/Edit/Write tools",
          )
        }
        return
      }

      if (PYTHON_DIRECT_RUNNERS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }
    })
  },
})
