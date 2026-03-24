from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/samples/summary")
def get_samples_summary():
    return _runner.get_samples_summary()


@app.get("/v1/samples/kling/real")
def get_real_kling_samples():
    return _runner.get_real_kling_samples_manifest()


@app.get("/v1/samples/kling/real/{sample_id}")
def get_real_kling_sample(sample_id: str):
    sample = _runner.get_real_kling_sample_by_id(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"sample not found: {sample_id}")
    return sample


@app.post("/v1/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(req: WorkflowRunRequest):
    try:
        return _runner.run(req)
    except UnknownStepError as e:
        raise HTTPException(status_code=400, detail=str(e))