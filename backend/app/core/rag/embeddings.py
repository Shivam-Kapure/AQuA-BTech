from langchain_community.embeddings import HuggingFaceEmbeddings
from functools import lru_cache

@lru_cache()
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Returns a singleton instance of local HuggingFace embeddings
    using sentence-transformers.
    """
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": False}
    )
