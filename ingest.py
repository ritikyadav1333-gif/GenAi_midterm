"""PDF ingestion, chunking, deterministic offline embeddings, and Chroma persistence."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Iterable

import chromadb
from dotenv import load_dotenv
from pypdf import PdfReader

ROOT = Path(__file__).parent
DB_PATH = ROOT / "chroma_db"
COLLECTION_NAME = "indian_railways_telegraph_history"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 120


class OfflineHashEmbedding:
    """A reproducible 384-dimensional local embedding function.

    It has no network calls, model download, API key, or external knowledge.
    Feature hashing keeps the vector database portable for an exam submission.
    """

    dimension = 384

    def name(self) -> str:
        """Stable identifier Chroma stores with the persisted collection."""
        return "offline_hash_384_v1"

    def __call__(self, input: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for document in input:
            vector = [0.0] * self.dimension
            tokens = re.findall(r"[a-z0-9]+", document.lower())
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                slot = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] % 2 else -1.0
                vector[slot] += sign
            magnitude = sum(value * value for value in vector) ** 0.5 or 1.0
            vectors.append([value / magnitude for value in vector])
        return vectors

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> Iterable[str]:
    """Create readable overlapping chunks, preferring paragraph/sentence boundaries."""
    text = re.sub(r"\s+", " ", text).strip()
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            boundary = max(text.rfind(". ", start + chunk_size // 2, end), text.rfind(" ", start + chunk_size // 2, end))
            if boundary > start:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)


def clean_page_text(text: str) -> str:
    """Remove repeating page furniture while retaining the archival body text."""
    if "====" in text:
        text = text.split("====")[-1]
    text = re.sub(r"^CHAPTER[^\n]*\n", "", text, count=1)
    text = re.sub(r"Page \d+ of 50 \| Confidential Assessment Corpus - Do Not Distribute", "", text)
    return text.strip()


def get_collection():
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=OfflineHashEmbedding(),
        metadata={"source": "assigned PDF only", "embedding": "offline-hash-384"},
    )


def build_index(force: bool = False) -> int:
    """Extract all PDF pages and persist page-level overlapping chunks in ChromaDB."""
    load_dotenv(ROOT / ".env")
    pdf_path = Path(os.getenv("PDF_PATH", ROOT / "data" / "indian_railways_and_telegraph_history_50p.pdf"))
    if not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path
    if not pdf_path.exists():
        raise FileNotFoundError(f"Assigned PDF not found: {pdf_path}")

    collection = get_collection()
    if collection.count() and not force:
        return collection.count()
    if force and collection.count():
        client = chromadb.PersistentClient(path=str(DB_PATH))
        client.delete_collection(COLLECTION_NAME)
        collection = get_collection()

    ids, documents, metadatas = [], [], []
    reader = PdfReader(str(pdf_path))
    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_page_text(page.extract_text() or "")
        for chunk_number, chunk in enumerate(split_text(text), start=1):
            ids.append(f"p{page_number:02d}-c{chunk_number:02d}")
            documents.append(chunk)
            metadatas.append({"page": page_number, "chunk_id": ids[-1], "source_file": pdf_path.name})
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


if __name__ == "__main__":
    print(f"Indexed {build_index()} chunks in {DB_PATH}")
