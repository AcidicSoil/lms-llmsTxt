---
name: lmstudio-log-observability
description: "Stream, capture, and inspect LM Studio local server, runtime, and model I/O logs. WHEN: \"lms log\", \"LM Studio logs\", \"debug local LLM server\", \"capture model input output\", \"server log stream\"."
license: MIT
metadata:
  author: ChatGPT
  version: "1.0.0"
---

# LM Studio Log Observability

Use this skill to debug LM Studio local server behavior with repeatable `lms log stream` workflows.

## Workflow

1. **Verify CLI access**
   ```bash
   lms --help
   lms log stream --help
   ```
2. **Start or confirm the local server**
   ```bash
   lms server start
   lms server status
   ```
3. **Choose the log source**

   | Goal | Command |
   |---|---|
   | Stream HTTP/server events | `lms log stream --source server` |
   | Short form | `lms log stream -s server` |
   | Inspect prompt/model I/O | `lms log stream --source model --filter input,output` |
   | Save server logs | `lms log stream -s server \| tee -a lmstudio-server.log` |
   | Save JSONL logs | `lms log stream -s server --json \| tee -a lmstudio-server.jsonl` |

4. **Generate traffic** from another terminal, client, or test harness.
5. **Correlate failures** by timestamp, endpoint, model identifier, response status, and whether the issue appears in server logs, model I/O, or runtime behavior.
6. **Use installed CLI help as authority** when sources differ. Some installs may expose extra sources such as `runtime`; only use them if `lms log stream --help` lists them.

## When More Detail Is Needed

- Use [command recipes](references/commands.md) for capture, filtering, and replay commands.
- Use [troubleshooting](references/troubleshooting.md) for common failure patterns.
- Use [automation scripts](references/scripts.md) when the user wants reusable capture commands.

## Output Pattern

When responding, provide:

1. The exact log command to run.
2. The companion command that generates server traffic.
3. The expected signal in the logs.
4. A minimal next diagnostic step if no logs appear.
