# FTF prototype — distributed compute

REST API → queue → workers → compute container → S3 (per client). Ships in two
deploy modes from one codebase:

- **cloud** (`DEPLOY_MODE=cloud`, default) — Celery/Redis queue, Postgres, separate
  workers. The full distributed stack (docker-compose). See *Run* below.
- **local** (`DEPLOY_MODE=local`) — single desktop process: the API, dashboard and
  an in-process thread-pool worker, with SQLite + a local S3. No Redis/Celery/
  Postgres/Docker. This is what a packaged Windows `.exe` runs. See *Local mode*.

`RUN_MODE` selects how the compute is launched: `docker` (sibling container, needs
the Docker socket) or `subprocess` (runs `python -m stub.compute` in a child
process — no socket, safe on shared hosts and in desktop mode).

## Run

```bash
cp .env.example .env
docker build -t stub-compute:latest stub/
docker compose up --build -d
```

API at http://localhost:8000, MinIO console at http://localhost:9001 (minioadmin/minioadmin).

## Try it

```bash
# launch a run
curl -X POST localhost:8000/clients/c1/runs -H 'content-type: application/json' \
  -d '{"nbr_pts": 1000, "step": 10}'

# poll status
curl localhost:8000/clients/c1/runs/<run_id>
```

## Local mode (single process, no Docker)

For running entirely on a client machine — compute and storage both local. Needs
only Python and a local S3 endpoint. A native `minio` binary can be auto-started
by pointing `FTF_MINIO_BIN` at it; otherwise bring your own local S3.

```bash
pip install -e .
# point at a local S3 (e.g. a native minio binary, or an existing one)
export FTF_MINIO_BIN=/path/to/minio          # optional: auto-start bundled minio
python -m app.local_main                      # serves http://127.0.0.1:8000/ and opens a browser
```

Defaults (overridable via env): `DEPLOY_MODE=local`, `RUN_MODE=subprocess`,
SQLite DB + MinIO data under the OS app-data dir (`%LOCALAPPDATA%\ftf` on Windows,
`~/.local/share/ftf` elsewhere), S3 at `http://127.0.0.1:9000`. `FTF_PORT` sets
the port; `FTF_OPEN_BROWSER=0` disables the browser launch.

This module is the entrypoint a PyInstaller-packaged Windows `.exe` runs, bundled
alongside `minio.exe` and the native compute binary — no Docker required.

## Tests

```bash
pip install -e ".[dev]"
pytest                 # unit tests (no stack needed)
FTF_E2E=1 pytest -m e2e  # end-to-end (cloud stack must be up)
```
