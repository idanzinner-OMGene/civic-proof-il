# Docker — local development stack

Compose stack for the civic-proof-il political verifier. Brings up PostgreSQL,
Neo4j, OpenSearch, MinIO, the one-shot `migrator`, the API, and the worker.

## Running

From the repo root:

```bash
make up
# or, equivalently:
docker compose -f infra/docker/docker-compose.yml up -d --build --wait
```

The override file `docker-compose.override.yml` is picked up automatically by
`docker compose` when run from `infra/docker/`, and mirrored by `make up`.

## Prerequisites

- A populated `.env` file at the repo root. Copy the template:
  ```bash
  cp .env.example .env
  ```
- Docker Engine 24+ with the Compose V2 plugin.

## Endpoints (host ports)

- API:             http://localhost:8000 (try `/healthz`, `/readyz`)
- Neo4j browser:   http://localhost:7474 (bolt: `bolt://localhost:7687`)
- OpenSearch:      http://localhost:9200
- MinIO S3 API:    http://localhost:9000
- MinIO console:   http://localhost:9001
- PostgreSQL:      `localhost:5432`

## Common pitfalls

- **Linux + OpenSearch:** raise the mmap limit before `up`:
  ```bash
  sudo sysctl -w vm.max_map_count=262144
  ```
  To persist, add `vm.max_map_count=262144` to `/etc/sysctl.conf`.
- **macOS / Docker Desktop:** allocate at least 6 GB of memory to the VM,
  otherwise OpenSearch + Neo4j will OOM.
- **First boot of Neo4j/OpenSearch is slow.** Healthchecks use generous
  `start_period` values; `make up --wait` may take 60–90 s on a cold start.
