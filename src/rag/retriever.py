import hashlib
import json
import os
import uuid
from functools import lru_cache
from qdrant_client import QdrantClient, models
from sklearn.feature_extraction.text import HashingVectorizer
from langchain_core.runnables import RunnableLambda
from src.config import DATA, RETRIEVAL_MODE, runtime_dir
from src.reranker.reranker_service import Reranker, tokens


class Encoder:
    def __init__(self):
        self.mode = RETRIEVAL_MODE
        self.dim = 384
        self.local = HashingVectorizer(n_features=self.dim, analyzer="char_wb", ngram_range=(3, 5), alternate_sign=False, norm="l2")
        self.model = None
        if self.mode == "semantic":
            from sentence_transformers import SentenceTransformer
            path = os.environ["ORDOPLAN_EMBEDDING_PATH"]
            self.model = SentenceTransformer(path, local_files_only=True, trust_remote_code=False)
            self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts):
        if self.model is not None:
            return self.model.encode(texts, normalize_embeddings=True).tolist()
        return self.local.transform(texts).toarray().tolist()


class Retriever:
    def __init__(self, memory=False):
        self.chunks = json.loads((DATA / "corpus/chunks.json").read_text())
        self.encoder = Encoder()
        self.client = QdrantClient(":memory:") if memory else (QdrantClient(url=os.environ["QDRANT_URL"], check_compatibility=False) if os.getenv("QDRANT_URL") else QdrantClient(path=str(runtime_dir()/"qdrant")))
        content_hash = hashlib.sha256((DATA / "corpus/chunks.json").read_bytes()).hexdigest()[:10]
        self.collection = f"ordoplan_{self.encoder.mode}_{self.encoder.dim}_{content_hash}"
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=self.encoder.dim, distance=models.Distance.COSINE))
            vectors = self.encoder.encode([p["title"]+" "+p["text"] for p in self.chunks])
            points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, self.key(p))), vector=v, payload=p) for p, v in zip(self.chunks, vectors)]
            self.client.upsert(self.collection, points=points)
        self.reranker = Reranker()
        self.chain = RunnableLambda(lambda x: self.search(**x))

    @staticmethod
    def key(p):
        return f"{p['document_id']}:{p['version']}:{p['page']}:{p['element_id']}"

    def allowed(self, user):
        return [p for p in self.chunks if p["workshop_id"] == user["workshop"] and user["role"] in p["groups"]]

    def search(self, query, user, limit=5, rerank=True):
        authorized = self.allowed(user)
        if not authorized:
            return []
        filt = models.Filter(must=[models.FieldCondition(key="workshop_id", match=models.MatchValue(value=user["workshop"])), models.FieldCondition(key="groups", match=models.MatchAny(any=[user["role"]]))])
        vector = self.encoder.encode([query])[0]
        hits = self.client.query_points(self.collection, query=vector, query_filter=filt, limit=20).points
        dense = [h.payload for h in hits]
        q = tokens(query)
        lexical = sorted(authorized, key=lambda p: len(q & tokens(p["title"]+" "+p["text"]))/max(1,len(q)), reverse=True)[:20]
        # Le profil CPU cherche les descriptions/OCR des pages ; le vrai CLIP est optionnel.
        visual = sorted(authorized, key=lambda p: len(q & tokens(p["title"]+" "+p["machine"])), reverse=True)[:20]
        if os.getenv("ORDOPLAN_CLIP_TEXT_PATH"):
            from src.rag.visual import visual_search
            visual = visual_search(query, authorized, limit=20)
        scores, objects = {}, {}
        for ranking in [dense, lexical, visual]:
            for rank, p in enumerate(ranking, 1):
                key = self.key(p)
                scores[key] = scores.get(key, 0)+1/(60+rank)
                objects[key] = p
        fused = [objects[k] for k in sorted(scores, key=scores.get, reverse=True)]
        result = self.reranker.rank(query, fused) if rerank else fused
        return result[:limit]

    def citation(self, p):
        return {k: p[k] for k in ("document_id", "version", "page", "element_id")} | {"excerpt": p["text"]}

    def verify_citations(self, citations, user):
        allowed = {self.key(p): p for p in self.allowed(user)}
        return all(self.key(c) in allowed and c["excerpt"] in allowed[self.key(c)]["text"] for c in citations)


@lru_cache(maxsize=1)
def get_retriever():
    return Retriever()
