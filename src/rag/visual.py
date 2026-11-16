"""Recherche CLIP multilingue avec le couple d'encodeurs explicitement apparié."""
import os
from functools import lru_cache
import numpy as np
from PIL import Image
from src.config import ROOT


@lru_cache(maxsize=1)
def models():
    from sentence_transformers import SentenceTransformer
    text = SentenceTransformer(os.environ["ORDOPLAN_CLIP_TEXT_PATH"], local_files_only=True)
    image = SentenceTransformer(os.environ["ORDOPLAN_CLIP_IMAGE_PATH"], local_files_only=True)
    return text, image


@lru_cache(maxsize=256)
def image_vector(path):
    _, encoder = models()
    with Image.open(ROOT/path) as im:
        return encoder.encode([im.convert("RGB")], normalize_embeddings=True)[0]


def visual_search(query, authorized, limit=20):
    encoder, _ = models()
    q = encoder.encode([query], normalize_embeddings=True)[0]
    return sorted(authorized, key=lambda p: float(np.dot(q, image_vector(p["image"]))), reverse=True)[:limit]
