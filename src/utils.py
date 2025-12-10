import json
import os

def save_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_config(path="config.yaml"):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_rag_prompt(question: str, chunks_with_meta):
    """
    собираем контекст для RAG: перечислим чанки + метаданные
    """
    ctx = []
    for i, cm in enumerate(chunks_with_meta, start=1):
        meta = cm.get("meta", {})
        ctx.append(f"{i}. (score: {cm.get('score',0):.3f}) [{meta.get('sentiment','?')}] {meta.get('tags','')}\n{cm['chunk']['text']}")
    prompt = f"You are an analyst. Use ONLY the information below to answer briefly.\nQUESTION: {question}\n\nCONTEXT:\n" + "\n\n".join(ctx) + "\n\nAnswer (short, bullet points):"
    return prompt
