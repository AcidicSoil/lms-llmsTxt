# mcp-doc-context-collection-before-starting-work-always

## Doc Tool Selection and usage

### contex7

Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

### MCPdoc server

for ANY work relating to <libraries> and/or providers use the <name>-docs-mcp server to help answer --

- call list_doc_sources tool to get the available llms.txt file
- call fetch_docs tool to read it
- reflect on the urls in llms.txt
- reflect on the input question
- call fetch_docs on any urls relevant to the question
- use this to answer the question

---

### gitmcp Server usage

for ANY work or questions relating to <libraries> and/or providers use the <name>_docs server for that repo:

- call search_<name>_documentation to find relevant docs
- call fetch_<name>_documentation to read the primary docs
- reflect on the input question
- call fetch_url_content for any external URLs referenced
- call search_<name>_code if code locations are referenced or needed
- use this to answer the question

---
