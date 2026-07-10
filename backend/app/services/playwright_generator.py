"""
Generate a runnable Playwright Python script from a test case using the LLM.
Uses LangChain ChatOpenAI (LM Studio compatible) to produce code-only output.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.rag.knowledge_manager import KnowledgeManager


SYSTEM_PROMPT = """You are an agentic Playwright test generator. You output only runnable Python code, no markdown, no explanation.

Requirements for the script:
- Use ONLY the synchronous API: from playwright.sync_api import sync_playwright, expect (we use sync for subprocess execution).
- The script must: launch browser (chromium, headless=True), create a page, goto the given URL, then perform each step in order.
- Map natural language steps to Playwright calls, e.g. "Click on the login button" -> page.click("button:has-text('Login')") or page.click("#login"); "Enter username" -> page.fill("input[name=username]", "testuser"); "Open the target URL" -> already done with goto.
- After performing all steps, assert the expected result (e.g. check that the page contains the expected text or element). Use expect from playwright.sync_api or assert with page content.
- Use sync_playwright() and run everything inside a with block. At the end, close the browser.
- If the script fails (exception or assertion), exit with non-zero (sys.exit(1)); if all steps and assertions pass, exit 0 (sys.exit(0)).
- Prefer robust selectors: get_by_role, get_by_text, get_by_label; fallback to CSS.
- NEVER use page.query_selector() as it can return None and cause 'NoneType' errors. ALWAYS use page.locator() and expect() for assertions.
- Do not use input() or any interactive stdin. No external files. Single file script only.
- Start the script with: from playwright.sync_api import sync_playwright, expect\nimport sys, os, json, hashlib, traceback

INPUT AND ASSERTION POLICY:
- For negative login/input validation scenarios (invalid credentials, blank fields, malformed values), DO run the test with clearly invalid/blank values and assert an error state.
- Error state can be inline on the same page (text/banner/aria-invalid) OR via navigation. Do not assume navigation is required.
- For positive/protected auth flows, do not guess real credentials. Use TEST_USERNAME (or TEST_EMAIL) and TEST_PASSWORD from env.
- If a positive auth flow needs credentials and they are missing, emit waiting with required_inputs and exit code 2.
- For non-auth non-sensitive fields, reasonable dummy values are allowed when needed.

WAITING / FURTHER INPUT REQUIRED:
- When user input is required (credentials/OTP/captcha), you must output the exact python syntax:
  print('__ARTIFACT_JSON__=' + json.dumps({"status":"waiting","required_inputs":[{"name":"TEST_USERNAME","hint":"..."},{"name":"TEST_PASSWORD","hint":"..."}]}))
  Then exit with sys.exit(2).
- Waiting is NOT a failure.
- Capture DOM before and after steps:
  - After goto, compute dom_before = page.content(), dom_hash_before = sha256(dom_before)
  - After steps, compute dom_after, dom_hash_after
  - To emit results, you must output the exact python syntax:
    print('__ARTIFACT_JSON__=' + json.dumps({"dom_hash_before": "...", "dom_hash_after": "...", "dom_changed": True, "artifact_dir": "...", "status": "passed"}))
  - If ARTIFACT_DIR env var is set, write dom_before.html and dom_after.html in it and a screenshot.png at the end.
