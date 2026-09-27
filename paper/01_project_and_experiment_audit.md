# AQUA project and evidence audit

**Audit date:** 2026-09-24  
**Purpose:** establish the implementation facts and evidence limits that bound a journal-paper submission.

## Implemented system scope

AQUA is a React/Vite frontend and FastAPI backend backed by MongoDB. Its implemented, paper-relevant API-testing path accepts OpenAPI or Postman-derived specifications, normalizes API operations, generates schema-constrained API test cases through a configured LLM, executes requests deterministically with `httpx`, evaluates assertions, persists runs, and creates passive security findings. API workflows can pass extracted response values to dependent requests. The frontend exposes an authenticated API workspace for import, editing requests and assertions, execution, run history, and finding remediation.

The UI-testing path fetches a page, extracts interactive DOM elements, stores element representations in Chroma, generates UI test cases through an LLM, and uses retrieved element context when generating Playwright scripts. A deterministic Playwright-script fallback is present. The backend also exposes a single LLM decision step that decides whether to trigger UI-test generation.

## Explicit non-claims

- The repository does **not** implement a programming-assignment evaluator, student-submission grader, Digital TA feedback workflow, Piston execution service, or Supabase integration.
- The `Analyzer`, `Planner`, `Executor`, and `Observer` modules are empty. AQUA must not be described as an implemented multi-agent architecture.
- The one-shot `run_agent_once` endpoint is an LLM-controlled decision boundary, not an iterative agent loop with observation, planning, and execution roles.
- No empirical benchmark, user study, API-coverage measurement, defect-detection study, cost study, or comparison against an external baseline is stored in the repository.

## Implementation evidence

- `backend/app/services/openapi_parser.py`: parses OpenAPI documents into normalized operations, including paths, parameters, request/response schemas, and declared authentication schemes.
- `backend/app/services/api_case_generation.py`: requests JSON test cases from an LLM and rejects any case whose method/path is absent from the imported operation set.
- `backend/app/services/api_executor.py`: performs deterministic HTTP execution, substitutes declared variables, supports bearer/basic request credentials, and evaluates assertions.
- `backend/app/services/api_workflow.py`: supports dependent-request execution.
- `backend/app/services/api_security_scan.py`: performs passive checks; active probes explicitly fail closed.
- `backend/app/services/test_generation_service.py`, `backend/app/core/rag/knowledge_manager.py`, and `backend/app/services/playwright_generator.py`: implement the UI/RAG/Playwright path.
- `aqua-test-target/`: a local social-media API with nine documented operations and deliberately seeded local-only security signals; it is a potential controlled system under test, not an evaluated benchmark.

## Current software validation

On 2026-09-24, `uv run pytest` collected and passed 48 backend tests. `npm run lint && npm run build` completed successfully for the frontend; the build emitted only a chunk-size warning. These results establish regression-test and build health. They do **not** establish test-generation effectiveness, fault-detection effectiveness, usability, or generalizability.

## Experimental evidence audit

Detected axes: task_type=general; evidence_type=baseline, reproducibility, real-world, statistical; failure_mode=missing-traditional-baseline, overclaimed-results, insufficient-reproducibility; stage=planning.

| Proposed claim | Required evidence | Current evidence | Missing experiment | Review risk |
|---|---|---|---|---|
| AQUA produces structurally valid API cases from imported specifications. | A fixed corpus of OpenAPI specifications; proportion of generated cases that validate against the imported operation set; raw failures. | Code validates the generated case model and method/path membership; unit tests cover rejection of unknown operations. | Generate a fixed number of cases per specification across repeated runs and report validation rate with confidence intervals. | Critical |
| AQUA improves executable-test yield relative to a simple baseline. | Same specifications, models, budgets, and execution environment; executable-test rate and assertion-pass rate against a deterministic/spec-template baseline. | No comparative run data. | [EXPERIMENT REQUIRED] Implement and evaluate a deterministic OpenAPI-template baseline. | Critical |
| AQUA supports stateful/dependent API workflows. | Workflows requiring value extraction and authenticated follow-on requests; completion rate and manual-repair rate. | Workflow implementation and unit coverage exist; the local target contains login-to-post/comment flows. | [EXPERIMENT REQUIRED] Execute a predefined workflow corpus against the local target and at least two independent open-source APIs. | Critical |
| Passive analysis identifies meaningful API-security findings. | Seeded, documented findings; precision/recall against a manually labeled ground truth; false-positive analysis. | Code checks declared authentication, static authorization heuristics, CORS, rate-limit headers, error responses, schema mismatch, and sensitive-looking response fields. The local target intentionally exposes safe signals. | [EXPERIMENT REQUIRED] Create and release a finding ground-truth ledger, then report precision, recall, and per-category results. | Critical |
| The platform is practical for local use. | Runtime, token/cost accounting, memory, hardware/software versions, and repeated-run variance. | None. | [EXPERIMENT REQUIRED] Measure per-stage latency and resource use under fixed model/provider settings. | Major |

## Minimum experiment package

1. Select at least three reproducible OpenAPI-described systems: the included local target plus two independently maintained, containerized/open-source APIs. Keep versions, commit hashes, OpenAPI files, and reset procedure fixed.
2. Compare AQUA with (a) a deterministic OpenAPI-template generator and (b) one established black-box API-testing tool that can run on the selected systems. State when a baseline cannot support a system and exclude it symmetrically.
3. For each system, run a preregistered number of seeds/generation attempts with identical request budgets. Measure schema-valid generation rate, executable-test rate, operation coverage, parameter coverage where measurable, workflow completion, unique seeded faults/findings detected, latency, and token/cost use.
4. Conduct ablations that isolate schema validation and dependency workflow support. Do not claim a RAG contribution unless the UI path is separately evaluated.
5. Publish prompts, model identifiers and parameters, complete OpenAPI inputs, execution logs with secrets redacted, scripts, environment details, and raw per-run results.

## Manuscript-safe contribution framing before experiments

Until the experiment package is completed, the paper may claim an **implementation**: an integrated workflow that constrains LLM-generated API cases to imported operations and executes them through a deterministic runner with persisted evidence and passive security checks. It must not claim improved coverage, higher fault detection, better accuracy, cost efficiency, or superiority over prior systems.
