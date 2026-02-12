"""
Workflow API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from ..orchestration.models import WorkflowRequest, WorkflowResponse
from ..orchestration.engine import WorkflowEngine
from ..orchestration.loader import WorkflowLoader
import structlog

logger = structlog.get_logger()
router = APIRouter()


def get_workflow_engine():
    """Get workflow engine from app state"""
    from ..main import workflow_engine
    if workflow_engine is None:
        raise HTTPException(status_code=503, detail="Workflow engine not initialized")
    return workflow_engine


def get_workflow_loader():
    """Get workflow loader from app state"""
    from ..main import workflow_loader
    if workflow_loader is None:
        raise HTTPException(status_code=503, detail="Workflow loader not initialized")
    return workflow_loader


@router.post("/v1/workflow/{name}", response_model=WorkflowResponse)
async def execute_workflow(
    name: str,
    request: WorkflowRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
    loader: WorkflowLoader = Depends(get_workflow_loader)
) -> WorkflowResponse:
    """Execute a workflow by name"""
    try:
        # Get workflow definition
        workflow = loader.get_workflow(name)
        
        # Execute workflow
        result = await engine.execute(workflow, request.input)
        
        return WorkflowResponse(**result)
    
    except ValueError as e:
        logger.error("workflow_not_found", name=name)
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error("workflow_execution_failed", name=name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/workflows")
async def list_workflows(loader: WorkflowLoader = Depends(get_workflow_loader)):
    """List all available workflows"""
    workflows = loader.list_workflows()
    return {"workflows": workflows}
