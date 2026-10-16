# AQuA-BTech — Local Run (Groq) + Free-Tier Cloud Deployment

## Overview
AQuA runs locally with Groq (no LM Studio needed) and deploys on free tiers:

| Component | Host | Why |
|---|---|---|
| LLM | Groq free tier (`openai/gpt-oss-120b`, fallback `openai/gpt-oss-20b`) | Fast OpenAI-compatible API |
| Database | MongoDB Atlas M0 | Free, works with Motor + Mongoose |
| Backend (FastAPI + Playwright/Chromium) | **Google Cloud Run** (Docker, 2 GiB / 1 vCPU, scale to zero) | Chromium needs ~2 GB RAM; free tier + trial credit |
| Demo target (Circle Social, Express) | **Render** free web service (Node) | Small Node app fits 512 MB |
| Frontend (Vite SPA) | **Vercel** Hobby | `/api/*` rewrite to Cloud Run → no CORS |

Not used: Hugging Face Docker Spaces (now a paid feature) and Render for the backend (512 MB / 0.1 CPU is too small for Chromium).

Free-tier trade-offs: Render sleeps after 15 min idle (~50 s wake-up); Cloud Run cold starts take ~10–30 s; Cloud Run disk is ephemeral (Chroma RAG data, generated scripts and artifacts reset on restart; test records in Atlas persist); ZAP scans need Docker and do not run on Cloud Run.

---

## Part A — What the code does for this setup

### LLM layer (`backend/app/core/llm/openai_compat_client.py`)
All LLM calls (test generation, Playwright script writing, the pass/fail verdict, API test generation, security test generation) use one OpenAI-compatible client selected by `LLM_PROVIDER` (`groq` or `lmstudio`). It:
- waits out per-minute rate limits (HTTP 429) and retries;
- switches to `LLM_FALLBACK_MODEL` (comma-separated chain allowed) when a model hits its **daily** cap, and skips exhausted models afterwards;
- limits simultaneous requests to `LLM_MAX_CONCURRENCY`;
- sends `reasoning_effort` (`LLM_REASONING_EFFORT`) to `gpt-oss` models to save tokens;
- strips `<think>` blocks from replies.
Rate-limit errors reach users as HTTP 503 with a clear message.

### Backend image (`backend/Dockerfile`)
Playwright Python base image (Chromium included), `uv sync --locked`, non-root user (uid 1000) with `HOME=/app`, ONNX embedding model downloaded at build time, listens on `$PORT` (Cloud Run sets 8080; 7860 when unset; docker-compose pins 8000).

### Embeddings
RAG uses Chroma's bundled ONNX `all-MiniLM-L6-v2` (`backend/app/core/rag/embeddings.py`). `sentence-transformers`/torch were removed.

### Target app (`aqua-test-target/`)
Has its own `Dockerfile`, but on Render it runs as a plain Node service. `/openapi.json` is served dynamically with `servers` set to the host it is called on.

### Frontend (`frontend/vercel.json`)
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://aqua-backend-632611164207.asia-south1.run.app/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
Replace the destination if your Cloud Run URL differs.

---

## Part B — Groq setup
1. https://console.groq.com → sign in → **API Keys** → **Create API Key** → copy the `gsk_...` key (shown once).
2. Models: `openai/gpt-oss-120b` (default) and `openai/gpt-oss-20b` (fallback, separate quota). Do not use `meta-llama-3-8b-instruct` (LM Studio name) or retired models such as `llama-3.3-70b-versatile` — Groq returns 404 `model_not_found`. List the models your key can use with `GET https://api.groq.com/openai/v1/models`. `qwen/qwen3.8-27b` is listed but the free tier caps its output at 1,000 tokens/min, too low for test generation.
3. Limits change — check **console.groq.com/settings/limits**. Each model has a per-minute cap (≈8,000 tokens) and a **daily** cap (≈200,000 tokens). `LLM_REASONING_EFFORT=low` cuts token use by ~30 %.

## Part C — Local MongoDB + Compass
1. Compass → New Connection → `mongodb://localhost:27017` → Connect.
2. No manual setup: the backend creates `agentic_testing` and the target app creates `circle_social` on first use.

## Part D — Local environment
`backend/.env` (see `backend/.env.example`):
```env
APP_ENV=development
AUTH_SECRET_KEY=<any long random string>
MONGODB_URI=mongodb://localhost:27017
DB_NAME=agentic_testing
# Empty = any URL may be tested. A comma-separated list restricts targets to those hosts.
TARGET_HOST_ALLOWLIST=
ALLOW_PRIVATE_TARGETS=true
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=openai/gpt-oss-120b
AGENT_LLM_MODEL=openai/gpt-oss-120b
LLM_FALLBACK_MODEL=openai/gpt-oss-20b
LLM_REASONING_EFFORT=low
LLM_MAX_CONCURRENCY=2
LLM_READINESS_REQUIRED=false
```
Target app: no `.env` needed (defaults: `PORT=3001`, `mongodb://127.0.0.1:27017/circle_social`).
Frontend: no `.env` needed — `vite.config.js` proxies `/api` to `127.0.0.1:8000`.

