"""Rétention minimale ; ne supprime pas les versions MES sans action explicite."""
import time
from src.storage.store import Store


def main():
    store=Store();now=time.time()
    with store.db() as db:
        db.execute("DELETE FROM sessions WHERE expires<?",(now,))
        db.execute("DELETE FROM link_codes WHERE expires<?",(now,))
        db.execute("DELETE FROM approvals WHERE expires<? AND used=0",(now-86400,))
        db.execute("DELETE FROM audit WHERE at<?",(now-30*86400,))
    print("Sessions et codes expirés purgés ; audit conservé 30 jours. Versions MES conservées pour retour arrière.")


if __name__=="__main__":main()
