# Task ID: 7

**Title:** MCP Server Tool & Resource Wiring

**Status:** done

**Dependencies:** 6 ✓

**Priority:** high

**Description:** Configure the FastMCP server instance and register tools and resources.

**Details:**

In `server.py`, initialize `FastMCP`. Register the `lmstxt_generate` and `lmstxt_read_artifact` functions as tools with appropriate descriptions. Register the `lmstxt://runs/{run_id}/{artifact}` pattern as a resource. Ensure the `lmstxt_list_runs` tool is also registered. Wire up the `stdio` and `http` transport capabilities provided by FastMCP/MCP SDK.

Libraries: `fastmcp` (or standard `mcp` SDK depending on preference/availability).
files: `src/lmstxt_mcp/server.py`.

**Test Strategy:**

Functional test: Instantiate the server in a test harness. Call `list_tools` and `list_resources` to verify registration. Simulate a tool call and resource read request.

## Subtasks

### 7.1. Initialize FastMCP Server Instance

**Status:** done  
**Dependencies:** None  

Set up the basic FastMCP server application shell and entry point. [Updated: 1/3/2026]

**Details:**

In `src/lmstxt_mcp/server.py`, import `FastMCP` and instantiate the server object with the name 'lmstxt-mcp'. Define the standard `if __name__ == "__main__":` block to invoke `mcp.run()`, ensuring it defaults to the stdio transport mechanism for standard MCP communication.

### 7.2. Register MCP Tools

**Status:** done  
**Dependencies:** 7.1  

Expose the core generation and retrieval functions as MCP tools.

**Details:**

Import the logic from core modules. Use the `@mcp.tool()` decorator to register `lmstxt_generate`, `lmstxt_read_artifact`, and `lmstxt_list_runs`. Ensure type hints use the Pydantic models defined in `models.py` so that FastMCP generates the correct JSON schemas for the tool definitions.

### 7.3. Register Dynamic Resources

**Status:** done  
**Dependencies:** 7.1  

Implement the URI pattern for accessing generated artifacts as resources. [Updated: 1/3/2026]

**Details:**

Use the `@mcp.resource("lmstxt://runs/{run_id}/{artifact}")` decorator to register the resource handler. Implement the underlying function to parse the `run_id` and `artifact` name, retrieve the content from `RunStore`, and return it as a string resource.

### 7.4. Server Capability Verification

**Status:** done  
**Dependencies:** 7.2, 7.3  

Verify the complete wiring of tools and resources within the server instance. [Updated: 1/3/2026]

**Details:**

Create an integration test harness that loads the `server.py` module. Call the internal MCP introspection methods (e.g., `list_tools`, `list_resource_templates`) to verify that the server is correctly advertising its capabilities before it is deployed to a real client.
