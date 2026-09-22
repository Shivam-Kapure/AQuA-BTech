# AQUA Implementation Checkpoint

Last updated: 2026-09-22

## Resume Context

- Working branch: `main` (local checkout; ahead of `origin/main`)
- Follow-up PR: [#3](https://github.com/maaaazin/AQuA-BTech/pull/3) — open
- Previous security/runtime PR: [#2](https://github.com/maaaazin/AQuA-BTech/pull/2) — merged
- Continue using the `codebase-memory` graph before manual repository searches. Re-index after substantial changes.
- Do not stage unrelated local changes in `.DS_Store` or `opencode.json`.

## Completed Capability

Authentication and ownership, signed tokens, SSRF/TLS hardening, route JWT forwarding, secret-safe Playwright subprocesses, configurable ZAP execution, OpenAPI/Postman import, normalized operations, deterministic API execution, assertions, redaction, dependent workflows, LLM case generation, API run history, passive API security scanning, persisted findings, and the initial frontend API workspace are implemented.

## Validation

```bash
cd backend && .venv/bin/pytest       # currently 43 passing
cd frontend && npm run lint
cd frontend && npm run build
```

## Immediate Next Tasks

1. API UI slice is complete: authenticated request fields, workflow extraction/editing, and request assertions are implemented alongside parameter/body editors, workflow execution, run-detail/evidence, and persisted finding remediation states.
2. Complete API security coverage: BOLA/BFLA, schema abuse, rate-limit probes, and explicit active-probe worker policy.
3. Implement the shared durable run schema, status vocabulary, background worker/queue, cancellation, retries, and artifact retention.
4. Add frontend/API contract tests and CI gates.
5. Finish deployment configuration, health/readiness checks, observability, and backup documentation.

## Safety Notes

- Active or destructive API security probes must remain disabled unless explicitly authorized and isolated in a worker.
- Preserve owner scoping on every project/spec/run/finding query.
- Keep secrets out of generated scripts, persisted evidence, logs, and checkpoint files.

## 2026-09-22 Progress

- Completed the API workspace UI slice in `frontend/src/pages/ApiTestingPage.jsx`: saved-spec loading, operation selection, path/query/header/body editing, workflow assembly/execution, run evidence, and finding remediation controls.
- Added owner-scoped `PATCH /api/v1/api-specs/findings/{finding_id}` with `open`/`accepted`/`fixed` remediation states and optional notes.
- Validation: backend `pytest` 27 passed; frontend `npm run lint` passed; frontend `npm run build` passed (existing chunk-size warning only).
- Preserve the unrelated local `.DS_Store` deletion and untracked `opencode.json`; do not stage them.

## 2026-09-22 Continued Progress

- Added per-request Bearer/Basic authentication controls to the API workspace.
- Added configurable status, header, JSON-field, content-type, and response-time assertions.
- Added workflow step extraction editors for passing JSON response values into dependent requests.
- Validation remains green: backend `pytest` 27 passed, frontend lint passed, and frontend build passed with only the existing chunk-size warning.

## 2026-09-22 Security Progress

- Added passive API security candidate findings for object-scoped routes (BOLA), privileged/state-changing routes (BFLA), and missing or permissive request schemas (schema abuse).
- Added regression coverage; backend validation is now 28 passing tests.
- Active BOLA/BFLA and rate-limit probes remain disabled until the isolated worker, authorization policy, and durable security-run model are implemented.

## 2026-09-22 Run Foundation Progress

- Added shared `RunStatus` vocabulary (`queued`, `running`, `waiting`, `passed`, `failed`, `warning`, `cancelled`).
- Added `TestRunRecord` and `ArtifactMetadata` models plus an owner-scoped `TestRunRepository` with run and correlation indexes.
- Extended API run records with status, duration, runner version, generation mode, evidence, failure details, and correlation IDs; API execution now persists these fields without storing auth tokens.
- Added three shared-run model tests; full backend validation is now 31 passing tests.
- Added startup index setup for API specs, API runs, API findings, and shared test runs, including owner-scoped correlation uniqueness and spec checksum uniqueness.

## 2026-09-22 Worker Progress

- Added a process-local `AsyncJobQueue` boundary with queued/running/passed/failed/cancelled transitions, bounded timeouts, retry counts, and cancellation.
- Added worker regression tests; full backend validation is now 34 passing tests.
- The synchronous API execution contract remains unchanged. Next step is wiring queued API/security executions to persisted runs and exposing status/cancel endpoints.

## 2026-09-22 Async API Progress

- Added `POST /api/v1/api-specs/execute-async` to create an owner-scoped queued API run and dispatch it through `AsyncJobQueue`.
- Added `GET /api/v1/api-specs/jobs/{job_id}` for job/run status and `POST /api/v1/api-specs/jobs/{job_id}/cancel` for cancellation.
- Worker completion, failure, timeout, retry, and cancellation states update the persisted API run using its correlation ID.

## 2026-09-22 Async Security Progress

- Added `POST /api/v1/api-specs/security-scan-async` for queued passive security scans; active scans still fail closed with an isolated-worker policy error.
- The API workspace now polls security jobs, displays attempts/status, refreshes findings, and supports cancellation.
- Queue warning propagation is covered; full validation is now 35 backend tests passing, frontend lint/build passing.

## 2026-09-22 Extended Session Progress

- Added artifact retention configuration, owner-scoped `ArtifactRepository`, TTL indexing, size enforcement, expiry calculation, and explicit expired-artifact cleanup.
- API execution now uses the async queue in the frontend with shared polling/cancellation UX; security scans use the same lifecycle.
- Added `/health/live` and MongoDB-backed `/health/ready` endpoints plus integration coverage.
- Updated `.env.example` and README health-check documentation.
- Latest validation: backend `pytest` 38 passing; frontend lint/build passing.

## 2026-09-22 CI Progress

- Added `.github/workflows/ci.yml` running locked backend tests plus frontend install, lint, and production build on pushes and pull requests.

## 2026-09-22 Contract and Deployment Progress

- Replaced the placeholder integration test with route contracts for auth enforcement, authenticated OpenAPI parsing, active-scan fail-closed behavior, register/login, liveness, and readiness.
- Added backend/frontend Dockerfiles, root `docker-compose.yml` for MongoDB/API/UI, an opt-in ZAP profile, and `docs/DEPLOYMENT.md`.
- Documented that the current queue is process-local and must not be horizontally scaled until a shared broker/worker is introduced.
- Latest validation: backend `pytest` 41 passing; frontend lint/build passing; Compose configuration and diff checks passing with an explicit placeholder secret.

## 2026-09-22 SSRF and Finding Lifecycle Progress

- Added explicit one-hop OpenAPI import redirect validation: redirects remain disabled by default and a returned `Location` is resolved and revalidated before it is followed.
- API security findings now receive stable owner/project-scoped fingerprints; subsequent matching scans increment an occurrence count and refresh `last_seen_at` instead of creating duplicate records. Finding records retain first/last-seen history and remediation state.
- Finding severity is now validated as `low`, `medium`, `high`, or `critical` and assigned consistently from the passive-check category.
- Marked the completed API-operation-driven passive security coverage tasks in `tasks.md`.
- Latest backend validation: `pytest` 43 passed. DNS-rebinding-safe outbound connection pinning, isolated active probes/ZAP, a broker-backed worker, and the remaining review decisions remain intentionally open.

## 2026-09-22 Database Integrity Progress

- Added owner-scoped unique project-name indexes and per-project unique logical-ID indexes for UI and security test cases, with startup creation for the stable projects collection and creation-path enforcement for legacy per-project collections.
- Added repository index regression tests. The broader migration from name-specific collections to stable project-ID collections remains a separate task.

## 2026-09-22 Evidence Redaction Progress

- Expanded persisted API-evidence redaction to cover compound and normalized secret field names such as `clientSecret` and `api-key`, in addition to existing tokens, passwords, headers, and cookies.
