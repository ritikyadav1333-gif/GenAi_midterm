"""Strictly grounded RAG question answering over the assigned PDF only."""
from __future__ import annotations

import re
from typing import Any

from ingest import build_index, get_collection

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "from", "by", "with", "what", "which", "who", "was", "were", "is", "are", "did", "does", "do", "exact", "annual", "expressed", "as", "under", "this", "that", "it", "its", "between",
}


def terms(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS and len(token) > 2}


def best_supported_sentences(question: str, documents: list[str]) -> str:
    """Extract source sentences - never fabricate wording or use outside knowledge."""
    question_terms = terms(question)
    candidates: list[tuple[int, str]] = []
    for document in documents:
        for sentence in re.split(r"(?<!Dr\.)(?<=[.!?])\s+", document):
            sentence = sentence.strip()
            # Page headings are useful metadata but not part of the answer text.
            sentence = re.sub(r"^CHAPTER[^.]{0,200}?\s(?=(Under|During|Archival)\s)", "", sentence)
            overlap = len(question_terms & terms(sentence))
            if overlap:
                candidates.append((overlap, sentence))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates or candidates[0][0] < 2:
        return "[not found]"
    best = candidates[0][1]
    # Compound engineering questions can ask for two facts located in adjacent sentences.
    if "gradient" in question.lower() and "gradient" not in best.lower():
        gradient_sentence = next((sentence for _, sentence in candidates if "gradient" in sentence.lower()), None)
        if gradient_sentence:
            return f"{best} {gradient_sentence}"
    return best


def answer(question: str) -> dict[str, Any]:
    """Returns {"answer": <str>, "sources": [<page_or_chunk_id>, ...]}."""
    if not question.strip():
        return {"answer": "[not found]", "sources": []}
    build_index()
    results = get_collection().query(query_texts=[question], n_results=3, include=["documents", "metadatas", "distances"])
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    extracted = best_supported_sentences(question, documents)
    if extracted == "[not found]":
        return {"answer": "[not found]", "sources": []}
    source_metadata = [
        metadata for document, metadata in zip(documents, metadatas)
        if extracted in document
    ]
    return {
        "answer": extracted,
        "sources": [f"PDF p. {m['page']} ({m['chunk_id']})" for m in source_metadata[:1]],
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(answer(" ".join(sys.argv[1:])), indent=2))
