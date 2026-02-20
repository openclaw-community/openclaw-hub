# Workflows

This directory contains YAML workflow definitions for the AI Gateway.

## Available Workflows

### 1. **summarize** - Text Summarization Pipeline
**Purpose:** Extracts key points then creates a concise summary  
**Steps:**
1. Extract key points (using local Qwen model)
2. Create 2-sentence summary from points

**Usage:**
```bash
curl -X POST http://localhost:8080/v1/workflow/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Your long text here..."
    }
  }'
```

**Cost:** $0 (uses local Ollama model)

---

### 2. **smart-analysis** - Adaptive Analysis
**Purpose:** Quick scan first, then detailed analysis  
**Steps:**
1. Quick complexity assessment
2. Appropriate level analysis based on complexity

**Usage:**
```bash
curl -X POST http://localhost:8080/v1/workflow/smart-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Text to analyze..."
    }
  }'
```

**Cost:** $0 (uses local Ollama model)

---

## Workflow Format

```yaml
name: workflow-name
description: What this workflow does

steps:
  - id: step1
    type: llm  # or mcp_tool
    model: qwen2.5:32b-instruct
    prompt: |
      Your prompt here.
      Use ${variable} for substitution.
      Access nested values: ${input.field}
    output: result_variable

  - id: step2
    type: llm
    model: claude-sonnet
    prompt: |
      Use results from previous step: ${result_variable}
    output: final_result

output: final_result  # Variable to return
```

## Variable Substitution

- `${input.field}` - Access input data
- `${step_output}` - Use output from previous step
- `${nested.path}` - Navigate nested objects

## Creating New Workflows

1. Create a `.yaml` file in this directory
2. Follow the format above
3. Restart the server (workflows are loaded on startup)
4. Test with: `curl http://localhost:8080/v1/workflows`

## Advanced Examples

### Multi-Model Workflow (Cost Optimization)
```yaml
steps:
  - id: draft
    type: llm
    model: qwen2.5:32b-instruct  # Free, local
    prompt: Create a draft...
    output: draft

  - id: polish
    type: llm
    model: claude-sonnet  # Paid, high quality
    prompt: Polish this draft: ${draft}
    output: final
```

This uses free local model for drafting, expensive cloud model only for final polish!
