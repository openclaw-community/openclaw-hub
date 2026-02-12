#!/bin/bash
# Test AI Gateway routing to different providers

BASE_URL="http://localhost:8080"

echo "=== AI Gateway Provider Routing Test ==="
echo ""

echo "1. Testing Ollama (local, free):"
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:32b-instruct",
    "messages": [{"role": "user", "content": "Say hi"}],
    "max_tokens": 10
  }' | jq '.model, .cost_usd, .latency_ms'

echo ""
echo "2. Testing OpenAI routing (requires API key):"
echo "   Model: gpt-4o-mini → Should route to OpenAI"
echo ""

echo "3. Testing Anthropic routing (requires API key):"
echo "   Model: claude-sonnet → Should route to Anthropic"
echo ""

echo "4. Current available models:"
curl -s $BASE_URL/v1/models | jq
