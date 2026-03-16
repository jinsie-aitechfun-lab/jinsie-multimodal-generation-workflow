from fastapi import FastAPI, HTTPException

from app.schemas.workflow import WorkflowRunRequest, WorkflowRunResponse
from app.services.runner import UnknownStepError, WorkflowRunner

app = FastAPI(title="jinsie-multimodal-generation-workflow", version="0.1.0")

_runner = WorkflowRunner()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(req: WorkflowRunRequest):
    try:
        return _runner.run(req)
    except UnknownStepError as e:
        raise HTTPException(status_code=400, detail=str(e))