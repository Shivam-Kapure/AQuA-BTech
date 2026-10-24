# AQUA (Agentic Quality Assurance) - System Architecture

AQUA is a dynamic, AI-driven web application designed to automatically generate, execute, and validate Playwright software tests from natural language steps.

## High-Level System Diagram

```text
===================================================================================================
                                 [1] FRONTEND (Vite / React / TailwindCSS)
===================================================================================================
                                                  |
 [ Dashboard UI ] <---(HTTP REST)---+             | -> [ NeedsActionModal ] (Prompts for Inputs)
                                    |             |         ^
 [ Test Case Management ]           |             |         | (Sends Runtime Variables via Env)
                                    v             |         |
===================================================================================================
                                 [2] BACKEND (FastAPI / Uvicorn / Python)
===================================================================================================
                                    |
                           (API Controllers)
                                    |
              +-------------------------------------------+
              |           [ Test Run Service ]            |
              +-------------------------------------------+
                                    |
                                    v
===================================================================================================
                         [3] SCRIPT GENERATION ENGINE (playwright_generator.py)
===================================================================================================
                                    |
    +-------------------------------+-------------------------------+
    |                                                               |
(LLM Generation, or cached script)                     (Self-Repair on script bug)
    |                                                               |
    v                                                               v
[ RAG Knowledge Manager ]                               [ classify failure ]
  - Converts User Steps -> Embeddings                     - strict-mode / TypeError / bad selector
  - Queries ChromaDB (Local Vector DB)                    - regenerate once with the error
  - Extracts HTML context / Selectors                     - re-run; real failures reported
    |                                                               |
    v                                                               |
[ LLM client (Groq / LM Studio) ]                                   |
  - Prompt: "Generate sync_playwright script"                       |
  - Restricts page.query_selector() usage                           |
    |                                                               |
    +-------------------------------+-------------------------------+
                                    |
                                    v
                     (Outputs: raw_script.py buffer)
                                    |
===================================================================================================
                           [4] EXECUTION ENGINE (playwright_runner.py)
===================================================================================================
                                    |
  Runs via Subprocess >>> `python -c "import sys; exec(...) "`
                                    |
      +-----------------------------+-----------------------------+
      |                             |                             |
[ Success ]                   [ Waiting ]                   [ Failed ]
- Captures DOM (Before)     - Needs Credentials/Inputs    - Exception / AssertionError
- Captures DOM (After)      - Exits early (Code 2)        - Invalid Selectors
- Takes Screenshot          - Prints __ARTIFACT_JSON__    - Bad Auth
      |                             |                             |
      |                 <-----------+                           -----
      |                (Flags Frontend Modal)                     |
      v                                                           v
===================================================================================================
                           [5] POST-EXECUTION VALIDATION & Storage
===================================================================================================
      |
[ Verdict ] ---> (Playwright assertions decide; LLM validator only for assertion-free scripts)
      |
      +---> [ MongoDB (Motor) ]
              - Updates `test_cases` Collection
              - Inserts Execution Metadata / Status ('passed', 'failed', 'waiting')
              |
              +--- (Sends final status block to Frontend)
```

---

## UI Testing Workflow

```mermaid
flowchart TD
    User[QA engineer] --> ProjectUI[React project detail page]
    ProjectUI -->|Generate short suite\nPOST /api/v1/generate/| GenerateRoute[FastAPI test-generation route]
    GenerateRoute --> UIGeneration[UI test-generation service]

    UIGeneration --> FetchDOM[Fetch target page HTML]
    FetchDOM --> DiscoverElements[Extract interactive DOM elements]
    DiscoverElements --> RAG[Knowledge manager\nStore page context]
    DiscoverElements --> LLM[LLM generates structured UI cases]
    RAG --> ExecutionGenerator[Playwright script generator]
    LLM --> Score[Decision-scoring service]
    Score --> TestDB[(MongoDB\nprojects and test cases)]
    TestDB --> ProjectUI

    ProjectUI -->|Run selected case\nPOST /api/v1/{project_name}/{test_id}| RunRoute[FastAPI test-run route]
    RunRoute --> ExecutionGenerator
    ExecutionGenerator --> Browser[Playwright browser execution]
    Browser --> Outcome{Execution outcome}
    Outcome -->|Passed or failed| PersistResult[Persist status, evidence, and failure reason]
    Outcome -->|Needs user input| NeedsAction[Mark case as waiting\nand return required inputs]
    NeedsAction --> Modal[NeedsActionModal]
    Modal -->|Resume with supplied inputs\nPOST /resume| RunRoute
    PersistResult --> TestDB

    ProjectUI -->|Coverage decision\nPOST /api/v1/agent/run-once| AgentRoute[Coverage-decision route]
    AgentRoute --> Agent[QA orchestration agent]
    Agent -->|generate_tests, do_nothing, or finish| ProjectUI
```

