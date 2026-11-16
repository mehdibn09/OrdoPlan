"""Petit reranker local supervisé ; profil neuronal optionnel séparé."""
import json
import os
import re
import unicodedata
import numpy as np
from src.config import ROOT


def tokens(text):
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text))


def features(query, passage):
    a, b = tokens(query), tokens(passage)
    machines_a = {t for t in a if re.fullmatch(r"(?:cnc|tour)-[a-z]", t)}
    machines_b = {t for t in b if re.fullmatch(r"(?:cnc|tour)-[a-z]", t)}
    ids_a = {t for t in a if re.fullmatch(r"(?:ref|of)-\d+", t)}
    ids_b = {t for t in b if re.fullmatch(r"(?:ref|of)-\d+", t)}
    topics = [{"reglage", "changement", "serie", "setup", "changeover"}, {"unitaire", "operatoire", "duree", "duration"}, {"matiere", "reception", "material"}, {"outil", "outillage", "tool"}, {"alarme", "afficheur", "arret", "alarm"}, {"publication", "accord", "approbation", "validation", "approval"}, {"operateur", "absence", "operator"}, {"gele", "gel", "commencee", "freeze"}]
    return np.array([len(a & b)/max(1, len(a)), len(a & b)/max(1, len(a|b)), float(bool(machines_a & machines_b)), float(bool(machines_a and machines_b and not machines_a & machines_b)), float(bool(ids_a & ids_b)), float(bool(ids_a and ids_b and not ids_a & ids_b)), *[float(bool(a&t) and bool(b&t)) for t in topics], 1.0])


class Reranker:
    def __init__(self, mode="adapted"):
        self.mode = mode
        path = ROOT / "models/reranker_local_v1.json"
        self.weights = np.array(json.loads(path.read_text())["weights"]) if path.exists() else None

    def score(self, query, passage):
        x = features(query, passage)
        if self.mode == "adapted" and self.weights is not None:
            return float(x @ self.weights)
        return float(x[0] + .5*x[2] - .2*x[3] + .5*x[4] - .2*x[5])

    def rank(self, query, passages):
        if os.getenv("ORDOPLAN_RERANKER", "local") == "neural":
            return neural_rank(query, passages)
        return sorted(passages, key=lambda p: self.score(query, p["title"]+" "+p["text"]), reverse=True)


from functools import lru_cache


@lru_cache(maxsize=1)
def neural_model():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(2)
    path = os.getenv("ORDOPLAN_RERANKER_PATH", str(ROOT/"models/reranker_adapted"))
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True)
    model.eval()
    return tokenizer, model


def neural_rank(query, passages):
    import torch
    tokenizer, model = neural_model()
    scored = []
    with torch.inference_mode():
        for offset in range(0, len(passages), 8):
            batch = passages[offset:offset+8]
            inputs = tokenizer([query]*len(batch), [p["title"]+" "+p["text"] for p in batch], padding=True, truncation=True, max_length=128, return_tensors="pt")
            scores = model(**inputs).logits[:,0].tolist()
            scored.extend(zip(scores,batch))
    return [p for score,p in sorted(scored,key=lambda x:x[0],reverse=True)]
