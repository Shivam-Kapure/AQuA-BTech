# AQUA Implementation Checkpoint

Last updated: 2026-09-21

## Resume Context

- Working branch: `codex/codebase-memory-guidance`
- Follow-up PR: [#3](https://github.com/maaaazin/AQuA-BTech/pull/3) — open
- Previous security/runtime PR: [#2](https://github.com/maaaazin/AQuA-BTech/pull/2) — merged
- Continue using the `codebase-memory` graph before manual repository searches. Re-index after substantial changes.
- Do not stage unrelated local changes in `.DS_Store` or `opencode.json`.

## Completed Capability

Authentication and ownership, signed tokens, SSRF/TLS hardening, route JWT forwarding, secret-safe Playwright subprocesses, configurable ZAP execution, OpenAPI/Postman import, normalized operations, deterministic API execution, assertions, redaction, dependent workflows, LLM case generation, API run history, passive API security scanning, persisted findings, and the initial frontend API workspace are implemented.

## Validation

```bash
cd backend && .venv/bin/pytest       # currently 27 passing
cd frontend && npm run lint
cd frontend && npm run build
```

## Immediate Next Tasks

1. Finish the API UI: parameter/body editors, authenticated workflow builder, run-detail/evidence view, and finding remediation states.
2. Complete API security coverage: BOLA/BFLA, schema abuse, rate-limit probes, and explicit active-probe worker policy.
3. Implement the shared durable run schema, status vocabulary, background worker/queue, cancellation, retries, and artifact retention.
4. Add frontend/API contract tests and CI gates.
5. Finish deployment configuration, health/readiness checks, observability, and backup documentation.

## Safety Notes

- Active or destructive API security probes must remain disabled unless explicitly authorized and isolated in a worker.
- Preserve owner scoping on every project/spec/run/finding query.
- Keep secrets out of generated scripts, persisted evidence, logs, and checkpoint files.
