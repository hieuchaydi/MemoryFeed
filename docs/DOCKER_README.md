# Docker README

This guide covers running MemoryFeed in Docker with persistent local storage and strict local-first defaults.

## Quick Start

```bash
docker compose up -d --build
curl http://localhost:7749/healthz
```

PowerShell:

```powershell
docker compose up -d --build
curl.exe -i http://localhost:7749/healthz
```

Default service:
- Container: `memoryfeed`
- API: `http://localhost:7749`
- Data volume: `memoryfeed_data` mounted to `/data`

## What the Current Compose File Does

From `docker-compose.yml`:
- Builds from local `Dockerfile`
- Runs with:
  - `OFFLINE_ONLY=1`
  - `MEMORYFEED_AI_PROVIDER=none`
  - `MEMORYFEED_PUBLIC_MODE=true`
  - `MEMORYFEED_ADMIN_TOKEN=dev-local-token`
  - `MEMORYFEED_DATA_DIR=/data`

This means cloud AI is disabled by default, but API is exposed on host port `7749`.

## Recommended Local-Only Hardened Compose

For stricter local usage, use:

```yaml
services:
  memoryfeed:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: memoryfeed
    ports:
      - "127.0.0.1:7749:7749"
    environment:
      OFFLINE_ONLY: "1"
      MEMORYFEED_AI_PROVIDER: "none"
      MEMORYFEED_PUBLIC_MODE: "false"
      MEMORYFEED_ADMIN_TOKEN: "replace-with-strong-token"
      MEMORYFEED_DATA_DIR: "/data"
    volumes:
      - memoryfeed_data:/data
    restart: unless-stopped

volumes:
  memoryfeed_data:
```

Notes:
- `127.0.0.1:7749:7749` avoids LAN exposure.
- Keep `MEMORYFEED_PUBLIC_MODE=false` unless intentionally serving over network.

## Common Operations

Start:

```bash
docker compose up -d
```

Rebuild after code changes:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f memoryfeed
```

Stop:

```bash
docker compose down
```

Stop and remove volume (deletes all memory data):

```bash
docker compose down -v
```

## Backup and Restore

### Backup volume to local file

```bash
docker run --rm -v memoryfeed_data:/from -v ${PWD}:/to alpine sh -c "cd /from && tar czf /to/memoryfeed_data_backup.tgz ."
```

PowerShell:

```powershell
docker run --rm -v memoryfeed_data:/from -v ${PWD}:/to alpine sh -c "cd /from && tar czf /to/memoryfeed_data_backup.tgz ."
```

### Restore volume from backup

```bash
docker run --rm -v memoryfeed_data:/to -v ${PWD}:/from alpine sh -c "cd /to && tar xzf /from/memoryfeed_data_backup.tgz"
```

## Troubleshooting

Container name conflict:

```bash
docker rm -f memoryfeed
docker compose up -d
```

Docker daemon not running (Windows):
- Start Docker Desktop.
- Wait until engine is healthy.
- Re-run `docker compose up -d`.

Health check fails:
1. `docker compose logs --tail=200 memoryfeed`
2. Verify port usage on host (`7749` not occupied).
3. Confirm required env vars are set correctly.

## Security Notes

- Change `MEMORYFEED_ADMIN_TOKEN` before any shared-network use.
- Keep `OFFLINE_ONLY=1` and `MEMORYFEED_AI_PROVIDER=none` for strict privacy.
- Avoid `MEMORYFEED_PUBLIC_MODE=true` unless explicitly needed.
- Use host firewall rules if exposing beyond localhost.
