# AQUA — Agentic Quality Assurance

AQUA is a FastAPI + React application for generating and executing browser and API tests, then reviewing their evidence and security findings.

## What works today

- Authenticated project and test-case workflows with signed expiring tokens.
- Browser-test generation and execution through Playwright subprocesses, including waiting for user-provided inputs.
  - Generation reads the page's interactive elements (hidden-on-load elements flagged), a visible-text excerpt and optional project context, and produces 5 / 10 / 20 cases in batches with unique IDs (TC001…).
  - The Playwright run decides pass/fail; the LLM verdict is used only for scripts without assertions.
  - Scripts that fail because of their own bugs (ambiguous locators, invalid API calls, values used as selectors) are repaired once automatically; passing scripts are cached for instant re-runs.
  - Scripts create a fresh account when the target offers sign-up instead of guessing credentials.
- OpenAPI and Postman import with normalized API operations.
- API request execution with variables, Bearer/Basic auth, workflows, assertions, response evidence, and redaction.
- LLM-generated API test cases (normalized assertions, documented response codes, 401 for unauthenticated calls) that can be run individually or all at once, with expected vs actual per assertion.
- Passive API security checks for authentication declarations, BOLA/BFLA candidate surfaces, schema abuse, CORS, rate-limit signals, schema mismatches, sensitive fields, reachability, and error responses.
- Durable API run and finding history with statuses, remediation state, severity, fingerprints, and occurrence history.
- Security test generation that uses the page, its visible text and any published `/openapi.json` endpoints; LLM-written targets are resolved to real URLs and executed by deterministic checkers.
- Groq LLM integration with per-minute retry, daily-limit model fallback, a concurrency limit and reasoning-effort control; LM Studio remains supported.
- SSRF protections for target URLs and explicit redirect validation.
- Docker Compose deployment for MongoDB, the backend, and the frontend, plus a free-tier cloud deployment (Vercel, Google Cloud Run, Render, MongoDB Atlas).
- Circle Social (`aqua-test-target/`), a demo application to test against.

Active or destructive API security probes remain fail-closed until an isolated worker policy and authorization boundary are approved. The current async queue is process-local and must not be horizontally scaled.

## Quick start with Docker

From the repository root:

```bash
export AUTH_SECRET_KEY="replace-with-a-long-random-value"
docker compose up --build
```

Open the UI at [http://localhost:8080](http://localhost:8080). The API is available at [http://localhost:8000](http://localhost:8000).

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Readiness reports MongoDB, the process-local worker, and the configured LLM provider. Set `LLM_READINESS_REQUIRED=true` to make an unavailable LLM fail readiness; it is non-blocking by default because the Compose stack does not include an LLM service.

The optional ZAP service is isolated behind the Compose profile:

```bash
docker compose --profile security up zap
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment constraints and production secret handling.

## Local development

Prerequisites: Python 3.11+, `uv`, Node.js/npm, MongoDB, and an LLM provider for generation: a Groq API key (default, `LLM_PROVIDER=groq`) or LM Studio (`LLM_PROVIDER=lmstudio`, default endpoint `http://localhost:1234`). API execution and passive scans work without an LLM.

Backend:

```bash
cd backend
uv sync
uv run playwright install chromium
uv run uvicorn app.main:app --port 8000
```

On Windows, do not use `--reload` while generating or running browser tests (it prevents Chromium from launching and restarts the server mid-run); use `--reload --reload-dir app` only for non-browser work. See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#when-to-use---reload-windows).

Demo target app, in another terminal:

```bash
cd aqua-test-target
npm install
npm run dev   # http://127.0.0.1:3001
```

Frontend, in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server runs at [http://localhost:5173](http://localhost:5173).

Copy `backend/.env.example` to `backend/.env`, set a non-default `AUTH_SECRET_KEY` and your `GROQ_API_KEY`. For local development, `ALLOW_PRIVATE_TARGETS=true` is available only when intentionally testing local targets; production deployments should keep private-target access disabled. Leave `TARGET_HOST_ALLOWLIST` empty to allow any public URL, or list hosts to restrict targets.

## Cloud deployment

| Component | Platform |
|---|---|
| Frontend | Vercel (`frontend/vercel.json` rewrites `/api/*` to the backend) |
| Backend | Google Cloud Run (`backend/Dockerfile`, 2 GiB, max 1 instance) |
| Demo target | Render (Node web service, root `aqua-test-target`) |
| Database | MongoDB Atlas M0 |
| LLM | Groq (`openai/gpt-oss-120b`, fallback `openai/gpt-oss-20b`) |

Step-by-step instructions, environment variables and troubleshooting: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md).

## Validation

```bash
cd backend && uv run pytest
cd frontend && npm run lint && npm run build
```

CI runs the locked backend test suite plus frontend install, lint, and production build.

## Main API areas

- `/api/v1/auth` — registration and login.
- `/api/v1/projects` — owner-scoped projects.
- `/api/v1/test-cases`, `/api/v1/test-generation`, `/api/v1/test-execution` — browser test management and execution.
- `/api/v1/security-tests` — security test generation, execution, and ZAP integration.
- `/api/v1/api-specs` — OpenAPI/Postman import, operation execution, workflows, async jobs, runs, passive security scans, and findings.
- `/api/v1/llm` — LLM-backed operations.

For the component and data-flow view, see [architecture.md](architecture.md).
