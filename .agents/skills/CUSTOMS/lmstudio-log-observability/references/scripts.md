# Automation Scripts

Use the scripts when the user wants a reusable capture wrapper instead of typing commands manually.

## Bash

Path: `scripts/capture-lmstudio-logs.sh`

```bash
./scripts/capture-lmstudio-logs.sh server lmstudio-server.jsonl
./scripts/capture-lmstudio-logs.sh model lmstudio-model-io.jsonl
```

## PowerShell

Path: `scripts/Capture-LMStudioLogs.ps1`

```powershell
./scripts/Capture-LMStudioLogs.ps1 -Source server -Output lmstudio-server.jsonl
./scripts/Capture-LMStudioLogs.ps1 -Source model -Output lmstudio-model-io.jsonl
```

## Behavior

- `server` captures server logs with `--json`.
- `model` captures input/output logs with `--json`.
- `runtime` is allowed only after the user confirms their installed CLI supports it.
