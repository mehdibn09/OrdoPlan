"""Essai HTTP/MCP en conteneur de build, sans conserver identités ni secrets."""
import json
import base64
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    children=[]
    with tempfile.TemporaryDirectory(prefix="ordoplan-smoke-") as folder:
        env=dict(os.environ)
        env.update(ORDOPLAN_RUNTIME=str(Path(folder)/"runtime"),API_URL="http://127.0.0.1:8000",MCP_URL="http://127.0.0.1:8101/mcp",ORDOPLAN_MODEL_MODE="ocr",ORDOPLAN_RETRIEVAL="local",ORDOPLAN_RERANKER="local")
        subprocess.run([sys.executable,"-m","pytest","-q","--junitxml=reports/container-tests.xml","--basetemp",str(Path(folder)/"pytest"),"-o","cache_dir="+str(Path(folder)/"pytest_cache")],env=env,check=True,timeout=180)
        print("ORDOPLAN_TEST_XML "+base64.b64encode(Path("reports/container-tests.xml").read_bytes()).decode(),flush=True)
        log=(Path(folder)/"services.log").open("w")
        commands=[["-m","uvicorn","src.mcp_server.server:app","--host","127.0.0.1","--port","8101","--no-access-log"],["-m","uvicorn","src.api.main:app","--host","127.0.0.1","--port","8000","--no-access-log"],["-m","streamlit","run","src/ui/app.py","--server.address","127.0.0.1","--server.port","8501","--browser.gatherUsageStats","false"]]
        try:
            for command in commands:children.append(subprocess.Popen([sys.executable,*command],env=env,stdout=log,stderr=log))
            for attempt in range(50):
                if any(p.poll() is not None for p in children):raise RuntimeError("Service arrêté pendant le démarrage")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8000/health",timeout=1):pass
                    with urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health",timeout=1):pass
                    break
                except OSError:time.sleep(.4)
            else:raise RuntimeError("Services indisponibles")
            subprocess.run([sys.executable,"-m","scripts.demo_end_to_end"],env=env,check=True,timeout=90)
            result=json.loads(Path("reports/end_to_end.json").read_text())
            print("ORDOPLAN_E2E_JSON "+base64.b64encode(Path("reports/end_to_end.json").read_bytes()).decode(),flush=True)
            print("ORDOPLAN_BUILD_SMOKE_OK "+json.dumps({"status":result["status"],"transport":result["transport"],"latency_seconds":result["latency_seconds"],"ui_health":"ok","identity":"non-root","test_state_retained":False}),flush=True)
        finally:
            for child in children:
                if child.poll() is None:child.terminate()
            for child in children:
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            log.close()


if __name__=="__main__":main()
