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
- **LLMs (LMStudio / Groq)**: The LLMs are the brains behind analyzing UI contexts and outputting runnable python code.
- **ChromaDB**: A vector database used for Retrieval-Augmented Generation (RAG) to store and retrieve UI elements so the LLMs have accurate, up-to-date DOM structures to reference when writing code.

---

## 2. Core Components & Workflows

### A. Test Generation & RAG Ingestion (`test_generation_service.py`)
When a test generation request is triggered for a URL, the system doesn't just guess what the webpage looks like.
1. **Scraping**: Playwright headless browser visits the URL and extracts all interactive elements (buttons, inputs, links).
2. **Knowledge Base (RAG)**: These elements are grouped and injected into the ChromaDB vector database via the `KnowledgeManager`.
3. **LLM Generation**: The interactive elements are bundled into a prompt and sent to the LLM. The LLM is instructed to return high-quality QA test cases in JSON format.
4. **Storage**: The structured test cases are saved to MongoDB.

### B. Playwright Script Generation (`playwright_generator.py`)
Once a test case is selected to run, the system must translate English steps into executable Python code.
1. **Deterministic vs. LLM Engine**: 
   - If the test steps are structured (e.g. knowing exactly what selector to click), the system uses a **Deterministic Generator** to build the python file programmatically (`can_generate_deterministically`). This is extremely fast and avoids LLM hallucination.
   - If the test steps are natural language ("instruction" steps), the system falls back to the **LLM Generator**.
2. **Retrieval-Augmented Generation (RAG)**: If using the LLM, the system queries the `KnowledgeManager` using the test steps as a search query. ChromaDB returns the **top 10 most relevant UI elements** from the page. This prevents the LLM from hallucinating UI selectors (`#login-btn` instead of `.submit-auth`) by grounding it in reality.
3. **Robust Script Creation**: The generator wraps the execution in a `sync_playwright` block, takes DOM snapshots before and after, captures a screenshot, and includes safety catches for things like Wait/Input loops (e.g., waiting for User Captchas or 2FA).

### C. Execution & Reporting (`test_run_service.py`)
1. **Running the Code**: The newly generated `.py` script is saved as an artifact and executed as a sub-process.
2. **Status Evaluation**: 
   - Exit code `0` = Passed.
   - Exit code `1` = Failed.
   - Exit code `2` = Waiting (needs missing inputs like passwords or 2FA).
3. **Artifacts**: The execution bubbles up `__ARTIFACT_JSON__` payloads containing failure traces, run statuses, and DOM state hashes.

### D. The Intelligent Agent (`agent_service.py`)
For full autonomy, there is an overarching 'Orchestrator Agent'. 
- It examines the current state of a Project (e.g., "You have 10 test cases, 8 are passing").
- It uses a lightweight model (like Phi-4-mini) with a strict instruction to return JSON with a decision: `generate_tests`, `do_nothing`, or `finish`. 
- This simulates a QA manager continuously improving test coverage over time.

---

## 3. Potential Presentation Talking Points 🎤
If you're presenting to a technical audience, emphasize these architectural wins:

- **Highlight the RAG-assisted Scripting:** Explain how standard LLMs are terrible at writing Playwright scripts because they hallucinate CSS selectors. Your system solves this by scraping the DOM first, storing it in a vector DB (Chroma), and injecting the *actual* DOM elements into the LLM prompt right before generation.
- **Highlight the Deterministic Fallback:** Emphasize that you aren't calling the LLM blindly. If the system already knows what to click, you dynamically build the python AST without wasting tokens or causing unpredictable bugs.
- **Highlight "Waiting" States:** Show how the system handles the hard parts of automation. If an LLM encounters a password field, it doesn't guess "password123"—it pauses the script `sys.exit(2)`, bubbles up the required variables, and waits for secure user input.
