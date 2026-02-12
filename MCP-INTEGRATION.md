# MCP Integration Guide

## Overview

The AI Gateway now supports Model Context Protocol (MCP) servers, allowing workflows to use external tools like web search, file access, APIs, and more.

## What is MCP?

MCP (Model Context Protocol) is an open protocol that lets AI models use external tools and data sources. Think of it as a standardized way for AI assistants to:

- Search the web
- Read/write files
- Query databases
- Call APIs
- Access system information
- And much more...

## Architecture

```
Workflow Step → MCP Manager → MCP Server → Tool Execution → Result
                     ↓
              (manages multiple servers)
```

## Quick Start

### 1. Connect an MCP Server

```bash
curl -X POST http://localhost:8080/v1/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fetch",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-fetch"]
  }'
```

### 2. List Available Tools

```bash
curl http://localhost:8080/v1/mcp/servers/fetch/tools
```

### 3. Use in Workflows

```yaml
name: web-research
description: Fetch and analyze web content

steps:
  - id: fetch
    type: mcp_tool
    server: fetch       # Server name
    tool: fetch_url     # Tool name
    params:
      url: ${input.url} # Parameters
    output: content

  - id: analyze
    type: llm
    model: qwen2.5:32b-instruct
    prompt: |
      Analyze: ${content}
    output: analysis

output: analysis
```

### 4. Execute

```bash
curl -X POST http://localhost:8080/v1/workflow/web-research \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "url": "https://example.com"
    }
  }'
```

## Available MCP Servers

### Official Servers

1. **@modelcontextprotocol/server-fetch**
   - Fetch web content
   - Extract readable text
   - Tools: `fetch_url`

2. **@modelcontextprotocol/server-filesystem**
   - Read/write files
   - List directories
   - Tools: `read_file`, `write_file`, `list_directory`

3. **@modelcontextprotocol/server-brave-search**
   - Web search via Brave API
   - Tools: `search`, `local_search`

4. **@modelcontextprotocol/server-github**
   - GitHub API access
   - Tools: `search_repos`, `get_file`, `create_issue`

### Adding Custom Servers

You can create your own MCP servers or use community servers. Any MCP-compatible server works!

## API Reference

### POST /v1/mcp/servers
Connect to an MCP server

**Request:**
```json
{
  "name": "server-name",
  "command": "command-to-run",
  "args": ["arg1", "arg2"],
  "env": {"KEY": "value"}
}
```

**Response:**
```json
{
  "status": "connected",
  "server": "server-name"
}
```

### GET /v1/mcp/servers
List connected servers

**Response:**
```json
{
  "servers": ["fetch", "filesystem"]
}
```

### GET /v1/mcp/servers/{name}/tools
List tools from a server

**Response:**
```json
{
  "server": "fetch",
  "tools": [
    {
      "name": "fetch_url",
      "description": "Fetch content from a URL",
      "input_schema": {...}
    }
  ]
}
```

## Workflow Step Types

### MCP Tool Step

```yaml
- id: step_name
  type: mcp_tool
  server: server_name     # Required: which MCP server
  tool: tool_name         # Required: which tool to call
  params:                 # Required: tool parameters
    param1: ${input.var}  # Variable substitution works!
    param2: "static value"
  output: result_var      # Required: where to store result
```

### LLM Step (for comparison)

```yaml
- id: step_name
  type: llm
  model: qwen2.5:32b-instruct
  prompt: "Your prompt here"
  output: result_var
```

## Variable Substitution

MCP tool parameters support the same variable substitution as prompts:

```yaml
params:
  url: ${input.url}              # Simple variable
  query: ${user.search_term}     # Nested path
  limit: 10                      # Static value
  context: ${previous_step}      # Output from previous step
```

## Example Workflows

### Web Research Pipeline

