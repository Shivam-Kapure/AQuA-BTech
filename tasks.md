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
- [x] Define how `X-Aqua-Route-Jwt` is validated and passed to target requests, or remove the frontend feature.
- [x] Prevent generated scripts and subprocesses from inheriting application secrets.
- [x] Choose `pyproject.toml` + `uv.lock` as the canonical Python dependency source and update/remove the incomplete `requirements.txt`.
- [x] Add `.env.example`; remove secrets and runtime artifacts from version control.

## P1 — Shared Test and Run Domain

- [ ] Replace project-name-specific MongoDB collections with stable collections keyed by `project_id`.
- [x] Add indexes and uniqueness constraints for projects and logical test IDs.
- [x] Implement `TestRun` and artifact metadata models/repositories.
- [ ] Preserve every execution attempt instead of overwriting test status.
- [ ] Standardize statuses across UI, API, and security tests (`queued`, `running`, `waiting`, `passed`, `failed`, `warning`, `cancelled`).
- [ ] Persist duration, runner version, generation mode, inputs reference, evidence, and failure details.
- [ ] Add a background worker/queue for Playwright, API, and ZAP jobs.
- [ ] Add cancellation, timeouts, retry policy, structured logs, and run correlation IDs.
- [x] Define artifact retention, access control, redaction, and cleanup policies.

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
- [x] Add LLM-assisted case generation only after schema validation and structured execution are working.
- [x] Add optional Postman collection import after OpenAPI support is stable.
- [x] Add API run/list/detail endpoints for API executions.
- [x] Add generated OpenAPI documentation examples and response models for API contracts.

## P1 — Security Testing Completion

- [x] Implement the missing `authentication_configuration` checker.
- [x] Add API security checks for authentication, authorization/BOLA/BFLA, schema validation, excessive data exposure, rate limits, CORS, and error leakage.
- [x] Separate passive checks from active probes and require explicit opt-in for active/destructive methods.
- [x] Add passive API checks for declared authentication, CORS headers, reachability, and error responses.
- [x] Add passive API checks for rate-limit signals, response schema mismatches, and sensitive response fields.
- [x] Persist owner-scoped API security findings and expose finding history.
- [x] Reuse the API operation catalog for security case generation instead of relying only on page DOM context.
- [ ] Make ZAP scans asynchronous, scoped, deduplicated, and linked to a durable security run.
- [ ] Pin the ZAP image and document the required Docker permissions and network policy.
- [ ] Normalize `PASS`/`FAIL`/`WARNING` values and map them consistently to shared run statuses.
- [x] Add security finding deduplication, remediation state, severity validation, and historical results.

## P1 — UI and Contract Alignment

- [x] Add frontend API-suite, operation, test-case, run, and finding views.
- [x] Add initial authenticated API import, operation catalog, and passive-scan UI.
- [x] Add persisted-spec and API run-history actions to the API workspace UI.
- [x] Add direct operation execution controls with template-path safeguards.
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
- [x] Add CI/CD for linting, tests, and builds; dependency checks and image scanning remain follow-up work.
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

## Current Validation and Delivery Sprint

This checklist turns the requested hands-on validation into a small, testable delivery plan. Keep each item unchecked until its acceptance criteria are demonstrated in the local app and captured in the run history.

### 1. End-to-end project and functional-test validation

- [x] Create a disposable project against an approved test target; confirm it appears in the project workspace after a refresh. (Validated locally on 2026-09-28 with `http://127.0.0.1:3001`; this requires the explicit development-only `ALLOW_PRIVATE_TARGETS=true` setting.)
- [x] Generate a **short** functional-test suite and confirm every generated case is scoped to the selected project. (Validated locally on 2026-09-28: five cases generated for the project.)
- [x] Run at least one generated case, record its final status, duration, failure reason (if any), and any evidence/artifacts. (TC003, “Login with Empty Fields,” passed in 18,888 ms after selector remediation.)
- [x] For each failed functional case, triage it as product defect, flaky test/selector, environment dependency, or generation defect; add a reproducible remediation note before rerunning. (Initial TC003 failure was a generator selector mismatch: `Login` versus the target's exact `Sign in` name; tightened selector guidance and rerun passed.)
- [ ] Run the project’s agent/RL decision step and record the decision, rationale, recommended next action, and any request for credentials or route JWT.

### 2. API testing validation

- [ ] Import a valid, owner-scoped OpenAPI document and verify the parsed operation catalog, parameters, schemas, and declared authentication are shown.
- [ ] Execute one safe read-only operation with status, content type, JSON/body, and response-time assertions; verify sensitive headers and fields are redacted in stored evidence.
- [ ] Create and run a two-step API workflow that extracts a safe value from step one and injects it into step two; verify workflow failure identifies the failed step.
- [ ] Run the passive API-security scan; review and persist findings for authentication, authorization, schema, CORS, rate limiting, error leakage, and sensitive-data exposure.
- [ ] Add a frontend API-test smoke suite that covers import, operation execution, run history, remediation-state change, and job cancellation/timeout display.

### 3. Security-testing content and UX

- [x] Add a dedicated Security testing workspace for project-level generation, safe execution, findings, severity, remediation state, and evidence links.
- [x] Make the security-generation content explicit and defensive: show target, category, expected secure behavior, severity, safe execution boundary, and remediation guidance.
- [ ] Clearly label passive checks versus active/destructive probes; active probes must stay opt-in, target-scoped, and blocked unless the user has explicit authorization.
- [ ] Add UI acceptance tests for empty, loading, unauthorized, failed, warning, cancelled, and passed security-run states.
- [ ] Complete asynchronous, deduplicated ZAP baseline-scan handling with a pinned image, durable run record, timeout/cancellation, Docker/network prerequisites, and documented scope.

### 4. Decision-score metric for test cases

- [ ] Add an explainable `decision_score` (0–100) to generated UI, API, and security test cases, with a structured `decision_score_factors` breakdown. UI and security cases are complete; API-generated cases remain.
- [ ] Use a documented weighted formula: user/agent priority, risk or severity, target-change/coverage gap, historical failure or flakiness, and execution cost; never derive the score from sensitive request values.
- [ ] Display the score, confidence band, and top contributing factors in test-case lists and detail views; permit sort/filter by score.
- [ ] Include decision-score distribution and highest-risk unexecuted cases in the PDF report and add tests for score bounds, determinism, and redaction.

### 5. PDF report completion

- [ ] Extend the existing client-side PDF report with API executions, security findings, remediation status, decision scores, agent/RL decisions, evidence links/identifiers, and an explicit report scope/date range.
- [ ] Decide whether reports are compliance artifacts; if yes, replace client-only generation with a versioned server-side report contract, durable source snapshot, access control, and audit event.
- [ ] Add a browser-level PDF export smoke test that verifies download, title, project identity, summary metrics, test table, failure reasons, and graceful empty-state behavior.

### 6. Release gate and monitoring

- [ ] Run and retain the release checks: backend unit/integration tests, frontend lint/build, and the end-to-end smoke suite.
- [ ] Record deprecation warnings separately from test failures and schedule their cleanup (timezone-aware datetimes, Pydantic `ConfigDict`, and current FastAPI status constants).
- [ ] Add run correlation IDs and structured failure telemetry so new failed executions can be grouped, diagnosed, rerun, and closed with a remediation note.
