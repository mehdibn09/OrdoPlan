import hashlib
import json
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.config import DATA


def generate():
    rng = random.Random(2026)
    chunks = json.loads((DATA/"corpus/chunks.json").read_text())
    by_doc = {}
    for p in chunks:
        if p["page"] == 1 and p["document_id"] not in by_doc:
            by_doc[p["document_id"]] = p
    ids = sorted(by_doc)
    rng.shuffle(ids)
    splits = {"train":ids[:24],"validation":ids[24:32],"test":ids[32:]}
    starters = ["Que dit la documentation sur", "Quelle règle concerne", "Explique la procédure de", "Quelle information s'applique à", "Je cherche la règle concernant"]
    endings = ["?", " dans cet atelier ?", " avec une référence précise ?", " pour la planification ?", " selon la source autorisée ?"]
    records = []
    for split, document_ids in splits.items():
        texts = [by_doc[d]["title"]+" "+by_doc[d]["text"] for d in document_ids]
        tf = TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5)).fit_transform(texts)
        similarities = cosine_similarity(tf)
        for i, did in enumerate(document_ids):
            p = by_doc[did]
            candidates = sorted((j for j in range(len(document_ids)) if j!=i),key=lambda j:similarities[i,j],reverse=True)
            for v in range(25):
                query = f"{starters[v//5]} {p['title']}{endings[v%5]}"
                negative_id = document_ids[candidates[v%min(3,len(candidates))]]
                records.append({"id":f"{split}-{did}-{v}","split":split,"query":query,"positive_document_id":did,"negative_document_id":negative_id,"positive":p["title"]+" "+p["text"],"negative":by_doc[negative_id]["title"]+" "+by_doc[negative_id]["text"],"annotation":"source exacte du titre demandé ; négatif voisin lexical dans le même split", "verified_automatically":True, "expert_verified":False})
    path = DATA/"training/triplets.jsonl"
    path.write_text("\n".join(json.dumps(r,ensure_ascii=False) for r in records)+"\n")
    assert len(records)==1000
    assert not (set(splits["train"])&set(splits["test"]) or set(splits["train"])&set(splits["validation"]) or set(splits["validation"])&set(splits["test"]))
    for r in records:
        assert r["positive_document_id"] != r["negative_document_id"]
        assert r["positive_document_id"] in splits[r["split"]] and r["negative_document_id"] in splits[r["split"]]
    metadata = {"version":"1.0.0","seed":2026,"count":1000,"counts":{s:sum(r['split']==s for r in records) for s in splits},"documents":splits,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"validation":"Contrôles automatiques d'intégrité, séparation par document. Pas de validation par praticien. Questions synthétiques fondées sur les titres : benchmark limité et plus facile que des requêtes réelles."}
    (DATA/"training/manifest.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    return records


if __name__=="__main__":
    print(len(generate()),"triplets générés et contrôlés")
