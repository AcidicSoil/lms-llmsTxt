## Agent policy: non-blocking execution + deterministic verification (anti-stale-run)

### 0) Goal

Prevent the agent from executing any shell command (tests included) that can hang, wait, or become nondeterministic due to:

- missing required inputs (args/files/env vars/fixtures),
- interactive prompts (stdin, TUI, editor launch),
- reliance on external services/network/daemons not explicitly provisioned,
- long-running operations without an enforced stop condition.

This policy is *principle-based* and must apply to **all** commands and test frameworks without naming specific tests.

---

### 1) Execution gate: “Command Readiness Contract” (CRC)

Before running **any** shell command, the agent must write (mentally or explicitly) a CRC and only proceed if every field is satisfied.

**CRC fields**

1) **Purpose**: what this command verifies or produces (1 sentence).
2) **Inputs**: enumerate *all* required inputs and dependencies:
   - CLI args + expected shapes,
   - required files/paths,
   - required env vars,
   - required services/endpoints/daemons,
   - required credentials/secrets (must be mocked or omitted unless already available).
3) **Non-interactive guarantee**:
   - confirm the command cannot prompt; or
   - add known non-interactive flags; or
   - redirect stdin safely; otherwise **do not run**.
4) **Time bound**:
   - set a hard timeout for the command.
   - if no reliable timeout mechanism exists in the environment, **do not run**.
5) **Expected result**:
   - the concrete success signal (exit code + expected stdout/stderr patterns + created/modified artifacts).
6) **Failure handling**:
   - what to do if it fails (narrow scope, increase logging, switch strategy), without retry loops.

**Hard rule**

- If *any* CRC field is unknown, unavailable, or cannot be guaranteed, the agent must **not** run the command and must switch to an alternative verification strategy (Section 5).

---

### 2) Hard safety rules for shell execution

**A. No interactive commands**

- Never run commands that open an editor, a TUI, a REPL, or might block on stdin.
- If interactivity is possible and cannot be disabled with certainty, do not execute.

**B. Always enforce a timeout**

- Every command must be executed with a hard timeout.
- If the environment cannot enforce timeouts reliably, do not execute shell commands at all.

**C. One command per step**

- No chaining (`&&`, `;`, `||`) and no multi-command pipelines.
- Run one command, observe exit code/output, then decide the next step.

**D. No implicit external dependencies**

- Do not assume daemons, network access, or long-lived services exist.
- Only rely on external services if they are explicitly started/configured in the current workflow and validated via a bounded health check.

**E. Log capture**

- Commands must be run in a way that preserves enough output to diagnose failures without re-running interactively.

---

### 3) Testing policy: evidence-gated, smallest-scope-first

**A. Dependency discovery before execution**

- Before running tests, determine what they require:
  - fixtures, temp dirs, env vars, network, external binaries, background services.
- If requirements are not satisfied, do not run; instead supply a minimal fixture/mocked dependency or choose an alternate verification method.

**B. Smallest-scope-first progression**

- Run the narrowest check that can validate the change:
  1) targeted test selection (single file / single test / focused filter),
  2) small suite,
  3) full suite (only if earlier steps pass and runtime remains bounded).
- Avoid “run everything” as the default.

**C. Anti-hang requirements for tests**

- Tests must have a time bound at one or both levels:
  - whole-run timeout, and/or
  - per-test timeout mechanism (framework/plugin/runner support).
- Prefer fail-fast settings and focused selection to reduce time-to-signal.

**D. Explicitly separate unit vs integration**

- If tests exercise external services, treat them as integration tests:
  - run them only when the service is explicitly provisioned and verified (bounded health check),
  - otherwise skip and validate via unit tests with mocks/stubs.

---

### 4) Determinism policy: minimize flaky outcomes

When running tests or build steps, the agent must proactively reduce nondeterminism:

- Set stable environment knobs when applicable (locale/timezone, deterministic ordering, stable temp paths).
- Avoid relying on wall-clock time, network timing, or randomized ordering unless explicitly controlled.
- If a test is flaky, prefer isolating the minimal failing reproduction and adding/using deterministic fixtures rather than re-running.

---

### 5) Mandatory fallback when a command cannot be made safe

If a command/test cannot satisfy the CRC (complete inputs + non-interactive + time bounded), the agent must **not run it** and must use an alternate verification method, such as:

- static analysis (lint/typecheck/format checks that are non-interactive + time bounded),
- unit-level execution of the relevant module/function with a synthetic fixture,
- adding/reworking a test to make inputs explicit and non-interactive,
- mocking external boundaries (filesystem/network/service clients),
- “dry-run” / “collect-only” / “list tests” modes to validate selection without executing.

Fallback selection must still obey the CRC.

---

### 6) Operational definition of “done”

A step is complete only when:

- a bounded, non-interactive verification ran successfully, **or**
- the agent produced a concrete alternative verification artifact (e.g., a small deterministic unit test + fixture) that can run bounded and non-interactively.

---

### 7) Minimal generic execution pattern (example, not prescriptive)

For any verification:

- Run **one** bounded command that checks the narrowest target.
- Observe exit code + expected success signal.
- Only then expand scope if needed.

(No test names, no repo-specific references; the rule is: *bounded + non-interactive + smallest-scope-first*.)
