"""Ingest financial-literacy markdown docs into ChromaDB (+ persist BM25 corpus)."""

from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownTextSplitter

from app.config import settings
from app.core.logging import get_logger
from app.rag.hybrid import save_bm25_corpus
from app.rag.retriever import get_chroma_collection

logger = get_logger(__name__)


def _read_docs(directory: Path) -> list[tuple[str, str]]:
    docs = []
    for md in sorted(directory.glob("*.md")):
        docs.append((md.stem, md.read_text(encoding="utf-8")))
    return docs


def _chunk(text: str, source: str) -> list[tuple[str, dict]]:
    splitter = MarkdownTextSplitter(chunk_size=600, chunk_overlap=80)
    chunks = splitter.split_text(text)
    return [(c, {"source": source, "chunk": i}) for i, c in enumerate(chunks)]


def ingest_documents(directory: Path | None = None) -> int:
    directory = directory or settings.knowledge_dir
    docs = _read_docs(directory)
    if not docs:
        logger.warning("no_docs_found", dir=str(directory))
        return 0

    collection = get_chroma_collection(reset=True)
    embedder = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for source, content in docs:
        for i, (chunk_text, meta) in enumerate(_chunk(content, source)):
            ids.append(f"{source}-{i}")
            texts.append(chunk_text)
            metadatas.append(meta)

    embeddings = embedder.embed_documents(texts)
    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    # Persist BM25 corpus (used at retrieval time by hybrid_retrieve)
    save_bm25_corpus(ids, texts, metadatas)

    logger.info("rag_ingested", chunks=len(ids), docs=len(docs))
    return len(ids)
