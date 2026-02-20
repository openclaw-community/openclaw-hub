# AI Middleware Platform - MVP Plan

## Vision
Build a MuleSoft-like ESB specifically for AI/LLM orchestration - a unified control plane for multi-model workflows with MCP (Model Context Protocol) integration.

## Problem Statement
Current AI integration challenges:
- **Vendor lock-in**: Switching between OpenAI, Anthropic, local models requires code changes
- **No unified workflow**: Each LLM interaction is isolated, no orchestration
- **Cost opacity**: No visibility into per-task, per-model spend
- **Context fragmentation**: MCP servers exist but lack unified orchestration
- **Manual routing**: Developers hardcode model selection logic

## Solution: AI Gateway + Orchestrator
A lightweight middleware layer that:
1. **Abstracts providers** - unified API for OpenAI, Anthropic, Ollama, etc.
2. **Routes intelligently** - send requests to optimal model based on cost/latency/quality
3. **Tracks everything** - cost, tokens, latency per request/workflow
4. **Orchestrates workflows** - chain multiple LLM calls, integrate MCP tools
5. **Manages context** - MCP server discovery, capability routing

---

## MVP Scope (Phase 1)

### Core Features
1. **Gateway API**
   - Single REST endpoint: `/v1/chat/completions` (OpenAI-compatible)
   - Provider abstraction (OpenAI, Anthropic, Ollama)
   - Request routing based on simple rules

2. **Cost Tracking**
   - Log every request: model, tokens, cost, latency
   - Simple dashboard: daily spend, tokens by model
   - CSV export for analysis

3. **Basic Orchestration**
   - Sequential workflows: chain 2+ LLM calls
   - Variable passing between steps
   - Conditional branching (if/then routing)

4. **MCP Integration (Basic)**
   - Connect to local MCP servers
   - Expose available tools to LLM workflows
   - Execute tool calls and return results

### Out of Scope (Phase 1)
- UI/visual workflow builder (config files only)
- Advanced routing (A/B testing, quality scoring)
- Multi-tenancy / auth (single-user for MVP)
- Caching layer
- Streaming responses
- Load balancing across multiple instances

---

## Architecture

### Stack
- **Language**: Python 3.12 (already installed, fast development)
- **Framework**: FastAPI (async, OpenAPI docs, production-ready)
- **Storage**: SQLite (simple, file-based, no external DB needed)
- **Config**: YAML files (human-readable workflows)
- **MCP**: Python MCP SDK

### Components

```
┌─────────────────────────────────────────┐
│          Client Application             │
│   (OpenClaw, scripts, notebooks)        │
└─────────────┬───────────────────────────┘
              │ HTTP POST /v1/chat/completions
              ↓
┌─────────────────────────────────────────┐
│         AI Middleware Gateway           │
│  ┌─────────────────────────────────┐   │
│  │  FastAPI Router                 │   │
│  │  - Auth (optional)              │   │
│  │  - Request validation           │   │
│  └──────────┬──────────────────────┘   │
│             ↓                           │
│  ┌─────────────────────────────────┐   │
│  │  Orchestration Engine           │   │
│  │  - Workflow parser (YAML)       │   │
│  │  - Step executor                │   │
│  │  - Variable context             │   │
│  └──────────┬──────────────────────┘   │
│             ↓                           │
│  ┌─────────────────────────────────┐   │
│  │  Provider Manager               │   │
│  │  - OpenAI client                │   │
│  │  - Anthropic client             │   │
│  │  - Ollama client                │   │
│  │  - Cost calculator              │   │
│  └──────────┬──────────────────────┘   │
│             ↓                           │
│  ┌─────────────────────────────────┐   │
│  │  MCP Manager                    │   │
│  │  - Server discovery             │   │
│  │  - Tool execution               │   │
│  │  - Result formatting            │   │
│  └─────────────────────────────────┘   │
│             ↓                           │
│  ┌─────────────────────────────────┐   │
│  │  Metrics & Logging              │   │
│  │  - SQLite logs                  │   │
│  │  - Cost tracking                │   │
│  │  - Performance metrics          │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
              │
              ↓
    ┌──────────────────┐
    │ External LLM APIs│
    │ & MCP Servers    │
    └──────────────────┘
```

### Data Model (SQLite)

