import logging
import os
from typing import Optional

from dotenv import load_dotenv
from haystack.utils import Secret
from qdrant_client.http import models as rest

from src.core.provider import DocumentStoreProvider
from src.providers.document_store import AsyncQdrantDocumentStore, AsyncQdrantEmbeddingRetriever

load_dotenv()

logger = logging.getLogger(__name__)


class QdrantProvider(DocumentStoreProvider):
    def __init__(
        self,
        location: str = os.getenv("QDRANT_HOST", "qdrant"),
        api_key: Optional[str] = os.getenv("QDRANT_API_KEY", None),
        timeout: Optional[int] = (
            int(os.getenv("QDRANT_TIMEOUT")) if os.getenv("QDRANT_TIMEOUT") else 120
        ),
        embedding_model_dim: int = (
            int(os.getenv("EMBEDDING_MODEL_DIMENSION"))
            if os.getenv("EMBEDDING_MODEL_DIMENSION")
            else 3072
        ),
        recreate_index: bool = (
            bool(os.getenv("SHOULD_FORCE_DEPLOY"))
            if os.getenv("SHOULD_FORCE_DEPLOY")
            else False
        ),
        **_,
    ):
        self._location = location
        self._api_key = Secret.from_token(api_key) if api_key else None
        self._timeout = timeout
        self._embedding_model_dim = embedding_model_dim
        self._reset_document_store(recreate_index)

    def _reset_document_store(self, recreate_index: bool):
        self.get_store(recreate_index=recreate_index)
        self.get_store(dataset_name="table_descriptions", recreate_index=recreate_index)
        self.get_store(dataset_name="view_questions", recreate_index=recreate_index)

    def get_store(
        self,
        dataset_name: Optional[str] = None,
        recreate_index: bool = False,
    ):
        logger.info(
            f"Using Qdrant Document Store with Embedding Model Dimension: {self._embedding_model_dim}"
        )

        return AsyncQdrantDocumentStore(
            location=self._location,
            api_key=self._api_key,
            embedding_dim=self._embedding_model_dim,
            index=dataset_name or "Document",
            recreate_index=recreate_index,
            on_disk=True,
            timeout=self._timeout,
            quantization_config=(
                rest.BinaryQuantization(
                    binary=rest.BinaryQuantizationConfig(
                        always_ram=True,
                    )
                )
                if self._embedding_model_dim >= 1024
                else None
            ),
            # to improve the indexing performance, we disable building global index for the whole collection
            # see https://qdrant.tech/documentation/guides/multiple-partitions/?q=mul#calibrate-performance
            hnsw_config=rest.HnswConfigDiff(
                payload_m=16,
                m=0,
            ),
        )

    def get_retriever(
        self,
        document_store: AsyncQdrantDocumentStore,
        top_k: int = 10,
    ):
        return AsyncQdrantEmbeddingRetriever(
            document_store=document_store,
            top_k=top_k,
        )