```yaml
name: research-pipeline
description: Search, fetch, and analyze web content

steps:
  - id: search
    type: mcp_tool
    server: brave-search
    tool: search
    params:
      query: ${input.topic}
      count: 5
    output: search_results

  - id: fetch_top_result
    type: mcp_tool
    server: fetch
    tool: fetch_url
    params:
      url: ${search_results.top.url}
    output: article

  - id: analyze
    type: llm
    model: claude-sonnet
    prompt: |
      Based on this article, write a summary of ${input.topic}:
      ${article}
    output: summary

output: summary
```

### File Processing

```yaml
name: document-processor
description: Read file, process with AI, write result

steps:
  - id: read
    type: mcp_tool
    server: filesystem
    tool: read_file
    params:
      path: ${input.filepath}
    output: content

  - id: process
    type: llm
    model: qwen2.5:32b-instruct
    prompt: |
      Extract key points from:
      ${content}
    output: summary

  - id: write
    type: mcp_tool
    server: filesystem
    tool: write_file
    params:
      path: ${input.output_path}
      content: ${summary}
    output: write_status

output: write_status
```

## Error Handling

MCP tool failures will:
1. Stop workflow execution
2. Return error details
3. Log to console with structured logging

```json
{
  "error": "Tool execution failed",
  "details": "Server 'fetch' not connected"
}
```

## Best Practices

### 1. Cost Optimization
```yaml
# Bad: Use expensive model for everything
- id: analyze
  type: llm
  model: gpt-4  # $$$

# Good: Use MCP tools + cheap local model
- id: fetch
  type: mcp_tool  # Free!
  server: fetch

- id: analyze
  type: llm
  model: qwen2.5:32b-instruct  # Free!
```

### 2. Server Naming
Use descriptive server names:
- ✅ `brave-search`, `github-api`, `local-files`
- ❌ `server1`, `mcp`, `tool`

### 3. Error Messages
MCP tools should validate inputs and return clear errors:
```yaml
params:
  url: ${input.url}  # Make sure input.url exists!
```

### 4. Caching
For repeated tool calls, consider storing results in workflow variables:
```yaml
- id: fetch_once
  type: mcp_tool
  server: fetch
  tool: fetch_url
  params:
    url: "https://example.com"
  output: cached_content  # Reuse in multiple steps
```

## Security Considerations

1. **Sandboxing**: MCP servers run in separate processes
2. **Validation**: Input parameters are validated before execution
3. **Permissions**: Filesystem tools respect system permissions
4. **API Keys**: Use environment variables for sensitive data

## Troubleshooting

### Server Won't Connect
```bash
# Check if command is available
npx -y @modelcontextprotocol/server-fetch --version

# Check logs
tail -f logs/mcp-manager.log
```

### Tool Not Found
```bash
# List available tools
curl http://localhost:8080/v1/mcp/servers/SERVER_NAME/tools
```

### Variable Substitution Issues
```yaml
# Incorrect:
params:
  url: $input.url  # Missing curly braces

# Correct:
params:
  url: ${input.url}
```

## Next Steps

1. **Install MCP Servers**
   ```bash
   npm install -g @modelcontextprotocol/server-fetch
   npm install -g @modelcontextprotocol/server-filesystem
   ```

2. **Create Workflows**
   - Start with simple single-tool workflows
   - Combine tools with LLMs for powerful pipelines
   - Test with sample data before production

3. **Monitor Performance**
   - Check execution metrics
   - Track tool usage
   - Optimize expensive tools

## Community

- **Find MCP Servers**: https://github.com/modelcontextprotocol
- **Build Your Own**: https://modelcontextprotocol.io/docs
- **Share Workflows**: Contribute examples to the community!

## Examples Repository

See `/workflows/` for more examples:
- `web-research.yaml` - Fetch and analyze web content
- `summarize.yaml` - Basic text processing
- `smart-analysis.yaml` - Adaptive complexity routing

---

**Status**: MCP integration complete! ✅  
**Next**: Build advanced workflows combining LLMs + tools
