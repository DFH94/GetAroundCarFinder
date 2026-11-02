"""Revisión de fotos en local y gratis: CLIP (zero-shot) detecta coches con daños visibles.

No hay llamadas a APIs de pago: el modelo (~600 MB, ONNX) se descarga una vez en data/models y corre en tu CPU.
CLIP compara cada foto con frases ("coche destrozado tras un golpe" frente a "coche intacto", "interior"...) y
se descarta el anuncio solo si alguna foto se parece claramente más a las frases de daño."""
import io
import logging
import os
import threading

import httpx
import numpy as np

from .config import DATA_DIR

log = logging.getLogger(__name__)

TEXT_MODEL = "Qdrant/clip-ViT-B-32-text"
IMAGE_MODEL = "Qdrant/clip-ViT-B-32-vision"
CACHE_DIR = str(DATA_DIR / "models")
MAX_PHOTOS = 3
MAX_IMAGE_BYTES = 6_000_000
LOGIT_SCALE = 100.0  # el de CLIP
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"

# Un coche se descarta si, en alguna foto, la probabilidad de "daño" supera este umbral (calibrado: íntegros < 0,20; siniestrados > 0,45)
DAMAGE_THRESHOLD = float(os.getenv("PHOTO_DAMAGE_THRESHOLD", "0.35"))

DAMAGED = [
    "a photo of a car wrecked in a crash with severe body damage",
    "a photo of a car with a crushed front end after a collision",
    "a photo of a damaged car with the hood open and the bumper and fender removed",
    "a photo of a burned car",
    "a photo of a flooded car",
    "a photo of a totaled car in a junkyard",
    "a photo of a car with a smashed side and broken windows",
]
INTACT = [
    "a photo of a clean car in perfect condition",
    "a photo of a car parked on the street",
    "a photo of a car in a dealership",
    "a photo of a new car seen from the front",
    "a photo of a car seen from the side",
    "a photo of the rear of a car",
]
NEUTRAL = [  # fotos que no enseñan la carrocería: no deben contar como daño
    "a photo of the interior of a car",
    "a photo of a car dashboard and steering wheel",
    "a photo of car seats",
    "a photo of a car wheel and tire",
    "a photo of a clean car engine",
    "a photo of the trunk of a car",
    "a screenshot with text",
]
PROMPTS = DAMAGED + INTACT + NEUTRAL
N_DAMAGED = len(DAMAGED)

_lock = threading.Lock()
_models = None  # (image_model, text_embeddings)


def enabled() -> bool:
    return os.getenv("PHOTO_REVIEW", "on").lower() not in ("off", "0", "false", "no")


def _load():
    """Carga perezosa: la primera vez descarga el modelo (~600 MB) y calcula las frases."""
    global _models
    with _lock:
        if _models is None:
            from fastembed import ImageEmbedding, TextEmbedding
            text = TextEmbedding(TEXT_MODEL, cache_dir=CACHE_DIR)
            image = ImageEmbedding(IMAGE_MODEL, cache_dir=CACHE_DIR)
            t = np.array(list(text.embed(PROMPTS)), dtype=np.float32)
            t /= np.linalg.norm(t, axis=1, keepdims=True)
            _models = (image, t)
        return _models


def _download(url: str):
    from PIL import Image
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        if len(r.content) > MAX_IMAGE_BYTES:
            return None
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        log.warning("foto no descargable %s: %s", url[:80], e)
        return None


def damage_probabilities(images) -> list[float]:
    """Probabilidad (0-1) de que cada imagen muestre un coche dañado."""
    model, text = _load()
    emb = np.array(list(model.embed(images)), dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    logits = LOGIT_SCALE * emb @ text.T
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    return [float(x) for x in p[:, :N_DAMAGED].sum(axis=1)]


def review(urls: list[str]) -> dict | None:
    """{'verdict': 'ok'|'damaged', 'score': prob. máxima de daño, 'note': ...} o None si no hay fotos utilizables."""
    images = [im for im in (_download(u) for u in urls[:MAX_PHOTOS] if u) if im is not None]
    if not images:
        return None
    try:
        probs = damage_probabilities(images)
    except Exception as e:  # noqa: BLE001
        log.warning("Revisión de fotos fallida: %s", e)
        return None
    top = max(probs)
    verdict = "damaged" if top >= DAMAGE_THRESHOLD else "ok"
    note = f"daño {top:.0%} en {len(images)} foto(s)"
    return {"verdict": verdict, "score": top, "note": note}


def is_blocking(result: dict) -> bool:
    return result["verdict"] == "damaged"
