"""Entraînement réel du reranker à caractéristiques locales (CPU léger)."""
import json
from sklearn.linear_model import LogisticRegression
from src.config import DATA, ROOT
from src.reranker.reranker_service import features


def train():
    rows = [json.loads(line) for line in (DATA/"training/triplets.jsonl").read_text().splitlines()]
    x,y = [],[]
    for r in rows:
        if r["split"] == "train":
            x.extend([features(r["query"],r["positive"]),features(r["query"],r["negative"])])
            y.extend([1,0])
    model = LogisticRegression(C=1.,random_state=42,max_iter=300).fit(x,y)
    artifact = {"version":"local-v1","kind":"supervised lexical multilingual feature ranker, not a pretrained transformer","weights":model.coef_[0].tolist(),"intercept":model.intercept_[0],"training_pairs":len(y),"data_version":"1.0.0","seed":42}
    (ROOT/"models/reranker_local_v1.json").write_text(json.dumps(artifact,ensure_ascii=False,indent=2))
    return artifact


if __name__=="__main__":
    print(train())
