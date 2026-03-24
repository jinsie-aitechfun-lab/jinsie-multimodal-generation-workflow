from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.workflow import WorkflowRunRequest, WorkflowRunResponse
from app.services.runner import UnknownStepError, WorkflowRunner

app = FastAPI(title="jinsie-multimodal-generation-workflow", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_runner = WorkflowRunner()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/samples/summary")
def get_samples_summary():
    return _runner.get_samples_summary()


@app.get("/v1/samples/kling/real")
def get_real_kling_samples():
    return _runner.get_real_kling_samples_manifest()


@app.post("/v1/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(req: WorkflowRunRequest):
    try:
        return _runner.run(req)
    except UnknownStepError as e:
        raise HTTPException(status_code=400, detail=str(e))