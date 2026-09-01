# PBL 2.2 - Run Guide

This repository has two separate apps:

- `backend` (FastAPI)
- `frontend` (Vite + React)

Run them in separate terminals.

## 1) Start backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

Quick health check:

```bash
curl http://127.0.0.1:8000/
```

Expected response:

```json
{"message":"Agentic Testing System Running"}
```

## 2) Start frontend

```bash
cd frontend
npm run dev
```

Frontend URL: `http://localhost:5173`

## Common startup mistakes

- Running `npm run dev` from repo root (fails because root has no `package.json`).
- Running backend with system Python that does not have `uvicorn`.
- Not running backend and frontend in separate terminals.

## 3) System Architecture

Below is the updated system design architecture detailing both the UI Testing and Security Testing pipelines.

```mermaid
flowchart TB
    User((User))
    
    subgraph Frontend["Frontend (Vite + React)"]
        UI[Dashboard UI]
    end
    
    subgraph Backend["Backend (FastAPI / Uvicorn)"]
        Router[API Router]
        
        subgraph UITesting["UI Testing Agent"]
            UIGen[Test Generation Service]
            UIRun[Test Run Service]
            PWGen[Playwright Generator]
            PWRun[Playwright Subprocess]
        end
        
        subgraph SecurityTesting["Security Testing Agent"]
            SecGen[Security Generation Service]
            SecRun[Security Run Service]
            SecCheck[Predefined Python Checkers]
            ZapScan[OWASP ZAP Scanner Module]
        end
        
        DB[Database Repositories]
    end
    
    subgraph External["External Services"]
        LLM[LLM / LM Studio / Groq]
        Docker[Docker Engine]
        ZAPContainer[zaproxy/zap2docker-stable]
    end
    
    subgraph Database["MongoDB (Local)"]
        Mongo[(MongoDB Database)]
    end

    User -->|Interacts| UI
    UI -->|REST API| Router
    Router -->|/generate| UIGen
    Router -->|/execute| UIRun
    Router -->|/security/generate| SecGen
    Router -->|/security/.../execute| SecRun
    Router -->|/security/zap-scan| ZapScan
    
    UIGen -->|Prompts for UI Tests| LLM
    UIRun -->|Calls| PWGen
    PWGen -->|Generates Script| LLM
    UIRun -->|Executes Script| PWRun
    
    SecGen -->|Prompts for Defensive Tests| LLM
    SecRun -->|Executes| SecCheck
    ZapScan -->|Spawns Container| Docker
    Docker -->|Runs Baseline Scan| ZAPContainer
    
    UIGen --> DB
    UIRun --> DB
    SecGen --> DB
    SecRun --> DB
    ZapScan --> DB
    
    DB <--> Mongo
```

## 4) Database Connectivity & Schema

The following diagram details the collections inside MongoDB and how the backend repositories interact with them.

```mermaid
erDiagram
    DATABASE ||--o{ PROJECTS : contains
    DATABASE ||--o{ TEST_CASES_PROJECT : contains
    DATABASE ||--o{ SECURITY_TESTS_PROJECT : contains
    
    PROJECTS {
        ObjectId _id PK
        string name
        string description
        string url
        datetime created_at
        datetime updated_at
    }
    
    TEST_CASES_PROJECT {
        ObjectId _id PK
        string project_id FK
        string test_id
        string name
        string description
        array steps
        string status
        datetime created_at
        datetime updated_at
    }
    
    SECURITY_TESTS_PROJECT {
        ObjectId _id PK
        string project_id FK
        string test_id
        string title
        string category
        string target
        string test_type
        string status "PASS / FAIL / WARNING"
        string finding
        string evidence
        string recommendation
    }
    
    ProjectRepository ||--o{ PROJECTS : Manages
    TestCaseRepository ||--o{ TEST_CASES_PROJECT : "Dynamic Collection"
    SecurityTestCaseRepository ||--o{ SECURITY_TESTS_PROJECT : "Dynamic Collection"
```
