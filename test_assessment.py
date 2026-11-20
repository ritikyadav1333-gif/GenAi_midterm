"""Run the five required assessment questions and save their generated RAG outputs."""
from __future__ import annotations

import json
from pathlib import Path

from ingest import build_index
from rag import answer

QUESTIONS = [
    "What exact annual guaranteed interest rate, expressed as a percentage, did the colonial administration promise private British railway companies under the 1849 contract terms?",
    "Which engineering obstacle on the Bhor Ghat incline made the reversing station described in Chapter 3 necessary, and what was the gradient ratio?",
    "What is the ticket price for an Executive Chair Car seat on the Vande Bharat Express between New Delhi and Varanasi?",
    "According to the archival records in the text, who supervised the laying of the experimental Diamond Harbour underwater telegraph cable in 1851?",
    "Which country won the 2022 FIFA World Cup?",
]

if __name__ == "__main__":
    build_index()
    outputs = [{"question": question, **answer(question)} for question in QUESTIONS]
    destination = Path(__file__).parent / "assessment_outputs.json"
    destination.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(destination.read_text(encoding="utf-8"))
