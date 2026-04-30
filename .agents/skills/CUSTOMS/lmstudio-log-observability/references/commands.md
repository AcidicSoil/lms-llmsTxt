# Command Recipes

Use these commands from separate terminals so logs remain visible while test traffic runs.

## Server Logs

```bash
lms server start
lms log stream --source server
```

Short form:

```bash
lms log stream -s server
```

Expected signal: startup messages, endpoints, HTTP request handling, status codes, and server-side errors.

## Model I/O Logs

```bash
lms log stream --source model --filter input,output
```

Use model I/O logs when prompt formatting, chat templates, tool-call payloads, or model output are the suspected failure point.

## JSONL Capture

```bash
lms log stream -s server --json | tee -a lmstudio-server.jsonl
lms log stream -s model --filter input,output --json | tee -a lmstudio-model-io.jsonl
```

Use JSONL when another process will parse logs or when attaching logs to an issue.

## Traffic Probe

```bash
curl http://localhost:1234/v1/models
```

Chat completion probe:

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-loaded-model-id",
    "messages": [{"role": "user", "content": "Say hello"}],
    "temperature": 0.7
  }'
```

## Runtime Source Check

Official LM Studio docs document `model` and `server` sources. If the user's installed CLI shows `runtime`, verify first:

```bash
lms log stream --help
```

Only then run:

```bash
lms log stream -s runtime
```