- End with explicit sys.exit(0) on success.
Output ONLY the Python script. No ```python wrapper, no other text."""


def _step_text(step: Any) -> str:
    if isinstance(step, dict):
        return str(step.get("value") or step.get("action") or step)
    return str(getattr(step, "value", None) or getattr(step, "action", None) or step)


def build_user_prompt(
    *,
    test_name: str,
    url: str,
    description: str,
    steps: list[str],
    expected_result: str,
    rag_context: str = "",
) -> str:
    steps_block = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
    
    context_block = f"""
Here are some relevant UI elements from the page that might help you write accurate selectors for the steps above:
{rag_context}
""" if rag_context else ""

    return f"""Generate a single Playwright (sync_api) Python script for this test case.

Test name: {test_name}
URL: {url}
Description: {description}

Steps to perform (in order):
{steps_block}

Expected result to assert: {expected_result}
{context_block}
Output only the Python script. Use sync_playwright. On success exit 0, on failure exit 1 and print error to stderr."""


async def generate_playwright_script(
    *,
    test_name: str,
    url: str,
    description: str,
    steps: list[Any],
    expected_result: str,
    runtime_input_keys: list[str] | None = None,
) -> str:
    """Generate a runnable Playwright Python script from test case fields using LLM."""
    steps_str = [_step_text(s) for s in steps]
    
    # Retrieve relevant UI context from RAG
    km = KnowledgeManager()
    query = " ".join(steps_str)
    rag_context = km.retrieve_elements_for_steps(url, query, k=10)
    
    user_content = build_user_prompt(
        test_name=test_name,
        url=url,
        description=description or "",
        steps=steps_str,
        expected_result=expected_result or "Success",
        rag_context=rag_context,
    )
    if runtime_input_keys:
        keys_block = ", ".join(sorted(set(runtime_input_keys)))
        user_content += (
            "\n\nRuntime input keys available as environment variables for this run: "
            f"{keys_block}"
        )

    # Same URL as test generation; the request "model" parameter selects Phi for script generation.
    base_url = (settings.AGENT_LMSTUDIO_URL or settings.LMSTUDIO_URL).rstrip("/") + "/v1"
    model = settings.AGENT_LLM_MODEL or settings.LLM_MODEL
    llm = ChatOpenAI(
        api_key="lm-studio",
        base_url=base_url,
        model=model,
        temperature=0.1,
        max_tokens=2048,
    )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
    response = await llm.ainvoke(messages)
    raw = response.content if hasattr(response, "content") else str(response)

    # Strip markdown code fence if present
    text = raw.strip()
    if text.startswith("```"):
        if text.startswith("```python"):
            text = text[9:]
        else:
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def _json_line(obj: dict[str, Any]) -> str:
    return "__ARTIFACT_JSON__=" + json.dumps(obj, ensure_ascii=False)


def _escape_py_string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _selector_expr(selector: str) -> str:
    sel = selector.strip()
    if sel.startswith("role="):
        rest = sel[len("role=") :].strip()
        parts = [p.strip() for p in rest.split("|") if p.strip()]
        role = parts[0] if parts else "button"
        name = None
        for p in parts[1:]:
            if p.startswith("name="):
                name = p[len("name=") :].strip()
        if name:
            return f"page.get_by_role({_escape_py_string(role)}, name={_escape_py_string(name)})"
        return f"page.get_by_role({_escape_py_string(role)})"

    if sel.startswith("label="):
        name = sel[len("label=") :].strip()
        return f"page.get_by_label({_escape_py_string(name)})"

    if sel.startswith("text="):
        txt = sel[len("text=") :].strip()
        return f"page.get_by_text({_escape_py_string(txt)})"

    return f"page.locator({_escape_py_string(sel)})"


def _needs_auth_inputs(test_name: str, description: str, steps: list[Any]) -> bool:
    hay = " ".join(
        [
            test_name or "",
            description or "",
            " ".join(_step_text(s) for s in (steps or [])),
        ]
    ).lower()
    auth_terms = ("login", "log in", "sign in", "auth", "username", "email", "password")
    return any(t in hay for t in auth_terms)


def can_generate_deterministically(steps: list[Any]) -> bool:
    """
    True if the test steps look structured enough to avoid an LLM call.

    We treat steps as deterministic if at least one step provides a selector or assertion,
    and no step is a freeform "instruction" without selector/assertion.
    """
    if not steps:
        return False

    saw_structure = False
    for s in steps:
        if isinstance(s, dict):
            action = str(s.get("action") or "")
            selector = s.get("selector")
            assertion = s.get("assertion")
        else:
            action = str(getattr(s, "action", "") or "")
            selector = getattr(s, "selector", None)
            assertion = getattr(s, "assertion", None)

        if selector or assertion:
            saw_structure = True
        if action.lower() == "instruction" and not selector and not assertion:
            return False
    return saw_structure


