"""
Workflow models for orchestration
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


class WorkflowStep(BaseModel):
    """A single step in a workflow"""
    id: str = Field(..., description="Unique step identifier")
    type: Literal["llm", "mcp_tool"] = Field(..., description="Step type")
    
    # LLM-specific fields
    model: Optional[str] = Field(None, description="LLM model to use")
    prompt: Optional[str] = Field(None, description="Prompt template with ${variable} syntax")
    
    # MCP tool-specific fields
    server: Optional[str] = Field(None, description="MCP server name")
    tool: Optional[str] = Field(None, description="Tool name")
    params: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    
    # Common fields
    output: str = Field(..., description="Variable name to store result")


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    output: str = Field(..., description="Final output variable")


class WorkflowExecution(BaseModel):
    """Workflow execution context"""
    workflow: WorkflowDefinition
    variables: Dict[str, Any] = Field(default_factory=dict)
    current_step: int = 0
    completed: bool = False
    error: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Request to execute a workflow"""
    input: Dict[str, Any] = Field(..., description="Input variables")


class WorkflowResponse(BaseModel):
    """Response from workflow execution"""
    output: Any = Field(..., description="Final output value")
    metrics: Dict[str, Any] = Field(..., description="Execution metrics")
