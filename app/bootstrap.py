from app.db import Base, engine
from app import models  # noqa: F401  (register tables)
from app import s3


def init() -> None:
    Base.metadata.create_all(engine)
    s3.ensure_bucket()
