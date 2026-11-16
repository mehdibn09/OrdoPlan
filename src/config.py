import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNTIME = Path(os.getenv("ORDOPLAN_RUNTIME", str(ROOT / ".runtime")))
MAX_UPLOAD = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
MODEL_MODE = os.getenv("ORDOPLAN_MODEL_MODE", "ocr")
RETRIEVAL_MODE = os.getenv("ORDOPLAN_RETRIEVAL", "local")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")


def runtime_dir():
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    return RUNTIME
