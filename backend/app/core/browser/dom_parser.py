import re
from typing import Any

from bs4 import BeautifulSoup

# Keep the prompt context small: free-tier LLMs (e.g. Groq) cap tokens per minute,
# and large sites expose hundreds of links/buttons.
MAX_ELEMENTS = 80
MAX_CONTEXT_CHARS = 6000
MAX_ATTR_CHARS = 80

# Most useful elements for test generation come first when the cap is reached.
_TAG_PRIORITY = {"form": 0, "input": 1, "textarea": 1, "select": 1, "button": 2, "a": 3}
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)


def _is_hidden(tag: Any) -> bool:
    """True when the element or an ancestor is hidden or sits inside a <template>."""
    node = tag
    while node is not None and getattr(node, "name", None):
        if node.name == "template":
            return True
        classes = node.get("class") or []
        if (
            node.has_attr("hidden")
            or node.get("aria-hidden") == "true"
            or "hidden" in classes
            or (node.name == "input" and str(node.get("type", "")).lower() == "hidden")
            or _HIDDEN_STYLE.search(node.get("style") or "")
        ):
            return True
        node = node.parent
    return False


def extract_interactive_elements(html: str) -> list[dict[str, Any]]:
    """
    Parse HTML and extract interactive elements: buttons, links, inputs, selects.
    Returns a list of dictionaries detailing the elements properties.
    Elements hidden on initial load are flagged with "hidden": "initially".
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    elements = []
    seen: set[tuple] = set()

    # Remove script and style tags to clean up the tree
    for script_or_style in soup(["script", "style", "noscript", "svg"]):
        script_or_style.decompose()

    # Find interactive elements
    tags_to_find = ["button", "a", "input", "select", "textarea", "form"]
    for tag in soup.find_all(tags_to_find):
        element_data = {
            "tag": tag.name,
            "text": " ".join(tag.get_text(" ", strip=True).split())[:100],  # Limit text length
        }

        # Grab important attributes
        important_attrs = ["id", "class", "name", "type", "placeholder", "value", "role", "aria-label", "href", "maxlength"]
        for attr in important_attrs:
            val = tag.get(attr)
            if val is not None:
                if isinstance(val, list):
                    val = " ".join(val)
                element_data[attr] = str(val)[:MAX_ATTR_CHARS]
        if _is_hidden(tag):
            element_data["hidden"] = "initially"

        # Only keep elements that have some identifying info or text
        if not (element_data.get("id") or element_data.get("name") or element_data.get("class") or element_data.get("text") or element_data.get("placeholder")):
            continue
        key = tuple(sorted(element_data.items()))
        if key in seen:
            continue
        seen.add(key)
        elements.append(element_data)

    if len(elements) > MAX_ELEMENTS:
        ranked = sorted(range(len(elements)), key=lambda i: (_TAG_PRIORITY.get(elements[i]["tag"], 9), i))
        keep = set(ranked[:MAX_ELEMENTS])
        elements = [el for i, el in enumerate(elements) if i in keep]
    return elements


def build_dom_context_string(elements: list[dict[str, Any]]) -> str:
    """
    Format a list of element dictionaries into a concise text block for LLM prompts.
    """
    lines = []
    total = 0
    for el in elements:
        parts = [f"<{el['tag']}"]
        for k, v in el.items():
            if k not in ("tag", "text") and v:
                parts.append(f"{k}='{v}'")
        parts_str = " ".join(parts)
        if el.get("text"):
            line = f"{parts_str}> {el['text']} </{el['tag']}>"
        else:
            line = f"{parts_str} />"
        if total + len(line) > MAX_CONTEXT_CHARS:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


MAX_PAGE_TEXT_CHARS = 1500


def visible_text(html: str) -> str:
    """
    Text a user would actually see: drops scripts, styles, templates and elements
    hidden via the `hidden` attribute, aria-hidden, a `hidden` class or inline
    display:none / visibility:hidden.
    """
    soup = BeautifulSoup(html, "lxml")
    return _visible_text_of(soup)


def _visible_text_of(soup: Any) -> str:
    for tag in soup(["script", "style", "template", "noscript", "svg"]):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.decomposed:
            continue
        classes = tag.get("class") or []
        if (
            tag.has_attr("hidden")
            or tag.get("aria-hidden") == "true"
            or "hidden" in classes
            or _HIDDEN_STYLE.search(tag.get("style") or "")
        ):
            tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def page_text_excerpt(html: str, limit: int = MAX_PAGE_TEXT_CHARS) -> str:
    """
    Short excerpt of the page's visible text (instructions, labels, demo credentials,
    rules) for test generation. Prefers <main>/<article> content and skips site
    chrome (nav, header, footer) when present.
    """
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    root = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in root.find_all(["nav", "footer"]):
        tag.decompose()
    if root is soup.body or root is soup:
        for tag in root.find_all("header"):
            tag.decompose()
    # Shorten runaway "words" (e.g. user posts of repeated characters) so they don't crowd out instructions.
    text = re.sub(r"(\S{40})\S+", r"\1…", _visible_text_of(root))
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"
