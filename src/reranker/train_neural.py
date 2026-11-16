"""Adaptation ciblée d'un cross-encoder multilingue ouvert, sans service tiers."""
import argparse
import json
import time
import numpy as np
from src.config import DATA,ROOT
from src.reranker.evaluate_reranker import ranking_metrics


def main():
    import torch
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    parser=argparse.ArgumentParser()
    parser.add_argument("--epochs",type=int,default=1)
    parser.add_argument("--batch-size",type=int,default=8)
    parser.add_argument("--max-length",type=int,default=128)
    args=parser.parse_args()
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    np.random.seed(2026)
    source=ROOT/"models/reranker"
    destination=ROOT/"models/reranker_adapted"
    tokenizer=AutoTokenizer.from_pretrained(source,local_files_only=True)
    model=AutoModelForSequenceClassification.from_pretrained(source,local_files_only=True)
    rows=[json.loads(line) for line in (DATA/"training/triplets.jsonl").read_text().splitlines()]
    train=[r for r in rows if r["split"]=="train"]
    validation=[r for r in rows if r["split"]=="validation"]
    test=[r for r in rows if r["split"]=="test"]
    manifest=json.loads((DATA/"training/manifest.json").read_text())
    def score(pairs):
        model.eval()
        values=[]
        with torch.inference_mode():
            for i in range(0,len(pairs),args.batch_size):
                batch=pairs[i:i+args.batch_size]
                encoded=tokenizer([q for q,p in batch],[p for q,p in batch],padding=True,truncation=True,max_length=args.max_length,return_tensors="pt")
                values.extend(model(**encoded).logits[:,0].tolist())
        return values
    def evaluate(split_rows):
        passages={r["positive_document_id"]:r["positive"] for r in split_rows}
        ids=sorted(passages)
        pairs=[(r["query"],passages[d]) for r in split_rows for d in ids]
        values=np.array(score(pairs)).reshape(len(split_rows),len(ids))
        ranks=[sorted(range(len(ids)),key=lambda j:values[i,j],reverse=True).index(ids.index(r["positive_document_id"]))+1 for i,r in enumerate(split_rows)]
        return ranking_metrics(ranks)
    started=time.monotonic()
    before=evaluate(test)
    print("pretrained",before,flush=True)
    # Adapter les deux dernières couches et la tête ; le reste reste gelé.
    for name,param in model.named_parameters():
        param.requires_grad=any(part in name for part in ["encoder.layer.10.","encoder.layer.11.","classifier","pooler"])
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=2e-5)
    pairs=[(r["query"],r[field],label) for r in train for field,label in [("positive",1.),("negative",0.)]]
    losses=[]
    validation_losses=[]
    rng=np.random.default_rng(2026)
    for epoch in range(args.epochs):
        model.train()
        indices=rng.permutation(len(pairs))
        for step,start in enumerate(range(0,len(pairs),args.batch_size)):
            batch=[pairs[i] for i in indices[start:start+args.batch_size]]
            encoded=tokenizer([q for q,p,y in batch],[p for q,p,y in batch],padding=True,truncation=True,max_length=args.max_length,return_tensors="pt")
            labels=torch.tensor([y for q,p,y in batch])
            logits=model(**encoded).logits[:,0]
            loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,labels)
            optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(params,1.);optimizer.step()
            losses.append(float(loss.detach()))
            if step%25==0:
                print("epoch",epoch,"batch",step,"loss",losses[-1],flush=True)
        val_pairs=[(r["query"],r[f]) for r in validation for f in ["positive","negative"]]
        val_logits=torch.tensor(score(val_pairs))
        val_labels=torch.tensor([v for _ in validation for v in [1.,0.]])
        validation_losses.append(float(torch.nn.functional.binary_cross_entropy_with_logits(val_logits,val_labels)))
    after=evaluate(test)
    model.save_pretrained(destination,safe_serialization=True)
    tokenizer.save_pretrained(destination)
    report={"base_model":"cross-encoder/mmarco-mMiniLMv2-L12-H384-v1","revision":json.loads((ROOT/"models/models.lock.json").read_text())["reranker"]["revision"],"dataset_sha256":manifest["sha256"],"train_triplets":len(train),"validation_triplets":len(validation),"test_queries":len(test),"epochs":args.epochs,"batch_size":args.batch_size,"max_length":args.max_length,"seed":2026,"trainable_parameters":sum(p.numel() for p in params),"pretrained":before,"adapted":after,"validation_losses":validation_losses,"training_loss_mean":float(np.mean(losses)),"elapsed_seconds":time.monotonic()-started,"hardware":"CPU, 2 threads, pas de GPU","limitations":"Données synthétiques, séparation par document, titres explicites. Aucune validation experte ou revendication de généralisation. L'amélioration n'est pas garantie."}
    (ROOT/"reports/neural_reranker_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (destination/"adaptation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=="__main__":
    main()
