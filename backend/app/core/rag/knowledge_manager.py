import json
from langchain_core.documents import Document
from app.core.rag.vector_store import get_vector_store
from loguru import logger

class KnowledgeManager:
    def __init__(self, collection_name: str = "ui_elements"):
        self.vector_store = get_vector_store(collection_name)
    
    def ingest_elements(self, url: str, elements: list[dict]):
        """
        Embeds UI elements for a specific URL and adds them to Chroma DB.
        """
        try:
            # Delete old elements for this URL to avoid duplication
            # This is a naive cleanup approach
            existing = self.vector_store.get(where={"url": url})
            if existing and existing.get("ids"):
                self.vector_store.delete(ids=existing["ids"])
            
            docs = []
            for idx, el in enumerate(elements):
                # The page_content is the semantic representation of the element
                # that we want the LLM to search against (e.g. "Login Button")
                content_parts = []
                if el.get('text'): content_parts.append(f"Text/Label: {el['text']}")
                if el.get('role'): content_parts.append(f"Role: {el['role']}")
                if el.get('placeholder'): content_parts.append(f"Placeholder: {el['placeholder']}")
                if el.get('name'): content_parts.append(f"Name: {el['name']}")
                if el.get('id'): content_parts.append(f"ID: {el['id']}")
                
                content = " ".join(content_parts)
                # Fallback if empty
                if not content.strip():
                    content = f"{el.get('tag')} element"
                    
                doc = Document(
                    page_content=content,
                    metadata={
                        "url": url,
                        "tag": el.get("tag", ""),
                        "raw_json": json.dumps(el) # Store the full attr dict
                    }
                )
                docs.append(doc)
                
            if docs:
                self.vector_store.add_documents(docs)
                logger.info(f"Ingested {len(docs)} elements into RAG for {url}")
        except Exception as e:
            logger.error(f"Failed to ingest elements into RAG: {e}")

    def retrieve_elements_for_steps(self, url: str, query: str, k: int = 5) -> str:
        """
        Retrieves the top k most relevant UI elements for a given text query (like a test case step)
        Returns a formatted strings of the raw metadata.
        """
        try:
            # Filter by exactly this URL to avoid fetching elements from other pages
            docs = self.vector_store.similarity_search(query, k=k, filter={"url": url})
            if not docs:
                return "No matching UI elements found in context."
                
            contexts = []
            for doc in docs:
                raw_data = json.loads(doc.metadata["raw_json"])
                
                parts = [f"<{raw_data['tag']}"]
                for key, val in raw_data.items():
                    if key not in ("tag", "text") and val:
                        parts.append(f"{key}='{val}'")
                parts_str = " ".join(parts)
                
                if raw_data.get("text"):
                    contexts.append(f"{parts_str}> {raw_data['text']} </{raw_data['tag']}>")
                else:
                    contexts.append(f"{parts_str} />")
                    
            return "\n".join(contexts)
        except Exception as e:
            logger.error(f"Failed to retrieve contexts: {e}")
            return ""
