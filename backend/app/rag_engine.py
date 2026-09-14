from pathlib import Path
from typing import Dict, Any

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base.txt"

def load_knowledge():
    return KB_PATH.read_text(encoding="utf-8")

def retrieve_context(query: str, max_chars: int = 5000) -> str:
    text = load_knowledge()
    q = query.lower()

    sections = text.split("\n## ")
    scored = []

    for section in sections:
        section_lower = section.lower()
        score = sum(1 for word in q.split() if len(word) > 2 and word in section_lower)
        scored.append((score, section))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = "\n\n## ".join(section for score, section in scored if score > 0)

    if not selected:
        selected = text

    return selected[:max_chars]

def execute_rag_query(query: str) -> Dict[str, Any]:
    context = retrieve_context(query)

    return {
        "source": "knowledge_base",
        "query": query,
        "context": context,
        "count": 1
    }
