# Agentic Testing System - Project Walkthrough

This document serves as a presentation guide to help you explain the architecture, workflows, and core technologies of your Agentic Testing System.

## 1. High-Level Overview
The system is an **autonomous QA testing orchestrator**. Instead of manually writing and maintaining end-to-end tests, the user simply provides a target URL. The system autonomously:
1. Crawls the target application.
2. Generates comprehensive test cases (happy path, edge cases, negative tests).
3. Writes Playwright Python scripts for those test cases.
4. Executes the scripts and reports the results.

### Core Technologies
- **FastAPI / Python**: The backend web framework managing API routes and background tasks.
- **MongoDB**: Storage for Projects, Test Cases, and Run States.
- **Playwright**: A browser automation library used to scrape UI contexts and execute generated tests.
- **LLMs (Groq `openai/gpt-oss-120b` with `gpt-oss-20b` fallback, or LM Studio)**: The LLMs are the brains behind analyzing UI contexts and outputting runnable python code.
- **ChromaDB**: A vector database used for Retrieval-Augmented Generation (RAG) to store and retrieve UI elements so the LLMs have accurate, up-to-date DOM structures to reference when writing code. Embeddings use the ONNX all-MiniLM-L6-v2 model (no torch).

---

## 2. Core Components & Workflows

### A. Test Generation & RAG Ingestion (`test_generation_service.py`)
When a test generation request is triggered for a URL, the system doesn't just guess what the webpage looks like.
1. **Scraping**: Playwright headless browser visits the URL and extracts interactive elements (buttons, inputs, links, forms), flags elements hidden on first load, and reads a short excerpt of the visible text (instructions, demo credentials, rules). The context is capped so large sites stay within LLM limits.
2. **Knowledge Base (RAG)**: These elements are grouped and injected into the ChromaDB vector database via the `KnowledgeManager`.
3. **LLM Generation**: The elements, page text and the project's context are bundled into a prompt. Cases are generated in batches of five (Quick 5, Standard 10, Detailed 20), and AQuA assigns unique IDs (TC001…).
4. **Storage**: The structured test cases are saved to MongoDB.

### B. Playwright Script Generation (`playwright_generator.py`)
Once a test case is selected to run, the system must translate English steps into executable Python code.
1. **LLM Engine with cache**: Each test's script is written by the LLM. A script that passed before is cached and reused, so re-runs need no LLM call. If no script can be written (e.g. the LLM is rate-limited), the test is reported as failed with that reason — no template script is run.
2. **Retrieval-Augmented Generation (RAG)**: If using the LLM, the system queries the `KnowledgeManager` using the test steps as a search query. ChromaDB returns the **top 10 most relevant UI elements** from the page. This prevents the LLM from hallucinating UI selectors (`#login-btn` instead of `.submit-auth`) by grounding it in reality.
3. **Robust Script Creation**: The generator wraps the execution in a `sync_playwright` block, takes DOM snapshots before and after, captures a screenshot, and includes safety catches for things like Wait/Input loops (e.g., waiting for User Captchas or 2FA).

### C. Execution & Reporting (`test_run_service.py`)
1. **Running the Code**: The newly generated `.py` script is saved as an artifact and executed as a sub-process.
2. **Status Evaluation**:
   - Exit code `0` with assertions = Passed (the browser's result is authoritative; an LLM verdict is used only for scripts without assertions).
   - Exit code `1` = Failed, with the real Playwright error.
   - Exit code `2` = Waiting (needs missing inputs like passwords or 2FA).
   - **Self-repair**: if the failure is a bug in the script itself (ambiguous locator, invalid API call, a value used as a selector), the LLM fixes the script once and it is re-run.
3. **Artifacts**: The execution bubbles up `__ARTIFACT_JSON__` payloads containing failure traces, run statuses, and DOM state hashes.

### D. The Intelligent Agent (`agent_service.py`)
For full autonomy, there is an overarching 'Orchestrator Agent'.
- It examines the current state of a Project (e.g., "You have 10 test cases, 8 are passing").
- It uses the configured agent model (`AGENT_LLM_MODEL`, e.g. `openai/gpt-oss-120b` on Groq) with a strict instruction to return JSON with a decision: `generate_tests`, `do_nothing`, or `finish`. 
- This simulates a QA manager continuously improving test coverage over time.

---

## 3. Potential Presentation Talking Points 🎤
If you're presenting to a technical audience, emphasize these architectural wins:

- **Highlight the RAG-assisted Scripting:** Explain how standard LLMs are terrible at writing Playwright scripts because they hallucinate CSS selectors. Your system solves this by scraping the DOM first, storing it in a vector DB (Chroma), and injecting the *actual* DOM elements into the LLM prompt right before generation.
- **Highlight Self-Healing and Trustworthy Verdicts:** Generated scripts can be wrong. AQuA separates script bugs (repaired once automatically) from real app failures (reported with the exact Playwright error), and lets the browser's assertions — not the LLM — decide pass/fail. Passing scripts are cached, so re-runs cost no tokens.
- **Highlight "Waiting" States:** Show how the system handles the hard parts of automation. If an LLM encounters a password field, it doesn't guess "password123": when the app offers sign-up the script creates a fresh account; otherwise it pauses the script `sys.exit(2)`, bubbles up the required variables, and waits for secure user input.
- **Highlight Free-Tier Resilience:** Rate limits are waited out, a daily cap switches to a fallback model, and concurrent LLM calls are limited — the system runs on Groq, Cloud Run, Vercel, Render and Atlas free tiers.
