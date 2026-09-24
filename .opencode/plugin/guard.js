/**
 * plan-marshall guard plugin — tool.execute.before enforcement of R1-R4.
 *
 * The opencode host loads every module under `{plugin,plugins}/*.{ts,js}` in the
 * project config directory and imports it with Bun. This plugin registers a
 * `tool.execute.before` hook that inspects each tool invocation against the four
 * plan-marshall hard-rule bypass classes and THROWS to block the execution,
 * appending one audit line to `.plan/temp/guard.log` per blocked invocation.
 *
 * The plugin is not covered by the Python test harness; its decision table below
 * is mirrored as a behavioral contract in
 * `test/plan-marshall/platform-runtime/test_opencode_enforcement.py`. Keep the
 * two in lock-step when the table changes.
 *
 * DECISION TABLE (authoritative — mirrored in the D4 runtime matrix):
 *
  *   Guarded tools: bash (R1, R2, R4), edit/write/patch/apply_patch (R3).
  *   Every other tool passes through untouched.
 *
 *   R1 — shell-chaining constructors (bash): the command, with single-quoted
 *   regions stripped and double-quoted regions stripped except for command
 *   substitution, contains `&&`, `||`, `;`, `|`, `$(`,
 *   a backtick, any unquoted `&` or `(`, or a newline  => block. `$(` and backticks
 *   inside double quotes still block because Bash executes them there.
 *
 *   R2 — shell file operations, mutation class (bash): the command's first token,
 *   after stripping `command`/`env`/`sudo` wrappers (with options), leading
 *   `NAME=value` assignments, quotes, and path qualification,
 *   is one of {rm mv cp touch mkdir rmdir truncate tee chmod chown ln dd}  => block.
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
 *     - first token is `python`/`python3` and the basename of the second
 *       token is `build.py` (`python3 ./build.py` included);
 *     - `python(3) -m {pytest mypy ruff}`; a bare {pytest mypy ruff}.
 *   The executor permit `python3 .plan/execute-script.py <verb> ...` is exempt.
 */
import { appendFileSync, mkdirSync } from "node:fs"
import path from "node:path"

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
const JS_RUNNER_BUILD_VERBS = new Set(["test", "run", "build"])
const PYTHON_DIRECT_RUNNERS = new Set(["pytest", "mypy", "ruff"])

// Shell wrappers (`command`, `env`, `sudo`) and leading `NAME=value`
// assignments are transparent to the shell: `command rm -f file` still runs
// `rm`. Strip them before first-token checks so R2/R4 cannot be bypassed
// by prefixing a blocked invocation. Wrapper options (`env -i`,
// `sudo -u <user>`, `command -p`) are skipped alongside the wrapper itself;
// fail closed on unparseable wrapper syntax by treating the invocation as
// wrapped until a non-option executable token is reached.
const SHELL_WRAPPERS = new Set(["command", "env", "sudo"])

// Wrapper options that consume a following value token (`sudo -u <user>`).
const WRAPPER_OPTS_WITH_VALUE = new Set([
  "-u", "--user", "-g", "--group", "-U", "--other-user",
  "-C", "--chdir", "--directory",
])

function commandTokens(command) {
  const tokens = command.trimStart().split(/\s+/)
  let i = 0
  while (i < tokens.length) {
    const t = tokens[i]
    if (SHELL_WRAPPERS.has(t)) {
      i++
      while (i < tokens.length) {
        const o = tokens[i]
        if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(o)) {
          i++
          continue
        }
        if (o.startsWith("-") && o.length > 1) {
          const base = o.split("=")[0]
          i++
          if (WRAPPER_OPTS_WITH_VALUE.has(base) && i < tokens.length && !tokens[i].startsWith("-")) {
            i++
          }
          continue
        }
        break
      }
      continue
    }
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(t)) {
      i++
      continue
    }
    break
  }
  return tokens.slice(i)
}

// Normalize an executable token for R2/R4 comparison: strip surrounding
// quotes and path qualification (`"rm"`, `'rm'`, `/bin/rm`, `./rm` all
// resolve to `rm`). Executor-permit matching stays exact and separate.
function normalizeToken(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim()
  if (t.length >= 2 && ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'")))) {
    t = t.slice(1, -1)
  }
  const slash = t.lastIndexOf("/")
  if (slash !== -1) t = t.slice(slash + 1)
  return t
}

function basenameOf(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim().replace(/\\/g, "/")
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    t = t.slice(1, -1)
  }
  const slash = t.lastIndexOf("/")
  if (slash !== -1) t = t.slice(slash + 1)
  return t
}

function tokenAt(command, index) {
  const tokens = commandTokens(command)
  return tokens[index] ?? ""
}

function isExecutorPermit(command) {
  return /^python3\s+\.plan\/execute-script\.py\b/.test(commandTokens(command).join(" "))
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

function auditLine(rule, tool, sessionID, callID, detail) {
  return `${new Date().toISOString()} | tool=${tool} | rule=${rule} | session=${sessionID} | call=${callID} | ${detail}`
}

export const GuardPlugin = async ({ worktree, directory }) => {
  const root = worktree || directory || "."
  const logPath = path.join(root, ".plan", "temp", "guard.log")

  function audit(entry) {
    try {
      mkdirSync(path.dirname(logPath), { recursive: true })
      appendFileSync(logPath, entry + "\n", "utf8")
    } catch {
      // An audit failure must never mask the throw that triggered it.
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      const tool = input?.tool ?? ""
      const sessionID = input?.sessionID ?? "?"
      const callID = input?.callID ?? "?"
      const args = (output && output.args) || {}
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

      if (tool !== "bash") return

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

      if (JS_RUNNER_BUILD_VERBS.has(normalizeToken(tokenAt(command, 1))) && new Set(["npm", "npx", "bun", "pnpm", "yarn"]).has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      if (token === "python3" || token === "python") {
        const second = basenameOf(tokenAt(command, 1))
        const third = normalizeToken(tokenAt(command, 2))
        if (second === "build.py" || (tokenAt(command, 1) === "-m" && PYTHON_DIRECT_RUNNERS.has(third))) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
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
    },
  }
}