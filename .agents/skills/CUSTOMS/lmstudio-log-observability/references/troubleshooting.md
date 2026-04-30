# Troubleshooting

| Symptom | Likely Cause | Check | Next Step |
|---|---|---|---|
| `lms` command missing | CLI unavailable in PATH | `lms --help` | Open LM Studio once or reinstall/link the CLI. |
| No server logs appear | Server is not receiving traffic | `curl http://localhost:1234/v1/models` | Confirm port and base URL used by the client. |
| Server logs show requests but client fails | Endpoint, payload, or model mismatch | Check status code and route | Compare requested model with `lms ps`. |
| Model I/O absent | Using server logs only | `lms log stream -s model --filter input,output` | Run model source in a separate terminal. |
| JSON parsing fails | Mixed plain text and JSON logs | Confirm `--json` was used | Capture to a fresh `.jsonl` file. |
| Runtime issue suspected | Backend/inference behavior | `lms log stream --help` | Use runtime source only if supported by installed CLI. |

## Isolation Order

1. Confirm `lms server status`.
2. Probe `/v1/models` to verify the server responds.
3. Stream `server` logs while reproducing the failing request.
4. Stream `model --filter input,output` if prompt or output formatting is suspect.
5. Capture JSONL when the log needs to be shared or parsed.
