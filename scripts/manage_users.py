"""Création explicite d'un utilisateur hors mode démonstration."""
import argparse
import getpass
import secrets
from src.storage.store import Store
from src.auth.auth_service import password_hash


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--role",choices=["chef","planificateur","lecteur"],required=True)
    parser.add_argument("--workshop",choices=["ATELIER-1","ATELIER-2"],required=True)
    args=parser.parse_args()
    password=getpass.getpass("Mot de passe (12 caractères minimum) : ")
    if len(password)<12:raise SystemExit("Mot de passe trop court")
    salt=secrets.token_hex(16)
    with Store().db() as db:
        db.execute("INSERT INTO users VALUES(?,?,?,?,?)",(args.username,salt,password_hash(password,salt),args.role,args.workshop))
    print("Utilisateur créé")


if __name__=="__main__":main()
