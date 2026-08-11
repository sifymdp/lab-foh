import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def generate_text(prompt: str, fallback: str) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            text = (data.get("response") or "").strip()
            return text or fallback
    except Exception as exc:
        logger.info("Ollama unavailable (%s), using fallback", exc)
        return fallback
