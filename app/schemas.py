from pydantic import BaseModel, Field, ConfigDict


class RunCreate(BaseModel):
    nbr_pts: int = Field(gt=0)
    step: int = Field(gt=0)
    active_checkpoint: str | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    client_id: str
    nbr_pts: int
    step: int
    active_checkpoint: str | None
    status: str
    checkpoints: list[str]
    error: str | None


class ClientSummary(BaseModel):
    client_id: str
    total: int
    done: int
    failed: int
    running: int
    queued: int
