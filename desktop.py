"""PyInstaller entrypoint for the desktop build.

The frozen executable plays two roles, selected by the FTF_CHILD env marker:
- FTF_CHILD=stub → run one compute job (the worker re-invokes the exe this way,
  since a frozen binary can't be launched as `python -m stub.compute`).
- otherwise     → run the local single-process app (API + dashboard + worker).
"""
import os
import sys

if os.environ.get("FTF_CHILD") == "stub":
    from stub.compute import main as stub_main

    stub_main()
    sys.exit(0)

from app.local_main import main

if __name__ == "__main__":
    main()
