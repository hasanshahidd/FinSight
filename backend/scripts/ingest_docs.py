"""Ingest financial-literacy markdown docs into ChromaDB + persist BM25 corpus.

Usage:  python scripts/ingest_docs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.ingest import ingest_documents


def main() -> None:
    n = ingest_documents()
    print(f"Ingested {n} chunks into the knowledge base (dense + BM25).")


if __name__ == "__main__":
    main()
