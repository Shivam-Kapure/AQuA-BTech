from app.core.browser.dom_parser import MAX_CONTEXT_CHARS, MAX_ELEMENTS, build_dom_context_string, extract_interactive_elements
from app.core.llm.rate_limits import is_daily_limit, retry_delay_s
from app.services.test_run_service import _is_script_bug


def test_retry_delay_parses_groq_durations() -> None:
    assert retry_delay_s("Please try again in 8.295s.") == 8.295
    assert retry_delay_s("Please try again in 23m20.5s.") == 1400.5
    assert retry_delay_s("no hint here") is None
    assert retry_delay_s("ignored", {"retry-after": "7"}) == 7.0


def test_daily_limit_detection() -> None:
    assert is_daily_limit("Rate limit reached ... on tokens per day (TPD): Limit 200000")
    assert not is_daily_limit("Rate limit reached ... on tokens per minute (TPM): Limit 8000")


def test_script_bug_detection() -> None:
    assert _is_script_bug('Error: strict mode violation: locator("button.like") resolved to 12 elements')
    assert _is_script_bug("TypeError: to_have_count() got an unexpected keyword argument 'greater_than'")
    assert not _is_script_bug("AssertionError: Locator expected to have text 'Welcome'")
    assert not _is_script_bug(None)
    # A value used as a selector (bare word that is not an HTML tag) is a script bug...
    assert _is_script_bug('Error: element(s) not found  Call log: - waiting for locator("testkapure")')
    # ...but a missing real element may be an app bug.
    assert not _is_script_bug('Error: element(s) not found  Call log: - waiting for locator("article")')
    assert not _is_script_bug('Error: element(s) not found  Call log: - waiting for locator("#composer")')


def test_dom_context_is_capped_and_marks_hidden_elements() -> None:
    links = "".join(f'<a href="/p{i}" class="{"x" * 200}">Link {i}</a>' for i in range(400))
    html = (
        '<form id="auth"><input name="username"><button id="login">Sign in</button></form>'
        '<button id="logout" class="hidden">Sign out</button>' + links
    )
    elements = extract_interactive_elements(html)
    assert len(elements) <= MAX_ELEMENTS
    # Forms, inputs and buttons survive the cap ahead of links.
    assert {"form", "input", "button"} <= {el["tag"] for el in elements}
    assert next(el for el in elements if el.get("id") == "logout")["hidden"] == "initially"
    assert all(len(el.get("class", "")) <= 80 for el in elements)
    assert len(build_dom_context_string(elements)) <= MAX_CONTEXT_CHARS


def test_page_text_excerpt_keeps_instructions_and_skips_chrome() -> None:
    from app.core.browser.dom_parser import page_text_excerpt

    html = (
        "<html><body><nav>Home Blog Courses</nav>"
        "<main><h1>Test login</h1><p>Use next credentials: Username: student Password: Password123</p>"
        "<p class='hidden'>secret</p><p>" + "a" * 300 + "</p></main>"
        "<footer>Copyright</footer><script>var x = 1</script></body></html>"
    )
    text = page_text_excerpt(html)
    assert "Username: student Password: Password123" in text
    assert "Home Blog" not in text and "Copyright" not in text and "secret" not in text and "var x" not in text
    assert "a" * 41 not in text and "a" * 40 + "…" in text  # long runs are shortened
    assert len(page_text_excerpt("<main>" + "word " * 2000 + "</main>")) <= 1502
