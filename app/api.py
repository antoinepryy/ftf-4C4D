from uuid import uuid4
from fastapi import FastAPI, HTTPException
from app.db import get_session
from app import repository, s3
from app.schemas import RunCreate, RunOut
from app.tasks import run_compute

app = FastAPI(title="FTF prototype")


@app.post("/clients/{client_id}/runs", response_model=RunOut, status_code=201)
def create_run(client_id: str, payload: RunCreate):
    if payload.active_checkpoint and not s3.object_exists(payload.active_checkpoint):
        raise HTTPException(status_code=400, detail="active_checkpoint not found in S3")
    run_id = uuid4().hex
    with get_session() as session:
        run = repository.create_run(session, run_id, client_id, payload)
        out = RunOut.model_validate(run)
    run_compute.delay(run_id, client_id)
    return out


@app.get("/clients/{client_id}/runs/{run_id}", response_model=RunOut)
def get_run(client_id: str, run_id: str):
    with get_session() as session:
        run = repository.get_run(session, client_id, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunOut.model_validate(run)


@app.get("/clients/{client_id}/runs", response_model=list[RunOut])
def list_runs(client_id: str):
    with get_session() as session:
        return [RunOut.model_validate(r) for r in repository.list_runs(session, client_id)]
