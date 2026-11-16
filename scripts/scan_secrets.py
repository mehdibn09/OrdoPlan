"""Contrôle du périmètre livrable, sans afficher les valeurs détectées."""
import re
from src.config import ROOT


def main():
    findings=[]
    excluded={".git",".runtime",".venv","__pycache__","models","mlruns"}
    patterns=[re.compile(r"AKIA[0-9A-Z]{16}"),re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{35}\b"),re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")]
    for path in ROOT.rglob("*"):
        if not path.is_file() or excluded&set(path.relative_to(ROOT).parts) or path.suffix not in {".py",".yaml",".yml",".txt",".md",".json",".toml",".example"}:
            continue
        text=path.read_text(errors="ignore")
        if any(pattern.search(text) for pattern in patterns):findings.append(str(path.relative_to(ROOT)))
    if (ROOT/".env").exists():
        print(".env local présent : exclu des archives par le script de livraison")
    if findings:raise SystemExit("Motifs de secrets détectés dans : "+", ".join(findings))
    print("Aucun motif de secret détecté dans les sources et documents livrables.")


if __name__=="__main__":main()
