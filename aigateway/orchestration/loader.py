"""
Workflow loader from YAML files
"""

import yaml
from pathlib import Path
from typing import Dict
from .models import WorkflowDefinition
import structlog

logger = structlog.get_logger()


class WorkflowLoader:
    """Loads and manages workflow definitions"""
    
    def __init__(self, workflows_dir: str = "./workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows: Dict[str, WorkflowDefinition] = {}
    
    def load_workflow(self, filepath: Path) -> WorkflowDefinition:
        """Load a single workflow from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        workflow = WorkflowDefinition(**data)
        logger.info("workflow_loaded", name=workflow.name, file=str(filepath))
        return workflow
    
    def load_all(self):
        """Load all workflows from directory"""
        if not self.workflows_dir.exists():
            logger.warning("workflows_dir_not_found", path=str(self.workflows_dir))
            return
        
        for filepath in self.workflows_dir.glob("*.yaml"):
            try:
                workflow = self.load_workflow(filepath)
                self.workflows[workflow.name] = workflow
            except Exception as e:
                logger.error("workflow_load_failed", file=str(filepath), error=str(e))
        
        logger.info("workflows_loaded", count=len(self.workflows))
    
    def get_workflow(self, name: str) -> WorkflowDefinition:
        """Get a workflow by name"""
        if name not in self.workflows:
            raise ValueError(f"Workflow '{name}' not found")
        return self.workflows[name]
    
    def list_workflows(self) -> list:
        """List all available workflow names"""
        return list(self.workflows.keys())
