import json
import math
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data" if (BASE_DIR.parent / "data").exists() else BASE_DIR / "data"


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9À-ÿ']+", text)]


class VectorStoreIndex:
    """Lightweight vector/TF-IDF index for fast, zero-dependency in-memory RAG.

    Guaranteed to run anywhere on lightweight Render containers without downloading multi-GB models.
    """

    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []
        self.vocabulary: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_vectors: list[dict[str, float]] = []
        self._load_and_index()

    def _load_and_index(self) -> None:
        docs: list[dict[str, Any]] = []

        # Load travel knowledge
        know_path = DATA_DIR / "travel_knowledge.json"
        if know_path.exists():
            try:
                know_data = json.loads(know_path.read_text(encoding="utf-8"))
                for item in know_data:
                    item["source_file"] = "travel_knowledge.json"
                    docs.append(item)
            except Exception:
                pass

        # Load travel policies
        pol_path = DATA_DIR / "travel_policies.json"
        if pol_path.exists():
            try:
                pol_data = json.loads(pol_path.read_text(encoding="utf-8"))
                for item in pol_data:
                    item["source_file"] = "travel_policies.json"
                    docs.append(item)
            except Exception:
                pass

        self.documents = docs
        if not docs:
            return

        # Compute document frequencies
        doc_freq: dict[str, int] = {}
        tokenized_docs: list[list[str]] = []
        num_docs = len(docs)

        for doc in docs:
            full_text = f"{doc.get('destination', '')} {doc.get('topic', '')} {doc.get('content', '')}"
            terms = set(tokenize(full_text))
            tokenized_docs.append(tokenize(full_text))
            for t in terms:
                doc_freq[t] = doc_freq.get(t, 0) + 1

        # Compute IDF
        for term, df in doc_freq.items():
            self.idf[term] = math.log((num_docs + 1) / (df + 1)) + 1.0

        # Compute TF-IDF document vectors
        self.doc_vectors = []
        for terms in tokenized_docs:
            tf: dict[str, int] = {}
            for t in terms:
                tf[t] = tf.get(t, 0) + 1
            length = len(terms) or 1
            vec: dict[str, float] = {}
            for t, count in tf.items():
                tfidf = (count / length) * self.idf.get(t, 1.0)
                vec[t] = tfidf
            # Normalize vector
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            for t in vec:
                vec[t] /= norm
            self.doc_vectors.append(vec)

    def search_vector(self, query: str, top_k: int = 5) -> list[tuple[float, dict[str, Any]]]:
        q_terms = tokenize(query)
        if not q_terms or not self.doc_vectors:
            return []

        # Query vector
        q_tf: dict[str, int] = {}
        for t in q_terms:
            q_tf[t] = q_tf.get(t, 0) + 1
        q_len = len(q_terms)
        q_vec: dict[str, float] = {}
        for t, count in q_tf.items():
            if t in self.idf:
                q_vec[t] = (count / q_len) * self.idf[t]
        norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        for t in q_vec:
            q_vec[t] /= norm

        scores: list[tuple[float, dict[str, Any]]] = []
        for idx, d_vec in enumerate(self.doc_vectors):
            dot_product = sum(q_vec[t] * d_vec[t] for t in q_vec if t in d_vec)
            if dot_product > 0.05:
                scores.append((round(dot_product, 4), self.documents[idx]))

        scores.sort(key=lambda item: item[0], reverse=True)
        return scores[:top_k]


class RAGPipeline:
    _index: VectorStoreIndex | None = None

    @classmethod
    def get_index(cls) -> VectorStoreIndex:
        if cls._index is None:
            cls._index = VectorStoreIndex()
        return cls._index

    @classmethod
    def retrieve(cls, query: str, limit: int = 3, category_filter: str | None = None) -> list[dict[str, Any]]:
        index = cls.get_index()
        vector_results = index.search_vector(query, top_k=limit * 2)

        # Keyword boost / BM25 term overlap
        q_words = set(tokenize(query))
        reranked = []
        for score, doc in vector_results:
            if category_filter and doc.get("category") != category_filter:
                continue
            doc_words = set(tokenize(f"{doc.get('destination', '')} {doc.get('topic', '')} {doc.get('content', '')}"))
            overlap = len(q_words.intersection(doc_words)) / max(1, len(q_words))
            hybrid_score = round(0.6 * score + 0.4 * overlap, 4)
            reranked.append((hybrid_score, doc))

        reranked.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in reranked[:limit]]

    @classmethod
    def format_sources(cls, docs: list[dict[str, Any]]) -> list[str]:
        return [f"{d.get('topic', 'Travel Info')}: {d.get('content', '')}" for d in docs]
