# AQUA Implementation Tasks

This is the proposed implementation backlog from the architecture review. Review and reorder this file before implementation begins. Do not mark a task complete until its acceptance criteria and tests are satisfied.

## P0 — Security and Platform Foundations

- [x] Define the trust boundary and deployment threat model. See `aqua-threat-model.md`.
- [x] Implement real authentication with a password-hashing library (Argon2id or bcrypt).
- [x] Replace opaque, unverifiable login tokens with signed, expiring access tokens.
- [x] Add authentication dependencies to protected API routes.
- [x] Add project ownership and enforce authorization on every project-scoped operation.
- [ ] Add URL validation and an SSRF policy: approved schemes, host allow-list, blocked private/link-local ranges, redirect validation, and DNS-rebinding protections.
- [x] Remove `verify=False` from security HTTP clients; make TLS verification configurable only for local development.
- [ ] Define how `X-Aqua-Route-Jwt` is validated and passed to target requests, or remove the frontend feature.
- [ ] Prevent generated scripts and subprocesses from inheriting application secrets.
- [ ] Choose `pyproject.toml` + `uv.lock` as the canonical Python dependency source and update/remove the incomplete `requirements.txt`.
- [ ] Add `.env.example`; remove secrets and runtime artifacts from version control.

## P1 — Shared Test and Run Domain

- [ ] Replace project-name-specific MongoDB collections with stable collections keyed by `project_id`.
- [ ] Add indexes and uniqueness constraints for projects and logical test IDs.
- [ ] Implement `TestRun` and artifact metadata models/repositories.
- [ ] Preserve every execution attempt instead of overwriting test status.
- [ ] Standardize statuses across UI, API, and security tests (`queued`, `running`, `waiting`, `passed`, `failed`, `warning`, `cancelled`).
- [ ] Persist duration, runner version, generation mode, inputs reference, evidence, and failure details.
- [ ] Add a background worker/queue for Playwright, API, and ZAP jobs.
- [ ] Add cancellation, timeouts, retry policy, structured logs, and run correlation IDs.
- [ ] Define artifact retention, access control, redaction, and cleanup policies.

## P1 — API Testing Module

- [x] Add `ApiSpec` and `ApiOperation` models for OpenAPI documents and normalized endpoints.
- [ ] Implement OpenAPI upload/URL import with validation, size limits, and checksum/version tracking.
- [x] Validate inline OpenAPI documents and compute stable checksums.
- [x] Persist owner-scoped OpenAPI imports with versioned listing endpoints.
- [x] Support URL-based OpenAPI import with SSRF and size validation.
- [x] Add a normalized operation catalog: method, path, parameters, request schema, response schema, tags, and auth scheme.
- [x] Add `ApiTestCase`, `ApiAssertion`, and `ApiAuthContext` models.
- [x] Implement deterministic HTTP execution with `httpx` in the worker layer.
- [x] Expose an authenticated API test execution endpoint backed by the deterministic runner.
- [x] Support URL/path/query/header/body templates and environment-safe variable substitution.
- [x] Implement assertions for status, headers, JSON Schema, JSONPath/body fields, content type, and response time.
- [x] Redact authorization headers, cookies, tokens, passwords, and sensitive response fields in stored evidence.
- [x] Add setup/teardown and dependent-request support for authenticated workflows.
- [ ] Add LLM-assisted case generation only after schema validation and structured execution are working.
- [ ] Add optional Postman collection import after OpenAPI support is stable.
- [x] Add API run/list/detail endpoints for API executions.
- [ ] Add generated OpenAPI documentation examples for all API contracts.

## P1 — Security Testing Completion

- [x] Implement the missing `authentication_configuration` checker.
- [ ] Add API security checks for authentication, authorization/BOLA/BFLA, schema validation, excessive data exposure, rate limits, CORS, and error leakage.
- [ ] Separate passive checks from active probes and require explicit opt-in for active/destructive methods.
- [ ] Reuse the API operation catalog for security case generation instead of relying only on page DOM context.
- [ ] Make ZAP scans asynchronous, scoped, deduplicated, and linked to a durable security run.
- [ ] Pin the ZAP image and document the required Docker permissions and network policy.
- [ ] Normalize `PASS`/`FAIL`/`WARNING` values and map them consistently to shared run statuses.
- [ ] Add security finding deduplication, remediation state, severity validation, and historical results.

## P1 — UI and Contract Alignment

- [ ] Add frontend API-suite, operation, test-case, run, and finding views.
- [ ] Add security-testing screens for generation, execution, ZAP scans, and findings.
- [ ] Decide whether generation profiles and `user_prompt` are supported; implement the backend contract or remove those UI fields.
- [ ] Connect route JWT handling end-to-end or remove the modal and marketing claim.
- [ ] Add run-history, artifact, evidence, and failure-detail views.
- [ ] Replace client-only PDF reporting with a defined report contract if reports are compliance artifacts.
- [ ] Add loading, error, empty, unauthorized, and not-found states with an application error boundary.

## P2 — Testing and Quality Gates

- [ ] Replace placeholder tests with unit tests for repositories, parsers, generators, assertions, checkers, and status transitions.
- [ ] Add API contract tests for authentication, ownership, validation, and every public endpoint.
- [ ] Add fakes/mocks for MongoDB, LLM providers, Playwright, Docker/ZAP, and HTTP targets.
- [ ] Add runner state-machine tests for success, failure, waiting, timeout, cancellation, and retry.
- [ ] Add frontend component and API-client tests.
- [ ] Add a small end-to-end smoke suite covering project creation, API import, case execution, and UI execution.
- [ ] Define coverage thresholds and enforce pytest, ESLint, build, and test gates in CI.
- [ ] Add security regression tests for SSRF, secret leakage, auth bypass, and cross-project access.

## P2 — Deployment and Operations

- [ ] Add Dockerfiles for backend, frontend, and worker plus Compose for local MongoDB/ZAP dependencies.
- [ ] Add health and readiness endpoints for API, MongoDB, worker, and LLM dependencies.
- [ ] Add production environment configuration and secret-injection documentation.
- [ ] Add CI/CD for linting, tests, builds, dependency checks, and image scanning.
- [ ] Add structured log shipping, metrics, error tracking, and audit events.
- [ ] Define MongoDB backup, migration/index, artifact retention, and disaster-recovery procedures.
- [ ] Update README and setup docs so every documented command works from a clean checkout.

## Review Decisions Before Implementation

- [ ] Confirm OpenAPI is the first API-test input format.
- [ ] Confirm whether active security testing is in scope for the first release.
- [ ] Choose local-only, self-hosted, or multi-user deployment as the initial security boundary.
- [ ] Choose the worker technology and whether Docker isolation is mandatory.
- [ ] Approve the shared test/run schema and status vocabulary.
- [ ] Define minimum acceptance criteria and coverage targets for the first milestone.
