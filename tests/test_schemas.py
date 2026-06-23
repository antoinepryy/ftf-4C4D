import pytest
from pydantic import ValidationError
from app.schemas import RunCreate


def test_runcreate_valid():
    rc = RunCreate(nbr_pts=100, step=10)
    assert rc.active_checkpoint is None


def test_runcreate_rejects_nonpositive():
    with pytest.raises(ValidationError):
        RunCreate(nbr_pts=0, step=10)
    with pytest.raises(ValidationError):
        RunCreate(nbr_pts=100, step=0)