## Part E — Run locally (3 PowerShell terminals)
```powershell
# Terminal 1 — target app
cd D:\AQuA\AQuA-BTech\aqua-test-target; npm install; npm run dev
# Terminal 2 — backend
cd D:\AQuA\AQuA-BTech\backend; uv sync; uv run playwright install chromium; uv run uvicorn app.main:app --port 8000
# Terminal 3 — frontend
cd D:\AQuA\AQuA-BTech\frontend; npm install; npm run dev
```
Check `http://localhost:8000/health/ready` → `"llm": {"status": "ok", "provider": "groq"}`.
E2E: open `http://localhost:5173` → Register → New Project (target `http://127.0.0.1:3001`) → Generate Tests → Run one test → refresh Compass.

### When to use `--reload` (Windows)
On Windows, `--reload` breaks anything that launches headless Chromium: uvicorn switches to a selector event loop that cannot start subprocesses (`NotImplementedError`, `DOM context length: 0`), restarts whenever a generated script is written to `playwright_scripts/` (killing the run: `Script exited with code 3221225786`), and the restart can crash with `OSError: [WinError 87]`.

Features that launch Chromium: **Generate Tests**, **Run / Test**, and security test generation.

| What you're doing | Command |
|---|---|
| Generating or running tests, demos | `uv run uvicorn app.main:app --port 8000` |
| Editing backend code and checking non-browser features | `uv run uvicorn app.main:app --reload --reload-dir app --port 8000` |

On Linux, macOS or WSL, `--reload --reload-dir app` works even for Playwright runs. The Docker image never uses `--reload`.

## Part F — MongoDB Atlas (free M0)
1. Atlas → Create → **M0 Free** → nearest region.
2. **Database Access** → add a user, **Autogenerate** the password (letters/digits avoid URL-encoding problems).
3. **Network Access** → **Add IP Address** → `0.0.0.0/0`, temporary toggle **off** — Render and Cloud Run use changing IPs.
4. **Connect → Drivers** → copy `mongodb+srv://<user>:<db_password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`.
   - Backend: use as-is (database chosen by `DB_NAME`).
   - Target app: add the database name: `...mongodb.net/circle_social?retryWrites=true&w=majority`.
5. Paste the URI into Compass to inspect production data.

## Part G — Deploy the target app to Render
1. https://render.com → **Sign up with GitHub** → **New → Web Service** → connect the repository.
2. Settings:

| Field | Value |
|---|---|
| Language | **Node** |
| Branch | `main` |
| Root Directory | `aqua-test-target` |
| Build Command | `npm ci` |
| Start Command | `node server.js` |
| Instance Type | Free |
| Environment | `MONGODB_URL` = circle_social URI, `NODE_VERSION` = `20` (do not set `PORT`) |
| Health Check Path (optional) | `/api/health` |

3. Check `https://<service>.onrender.com/api/health` → `{"ok":true,"service":"circle-social","storage":"mongodb"}` and `/openapi.json` → `servers` shows the https Render URL.

## Part H — Deploy the backend to Google Cloud Run
1. https://console.cloud.google.com → free trial (card for verification) → create project (e.g. `aqua-btech`).
2. **Billing → Budgets & alerts → Create budget** → *Alerts only*, small amount (e.g. ₹200), thresholds 50/90/100 %, email alerts on.
3. **Cloud Run → Connect repository** → **Cloud Build** → **Set up with Cloud Build** → GitHub → select the repository → Branch `^main$`, Build type **Dockerfile**, Source location `/backend/Dockerfile` → Save.
4. Service settings:

| Setting | Value |
|---|---|
| Service name / Region | `aqua-backend` / e.g. `asia-south1` |
| Authentication | Allow public access |
| Billing | **Instance-based** (background API jobs/scans need CPU between requests) |
| Scaling | min `0`, **max `1`** (job status is kept in memory) |
| Ingress | All |
| Container port | `8080` |
| Memory / CPU | 2 GiB / 1 |
| Request timeout | 900 s |
| Execution environment | Second generation, Startup CPU boost on |
| Security → Service account | Default compute account, or a new one with no roles |

5. **Variables & Secrets** (the form also accepts a pasted `.env` block):

