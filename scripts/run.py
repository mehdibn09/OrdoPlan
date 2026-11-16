"""Lance les trois services locaux ; arrêt propre par Ctrl+C."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env",override=False)
    runtime=ROOT/".runtime"
    runtime.mkdir(exist_ok=True,mode=0o700)
    os.chdir(ROOT)
    commands=[("mcp",["-m","uvicorn","src.mcp_server.server:app","--host","127.0.0.1","--port","8101","--no-access-log"]),
              ("api",["-m","uvicorn","src.api.main:app","--host","127.0.0.1","--port","8000","--no-access-log"]),
              ("ui",["-m","streamlit","run","src/ui/app.py","--server.address","127.0.0.1","--server.port","8501","--browser.gatherUsageStats","false"])]
    children=[]
    handles=[]
    try:
        for name,command in commands:
            handle=(runtime/(name+".log")).open("a",encoding="utf-8")
            handles.append(handle)
            child=subprocess.Popen([sys.executable,*command],cwd=ROOT,stdout=handle,stderr=handle)
            children.append(child)
            time.sleep(.3)
            if child.poll() is not None:
                raise RuntimeError(name+" n'a pas démarré ; consulter .runtime/"+name+".log (port déjà occupé ?)")
        for _ in range(40):
            if any(c.poll() is not None for c in children):
                raise RuntimeError("Un service s'est arrêté ; consulter .runtime/*.log")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health",timeout=1):break
            except Exception:time.sleep(.5)
        else:raise RuntimeError("API indisponible après 20 s")
        print("OrdoPlan prêt : http://127.0.0.1:8501\nAPI : http://127.0.0.1:8000/docs\nMCP : http://127.0.0.1:8101/mcp\nCompte : chef / OrdoPlan-demo-2026!\nCtrl+C pour arrêter.",flush=True)
        while all(c.poll() is None for c in children):time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt d'OrdoPlan…")
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill()
        for handle in handles:handle.close()


if __name__=="__main__":main()
