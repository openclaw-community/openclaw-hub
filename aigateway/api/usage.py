"""Usage documentation endpoint for AI agents."""
from fastapi import APIRouter

router = APIRouter(prefix="/v1")


@router.get("/usage")
async def get_usage_instructions():
    """
    Get usage instructions for AI agents.
    
    Returns comprehensive documentation on how to discover and use
    all Hub capabilities.
    """
    return {
        "name": "OpenClaw Hub",
        "version": "1.2.0",
        "description": "AI Gateway for multi-LLM orchestration, image generation, GitHub, Instagram, and more",
        "documentation": {
            "interactive": "http://127.0.0.1:8080/docs",
            "openapi": "http://127.0.0.1:8080/openapi.json",
            "redoc": "http://127.0.0.1:8080/redoc"
        },
        "getting_started": {
            "step_1": "Check health: GET /health",
            "step_2": "Discover capabilities: GET /v1/models, /v1/workflows, /v1/github/capabilities, etc.",
            "step_3": "Review OpenAPI docs: http://127.0.0.1:8080/docs",
            "step_4": "Make API calls to any endpoint"
        },
        "capabilities": {
            "llm_routing": {
                "description": "Route LLM requests to 18 models across 3 providers",
                "endpoint": "POST /v1/chat/completions",
                "discover": "GET /v1/models",
                "providers": ["ollama", "openai", "anthropic"],
                "cost_optimization": "Automatic routing saves 97% vs always using premium models"
            },
            "image_generation": {
                "description": "Generate images via DALL-E 2/3",
                "endpoint": "POST /v1/images/generations",
                "models": ["dall-e-2", "dall-e-3"],
                "max_resolution": "1792x1024 (HD)"
            },
            "instagram": {
                "description": "Post images/videos to Instagram via Late.dev",
                "discover": "GET /v1/social/capabilities",
                "endpoints": {
                    "post": "POST /v1/social/instagram/post",
                    "upload": "POST /v1/social/instagram/upload"
                },
                "supports": ["single images", "carousels (10 max)", "videos", "scheduled posts"]
            },
            "github": {
                "description": "Manage GitHub repos, issues, PRs, and search",
                "discover": "GET /v1/github/capabilities",
                "operations": [
                    "get_user",
                    "list_repos",
                    "get_repo",
                    "list_issues",
                    "create_issue",
                    "update_issue",
                    "list_prs",
                    "search_code",
                    "search_issues"
                ],
                "rate_limits": {
                    "standard": "5000 requests/hour",
                    "search": "30 requests/minute"
                }
            },
            "workflows": {
                "description": "Multi-step orchestration pipelines",
                "discover": "GET /v1/workflows",
                "execute": "POST /v1/workflow/{name}",
                "available": ["web-research", "smart-analysis", "summarize"]
            },
            "mcp": {
                "description": "Model Context Protocol - connect external tool servers",
                "endpoints": {
                    "register": "POST /v1/mcp/servers",
                    "list": "GET /v1/mcp/servers",
                    "tools": "GET /v1/mcp/servers/{name}/tools"
                }
            }
        },
        "authentication": {
            "api_keys": "Configured via .env file (GITHUB_TOKEN, OPENAI_API_KEY, etc.)",
            "note": "Hub handles all authentication - callers don't need API keys"
        },
        "discovery_pattern": {
            "description": "All capabilities expose discovery endpoints",
            "examples": [
                "GET /v1/models - List LLM models",
                "GET /v1/workflows - List workflows",
                "GET /v1/github/capabilities - GitHub operations",
                "GET /v1/social/capabilities - Social media operations",
                "GET /v1/videos/capabilities - Video generation status"
            ],
            "benefit": "AI agents can dynamically discover what's available without hardcoding"
        },
        "best_practices": {
            "for_ai_agents": [
                "Start by calling GET /v1/usage (this endpoint)",
                "Check capability endpoints before using features",
                "Review OpenAPI docs for request/response schemas",
                "Use Swagger UI for testing: http://127.0.0.1:8080/docs",
                "All endpoints return structured JSON with clear error messages"
            ]
        },
        "examples": {
            "chat_completion": {
                "endpoint": "POST /v1/chat/completions",
                "body": {
                    "model": "qwen2.5:32b-instruct",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "max_tokens": 100
                }
            },
            "generate_image": {
                "endpoint": "POST /v1/images/generations",
                "body": {
                    "prompt": "A robot crab building infrastructure",
                    "model": "dall-e-3",
                    "size": "1792x1024",
                    "quality": "hd"
                }
            },
            "create_github_issue": {
                "endpoint": "POST /v1/github/repos/{owner}/{repo}/issues",
                "body": {
                    "owner": "openclaw-community",
                    "repo": "openclaw-hub",
                    "title": "Feature request",
                    "body": "Description here",
                    "labels": ["enhancement"]
                }
            }
        },
        "support": {
            "github": "https://github.com/openclaw-community/openclaw-hub",
            "issues": "https://github.com/openclaw-community/openclaw-hub/issues",
            "documentation": "See docs/ folder in repository"
        }
    }
