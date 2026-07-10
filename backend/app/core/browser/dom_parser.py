from bs4 import BeautifulSoup
from typing import Any

def extract_interactive_elements(html: str) -> list[dict[str, Any]]:
    """
    Parse HTML and extract interactive elements: buttons, links, inputs, selects.
    Returns a list of dictionaries detailing the elements properties.
    """
    if not html:
        return []
        
    soup = BeautifulSoup(html, "lxml")
    elements = []
    
    # Remove script and style tags to clean up the tree
    for script_or_style in soup(["script", "style", "noscript", "svg"]):
        script_or_style.decompose()

    # Find interactive elements
    tags_to_find = ["button", "a", "input", "select", "textarea", "form"]
    for tag in soup.find_all(tags_to_find):
        element_data = {
            "tag": tag.name,
            "text": tag.get_text(strip=True)[:100], # Limit text length
        }
        
        # Grab important attributes
        important_attrs = ["id", "class", "name", "type", "placeholder", "value", "role", "aria-label", "href"]
        for attr in important_attrs:
            val = tag.get(attr)
            if val is not None:
                if isinstance(val, list):
                    val = " ".join(val)
                element_data[attr] = val
                
        # Only keep elements that have some identifying info or text
        if element_data.get("id") or element_data.get("name") or element_data.get("class") or element_data.get("text") or element_data.get("placeholder"):
            elements.append(element_data)
            
    return elements

def build_dom_context_string(elements: list[dict[str, Any]]) -> str:
    """
    Format a list of element dictionaries into a concise text block for LLM prompts.
    """
    lines = []
    for el in elements:
        parts = [f"<{el['tag']}"]
        for k, v in el.items():
            if k not in ("tag", "text") and v:
                parts.append(f"{k}='{v}'")
        parts_str = " ".join(parts)
        if el.get("text"):
            lines.append(f"{parts_str}> {el['text']} </{el['tag']}>")
        else:
            lines.append(f"{parts_str} />")
    return "\n".join(lines)
