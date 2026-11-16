import json
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from src.config import DATA,ROOT
from src.reranker.reranker_service import Reranker


def ranking_metrics(rankings):
    ranks = list(rankings)
    return {"Recall@5":float(np.mean([r<=5 for r in ranks])),"nDCG@5":float(np.mean([1/math.log2(r+1) if r<=5 else 0 for r in ranks])),"MRR@10":float(np.mean([1/r if r<=10 else 0 for r in ranks]))}


def evaluate():
    rows = [json.loads(line) for line in (DATA/"training/triplets.jsonl").read_text().splitlines() if json.loads(line)["split"] == "test"]
    passages = {r["positive_document_id"]:r["positive"] for r in rows}
    ids = sorted(passages)
    texts = [passages[i] for i in ids]
    vectorizer = TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5))
    matrix = vectorizer.fit_transform(texts)
    result = {}
    for name in ["sans_reranker", "reranker_regles_initial", "reranker_local_adapte"]:
        ranks = []
        for r in rows:
            if name == "sans_reranker":
                scores = (matrix@vectorizer.transform([r["query"]]).T).toarray().ravel()
            else:
                reranker = Reranker("base" if name=="reranker_regles_initial" else "adapted")
                scores = [reranker.score(r["query"],p) for p in texts]
            order = sorted(range(len(ids)),key=lambda i:scores[i],reverse=True)
            ranks.append(order.index(ids.index(r["positive_document_id"]))+1)
        result[name] = ranking_metrics(ranks)
    report = {"test_queries":len(rows),"test_documents":len(ids),"split":"documents disjoints", "results":result,"limitation":"Requêtes synthétiques à titres explicites ; ne démontre pas la généralisation aux requêtes d'atelier. Le reranker initial ici est à règles, la comparaison neuronale est dans neural_reranker_metrics.json."}
    (ROOT/"reports/retrieval_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=="__main__":
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
