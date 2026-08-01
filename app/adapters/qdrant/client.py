from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.adapters.qdrant.schema import EMBEDDING_DIM, QDRANT_COLLECTION


def get_qdrant_client(qdrant_url: str) -> QdrantClient:
    return QdrantClient(url=qdrant_url)


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(QDRANT_COLLECTION):
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=qmodels.VectorParams(
            size=EMBEDDING_DIM,
            distance=qmodels.Distance.COSINE,
        ),
    )
