# AQuA-BTech — Local Run (Groq) + 100% Free Cloud Deployment (Revised Guide)

## Overview
AQuA runs locally with Groq (no LM Studio) and deploys entirely on free tiers. Render free (512 MB RAM) is not used: the backend loads torch, a sentence-transformers model and headless Chromium, which need far more memory.

**Chosen free stack:**
| Component | Host | Why |
|---|---|---|
| LLM | Groq free tier | Already supported in code |
| Database | MongoDB Atlas M0 | Free, works with Motor + Mongoose |
| Backend (FastAPI + Playwright + torch) | **Hugging Face Spaces (Docker, CPU Basic)** | Free: 2 vCPU / **16 GB RAM**, no card needed, runs any Dockerfile |
| Target app (Express) | **Hugging Face Spaces (Docker)** — second Space | Same free tier, no extra account |
| Frontend (Vite SPA) | Vercel Hobby | Free, rewrites `/api/*` to backend (no CORS work) |

Known free-tier trade-offs (acceptable for a BTech demo): Spaces sleep after ~48 h idle and take 1–3 min to wake; container disk is ephemeral (Chroma vectors, generated scripts and artifacts reset on restart); Spaces must be **public** for Vercel to reach them (secrets stay hidden); ZAP security scans need Docker-in-Docker and won't work on any free host.

---

## Part A — Code changes (already applied in this repo)

### A1–A3. Groq for every LLM call
All LLM calls (test generation, Playwright script writing, the pass/fail verdict, API test generation, security test generation) go through one OpenAI-compatible client (`backend/app/core/llm/openai_compat_client.py`), selected by `LLM_PROVIDER` (`groq` or `lmstudio`). That client:
- waits out per-minute rate limits (HTTP 429) and retries;
- switches to `LLM_FALLBACK_MODEL` when the main model hits its **daily** cap;
- sends `reasoning_effort` (`LLM_REASONING_EFFORT`) to `gpt-oss` models to save tokens.