| Name | Value |
|---|---|
| `APP_ENV` | `production` |
| `AUTH_SECRET_KEY` | long random string |
| `MONGODB_URI` | Atlas URI without database name |
| `DB_NAME` | `agentic_testing` |
| `LLM_PROVIDER` | `groq` |
| `GROQ_API_KEY` | `gsk_...` |
| `LLM_MODEL` / `AGENT_LLM_MODEL` | `openai/gpt-oss-120b` |
| `LLM_FALLBACK_MODEL` | `openai/gpt-oss-20b` |
| `LLM_REASONING_EFFORT` | `low` |
| `LLM_MAX_CONCURRENCY` | `2` |
| `LLM_READINESS_REQUIRED` | `false` |
| `ALLOW_PRIVATE_TARGETS` | `false` |
| `TARGET_HOST_ALLOWLIST` | not set (any public URL allowed) |

6. **Create** → first build ~6–10 min (Build → Push → Deploy). Check `<service-url>/health/ready` → `"status":"ok"`, `"mongodb":"ok"`, `"llm":{"status":"ok","provider":"groq"}`.

## Part I — Deploy the frontend to Vercel
1. Put your Cloud Run URL in `frontend/vercel.json`, commit and push.
2. Vercel → **Add New → Project** → import the repository. Vercel detects three apps — click **Import single project** next to **frontend** only.
3. Root Directory `frontend`, preset **Vite**, default build settings, **no** environment variables (do not set `VITE_API_BASE`).
4. **Deploy** → open the site → Register → New Project with the Render target URL → Generate → Run.

## Part J — Continuous deployment
A push to `main` redeploys automatically: Vercel (frontend), Cloud Build → Cloud Run (backend), Render (target, on changes under `aqua-test-target/`).

## Part K — Verification matrix
| Component | URL | Expected |
|---|---|---|
| Local backend | `localhost:8000/health/ready` | `llm.status=ok, provider=groq` |
| Local frontend | `localhost:5173` | Register, generate, run tests |
| Render target | `https://<service>.onrender.com/api/health` | `{"ok":true,...}` |
| Cloud Run backend | `https://<service>.run.app/health/ready` | `status ok`, mongodb ok, llm ok |
| Vercel | `https://<project>.vercel.app` | Full flow against the Render target |

Before pushing, run `uv run pytest` in `backend/`, plus `npm run lint && npm run build` in `frontend/`.

## Part L — Troubleshooting
- **Groq 404 model not found** → wrong or retired model name (see Part B).
- **Groq 429** → per-minute limits are retried automatically; a daily cap switches to the fallback model.
- **"Could not write the test script: the LLM provider's rate limit was reached"** / HTTP 503 → all configured models are over their caps; try again in a minute (per-minute) or later (daily).
- **How pass/fail is decided** → the Playwright script's own result is final: a failing script is *failed* with its real error; a script that passes its `expect(...)`/`assert` checks is *passed*. The LLM verdict is only used when a script passes without checking anything.
- **Generation mode `llm_repaired`** → the first script had a bug of its own (ambiguous locator, wrong API call, a value used as a selector, …); AQuA sent the error back to the LLM once and ran the corrected script. Real assertion failures are never retried.
- **Re-running a passed test is instant** → its script is cached (`generation_mode: cached`); a failing cached script is discarded.
- **Some generated tests still fail** → LLM-written tests can misjudge an app. Run again, or describe the app in the project's "Short prompt". On-page text (e.g. demo credentials) is read automatically.
- **Generated tests ignore your context** → existing projects reuse their old tests; create a **new** project after changing the context.
- **"Target host is not allow-listed"** → `TARGET_HOST_ALLOWLIST` is set and the host is not in it; leave it empty to allow any URL (restart the backend).
- **"Target resolves to a private or reserved address"** → `ALLOW_PRIVATE_TARGETS=false` blocks localhost/LAN targets (the deployed setting). Use public URLs in production.
- **Render: "Exited with status 1"** → MongoDB connection failed: check `MONGODB_URL`, Atlas Network Access `0.0.0.0/0`, and the password (the log masks it).
- **Cloud Run deploy fails** → open the service's **Logs**; usually a mistyped variable name (`MONGODB_URI`) or Atlas access.
- **Slow first request** → cold starts (Render ~50 s, Cloud Run ~10–30 s).
- **ZAP scan returns 503** → OWASP ZAP runs in Docker; install/start Docker Desktop. Local targets are reached via `host.docker.internal` automatically.
- **Local `Executable doesn't exist`** → `uv run playwright install chromium`.
- **Windows: do not use `--reload` for browser features** → see "When to use `--reload` (Windows)" in Part E.
