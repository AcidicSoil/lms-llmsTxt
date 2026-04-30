### Dependency Security Posture Policy

Treat dependency resolution, installation, and execution as a **software supply chain security boundary**.

This policy is **package-manager agnostic**. Apply the posture first, then map it to the repository’s actual tooling.
Do not assume npm, pnpm, yarn, pip, cargo, bundler, go modules, or any other ecosystem until the repository has been inspected.

---

## Primary posture

Default to an **aggressive zero-trust dependency posture**:

- delay adoption of newly published packages and versions where the ecosystem supports it
- block or tightly control install-time and build-time scripts
- prevent silent dependency graph drift
- prefer repo-enforced policy over developer-local machine settings
- fail closed when trust signals weaken or transitive source provenance becomes less controlled
- preserve deterministic installs through committed lockfiles
- surface policy conflicts before performing installs or dependency mutations
- do not silently weaken security controls for compatibility

This policy is intended to protect **what gets installed**, **how it gets installed**, and **what gets executed during installation**.

---

## Required agent behavior

Before adding, updating, removing, reinstalling, or approving any dependency, the agent must:

1. detect the active dependency ecosystem from the repo
2. inspect the repo’s package-manager and install-policy config
3. identify which security controls are present, absent, or conflicting
4. warn on policy drift or contradiction
5. only then propose or perform dependency changes

Never install dependencies first and audit later.

---

## Repo-first enforcement rule

Security policy must be enforced at the **repository level** wherever the ecosystem supports it.

- Prefer committed repo/workspace config over `~` user config
- Treat user-home config as personal preference, credentials, or registry/auth scope only
- Do not mistake `~/.npmrc`, shell aliases, or local machine defaults for team enforcement
- If security controls exist only in user config and not in the repo, warn that the repo is effectively unprotected for teammates and CI

---

## Security control categories

Map the active ecosystem to these control classes:

### 1. Freshness quarantine

Delay newly published packages or versions before they become installable.

### 2. Script execution control

Block or explicitly approve install/build/postinstall/native compilation scripts.

### 3. Deterministic resolution

Require lockfile-driven installs and block silent graph mutation in CI.

### 4. Provenance and source restrictions

Reject or flag exotic, non-registry, or trust-downgraded transitive sources where supported.

### 5. Exactness and drift reduction

Prefer exact versions for newly added dependencies unless the repo explicitly opts into ranged resolution.

### 6. Engine/runtime enforcement

Fail if dependency runtime constraints are incompatible with the enforced runtime.

### 7. Pre-run dependency verification

Refuse to run project scripts against stale, mutated, or unverified dependency state where supported.

---

## Conflict detection rule

Before any dependency-changing action, compare **current repo config** against the target posture and emit a conflict report.

A setting is **conflicting** if any of the following are true:

- the required control is absent
- the control exists only in user-local config but not in repo config
- the current value weakens the required posture
- two configured controls contradict each other operationally
- the configured package manager supports a stronger native mechanism, but the repo is relying on a weaker legacy workaround
- the lockfile/install workflow allows graph mutation contrary to policy

If conflicts exist, warn explicitly before performing the action.

Use this warning structure:

```text
Dependency security posture conflicts detected

- Ecosystem: <detected manager>
- Enforcement scope: <repo|user|mixed>
- Blocking conflicts:
  - <file>: <setting> = <current> conflicts with <expected> because <reason>
- Redundant controls:
  - <file>: <setting> overlaps with <other setting> and may mask intended approval workflow
- Missing controls:
  - <file or scope>: <missing setting/control>
- Operational risk:
  - <brief statement of what can still happen>
- Required remediation:
  - <ordered changes>