**Table: requests**
```sql
CREATE TABLE requests (
  id TEXT PRIMARY KEY,
  timestamp DATETIME,
  workflow_name TEXT,
  model TEXT,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  success BOOLEAN,
  error TEXT
);
```

**Table: workflows**
```sql
CREATE TABLE workflows (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE,
  config_yaml TEXT,
  created_at DATETIME,
  updated_at DATETIME
);
```

---

## MVP Workflow Example

**Use Case**: Research assistant that:
1. Searches web for topic (MCP tool)
2. Summarizes results (cheap fast model)
3. Writes detailed report (premium model)

**Workflow Config** (`examples/research.yaml`):
```yaml
name: research-assistant
description: Search web, summarize, write report

steps:
  - id: search
    type: mcp_tool
    server: brave-search
    tool: web_search
    params:
      query: ${input.topic}
      count: 5
    output: search_results

  - id: summarize
    type: llm
    model: local  # Ollama Qwen (free)
    prompt: |
      Summarize these search results:
      ${search_results}
    output: summary

  - id: report
    type: llm
    model: claude-sonnet-4-5  # Premium for final output
    prompt: |
      Write a detailed 3-paragraph report on ${input.topic}.
      Use this summary as foundation:
      ${summary}
    output: final_report

output: ${final_report}
```

**API Call**:
```bash
curl -X POST http://localhost:8080/v1/workflow/research-assistant \
  -H "Content-Type: application/json" \
  -d '{"input": {"topic": "AI middleware patterns"}}'
```

**Response**:
```json
{
  "output": "AI middleware patterns encompass...",
  "metrics": {
    "total_cost_usd": 0.0042,
    "total_tokens": 1247,
    "latency_ms": 3421,
    "steps": [
      {"id": "search", "cost": 0, "latency_ms": 842},
      {"id": "summarize", "cost": 0, "latency_ms": 1203},
      {"id": "report", "cost": 0.0042, "latency_ms": 1376}
    ]
  }
}
```

---

## Implementation Plan

### Week 1: Foundation
- [x] Project planning (this document)
- [ ] Set up Python project structure
- [ ] FastAPI skeleton + health endpoint
- [ ] SQLite schema + migrations
- [ ] Provider abstraction layer (OpenAI client wrapper)

### Week 2: Core Gateway
- [ ] OpenAI provider implementation
- [ ] Anthropic provider implementation
- [ ] Ollama provider implementation
- [ ] Cost calculation logic
- [ ] Request logging to SQLite

### Week 3: Orchestration
- [ ] YAML workflow parser
- [ ] Step executor (sequential only)
- [ ] Variable substitution
- [ ] Workflow API endpoint

### Week 4: MCP Integration
- [ ] MCP SDK integration
- [ ] Server discovery
- [ ] Tool execution in workflows
- [ ] Error handling

### Week 5: Analytics & Polish
- [ ] Simple web dashboard (FastAPI + HTML/JS)
- [ ] CSV export endpoint
- [ ] Documentation
- [ ] Testing with real workflows

---

## Success Metrics

**Must Have (MVP Complete)**:
- ✅ Can route requests to 3+ providers (OpenAI, Anthropic, Ollama)
- ✅ Can execute 3-step workflow with MCP tool
- ✅ Accurately tracks cost per request
- ✅ Dashboard shows daily spend breakdown

**Nice to Have**:
- ⭐ Sub-100ms routing overhead
- ⭐ OpenClaw integration (replace direct Anthropic calls)
- ⭐ 5+ example workflows for common tasks

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP SDK changes | High | Pin version, abstract interface |
| Provider API changes | Medium | Version client libraries, test suite |
| SQLite performance | Low | Sufficient for MVP, plan Postgres migration |
| Scope creep | High | Strict MVP feature freeze, backlog for v2 |

---

## Next Steps

1. **Create project structure** - folders, dependencies, git repo
2. **Scaffold FastAPI app** - basic server, health check
3. **Implement first provider** - Start with Ollama (local, no API keys)
4. **Test simple proxy** - Single LLM call through gateway

---

**Project Name**: `aigateway`  
**Repository**: `/Users/openclaw/.openclaw/workspace/ai-middleware/`  
**Port**: 8080 (avoid conflict with previous 8000)  
**Started**: 2026-02-11  
**Target MVP**: 2026-03-11 (4 weeks)
