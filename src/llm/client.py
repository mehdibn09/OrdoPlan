"""VLM à poids ouverts, strictement local. Aucun appel à un modèle hébergé."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from src.config import MODEL_MODE, ROOT, runtime_dir
from src.ingestion.pdf_parser import bounded_image, ocr, parse_observation
from src.mcp_server.client import Budget


def analyze_image(data, budget=None):
    budget = budget or Budget()
    image = bounded_image(data)
    text = ocr(image)
    observation = parse_observation(text)
    result = {"ocr": text, "observation": observation, "mode": "ocr", "needs_validation": True, "uncertainties": [], "vlm": None}
    if MODEL_MODE == "vlm":
        budget.consume_model()
        model_path = Path(os.getenv("ORDOPLAN_VLM_PATH", "models/vlm"))
        if not model_path.is_absolute():
            model_path = ROOT / model_path
        if not model_path.exists():
            result["uncertainties"].append("Poids VLM absents : lecture OCR seule, à valider")
        else:
            with tempfile.TemporaryDirectory(dir=runtime_dir()) as folder:
                image_path = Path(folder)/"input.png"
                output = Path(folder)/"result.json"
                image.thumbnail((1280, 1280))
                image.save(image_path)
                remaining = max(1, min(35, 59-(__import__('time').monotonic()-budget.started)))
                try:
                    subprocess.run([sys.executable, "-m", "src.llm.worker", "--model", str(model_path), "--image", str(image_path), "--output", str(output)], cwd=ROOT, check=True, timeout=remaining, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    vlm = json.loads(output.read_text())
                    result.update(vlm=vlm, mode="vlm+ocr")
                    parsed = parse_observation(vlm["text"])
                    comparable = observation["kind"] != "unknown" and all(parsed.get(k) == v for k, v in observation.items() if v is not None)
                    if not comparable:
                        result["uncertainties"].append("Désaccord OCR/VLM : validation des champs obligatoire")
                except (subprocess.SubprocessError, ValueError, OSError):
                    result["uncertainties"].append("VLM indisponible ou délai dépassé : OCR à valider")
    else:
        result["uncertainties"].append("Profil CPU : OCR seul ; validation humaine obligatoire avant calcul")
    if observation["kind"] == "unknown":
        result["uncertainties"].append("Photographie illisible ou équipement non reconnu")
    if observation["kind"] == "machine_display" and observation["downtime_minutes"] is None:
        result["uncertainties"].append("Durée d'arrêt inconnue ; fournir une durée et un instant de début")
    budget.check()
    return result
