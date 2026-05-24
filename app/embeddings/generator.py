from sentence_transformers import SentenceTransformer
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        self.model_name = settings.embedding_model
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Initializing lazy load sentence embedding transformers engine...")
            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def get_embedding(self, text: str) -> list:
        if not text: return [0.0] * 384
        return self.model.encode(text.replace("\n", " ").strip(), convert_to_numpy=True).tolist()

    def get_embeddings_batch(self, texts: list) -> list:
        if not texts: return []
        cleaned = [t.replace("\n", " ").strip() if t else "" for t in texts]
        return self.model.encode(cleaned, convert_to_numpy=True, batch_size=32).tolist()