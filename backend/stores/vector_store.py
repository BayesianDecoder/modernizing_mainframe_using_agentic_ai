"""ChromaDB local vector store — runbooks, ADRs, incidents."""
import re
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

PERSIST_DIR = str(Path(__file__).parent.parent.parent / ".maia_chroma")
_col = None

def col():
    global _col
    if _col is None:
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        try:
            ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        except Exception:
            ef = None
        _col = client.get_or_create_collection(
            name="maia_runbooks",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _col

def ingest_file(path: str) -> int:
    text = Path(path).read_text(errors="replace")
    fname = Path(path).name

    # One chunk per "### " section (one ADR, one incident, one SOP) rather
    # than packing paragraphs up to a fixed character budget. An incident's
    # root cause and its fix must never land in two different chunks — if
    # they did, a search hit could surface only half the story. Splitting on
    # the document's own section headings keeps each issue whole regardless
    # of length.
    sections = re.split(r"\n(?=### )", text)
    chunks = [s.strip() for s in sections if s.strip()]

    # Clear existing
    existing = col().get(where={"source": fname})
    if existing["ids"]:
        col().delete(where={"source": fname})

    ids, docs, metas = [], [], []
    for idx, chunk in enumerate(chunks):
        ids.append(f"{fname}::{idx}")
        docs.append(chunk)
        metas.append({"source": fname, "chunk": idx})

    if ids:
        col().add(ids=ids, documents=docs, metadatas=metas)
    return len(ids)

def search(query: str, n: int = 4) -> list[dict]:
    c = col()
    count = c.count()
    if count == 0:
        return []
    res = c.query(query_texts=[query], n_results=min(n, count))
    out = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append({
            "text":      text,
            "source":    meta.get("source",""),
            "relevance": round(1 - dist, 3),
        })
    return out
