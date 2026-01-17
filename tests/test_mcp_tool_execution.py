import subprocess
import json
import os
import sys
import pytest

@pytest.mark.integration
def test_mcp_stdio_server_tool_execution():
    """
    Launches the installed lmstxt-mcp CLI and verifies actual tool execution via JSON-RPC.
    """
    cmd = [".venv/bin/lmstxt-mcp"]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # 1. Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        process.stdin.write(json.dumps(init_req) + "\n")
        process.stdin.flush()
        process.stdout.readline() # Read init response

        # 2. Notification
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }) + "\n")
        process.stdin.flush()

        # 3. Execute Tool: lmstxt_list_runs
        # This tests that arguments (limit) are correctly parsed and the result marshaled back.
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "lmstxt_list_runs",
                "arguments": {
                    "limit": 5
                }
            }
        }
        process.stdin.write(json.dumps(call_req) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        assert response_line, "Server produced no output for tool call"

        resp = json.loads(response_line)
        assert resp.get("id") == 2
        assert "result" in resp

        # FastMCP returns tool results in a specific content format
        content = resp["result"]["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"

        # The tool returns a JSON string, so we parse that
        tool_result_json = content[0]["text"]
        runs = json.loads(tool_result_json)
        assert isinstance(runs, list)
        assert len(runs) == 0 # RunStore is empty on fresh start

        # 4. Execute Tool: lmstxt_read_artifact (Error case)
        # This tests error handling for missing arguments or logical errors
        call_req_error = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "lmstxt_read_artifact",
                "arguments": {
                    "run_id": "missing-id",
                    "artifact_name": "llms.txt",
                    "offset": 0,
                    "limit": 100
                }
            }
        }
        process.stdin.write(json.dumps(call_req_error) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        resp = json.loads(response_line)

        # FastMCP might return isError: true in the result or a JSON-RPC error
        # In this case, the python function raises an exception.
        # FastMCP catches exceptions and usually returns a successful JSON-RPC response
        # containing the error message in the content text (or isError=True).

        assert resp.get("id") == 3
        # Check for isError flag in result
        assert resp["result"].get("isError") is True
        # Verify error message contains exception text
        text_content = resp["result"]["content"][0]["text"]
        assert "not found" in text_content or "Run ID missing-id not found" in text_content

    finally:
        process.kill()
        process.wait()
