# MCP Inspector Payloads (llmstxt)

Paste each payload into the Inspector input, in order. These are intentionally **not JSON**.

## Payload 1: initialize

```
method
initialize

params.protocolVersion
2024-11-05

params.capabilities
{}

params.clientInfo.name
mcp-inspector

params.clientInfo.version
1.0
```

## Payload 2: notifications/initialized

```
method
notifications/initialized

params
{}
```

## Payload 3: tools/list

```
method
tools/list

params
{}
```

## Payload 4: llmstxt_generate_llms_txt

```
method
tools/call

params.name
llmstxt_generate_llms_txt

params.arguments.url
https://github.com/owner/repo

params.arguments.output_dir
./output

params.arguments.cache_lm
true
```

## Payload 5: llmstxt_generate_llms_full (deterministic path mode)

```
method
tools/call

params.name
llmstxt_generate_llms_full

params.arguments.repo_url
https://github.com/owner/repo

params.arguments.output_dir
./output
```

## Payload 6: llmstxt_generate_llms_ctx (deterministic path mode)

```
method
tools/call

params.name
llmstxt_generate_llms_ctx

params.arguments.repo_url
https://github.com/owner/repo

params.arguments.output_dir
./output
```

## Payload 7: llmstxt_read_artifact (deterministic path mode)

```
method
tools/call

params.name
llmstxt_read_artifact

params.arguments.repo_url
https://github.com/owner/repo

params.arguments.output_dir
./output

params.arguments.artifact_name
llms.txt

params.arguments.offset
0

params.arguments.limit
2000
```

## Payload 8: llmstxt_read_artifact (error case)

```
method
tools/call

params.name
llmstxt_read_artifact

params.arguments.repo_url
https://github.com/owner/repo

params.arguments.output_dir
./output

params.arguments.artifact_name
llms.txt

params.arguments.offset
0

params.arguments.limit
200
```
