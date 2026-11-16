"""Réextrait les PDF et construit l'index avec métadonnées et droits existants."""
import hashlib
import json
import argparse
from src.config import DATA,ROOT
from src.ingestion.pdf_parser import extract_pdf
from src.rag.retriever import Retriever


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--verify",action="store_true");args=parser.parse_args()
    manifest=json.loads((DATA/"corpus/manifest.json").read_text())
    chunks=json.loads((DATA/"corpus/chunks.json").read_text())
    for document in manifest:
        path=ROOT/document["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=document["sha256"]:raise ValueError("Hash PDF différent : "+document["id"])
        pages=extract_pdf(path.read_bytes())
        for p in [c for c in chunks if c["document_id"]==document["id"]]:
            page=pages[p["page"]-1]
            if not page["text"].strip():raise ValueError("Page vide : "+document["id"])
            if not (ROOT/p["image"]).exists():raise ValueError("Figure absente")
    if not args.verify:
        retriever=Retriever();print("Index Qdrant :",retriever.collection);retriever.client.close()
    print(f"{len(manifest)} documents et {len(chunks)} éléments vérifiés")


if __name__=="__main__":main()
