# Security Policy and Threat Model

## Security Model

MemoryFeed is local-first: captured memories are stored on the local machine by default. Network egress is optional and only used when cloud AI providers are explicitly enabled.

## Protected Assets

- Captured posts/content text
- Images/thumbnails cached locally
- Embeddings and vector index data
- User metadata (tags, notes, starred state)
- Search queries and resurfacing context
- API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`)

## Trust Boundaries

- Browser extension (capture agent running on social domains)
- Local FastAPI server (`memoryfeed serve`)
- Optional Gemini/Groq cloud providers
- MCP clients (Claude/Cursor/other local/remote agent tools)
- Public web mode (`serve-web` on non-loopback host)

## Primary Risks

- Accidental public exposure of personal memory data
- Over-capture of unintended page content
- Prompt injection from captured social content
- Cloud-provider leakage of selected prompts/images
- Browser extension permission abuse
- MCP over-querying/exfiltration of memory excerpts

## Current Mitigations

- Local-first default storage in local SQLite + LanceDB
- Offline-only mode: `OFFLINE_ONLY=1` and `MEMORYFEED_AI_PROVIDER=none`
- Provider opt-in controls: `MEMORYFEED_AI_PROVIDER=none|gemini|groq|auto`
- Public bind guardrails:
  - `MEMORYFEED_PUBLIC_MODE` must be true for public bind
  - `MEMORYFEED_ADMIN_TOKEN` required for public bind via CLI
- Admin endpoint protection with Bearer token (`Authorization: Bearer <token>`)
- MCP safety controls:
  - bounded result counts (`MEMORYFEED_MCP_MAX_RESULTS`)
  - timeline disabled by default (`MEMORYFEED_MCP_ALLOW_TIMELINE=false`)
  - output redaction enabled by default (`MEMORYFEED_MCP_REDACT_OUTPUT=true`)
  - audit logging for MCP calls (timestamp, tool, query, result count)
- Prompt-injection risk scoring on capture (`prompt_risk_score`, `prompt_risk_reason`)
- Sensitive content classification on capture (`sensitivity_level`, `sensitivity_reasons`)
- Optional sensitive-data suppression:
  - hide from search (`MEMORY_HIDE_SENSITIVE_FROM_SEARCH=true`)
  - skip embedding/indexing (`MEMORY_SKIP_SENSITIVE_EMBEDDING=true`)
- MCP untrusted-content sanitization path for high prompt-risk records
- Extension host permissions scoped to explicit domains (no wildcard `https://*/*`)
- Export/delete controls:
  - explicit admin endpoints
  - reset requires `confirm=RESET`
- Rotating logs and request-level audit entries
- In-memory API rate limiter on `/api/*` endpoints (configurable window + quota)
- Queue resilience with retry + exponential backoff + dead-letter counters (vision/indexer)
- Provider circuit breakers for Gemini/Groq to prevent cascading external failures
- Readiness probe `/readyz` exposing queue health and provider breaker state

## Redaction Scope

When MCP redaction is enabled, obvious patterns are masked in outputs:

- Email addresses
- Phone-like numbers
- API-key-like strings
- Bearer tokens

Redaction is best-effort and pattern-based. It is not a formal DLP system.

## Storage Integrity Controls

- `memoryfeed verify` scans for malformed records, invalid canonical URLs, missing timestamps, broken references, duplicate fingerprints, missing embedding state, and schema-shape violations.
- `memoryfeed verify --repair` performs non-destructive repair only:
  - rebuild fingerprints
  - normalize canonical URLs
  - remove invalid cache references
  - recover invalid timestamps
- Repair mode does not silently delete user memories.

## Operational Guidance

- Keep default mode local (`127.0.0.1`) unless network access is necessary.
- Use long random `MEMORYFEED_ADMIN_TOKEN` in public mode.
- Prefer offline mode for sensitive workflows.
- Rotate/revoke cloud API keys if accidental exposure is suspected.
- Review logs in `~/.memoryfeed/logs/memoryfeed.log` during incident response.

## Reporting Security Issues

For responsible disclosure, open a private security report in your fork/org workflow and avoid posting sensitive details in public issues.
