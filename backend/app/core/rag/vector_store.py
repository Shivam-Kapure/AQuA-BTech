import os
from langchain_community.vectorstores import Chroma
from app.core.rag.embeddings import get_embeddings

# Use local data folder for persistence
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "data", "chroma")

def get_vector_store(collection_name: str = "ui_elements") -> Chroma:
    """
    Returns a Chroma vector store instance persisted to the disk.
    """
    os.makedirs(PERSIST_DIRECTORY, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )
