# AQUA — Agentic Quality Assurance

AQUA is a FastAPI + React application for generating and executing browser and API tests, then reviewing their evidence and security findings.

## What works today

- Authenticated project and test-case workflows with signed expiring tokens.
- Browser-test generation and execution through Playwright subprocesses, including waiting for user-provided inputs.
- OpenAPI and Postman import with normalized API operations.
- API request execution with variables, Bearer/Basic auth, workflows, assertions, response evidence, and redaction.
- Passive API security checks for authentication declarations, BOLA/BFLA candidate surfaces, schema abuse, CORS, rate-limit signals, schema mismatches, sensitive fields, reachability, and error responses.
- Durable API run and finding history with statuses, remediation state, severity, fingerprints, and occurrence history.
- SSRF protections for target URLs and explicit redirect validation.
- Docker Compose deployment for MongoDB, the backend, and the frontend.

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

Prerequisites: Python 3.11+, `uv`, Node.js/npm, and MongoDB. LM Studio is optional for deterministic API tests and browser fallback flows, but required for LLM-assisted generation. The default LM Studio endpoint is `http://localhost:1234`.

Backend:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server runs at [http://localhost:5173](http://localhost:5173).

Copy `backend/.env.example` to `backend/.env` and set a non-default `AUTH_SECRET_KEY`. For local development, `ALLOW_PRIVATE_TARGETS=true` is available only when intentionally testing local targets; production deployments should keep private-target access disabled.

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
