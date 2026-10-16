# AQUA System Architecture

AQUA has two user-facing testing paths behind one authenticated FastAPI service:

1. Browser testing turns natural-language or structured steps into Playwright scripts and executes them in a subprocess.
2. API testing imports an API contract, normalizes its operations, executes deterministic HTTP cases, and runs passive security analysis over the same operation catalog.

## Component view

```mermaid
flowchart TB
    User((User)) --> UI[React/Vite UI]
    UI --> Client[Axios API client]
    Client --> API[FastAPI /api/v1]
    API --> Auth[Auth and ownership]
    API --> Browser[Browser routes]
    API --> Api[API routes]
    API --> Security[Security routes]
    API --> LLMRoutes[LLM routes]
    Browser --> Generation[Browser generation]
    Browser --> Runs[Test execution and run services]
    Generation --> Perception[Page perception: elements, hidden flags, visible text]
    Generation --> LLM[Groq or LM Studio via rate-limit-aware client]
    Generation --> RAG[Chroma RAG context, ONNX MiniLM embeddings]
    Runs --> Verdict[Verdict policy, self-repair, script cache]
    Runs --> Playwright[Playwright subprocess]
    Api --> Import[OpenAPI/Postman import]
    Import --> Catalog[Normalized operation catalog]
    Catalog --> HttpRunner[Deterministic httpx runner]
    Catalog --> Passive[Passive API security checks]
    HttpRunner --> Targets[Approved HTTP targets]
    Passive --> Findings[Finding history and remediation]
    Api --> Queue[Process-local async queue]
    Queue --> ApiRuns[Durable API runs]
    API --> Repositories[Owner-scoped repositories]
    Repositories --> Mongo[(MongoDB)]
    Runs --> Artifacts[Redacted retained artifacts]
    Artifacts --> Mongo
    Security --> ZAP[Optional Docker ZAP integration]
```

## Frontend

The frontend is a Vite/React application with React Router, Axios, and Zustand stores for authentication and theme state. Its main surfaces are:

- `ProjectsPage` and `ProjectDetailPage` for project and browser-test workflows.
- `ApiTestingPage` for spec import, operation editing, API execution, workflows, run history, passive scans, and finding remediation.
- `LoginPage` and protected routing for authenticated access.
- `NeedsActionModal` for browser runs that require user input.

## Backend layers

`backend/app/api/v1/` contains route handlers grouped by capability. Models and persistence are separated from service logic:

- `models/` defines projects, test cases, API specs/operations, API runs/findings, shared run metadata, and status vocabulary.
- `db/repositories/` owns MongoDB access and owner-scoped queries. Project names are unique per owner; legacy per-project test collections enforce logical-ID uniqueness per project. A complete migration to stable project-ID collections remains planned.
- `services/` contains parsing/import, deterministic API execution, workflow execution, browser generation/execution, security checks, reporting, and the async job boundary.
- `core/` contains authentication, URL/SSRF policy, browser control, LLM clients, and RAG helpers.

## Browser-testing flow

1. **Perception** — Playwright loads the target (`domcontentloaded`, then at most 5 s for network idle), `dom_parser` extracts interactive elements (capped at 80 elements / 6,000 characters, elements hidden on first load flagged `hidden='initially'`) and a visible-text excerpt (≤1,500 characters, nav/footer removed). Elements are indexed in Chroma for script generation.
2. **Generation** — the LLM produces cases in batches of five (Quick 5, Standard 10, Detailed 20), each batch with its own focus and the names already generated. AQuA assigns IDs `TC001…`. The project's description (the "Short prompt") is passed as authoritative context to generation, script writing and verdicts.
3. **Script writing** — the LLM writes a Playwright script per case with RAG selectors and prompt rules (strict-mode-safe locators, no guessed message wording, real Playwright APIs only, self-registration when sign-up exists, `domcontentloaded` navigation).
4. **Execution** — the script runs in a subprocess using the backend's Python, a minimal environment (UTF-8, no application secrets) and the run timeout.
5. **Verdict** — a failing script is `failed` with its real error; a passing script with assertions is `passed`; only assertion-free scripts are judged by the LLM on visible (hidden-element-aware) page text. Scripts asking for inputs become `waiting` ("Need action"); asking again for inputs already supplied is reported as `failed`.
6. **Self-repair and cache** — failures caused by the script itself (strict-mode violations, `TypeError`, invalid keyword arguments, a value used as a selector, …) are regenerated once with the error as feedback (`llm_repaired`). Passing LLM scripts are cached on the test case and reused (`cached`); a failing cached script is discarded. If no script can be written (e.g. LLM rate limit) the test fails with that reason instead of running a template script.

## LLM client

All LLM calls use `core/llm/openai_compat_client.py`: per-minute 429s are retried after the advertised delay, a daily cap switches to `LLM_FALLBACK_MODEL` (exhausted models are skipped for the rest of the window), at most `LLM_MAX_CONCURRENCY` requests run at once, `reasoning_effort` is sent to `gpt-oss` models, and `<think>` blocks are stripped. Provider rate limits reach clients as HTTP 503.

## Run and job lifecycle

Shared statuses are `queued`, `running`, `waiting`, `passed`, `failed`, `warning`, and `cancelled`. API runs persist correlation IDs, timing, runner/generation metadata, evidence, and failure details. The current `AsyncJobQueue` provides bounded timeout, retry, and cancellation behavior inside one backend process; it is not a distributed worker and should not be horizontally scaled.

Browser execution remains subprocess-based so generated code does not execute inside the Uvicorn process. Secrets are passed only through controlled runtime inputs and are excluded from generated scripts, logs, and persisted evidence.

## API-testing flow

```mermaid
sequenceDiagram
    participant U as UI
    participant A as API routes
    participant I as Import/parser
    participant R as httpx runner
    participant S as Passive scanner
    participant M as MongoDB
    U->>A: Import OpenAPI or Postman document
    A->>I: Validate and normalize operations
    I-->>A: Spec, catalog, checksum
    A->>M: Store owner-scoped version
    U->>A: Execute operation or workflow
    A->>R: Queue deterministic request
    R-->>A: Redacted response/assertion evidence
    A->>M: Store API run and status
    U->>A: Start passive security scan
    A->>S: Scan catalog and approved targets
    S->>M: Upsert fingerprinted findings
```

URL imports and target requests accept only HTTP(S), validate host policy and DNS results, block private/reserved targets by default, and do not follow redirects automatically. OpenAPI imports validate an explicit one-hop redirect before following it. DNS-rebinding-safe connection pinning and active/destructive probes are still deployment-policy work.

## Deployment boundaries

The default Compose stack contains MongoDB, the backend, and an Nginx-served frontend. LM Studio/Groq is external and optional unless strict LLM readiness is enabled. ZAP is an opt-in container profile.

The cloud deployment runs the frontend on Vercel (with `/api/*` rewritten to the backend, so the browser stays same-origin), the backend container on Google Cloud Run (max one instance because the job queue is process-local; disk is ephemeral), the Circle Social demo target on Render, and MongoDB on Atlas. See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md). Keep `AUTH_SECRET_KEY` in the environment or a managed secret store; do not commit runtime `.env` files.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for commands, health checks, scaling limitations, and security notes.
