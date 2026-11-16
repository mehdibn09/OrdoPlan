"""Point d'entrée compatible avec l'organisation du dépôt de référence."""
from src.rag.retriever import Retriever


def build_index():
    retriever=Retriever()
    result={"collection":retriever.collection,"dimension":retriever.encoder.dim,"mode":retriever.encoder.mode,"elements":len(retriever.chunks)}
    retriever.client.close()
    return result
