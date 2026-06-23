# FTF prototype — distributed compute

Local prototype: REST API → queue → workers → Docker compute container → S3 (per client).

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

## Tests

```bash
pip install -e ".[dev]"
pytest                 # unit tests (no stack needed)
FTF_E2E=1 pytest -m e2e  # end-to-end (stack must be up)
```
