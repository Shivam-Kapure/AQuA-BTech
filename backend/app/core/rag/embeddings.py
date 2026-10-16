from functools import lru_cache

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_core.embeddings import Embeddings


class OnnxMiniLMEmbeddings(Embeddings):
    """
    all-MiniLM-L6-v2 embeddings via Chroma's bundled ONNX runtime.

    Same model as sentence-transformers' all-MiniLM-L6-v2, without pulling in
    torch: a much smaller install/image, faster start-up and lower memory.
    """

    def __init__(self) -> None:
        self._embed = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(value) for value in vector] for vector in self._embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache()
def get_embeddings() -> OnnxMiniLMEmbeddings:
    """Singleton embedding model (the ONNX model is downloaded once and cached)."""
    return OnnxMiniLMEmbeddings()
