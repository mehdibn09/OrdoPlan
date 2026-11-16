"""Crée une archive de remise sans états privés, caches ou poids lourds."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"dist")
    parser.add_argument("--documents",type=Path,default=ROOT/"livrables")
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    excluded={".git",".venv",".runtime","__pycache__",".pytest_cache",".ruff_cache","mlruns",".cache","dist","livrables"}
    allowed_models={"models.lock.json","reranker_local_v1.json"}
    files=[]
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(ROOT)
        if excluded & set(rel.parts) or p.name==".env" or p.suffix in {".pyc",".log",".zip",".bundle"}:continue
        if rel.parts[0]=="models" and (len(rel.parts)!=2 or p.name not in allowed_models):continue
        files.append((p,Path("OrdoPlan")/rel))
    docs=["OrdoPlan_Rapport_Final.pdf","OrdoPlan_Rapport_Final.docx","OrdoPlan_Soutenance.pdf","OrdoPlan_Soutenance.pptx"]
    for name in docs:
        p=args.documents/name
        if not p.exists():raise FileNotFoundError("Document de livraison absent : "+str(p))
        files.append((p,Path("OrdoPlan/livrables")/name))
    manifest=[]
    target=args.output/"OrdoPlan_Complet.zip"
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p,rel in files:
            data=p.read_bytes();z.writestr(str(rel),data);manifest.append({"path":str(rel),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
        z.writestr("OrdoPlan/MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise ValueError("Archive corrompue")
        assert not any('/.runtime/' in n or n.endswith('/.env') or '/.git/' in n for n in z.namelist())
    (args.output/"OrdoPlan_Manifest_Source.json").write_text(json.dumps({"archive":target.name,"files":manifest},ensure_ascii=False,indent=2))
    print(f"{target.name} : {len(files)} fichiers, {target.stat().st_size} octets, CRC vérifiés")


if __name__=="__main__":main()