The UI generation flow uses the target page's DOM as context for LLM-created cases. Every newly generated case receives an explainable, bounded decision score before it is stored. Test execution can pause for a required human input rather than attempting to infer sensitive values.

## Security Testing Workflow

```mermaid
flowchart TD
    User[QA engineer] --> SecurityUI[React Security Testing page]
    SecurityUI --> SelectProject[Select a project and target URL]
    SelectProject -->|Generate security tests\nPOST /api/v1/security/generate| SecurityRoute[FastAPI security route]
    SecurityRoute --> SecurityGeneration[Security test-generation service]
    SecurityGeneration --> SecurityLLM[LLM creates structured defensive checks]
    SecurityLLM --> SecurityScore[Decision-scoring service\npriority, risk, coverage gap, execution cost]
    SecurityScore --> SecurityDB[(MongoDB\nsecurity test cases)]
    SecurityDB --> SecurityUI

    SecurityUI -->|Run safe check\nPOST /api/v1/security/{project_name}/{test_id}/execute| ExecuteRoute[Security execution route]
    ExecuteRoute --> SafeChecker[Built-in defensive checker]
    SafeChecker --> Result{Safe-check result}
    Result -->|Pass, fail, or warning| Findings[Finding and remediation guidance]
    Findings --> SecurityDB
    SecurityDB --> SecurityUI

    SecurityUI -->|Optional project scan\nPOST /api/v1/security/zap-scan/{project_name}| ZapRoute[ZAP scan route]
    ZapRoute --> Zap[Configured security scan]
    Zap --> Findings

    SecurityDB --> PDF[Project PDF export]
    PDF --> Report[Security-test results section]
```

The dedicated security page generates and executes defensive checks for a selected project's target URL. Individual checks run through the built-in safe checker; the user receives a status, a finding when applicable, and recommended remediation. Security-test results are included when the project PDF report is exported.

---

## Technical Stack & Modules in Detail

### 1. Frontend (React / Vite)
- **Frameworks**: Built using React and Vite for blazing-fast development. Styled using TailwindCSS to ensure a dynamic, responsive dark/light developer dashboard.
- **State Management & Data Fetching**: Utilizes `react-query` to maintain a living sync between the application UI and the FastAPI backend.
- **Special Interactions (`NeedsActionModal`)**: One of the core features of the system. If an automated script hits a login portal and does not know the credentials, the backend pauses execution, signals a "Waiting" status, and the frontend pops up a `NeedsActionModal`. The user inputs variables which are passed down to the Playwright subprocess as secure environmental variables.

### 2. Backend API (FastAPI)
- **Framework**: `FastAPI` managed by `Uvicorn`, executing completely asynchronously.
- **Configuration Layers**: Uses Pydantic V2 `SettingsConfigDict` to load and maintain settings. Includes connection mappings to MongoDB and Local AI logic variables.
- **Database (`app/db`)**: Async MongoDB operations via the `Motor` client, structured into repository patters like `ProjectRepository` and `TestCaseRepository`.

### 3. Script Generation Engine (`playwright_generator.py`)
This is the core "intelligence" of the platform that bridges natural language to executable Playwright code.
1. **The LLM RAG Iteration**:
   - A step array is piped to the `KnowledgeManager`, which queries `ChromaDB` (ONNX all-MiniLM-L6-v2 embeddings) for the target page's element structures.
   - Scripts are written by the configured agent model through the shared LLM client: Groq (`openai/gpt-oss-120b`, falling back to `openai/gpt-oss-20b` on daily limits) by default, or a local OpenAI-compatible server such as LM Studio.
   - The LLM strictly generates `playwright.sync_api` commands. It is explicitly instructed **never** to use unstable locator structures like `page.query_selector()`, to keep every locator matching exactly one element, not to guess message wording, and to create a fresh account when the target offers sign-up instead of guessing credentials.