def generate_playwright_script_deterministic(
    *,
    test_name: str,
    url: str,
    description: str,
    steps: list[Any],
    expected_result: str,
) -> str:
    """
    Deterministic Playwright script generator (no LLM).

    Supported step schema:
    - action: click | fill | type | press | check | uncheck | select | wait_for | assert_text | assert_visible
    - selector: "css=...", "#id", ".class", "text=...", "label=...", "role=button|name=Login"
    - value: text to fill/type/select or key for press
    - assertion: {"type": "text_contains"|"visible", "selector": "...", "text": "..."}
    """
    lines: list[str] = []
    auth_needed = _needs_auth_inputs(test_name, description, steps)
    text_for_intent = " ".join([test_name or "", description or "", expected_result or ""]).lower()
    expect_inline_error = any(
        t in text_for_intent for t in ("invalid", "wrong", "incorrect", "error", "required", "failed")
    )
    lines.append("from playwright.sync_api import sync_playwright, expect")
    lines.append("import sys, os, json, hashlib, traceback")
    lines.append("")
    lines.append("def _sha256(s: str) -> str:")
    lines.append("    return hashlib.sha256(s.encode('utf-8', errors='ignore')).hexdigest()")
    lines.append("")
    lines.append("def _artifact_dir() -> str | None:")
    lines.append("    d = os.environ.get('ARTIFACT_DIR')")
    lines.append("    if not d:")
    lines.append("        return None")
    lines.append("    os.makedirs(d, exist_ok=True)")
    lines.append("    return d")
    lines.append("")
    lines.append("def _emit_artifact(payload: dict) -> None:")
    lines.append("    print('__ARTIFACT_JSON__=' + json.dumps(payload, ensure_ascii=False))")
    lines.append("")
    lines.append("def main() -> int:")
    lines.append("    artifact_dir = _artifact_dir()")
    lines.append("    with sync_playwright() as p:")
    lines.append("        browser = p.chromium.launch(headless=True)")
    lines.append("        page = browser.new_page()")
    lines.append("        try:")
    lines.append(f"            page.goto({_escape_py_string(url)}, wait_until='domcontentloaded')")
    lines.append("            dom_before = page.content()")
    lines.append("            dom_hash_before = _sha256(dom_before)")
    lines.append("            if artifact_dir:")
    lines.append("                with open(os.path.join(artifact_dir, 'dom_before.html'), 'w', encoding='utf-8') as f:")
    lines.append("                    f.write(dom_before)")
    lines.append("")
    lines.append("            test_username = os.environ.get('TEST_USERNAME') or os.environ.get('TEST_EMAIL')")
    lines.append("            test_password = os.environ.get('TEST_PASSWORD')")
    lines.append("            required_inputs = []")
    if auth_needed:
        lines.append("            if not test_username:")
        lines.append("                required_inputs.append({'name': 'TEST_USERNAME', 'hint': 'Login username or email'})")
        lines.append("            if not test_password:")
        lines.append("                required_inputs.append({'name': 'TEST_PASSWORD', 'hint': 'Login password'})")
    lines.append("")

    def get_fields(step: Any) -> tuple[str, str | None, Any, dict[str, Any] | None]:
        if isinstance(step, dict):
            return (
                str(step.get("action") or ""),
                step.get("selector"),
                step.get("value"),
                step.get("assertion"),
            )
        return (
            str(getattr(step, "action", "") or ""),
            getattr(step, "selector", None),
            getattr(step, "value", None),
            getattr(step, "assertion", None),
        )

    for idx, raw_step in enumerate(steps, start=1):
        action, selector, value, assertion = get_fields(raw_step)
        action_l = action.lower().strip()
        sel_l = str(selector or "").lower()
        value_env_name = f"TEST_STEP_{idx}_VALUE"
        use_runtime_value = False

        if action_l in ("fill", "type", "select", "select_option") and value is None:
            if "password" in sel_l:
                lines.append("            if not test_password:")
                lines.append("                required_inputs.append({'name': 'TEST_PASSWORD', 'hint': 'Password value for login/auth step'})")
                use_runtime_value = True
            elif any(k in sel_l for k in ("email", "username", "user", "login")):
                lines.append("            if not test_username:")
                lines.append("                required_inputs.append({'name': 'TEST_USERNAME', 'hint': 'Username or email for login/auth step'})")
                use_runtime_value = True
            else:
                lines.append(
                    f"            if not os.environ.get({_escape_py_string(value_env_name)}):"
                )
                lines.append(
                    f"                required_inputs.append({{'name': {_escape_py_string(value_env_name)}, 'hint': 'Value for step {idx}: {action}'}})"
                )
                use_runtime_value = True

        if assertion and isinstance(assertion, dict):
            atype = str(assertion.get("type") or "").lower()
            aselector = assertion.get("selector") or selector
            atext = assertion.get("text") or assertion.get("value")
            if aselector and atype in ("visible", "is_visible"):
                lines.append(f"            expect({_selector_expr(str(aselector))}).to_be_visible()")
                continue
            if atype in ("text_contains", "contains") and atext is not None:
                if aselector:
                    lines.append(f"            expect({_selector_expr(str(aselector))}).to_contain_text({_escape_py_string(str(atext))})")
                else:
                    lines.append(f"            expect(page).to_have_text({_escape_py_string(str(atext))})")
                continue

        if action_l in ("assert_text", "assert_text_contains"):
            if selector is None or value is None:
                continue
            lines.append(f"            expect({_selector_expr(str(selector))}).to_contain_text({_escape_py_string(str(value))})")
            continue
        if action_l in ("assert_visible",):
            if selector is None:
                continue
            lines.append(f"            expect({_selector_expr(str(selector))}).to_be_visible()")
            continue

        if action_l in ("click",):
            if selector is None:
                continue
            lines.append(f"            {_selector_expr(str(selector))}.click()")
            continue
        if action_l in ("fill", "type"):
            if selector is None:
                continue
            if value is not None:
                val = str(value)
                lines.append(f"            {_selector_expr(str(selector))}.fill({_escape_py_string(val)})")
            elif "password" in sel_l:
                lines.append(f"            {_selector_expr(str(selector))}.fill(test_password)")
            elif any(k in sel_l for k in ("email", "username", "user", "login")):
                lines.append(f"            {_selector_expr(str(selector))}.fill(test_username)")
            elif use_runtime_value:
                lines.append(
                    f"            {_selector_expr(str(selector))}.fill(os.environ.get({_escape_py_string(value_env_name)}))"
                )
            continue
        if action_l in ("press",):
            if selector is None:
                continue
            key = "Enter" if value is None else str(value)
            lines.append(f"            {_selector_expr(str(selector))}.press({_escape_py_string(key)})")
            continue
        if action_l in ("check", "uncheck"):
            if selector is None:
                continue
            fn = "check" if action_l == "check" else "uncheck"
            lines.append(f"            {_selector_expr(str(selector))}.{fn}()")
            continue
        if action_l in ("select", "select_option"):
            if selector is None:
                continue
            if value is not None:
                val = str(value)
                lines.append(f"            {_selector_expr(str(selector))}.select_option({_escape_py_string(val)})")
            elif use_runtime_value:
                lines.append(
                    f"            {_selector_expr(str(selector))}.select_option(os.environ.get({_escape_py_string(value_env_name)}))"
                )
            continue
        if action_l in ("wait_for", "wait_for_selector"):
            if selector is not None:
                lines.append(f"            page.wait_for_selector({_escape_py_string(str(selector))}, timeout=10000)")
            continue

        # Unknown actions: ignore deterministically (LLM should be used for better mapping)

    lines.append("            if required_inputs:")
    lines.append("                _emit_artifact({")
    lines.append(f"                    'test_name': { _escape_py_string(test_name) },")
    lines.append("                    'status': 'waiting',")
    lines.append("                    'required_inputs': required_inputs,")
    lines.append("                    'dom_hash_before': dom_hash_before,")
    lines.append("                    'dom_hash_after': None,")
    lines.append("                    'dom_changed': None,")
    lines.append("                    'artifact_dir': artifact_dir,")
    lines.append("                })")
    lines.append("                return 2")
    lines.append("")
    if expect_inline_error:
        lines.append("            page_text_l = page.locator('body').inner_text().lower()")
        lines.append("            assert any(k in page_text_l for k in ['invalid', 'wrong', 'incorrect', 'error', 'required', 'failed']), 'Expected inline error message was not found'")
        lines.append("")

    # If we got here, assertions should have validated expected behavior already.
    # Add a lightweight expected_result check if it's not empty.
    exp = (expected_result or "").strip()
    if exp:
        lines.append(f"            # Expected result fallback check")
        lines.append(f"            expect(page.locator('body')).to_contain_text({_escape_py_string(exp)})")

    lines.append("")
    lines.append("            dom_after = page.content()")
    lines.append("            dom_hash_after = _sha256(dom_after)")
    lines.append("            if artifact_dir:")
    lines.append("                with open(os.path.join(artifact_dir, 'dom_after.html'), 'w', encoding='utf-8') as f:")
    lines.append("                    f.write(dom_after)")
    lines.append("                try:")
    lines.append("                    page.screenshot(path=os.path.join(artifact_dir, 'screenshot.png'), full_page=True)")
    lines.append("                except Exception:")
    lines.append("                    pass")
    lines.append("            _emit_artifact({")
    lines.append(f"                'test_name': { _escape_py_string(test_name) },")
    lines.append("                'status': 'passed',")
    lines.append("                'dom_hash_before': dom_hash_before,")
    lines.append("                'dom_hash_after': dom_hash_after,")
    lines.append("                'dom_changed': dom_hash_before != dom_hash_after,")
    lines.append("                'artifact_dir': artifact_dir,")
    lines.append("            })")
    lines.append("            return 0")
    lines.append("        except Exception as e:")
    lines.append("            dom_hash_before = None")
    lines.append("            dom_hash_after = None")
    lines.append("            try:")
    lines.append("                dom_hash_before = _sha256(page.content())")
    lines.append("            except Exception:")
    lines.append("                pass")
    lines.append("            payload = {")
    lines.append(f"                'test_name': { _escape_py_string(test_name) },")
    lines.append("                'status': 'failed',")
    lines.append("                'dom_hash_before': dom_hash_before,")
    lines.append("                'dom_hash_after': dom_hash_after,")
    lines.append("                'dom_changed': None,")
    lines.append("                'artifact_dir': artifact_dir,")
    lines.append("                'error': str(e),")
    lines.append("                'traceback': traceback.format_exc(),")
    lines.append("            }")
    lines.append("            _emit_artifact(payload)")
    lines.append("            print(payload['traceback'], file=sys.stderr)")
    lines.append("            return 1")
    lines.append("        finally:")
    lines.append("            try:")
    lines.append("                browser.close()")
    lines.append("            except Exception:")
    lines.append("                pass")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    sys.exit(main())")
    return "\n".join(lines)


