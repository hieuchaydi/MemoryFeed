# PRODUCTION.md

## Deployment Modes
- Local-only strict: `OFFLINE_ONLY=1`, `MEMORYFEED_AI_PROVIDER=none`, `MEMORY_ENCRYPTION_MODE=strict`.
- Hybrid AI: enable providers with circuit breaker defaults.

## Startup Checklist
1. Set `MEMORYFEED_ADMIN_TOKEN`.
2. Set `MEMORYFEED_NAMESPACE` per deployment profile.
3. Enable encryption: `MEMORY_ENCRYPTION_MODE=compat` (then migrate, then `strict`).
4. Verify `/healthz`, `/readyz`, `/metrics`.

## Encryption Cutover
1. Start in `compat` mode.
2. Run `memoryfeed encrypt-migrate --limit 5000` until `updated=0`.
3. Restart with `MEMORY_ENCRYPTION_MODE=strict`.

## Operational Limits
- API rate limit defaults: 120 req/60s per client+path.
- Queue retries defaults: max 4 attempts with exponential backoff.

## Rollback
- Set `MEMORY_ENCRYPTION_MODE=off` only for emergency read access.
- Restore DB + media from backup if corruption is suspected.
