"""Enregistre les métriques réelles et leurs rapports dans MLflow."""
import json
import os
from src.config import ROOT


def main():
    import mlflow
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI",(ROOT/"reports/mlruns").as_uri()))
    mlflow.set_experiment("ordoplan-v1")
    for filename in ["evaluation.json","retrieval_metrics.json","neural_reranker_metrics.json"]:
        path=ROOT/"reports"/filename
        if not path.exists():continue
        data=json.loads(path.read_text())
        with mlflow.start_run(run_name=filename.removesuffix(".json")):
            mlflow.log_params({"application":"1.0.0","data":"1.0.0","prompts":"v1","execution":"CPU local"})
            def log(prefix,value):
                if isinstance(value,dict):
                    for key,item in value.items():log(prefix+"_"+key,item)
                elif isinstance(value,(int,float)) and not isinstance(value,bool):
                    mlflow.log_metric(prefix.replace("@", "_at_"),value)
            for key in ["executed","passed","failed","latency_seconds","solver","replanning","results","pretrained","adapted","elapsed_seconds"]:
                if key in data and isinstance(data[key],(dict,int,float)):log(key,data[key])
            mlflow.log_artifact(str(path))
    experiment=mlflow.get_experiment_by_name("ordoplan-v1")
    runs=mlflow.tracking.MlflowClient().search_runs([experiment.experiment_id],max_results=3,order_by=["attributes.start_time DESC"])
    (ROOT/"reports/mlflow_runs.json").write_text(json.dumps([{"run_id":r.info.run_id,"status":r.info.status,"metrics":r.data.metrics,"params":r.data.params} for r in runs],ensure_ascii=False,indent=2))
    print("Expériences MLflow enregistrées.")


if __name__=="__main__":main()