### A4. `backend/Dockerfile` — make it run on HF Spaces (port 7860, non-root uid 1000)
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME=/app/.cache
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --locked --no-dev
COPY app ./app
RUN mkdir -p .cache data playwright_scripts playwright_artifacts && chown -R 1000:1000 /app
USER 1000
EXPOSE 7860
CMD ["sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
```
(Calls the venv's uvicorn directly so `uv run` doesn't try to write a cache as the non-root user. `PORT` lets the same image run locally on 8000.)

### A5. New `aqua-test-target/Dockerfile`
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
ENV PORT=7860
USER node
EXPOSE 7860
CMD ["node", "server.js"]
```
Plus `aqua-test-target/.dockerignore` containing `node_modules` and `.env`.

### A6. New `frontend/vercel.json`
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://<hf-username>-aqua-backend.hf.space/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```


---

## Part B — Groq setup
1. https://console.groq.com → sign in → **API Keys** → **Create API Key** → copy the `gsk_...` key (shown once).
2. Models: `openai/gpt-oss-120b` (best quality, default) or `openai/gpt-oss-20b` (much higher daily quota). Never use `meta-llama-3-8b-instruct` (an LM Studio name) or retired Groq models such as `llama-3.3-70b-versatile` — Groq returns 404 `model_not_found`. List the models your key can use with `GET https://api.groq.com/openai/v1/models`.
3. Free-tier limits change — check **console.groq.com/settings/limits**. Each model has a per-minute cap (≈8,000 tokens) and a **daily** cap (≈200,000 tokens). AQuA handles both automatically: per-minute limits are waited out, and when `LLM_MODEL` hits its daily cap it switches to `LLM_FALLBACK_MODEL` (`openai/gpt-oss-20b`, separate quota). `LLM_REASONING_EFFORT=low` cuts token use by ~30% so more tests fit in each minute.

## Part C — Local MongoDB + Compass
1. Compass → New Connection → `mongodb://localhost:27017` → Connect.
2. No manual setup: the backend creates `agentic_testing` (users, projects, test_cases, test_runs, api_specs, findings, artifacts) and the target app creates `circle_social` on first use.

## Part D — Local environment
`backend/.env`:
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
LLM_READINESS_REQUIRED=false
```
Target app: **no `.env` needed** — `server.js` doesn't load one, and its defaults (`PORT=3001`, `mongodb://127.0.0.1:27017/circle_social`) are already correct for local.
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
E2E: open `http://localhost:5173` → Register → New Project (target `http://127.0.0.1:3001`) → Generate Tests → Run one test → refresh Compass. With LM Studio closed, nothing should call port 1234.

### When to use `--reload` (Windows)
On Windows, `--reload` breaks anything that launches headless Chromium. With reload on, uvicorn switches to a selector event loop that cannot start subprocesses, so Playwright fails (`NotImplementedError`, `DOM context length: 0`). It also restarts the server whenever a generated script is written to `playwright_scripts/`, killing the running test (`Script exited with code 3221225786` = "terminated by Ctrl+C"), and that restart can crash with `OSError: [WinError 87]`.

Features that launch Chromium: **Generate Tests** (scrapes the page), **Run / Test**, and security runs.

| What you're doing | Command |
|---|---|
| Generating or running tests, demos, anything that uses the browser | `uv run uvicorn app.main:app --port 8000` |
| Editing backend code and checking non-browser features (login/register, projects, `/health/ready`, API testing page, LLM-only endpoints) | `uv run uvicorn app.main:app --reload --reload-dir app --port 8000` |

`--reload-dir app` watches only the source code, so files written to `playwright_scripts/` and `playwright_artifacts/` don't trigger restarts.

Typical workflow:
1. Editing code → run with `--reload --reload-dir app`.
2. Ready to generate/run tests → Ctrl+C, start the plain command.
3. Changed code again → Ctrl+C and restart (the plain command does not pick up changes).

On Linux, macOS or WSL, `--reload --reload-dir app` works even for Playwright runs; the limitation is Windows-only. In the cloud (Hugging Face Spaces) the Dockerfile never uses `--reload`, which is correct for production.

## Part F — MongoDB Atlas (free M0)
1. Atlas → Create → **M0 Free** → nearest region.
2. Security → Database Access → add user `aqua_admin` with a generated password (letters/digits only, or URL-encode special characters).
3. Security → Network Access → **Allow access from anywhere (0.0.0.0/0)** — HF Spaces has no fixed outbound IP.
4. Connect → Drivers → copy `mongodb+srv://aqua_admin:<pw>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`.
   - Backend uses it as-is (DB chosen by `DB_NAME`).
   - Target app needs the DB name in the path: `...mongodb.net/circle_social?retryWrites=true&w=majority`.
5. Paste the same URI into Compass to inspect production data.

## Part G — Deploy target app to Hugging Face Spaces
1. Create a free account at https://huggingface.co → Settings → Access Tokens → create a **write** token (used as the git password).
2. New Space → name `aqua-target` → SDK **Docker** → Blank → hardware **CPU basic (free)** → **Public**.
3. Space → Settings → **Variables and secrets** → New secret `MONGODB_URL` = the circle_social Atlas URI.
4. Push the code:
   ```powershell
   git clone https://huggingface.co/spaces/<hf-username>/aqua-target D:\hf\aqua-target
   # copy everything from aqua-test-target EXCEPT node_modules and .env into D:\hf\aqua-target
   ```
   Make sure the Space's `README.md` starts with:
   ```yaml
   ---
   title: AQuA Target
   sdk: docker
   app_port: 7860
   ---
   ```
   Then `git add . ; git commit -m "Deploy target app" ; git push` (username = HF username, password = the write token).
5. Wait for **Running**; check `https://<hf-username>-aqua-target.hf.space/api/health` → `{"ok":true,"service":"circle-social","storage":"mongodb"}`.

## Part H — Deploy backend to Hugging Face Spaces
1. New Space → `aqua-backend` → SDK **Docker** → CPU basic (free) → **Public**.
2. Settings → Variables and secrets:
   | Name | Type | Value |
   |---|---|---|
   | `MONGODB_URI` | secret | Atlas URI (no DB name) |
   | `GROQ_API_KEY` | secret | `gsk_...` |
   | `AUTH_SECRET_KEY` | secret | 32+ random chars |
   | `APP_ENV` | variable | `production` |
   | `DB_NAME` | variable | `agentic_testing` |
   | `LLM_PROVIDER` | variable | `groq` |
   | `LLM_MODEL` / `AGENT_LLM_MODEL` | variable | `openai/gpt-oss-120b` |
   | `LLM_FALLBACK_MODEL` | variable | `openai/gpt-oss-20b` |
   | `LLM_REASONING_EFFORT` | variable | `low` |
   | `ALLOW_PRIVATE_TARGETS` | variable | `false` |
   | `TARGET_HOST_ALLOWLIST` | variable | leave **empty** so any public URL can be tested, or list hosts (comma-separated) to restrict |
   | `LLM_READINESS_REQUIRED` | variable | `false` |
3. Clone `https://huggingface.co/spaces/<hf-username>/aqua-backend`, copy in `backend/`'s `Dockerfile`, `pyproject.toml`, `uv.lock`, `app/` (not `.env`, `.venv`, `playwright_*`, `data/`), add a README with the same front matter (`sdk: docker`, `app_port: 7860`), commit and push.
4. First build takes ~10–15 min (Playwright image + torch). When **Running**, check `https://<hf-username>-aqua-backend.hf.space/health/ready` → `{"status":"ok", ... "llm":{"status":"ok","provider":"groq"}}`.

## Part I — Deploy frontend to Vercel
1. Put your real backend Space URL in `frontend/vercel.json` (A6), commit and push to GitHub.
2. Vercel → Add New → Project → import `Shivam-Kapure/AQuA-BTech` → Root Directory `frontend` → preset **Vite** → build `npm run build` → output `dist` → Deploy. Do **not** set `VITE_API_BASE` (the code defaults to relative `/api`, which the rewrite proxies).
3. Open the Vercel URL → Register → New Project with target `https://<hf-username>-aqua-target.hf.space` → Generate Tests → Run.

## Part J — Verification matrix
| Component | URL | Expected |
|---|---|---|
| Local backend | `localhost:8000/health/ready` | `llm.status=ok, provider=groq` |
| Local frontend | `localhost:5173` | Register, generate, run tests |
| Target Space | `…-aqua-target.hf.space/api/health` | `{"ok":true,...}` |
| Backend Space | `…-aqua-backend.hf.space/health/ready` | `status ok`, mongodb ok, llm ok |
| Vercel | `<project>.vercel.app` | Full flow against the target Space |

Before pushing, run `uv run pytest` in `backend/`, plus `npm run lint && npm run build` in `frontend/`; optionally `docker build backend` to catch Dockerfile errors locally.

## Part K — Troubleshooting
- **Groq 404 model not found** → wrong model name (see Part B).
- **Groq 429** → free-tier cap hit. Per-minute limits (e.g. 8,000 tokens/min on `openai/gpt-oss-120b`) are retried automatically after Groq's advertised delay, so running several tests back to back just runs slower. A daily cap needs a wait, or switch to `openai/gpt-oss-20b`.
- **"Could not write the test script: the LLM provider's rate limit was reached"** → both the main and fallback models are over their caps for the moment. Run the test again in a minute (per-minute cap) or later (daily cap). The backend log shows `switching to openai/gpt-oss-20b` when the fallback kicks in.
- **How pass/fail is decided** → the Playwright script's own result is final: a script that fails is *failed* with its real error, and a script that passes its `expect(...)`/`assert` checks is *passed*. The LLM verdict is only used when a script passes without checking anything.
- **Generation mode `llm_repaired`** → the first script had a bug of its own (ambiguous locator, wrong API call, …); AQuA sent the error back to the LLM once and ran the corrected script. Real assertion failures are never retried.
- **Re-running a passed test is instant** → its script is cached and reused (`generation_mode: cached`); if the cached script ever fails, the cache is cleared and the next run writes a new one.
- **Some generated tests still fail** → LLM-written tests can misjudge an app (e.g. guess a button name). Run the test again (a new script is written) or describe the app in the project's "Short prompt" so the model gets it right.
- **Generated tests ignore your context** → the context ("Short prompt") is stored as the project's description and used for generation, scripts and verdicts. Existing projects reuse their old tests, so create a **new** project after changing the context.
- **Run hangs / connection refused :1234** → edits A1–A3 not applied or `LLM_PROVIDER` not `groq`.
- **Space stuck "Building"/"Runtime error"** → open the Space **Logs** tab; the most common cause is a missing `app_port: 7860` in README or a permission error writing to `/app` (fixed by A4's `chown`).
- **Space slow to respond** → it was sleeping; the first request wakes it (1–3 min).
- **`ServerSelectionTimeoutError`** → Atlas Network Access missing `0.0.0.0/0`, or wrong password/encoding in the URI.
- **"Target host is not allow-listed"** → `TARGET_HOST_ALLOWLIST` is set and the URL's host is not in it. Leave it empty to allow any URL (restart the backend after editing `.env`).
- **"Target resolves to a private or reserved address"** → `ALLOW_PRIVATE_TARGETS=false` blocks localhost/LAN targets (the safe setting when deployed). Set it to `true` for local testing.
- **ZAP scan returns 503** → OWASP ZAP runs in Docker; install/start Docker Desktop. Local targets are reached via `host.docker.internal` automatically.
- **Generated tests/artifacts gone after restart** → expected; free Space disk is ephemeral (test records in Atlas persist).
- **Local `Executable doesn't exist`** → `uv run playwright install chromium`.
- **Windows: do not use `--reload`.** With `--reload`, uvicorn switches to a selector event loop that cannot launch Chromium (`NotImplementedError`, `DOM context length: 0`). It also restarts whenever a test script is written to `playwright_scripts/`, which kills the running test (`Script exited with code 3221225786`), and the restart can fail with `WinError 87`. Run `uv run uvicorn app.main:app --port 8000` and restart it manually after code changes. See "When to use `--reload` (Windows)" in Part E.
