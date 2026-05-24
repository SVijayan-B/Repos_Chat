from sentence_transformers import SentenceTransformer
import logging
from typing import List
from app.config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        self.model_name = settings.embedding_model
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazily load the SentenceTransformer model to prevent startup lags."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            try:
                # Force model to run on CPU if GPU is not needed, making it lightweight for localhost
                self._model = SentenceTransformer(self.model_name, device="cpu")
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise e
        return self._model

    def get_embedding(self, text: str) -> List[float]:
        """Compute the embedding vector for a single piece of text."""
        if not text:
            # Return zero vector if text is empty (384 dimensions for all-MiniLM-L6-v2)
            return [0.0] * 384
            
        cleaned_text = text.replace("\n", " ").strip()
        embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
        return embedding.tolist()

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Compute embedding vectors in batch for efficiency."""
        if not texts:
            return []
            
        cleaned_texts = [t.replace("\n", " ").strip() if t else "" for t in texts]
        embeddings = self.model.encode(cleaned_texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False)
        return embeddings.tolist()
