Direct answer (1–4 bullets, evidence-cited)

Exit codes are not well-separated for automation: any exception from run_generation(...) is routed through parser.error(str(exc)), which is argparse’s usage error path (typically exit code 2). That conflates “bad CLI usage” with “runtime failure” (network/model/IO/etc.).

The return 2 is effectively dead code: ArgumentParser.error() calls exit(2) internally (raises SystemExit), so return 2 will generally never run, and callers invoking main() programmatically can’t reliably get an int on failures.

Fallback usage is surfaced clearly in the summary: on success, the summary appends a human-readable note when artifacts.used_fallback is true. This is good for users, but it remains plain text (not machine-readable).

Stdout/stderr separation is mostly OK for automation: logging goes to stderr by default, while the summary is printed to stdout. The main issue is failures printing argparse usage text (stderr) via parser.error, which is noisy and inconsistent for “runtime” errors.

Risks/unknowns (bullets)

Unknown whether “fallback used” should be considered a successful run (exit 0) for your automation use cases, or whether automation should be able to fail-fast when fallback occurs (e.g., CI gate). This depends on run_generation’s contract and when it sets used_fallback vs. raises. (Needs src/lmstudiotxt_generator/pipeline.py + fallback code paths.)

Unknown whether any exceptions are already wrapped into typed, actionable errors elsewhere (connectivity, model discovery, output-dir validation), which would change what the CLI should display vs. log. (Needs pipeline.py, lmstudio.py, and any custom exception classes.)

parser.error(str(exc)) will typically strip stack traces, which can make diagnosing automation failures harder unless logs capture full exception context elsewhere. (Needs confirmation of logging/exception handling in run_generation.)

Next smallest concrete experiment (1 action)

Add a single CLI-focused test that invokes main([...]) under three conditions—(a) invalid repo arg, (b) forced runtime exception in run_generation via monkeypatch, (c) run_generation returning artifacts with used_fallback=True)—and assert (1) exit behavior (int return vs SystemExit), (2) exit codes, and (3) stdout/stderr contents (presence of the fallback note only in case (c), and no argparse usage spam for runtime errors).

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next

src/lmstudiotxt_generator/pipeline.py (definition of run_generation, especially how it distinguishes “hard failure” vs “fallback success” and how it sets used_fallback / raises exceptions)

src/lmstudiotxt_generator/lmstudio.py (exception taxonomy and how failures are surfaced upward)

src/lmstudiotxt_generator/fallback.py (what “fallback JSON/schema output” precisely means and whether it should affect exit status)
