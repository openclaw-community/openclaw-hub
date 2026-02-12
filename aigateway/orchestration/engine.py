"""
Workflow execution engine
"""

import re
import time
from typing import Any, Dict, Optional
from .models import WorkflowDefinition, WorkflowExecution, WorkflowStep
from ..providers.base import CompletionRequest, Message
from ..providers.manager import ProviderManager
import structlog

logger = structlog.get_logger()


class WorkflowEngine:
    """Executes workflow definitions"""
    
    def __init__(self, provider_manager: ProviderManager, mcp_manager=None):
        self.provider_manager = provider_manager
        self.mcp_manager = mcp_manager
    
    def substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace ${variable} placeholders with actual values"""
        def replacer(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            # Navigate through nested variables
            value = variables
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return f"${{{var_path}}}"  # Keep placeholder if not found
            
            return str(value)
        
        return re.sub(r'\$\{([\w.]+)\}', replacer, template)
    
    async def execute_llm_step(
        self,
        step: WorkflowStep,
        variables: Dict[str, Any]
    ) -> str:
        """Execute an LLM completion step"""
        # Substitute variables in prompt
        prompt = self.substitute_variables(step.prompt, variables)
        
        # Create completion request
        request = CompletionRequest(
            model=step.model,
            messages=[Message(role="user", content=prompt)],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Execute via provider manager
        response = await self.provider_manager.complete(request)
        
        logger.info(
            "llm_step_complete",
            step_id=step.id,
            model=step.model,
            tokens=response.total_tokens,
            cost=response.cost_usd
        )
        
        return response.content
    
    async def execute_mcp_step(
        self,
        step: WorkflowStep,
        variables: Dict[str, Any]
    ) -> Any:
        """Execute an MCP tool step"""
        if not self.mcp_manager:
            raise ValueError("MCP manager not configured")
        
        # Substitute variables in parameters
        params = {}
        if step.params:
            for key, value in step.params.items():
                if isinstance(value, str):
                    params[key] = self.substitute_variables(value, variables)
                else:
                    params[key] = value
        
        # Execute tool
        result = await self.mcp_manager.call_tool(
            server_name=step.server,
            tool_name=step.tool,
            arguments=params
        )
        
        logger.info(
            "mcp_step_complete",
            step_id=step.id,
            server=step.server,
            tool=step.tool
        )
        
        return result
    
    async def execute_step(
        self,
        step: WorkflowStep,
        variables: Dict[str, Any]
    ) -> Any:
        """Execute a single workflow step"""
        logger.info("executing_step", step_id=step.id, step_type=step.type)
        
        if step.type == "llm":
            return await self.execute_llm_step(step, variables)
        elif step.type == "mcp_tool":
            return await self.execute_mcp_step(step, variables)
        else:
            raise ValueError(f"Unknown step type: {step.type}")
    
    async def execute(
        self,
        workflow: WorkflowDefinition,
        input_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a complete workflow"""
        start_time = time.time()
        
        # Initialize execution context
        execution = WorkflowExecution(
            workflow=workflow,
            variables={"input": input_vars}
        )
        
        logger.info(
            "workflow_starting",
            workflow=workflow.name,
            steps=len(workflow.steps)
        )
        
        # Track metrics
        total_tokens = 0
        total_cost = 0.0
        step_metrics = []
        
        try:
            # Execute each step sequentially
            for step in workflow.steps:
                step_start = time.time()
                
                # Execute step
                result = await self.execute_step(step, execution.variables)
                
                # Store result in variables
                execution.variables[step.output] = result
                
                step_latency = int((time.time() - step_start) * 1000)
                step_metrics.append({
                    "id": step.id,
                    "type": step.type,
                    "latency_ms": step_latency
                })
            
            # Mark as completed
            execution.completed = True
            
            # Extract final output
            final_output = execution.variables.get(workflow.output)
            
            total_latency = int((time.time() - start_time) * 1000)
            
            logger.info(
                "workflow_complete",
                workflow=workflow.name,
                total_latency_ms=total_latency,
                total_cost_usd=total_cost
            )
            
            return {
                "output": final_output,
                "metrics": {
                    "total_cost_usd": total_cost,
                    "total_tokens": total_tokens,
                    "latency_ms": total_latency,
                    "steps": step_metrics
                }
            }
        
        except Exception as e:
            logger.error(
                "workflow_failed",
                workflow=workflow.name,
                error=str(e),
                step=execution.current_step
            )
            raise
