# LM Studio setup and how to test

## Which model is used where

| Use case | Model | Config |
|----------|--------|--------|
| **Test case generation** (POST `/api/v1/generate/`) | **Llama** (e.g. llama-3-8b-instruct) | `LLM_MODEL`, `LMSTUDIO_URL` |
| **Playwright script generation** (when you run a single test) | **Phi** (e.g. phi-4-mini-instruct) | `AGENT_LLM_MODEL`, `AGENT_LMSTUDIO_URL` or `LMSTUDIO_URL` |
| **Agent orchestration** (POST `/api/v1/agent/run-once`) | **Phi** | Same as above |

- **Llama** = test case generation only (via `get_llm_client()` → `LLM_MODEL`).
- **Phi** = Playwright script generation + agent (via `get_agent_llm_client()` / LangChain with `AGENT_LLM_MODEL`).

## Single LM Studio URL (one server, both models)

LM Studio selects the model by the request **model** parameter. Use one URL; set `AGENT_LLM_MODEL` (e.g. phi-4-mini-instruct) so script generation requests use Phi.

## Setup (one server) 

1. In LM Studio, have both models available (e.g. Llama and Phi). Start the server (e.g. port 1234).

2. In `.env`:
   ```env
   LMSTUDIO_URL=http://localhost:1234
   LLM_MODEL=meta-llama-3-8b-instruct
   AGENT_LLM_MODEL=phi-4-mini-instruct
   PLAYWRIGHT_SCRIPT_OUTPUT_DIR=playwright_scripts
   ```
   Use the **exact model names** your LM Studio reports (e.g. from the API or UI).

3. **Test case generation** sends `model=LLM_MODEL` (Llama). **Playwright script generation** and **agent** send `model=AGENT_LLM_MODEL` (Phi). Same URL, different model name.

4. **Playwright scripts:** If `PLAYWRIGHT_SCRIPT_OUTPUT_DIR` is set, each run saves the generated script there; the API response includes `script_path`.

## How to test

### 1. Start the backend

```bash
cd backend
# If using venv: source .venv/bin/activate
uvicorn app.main:app --reload
```

### 2. Install Playwright browser (once)

```bash
playwright install chromium
```

### 3. Have MongoDB running

Default: `mongodb://localhost:27017`. Set `MONGODB_URI` in `.env` if needed.

### 4. Test case generation (Llama)

With **Llama** loaded in LM Studio (on 1234, or only instance):

```bash
curl -X POST http://localhost:8000/api/v1/generate/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "project_name": "Example"}'
```

You should get a JSON array of created test cases. If the model name or URL is wrong, you’ll get an LLM/connection error.

### 5. List test cases

```bash
curl http://localhost:8000/api/v1/test-cases/Example
```

Use the same `project_name` as above. Note one of the test `id` or `metadata.test_id` (e.g. `TC001`) for the next step.

### 6. Run a single test (Phi + Playwright)

The backend sends `model=AGENT_LLM_MODEL` (Phi) to the same LM Studio URL:

```bash
# Replace Example with your project name, and TC001 with a real test id or MongoDB _id
curl -X POST http://localhost:8000/api/v1/test/Example/TC001
```

Response will include `"status": "passed"` or `"status": "failed"` and, if failed, `"failure_reason"`. This flow uses **Phi** to generate the Playwright script, then runs the script; pass/fail is from the actual run, not an LLM decision.

### 7. (Optional) Agent run-once (Phi)

```bash
curl -X POST http://localhost:8000/api/v1/agent/run-once \
  -H "Content-Type: application/json" \
  -d '{"project_name": "Example", "url": "https://example.com"}'
```

Uses **Phi** to decide whether to generate tests; test generation itself still uses **Llama** when the agent chooses “generate_tests”.

## Quick checklist

- [ ] LM Studio server running (e.g. port 1234) with both models available.
- [ ] `.env` has `LLM_MODEL` and `AGENT_LLM_MODEL` set to exact names from LM Studio.
- [ ] `playwright install chromium` has been run.
- [ ] MongoDB is running.
