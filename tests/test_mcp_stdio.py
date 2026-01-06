import subprocess
import json
import os
import sys
import pytest

@pytest.mark.integration
def test_mcp_stdio_server():
    """
    Launches the installed llmstxt-mcp CLI and verifies JSON-RPC communication.
    """
    # Verify the command exists in the path/venv
    cmd = ["venv_test/bin/llmstxt-mcp"]
    
    # We need to run this in the context where the package is installed
    # subprocess.Popen will use the current environment variables
    
    # Start the server process
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )

    try:
        # 1. Initialize Request
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
        
        # Send initialize
        json_line = json.dumps(init_req) + "\n"
        process.stdin.write(json_line)
        process.stdin.flush()
        
        # Read response (might be multiple lines of logs on stderr, we want stdout)
        # FastMCP might send logs to stderr, JSON to stdout
        
        response_line = process.stdout.readline()
        assert response_line, "Server produced no output"
        
        resp = json.loads(response_line)
        assert resp.get("id") == 1
        assert "result" in resp
        # Matches FastMCP("lms-llmstxt")
        assert resp["result"]["serverInfo"]["name"] == "lms-llmstxt"

        # 2. Initialized Notification
        notify_req = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        process.stdin.write(json.dumps(notify_req) + "\n")
        process.stdin.flush()

        # 3. List Tools Request
        list_tools_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        process.stdin.write(json.dumps(list_tools_req) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        resp = json.loads(response_line)
        
        assert resp.get("id") == 2
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        
        assert "llmstxt_generate_llms_txt" in tool_names
        assert "llmstxt_generate_llms_full" in tool_names
        assert "llmstxt_generate_llms_ctx" in tool_names
        assert "llmstxt_list_runs" in tool_names
        assert "llmstxt_read_artifact" in tool_names

    finally:
        process.kill()
        process.wait()
