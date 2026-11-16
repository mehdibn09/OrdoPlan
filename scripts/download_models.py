"""Provisionnement explicite : le fonctionnement courant reste hors ligne."""
import argparse
import json
import os
from src.config import ROOT

MODELS = {
    "vlm": "HuggingFaceTB/SmolVLM-256M-Instruct",
    "embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "reranker": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "clip_text": "sentence-transformers/clip-ViT-B-32-multilingual-v1",
    "clip_image": "sentence-transformers/clip-ViT-B-32",
}


def main():
    from huggingface_hub import HfApi, snapshot_download
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", choices=list(MODELS), default=["vlm", "embedding", "reranker"])
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    lockpath = ROOT/"models/models.lock.json"
    lock = json.loads(lockpath.read_text()) if lockpath.exists() else {}
    for name in args.names:
        repo = MODELS[name]
        info = HfApi().model_info(repo)
        revision = lock.get(name, {}).get("revision", info.sha)
        dest = ROOT/"models"/name
        snapshot_download(repo, revision=revision, local_dir=dest, ignore_patterns=["*.bin", "*.h5", "*.ot", "onnx/*", "openvino/*", "*.msgpack", "*.tflite"], max_workers=2)
        lock[name] = {"repository": repo, "revision": revision, "license": getattr(info.card_data, "license", None), "local_path": str(dest.relative_to(ROOT))}
        lockpath.write_text(json.dumps(lock, indent=2))
        print(name, revision, flush=True)


if __name__ == "__main__":
    main()
