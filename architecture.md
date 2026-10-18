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
(Attempt LLM Generation)                               (Fallback to Deterministic Mode)
    |                                                               |
    v                                                               v
[ RAG Knowledge Manager ]                               [ parse_steps_strictly() ]
  - Converts User Steps -> Embeddings                     - if 'action' == click -> page.click()
  - Queries ChromaDB (Local Vector DB)                    - if 'action' == fill  -> page.fill()
  - Extracts HTML context / Selectors                     - Maps Env Variables
    |                                                               |
    v                                                               |
[ ChatOpenAI Client (LM Studio) ]                                   |
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
[ Visual Snapshot Validator ] ---> (Parses DOM After/Screenshots + Evaluates HTML Outcomes)
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
This is the core "intelligence" of the platform that bridges natural language to Python AST.
It operates in two dynamic phases:
1. **The LLM RAG Iteration**: 
   - A step array is piped to the `KnowledgeManager` which references `ChromaDB` containing pre-scanned knowledge or component structures for the target page. 
   - Uses `qwen2.5-coder` (or Llama/DeepSeek) served exclusively through local API endpoints (such as `LM Studio`).
   - The LLM strictly generates syntactic `playwright.sync_api` commands. It is explicitly programmed **never** to use unstable locator structures like `page.query_selector()` (which returns `NoneTypes` and crashes processes), favoring `page.locator().click()` setups.
2. **The Deterministic Fallback**:
   - If the LLM throws a generation error or is offline, the generator routes identically to a rigid deterministic Python string template. It hard-maps JSON actions such as `{"action": "click", "selector": "#id"}` directly into Playwright syntax.

### 4. Playwright Subprocess Shell
Instead of running generated code dangerously inside the main Uvicorn loop, the system streams the generated raw python string into a safe python Subprocess.
- **Artifact Standard Out**: The sandboxed script is designed to print structural dictionaries tagged with `__ARTIFACT_JSON__`. 
- **DOM Snapshots**: Playwright scripts take a localized snapshot of the HTML tree prior to acting (`dom_before.html`) and after execution (`dom_after.html`), checking these outputs against the expected parameters without making secondary LLM trips.

### 5. Backend Testing Structure
- Uses `pytest` standard.
- Models explicitly include `__test__ = False` descriptors inside base PyDantic models (`TestStep`, `TestCaseInDB`) to avoid triggering false-positive test collections. Integration (`test_api.py`) and Unit tests (`test_agents.py`, `test_services.py`) secure the functionality.