2. **Self-Repair and Caching** (replaces the former deterministic fallback):
   - If a run fails because of a bug in the generated script itself (strict-mode violation, `TypeError`, invalid arguments, a value used as a selector), the script is regenerated once with the error as feedback and re-run.
   - Scripts from passing runs are cached on the test case and reused for later runs without an LLM call.
   - If no script can be written (for example the LLM is rate-limited), the test fails with that reason; no template script is run.

### 4. Playwright Subprocess Shell
Instead of running generated code dangerously inside the main Uvicorn loop, the system streams the generated raw python string into a safe python Subprocess.
- **Artifact Standard Out**: The sandboxed script is designed to print structural dictionaries tagged with `__ARTIFACT_JSON__`. 
- **DOM Snapshots**: Playwright scripts take a localized snapshot of the HTML tree prior to acting (`dom_before.html`) and after execution (`dom_after.html`). The script's own assertions decide pass/fail; an LLM verdict on the visible (hidden-element-aware) page text is used only when a passing script contains no assertions.

### 5. Backend Testing Structure
- Uses `pytest` standard.
- Models explicitly include `__test__ = False` descriptors inside base PyDantic models (`TestStep`, `TestCaseInDB`) to avoid triggering false-positive test collections. Integration (`test_api.py`) and Unit tests (`test_agents.py`, `test_services.py`) secure the functionality.

---

## Browser-testing flow

1. **Perception** — Playwright loads the target (`domcontentloaded`, then at most 5 s for network idle), `dom_parser` extracts interactive elements (capped at 80 elements / 6,000 characters, elements hidden on first load flagged `hidden='initially'`) and a visible-text excerpt (≤1,500 characters, nav/footer removed). Elements are indexed in Chroma for script generation.
2. **Generation** — the LLM produces cases in batches of five (Quick 5, Standard 10, Detailed 20), each batch with its own focus and the names already generated. AQuA assigns IDs `TC001…`. The project's description (the "Short prompt") is passed as authoritative context to generation, script writing and verdicts.
3. **Script writing** — the LLM writes a Playwright script per case with RAG selectors and prompt rules (strict-mode-safe locators, no guessed message wording, real Playwright APIs only, self-registration when sign-up exists, `domcontentloaded` navigation).
4. **Execution** — the script runs in a subprocess using the backend's Python, a minimal environment (UTF-8, no application secrets) and the run timeout.
5. **Verdict** — a failing script is `failed` with its real error; a passing script with assertions is `passed`; only assertion-free scripts are judged by the LLM on visible (hidden-element-aware) page text. Scripts asking for inputs become `waiting` ("Need action"); asking again for inputs already supplied is reported as `failed`.
6. **Self-repair and cache** — failures caused by the script itself (strict-mode violations, `TypeError`, invalid keyword arguments, a value used as a selector, …) are regenerated once with the error as feedback (`llm_repaired`). Passing LLM scripts are cached on the test case and reused (`cached`); a failing cached script is discarded. If no script can be written (e.g. LLM rate limit) the test fails with that reason instead of running a template script.

## LLM client

All LLM calls use `core/llm/openai_compat_client.py`: per-minute 429s are retried after the advertised delay, a daily cap switches to `LLM_FALLBACK_MODEL` (exhausted models are skipped for the rest of the window), at most `LLM_MAX_CONCURRENCY` requests run at once, `reasoning_effort` is sent to `gpt-oss` models, and `<think>` blocks are stripped. Provider rate limits reach clients as HTTP 503.

## Cloud deployment

The cloud deployment runs the frontend on Vercel (with `/api/*` rewritten to the backend, so the browser stays same-origin), the backend container on Google Cloud Run (max one instance because the job queue is process-local; disk is ephemeral), the Circle Social demo target on Render, and MongoDB on Atlas. See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md). Keep `AUTH_SECRET_KEY` in the environment or a managed secret store; do not commit runtime `.env` files.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for commands, health checks, scaling limitations, and security notes.
