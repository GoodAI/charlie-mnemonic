from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

from typing import Dict, Any
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

class CrossEncoderEmbeddingFunction(EmbeddingFunction):
    models: Dict[str, Any] = {}
    tokenizers: Dict[str, Any] = {}

    def __init__(
        self,
        model_name: str = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
        device: str = 'cpu',
        normalize_embeddings: bool = False,
    ):
        if model_name not in self.models:
            self.models[model_name] = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_name)
        self._model = self.models[model_name]
        self.tokenizer = self.tokenizers[model_name]
        self._normalize_embeddings = normalize_embeddings
        self.device = torch.device(device)
        self._model.to(self.device)
        self._model.eval()

    def __call__(self, texts: Documents) -> Embeddings:
        with torch.no_grad():
            features = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
            embeddings = self._model(**features).logits
            if self._normalize_embeddings:
                embeddings = embeddings / torch.norm(embeddings, dim=1, keepdim=True)
            return embeddings.cpu().numpy().tolist()