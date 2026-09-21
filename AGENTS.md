# Repository Guidelines

## Project Structure & Module Organization

This repository contains two independently run applications. `backend/` is a Python 3.11+ FastAPI service. Application code is in `backend/app/`: routes in `api/v1/`, models in `models/`, persistence in `db/`, and agent/browser/LLM integrations in `core/` and `services/`. Tests are under `backend/tests/`; scripts are in `backend/scripts/`.

`frontend/` is a Vite + React application. Put pages in `frontend/src/pages/`, reusable UI in `src/components/`, API calls in `src/api/`, state in `src/store/`, and static assets in `src/assets/` or `public/`.

## Codebase Exploration Workflow

This repository is indexed by the `codebase-memory` MCP project named `AQUA`. Before manually searching source files with `rg`, `grep`, or broad file listings, query the graph for structural questions:

1. Check index readiness with `index_status(project="AQUA")`.
2. Use `get_architecture` for structure, routes, dependencies, and entry points.
3. Use `search_graph` to find symbols and `trace_path` to inspect callers/callees.
4. Use `get_code_snippet` for the exact source behind graph results.
5. Use `check_index_coverage` for every path used as evidence; fall back to targeted text search only for reported partial or excluded coverage.

Use `search_code` for literal/text searches after the graph workflow, and document any graph coverage limitation that affects conclusions. Re-index after substantial structural changes with `index_repository(repo_path="/Users/maaaazin/Developer/Curriculum Projects/AQUA", name="AQUA", mode="full", persistence=true)`.

## Build, Test, and Development Commands

Run commands from the relevant application directory.

```bash
cd backend && uv run uvicorn app.main:app --reload  # start API on :8000
cd backend && pytest                                # run backend tests
cd backend && playwright install chromium           # install browser once
cd frontend && npm ci                               # install locked JS dependencies
cd frontend && npm run dev                          # start Vite on :5173
cd frontend && npm run build                        # production build
cd frontend && npm run lint                         # ESLint checks
```

Backend test-execution flows require MongoDB and, where applicable, LM Studio; see `backend/docs/SETUP_AND_TESTING.md`.

## Coding Style & Naming Conventions

Use four-space indentation in Python and `snake_case` for modules, functions, and variables. Keep FastAPI handlers thin; place reusable behavior in services or core modules. Use `PascalCase` for React components and pages, `camelCase` for JavaScript values and hooks (for example, `useThemeStore`), and appropriately named `.jsx` files. Address ESLint errors rather than suppressing them.

## Testing Guidelines

Write pytest tests as `test_<behavior>` and place them in `tests/unit/` or `tests/integration/`. Mock MongoDB, LLMs, and browser execution in unit tests. Run `pytest` before submitting backend changes and `npm run lint && npm run build` for frontend changes. There is no coverage threshold; add regression tests for fixes.

## Commit & Pull Request Guidelines

History uses brief subjects (for example, `r2` and `first commit`); use clear imperatives such as `Add security test validation`. Keep commits focused. Pull requests should explain impact, list validation, link issues, and include screenshots for UI changes. Call out required environment variables or external-service setup.
