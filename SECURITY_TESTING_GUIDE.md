# AQUA Security Testing Agent: Documentation & Testing Guide

This document explains the recent implementation of the **Security Testing Agent** and how to test the newly added features locally. The security agent works in parallel with your existing UI testing agent and reuses the core architecture (MongoDB repositories, LLM integration, and FastAPI endpoints) while maintaining a strict boundary to prevent arbitrary payload execution.

---

## 1. What Has Been Implemented

The Security Testing Agent was implemented in three stages:

### Stage 1: Security Test Case Generation
We created a parallel pipeline to generate defensive security tests based on the application's DOM context.
- **Models:** Created `SecurityTestCaseCreate` and `SecurityTestCaseInDB` schemas in `app/models/security_test.py`.
- **Enums:** Strictly limited test types to `security_headers`, `cookie_security`, `input_validation`, `authentication_configuration`, and `information_disclosure`.
- **Database:** Added `SecurityTestCaseRepository` which stores cases in a `security_tests_{project_name}` collection.
- **Service:** Added `app/services/security_generation_service.py` to prompt the LLM to generate structured JSON without arbitrary exploit payloads.
- **API:** Added `POST /api/v1/security/generate` and `GET /api/v1/security/{project_name}` endpoints.

### Stage 2: Security Test Runner
Instead of using the LLM to generate executable attack payloads, the runner securely maps the generated `test_type` to predefined, deterministic Python checkers.
- **Checkers:** Implemented `check_security_headers`, `check_cookie_security`, `check_input_validation`, and `check_information_disclosure` in `app/services/security_checkers.py` using `httpx`.
- **Execution Service:** Added `app/services/security_run_service.py` to route the execution and update the database with rich structured results (`finding`, `evidence`, `recommendation`).
- **API:** Added `POST /api/v1/security/{project_name}/{test_id}/execute`.

### Stage 3: OWASP ZAP Baseline Scanner Integration
We integrated OWASP ZAP as an optional, non-destructive security scanner using Docker.
- **Docker Execution:** Uses the `zaproxy/zap2docker-stable` image to run `zap-baseline.py` in a contained environment with strict timeouts.
- **Target Safety:** The scanner extracts the target URL directly from the project's database configuration (`project.url`), preventing users from passing arbitrary URLs.
- **Integration:** The `zap_report.json` is parsed and mapped directly into the existing `SecurityTestCaseInDB` schema, allowing ZAP alerts to be viewed alongside custom generated tests.
- **API:** Added `POST /api/v1/security/zap-scan/{project_name}`.

---

## 2. How to Test Locally

Ensure your FastAPI server is running. You will also need LM Studio (or your configured LLM provider) running for Step 1, and Docker running for Step 3.

```bash
cd backend
uv run uvicorn app.main:app --reload
```

### Test Step 1: Generate Security Tests
First, generate the security tests for a project. This also sets the target URL for the project in the database.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/security/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "url": "https://example.com",
           "project_name": "TestProject"
         }'
```
*Note the `test_id` of one of the generated tests from the JSON response (e.g., `SEC001`).*

### Test Step 2: Execute a Specific Security Test
Run one of the custom Python security checkers against the generated test.

```bash
# Replace 'SEC001' with the actual test_id from the previous step
curl -X POST "http://127.0.0.1:8000/api/v1/security/TestProject/SEC001/execute"
```
**Expected Response:** A JSON object detailing the `status` (PASS/FAIL/WARNING), `severity`, `finding`, `evidence`, and `recommendation`.

### Test Step 3: Run the OWASP ZAP Baseline Scan
Trigger the ZAP scan. Ensure Docker is running. The baseline scan uses a spider and will take up to a few minutes to complete depending on the size of the target application.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/security/zap-scan/TestProject"
```
**Expected Response:** A JSON object containing `"message": "ZAP scan completed successfully"` along with a `"findings"` array containing all discovered alerts mapped to your database schema.

### Test Step 4: View All Generated & ZAP Tests
You can list all security tests (both LLM-generated and ZAP-discovered) for the project:

```bash
curl "http://127.0.0.1:8000/api/v1/security/TestProject"
```
