# BACKUP_STRATEGY.md

## What to backup
- `~/.memoryfeed/memoryfeed.db`
- `~/.memoryfeed/lancedb/`
- `~/.memoryfeed/images/`
- `~/.memoryfeed/images_enc/`
- `~/.memoryfeed/keys/master.key` (if file-based key mode)

## Backup Frequency
- Daily incremental.
- Weekly full snapshot.
- Keep 30 days retention.

## Restore Procedure
1. Stop MemoryFeed.
2. Restore DB + vector + media + keys.
3. Start in `MEMORY_ENCRYPTION_MODE=compat`.
4. Verify via `/readyz` and sample retrieval.

## Disaster Drill
- Quarterly restore drill on separate machine.
- Verify search, timeline, and encrypted image fetch (`/api/images/{name}`).
