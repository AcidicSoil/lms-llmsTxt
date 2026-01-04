# Task Master MCP Inspector Payloads

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

## Payload 4: add_task (smoke test)

```
method
tools/call

params.name
add_task

params.arguments.projectRoot
/home/user/projects/temp/lms-llmsTxt

params.arguments.prompt
Inspector smoke test task - safe to delete.
```

## Payload 5: get_tasks

```
method
tools/call

params.name
get_tasks

params.arguments.projectRoot
/home/user/projects/temp/lms-llmsTxt

params.arguments.withSubtasks
false
```