def generate_waiting_script_for_clarification(
    *,
    test_name: str,
    url: str,
    steps: list[Any],
) -> str:
    """
    Deterministic waiting script for unstructured steps.
    It intentionally avoids LLM/random interpretation and asks for required details.
    """
    needed: list[dict[str, str]] = []
    if _needs_auth_inputs(test_name, "", steps):
        needed.extend(
            [
                {"name": "TEST_USERNAME", "hint": "Login username or email"},
                {"name": "TEST_PASSWORD", "hint": "Login password"},
            ]
        )
    if not needed:
        needed.append(
            {
                "name": "TEST_DATA",
                "hint": "Provide required runtime test input values for this case.",
            }
        )

    lines = [
        "from playwright.sync_api import sync_playwright",
        "import sys, os, json, hashlib",
        "",
        "def _sha256(s: str) -> str:",
        "    return hashlib.sha256(s.encode('utf-8', errors='ignore')).hexdigest()",
        "",
        "def _emit(payload: dict) -> None:",
        "    print('__ARTIFACT_JSON__=' + json.dumps(payload, ensure_ascii=False))",
        "",
        "with sync_playwright() as p:",
        "    browser = p.chromium.launch(headless=True)",
        "    page = browser.new_page()",
        "    try:",
        f"        page.goto({_escape_py_string(url)}, wait_until='domcontentloaded')",
        "        dom_before = page.content()",
        "        _emit({",
        f"            'test_name': {_escape_py_string(test_name)},",
        "            'status': 'waiting',",
        f"            'required_inputs': {json.dumps(needed, ensure_ascii=False)},",
        "            'dom_hash_before': _sha256(dom_before),",
        "            'dom_hash_after': None,",
        "            'dom_changed': None,",
        "            'artifact_dir': os.environ.get('ARTIFACT_DIR'),",
        "        })",
        "        sys.exit(2)",
        "    finally:",
        "        browser.close()",
    ]
    return "\n".join(lines)
