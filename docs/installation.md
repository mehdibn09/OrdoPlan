# Installation et exploitation

## Environnement reproductible

Python 3.12 est la version testée. `requirements.in` décrit les dépendances directes et `requirements.lock.txt` fige leurs dépendances transitives. `requirements-full.lock.txt` décrit l'environnement complet des essais, y compris les outils de développement et les modèles. Le mode léger ne nécessite ni GPU, ni clé de modèle.

Le premier `docker compose up --build -d` requiert Internet pour les images et paquets. Après provisionnement, les services d'ordonnancement, de RAG et d'inférence fonctionnent localement. Le profil Telegram constitue une sortie réseau explicite indépendante des modèles. Ne pas confondre absence d'API de modèle et absence de téléchargement d'installation.

## Docker Compose

Pour une première démonstration, utiliser `docker compose -f docker-compose.compact.yml up --build -d`. Les trois processus tournent dans un conteneur avec un index Qdrant local. Le parcours HTTP/MCP et l'interface sont identiques. Prévoir 10 Go d'espace libre pour installer et construire, davantage avec les modèles. Le fichier principal ci-dessous sépare API, MCP, interface et serveur Qdrant ; son état de vérification est décrit dans le rapport de déploiement.

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail 50 api mcp ui
```

Les ports 8000 et 8501 sont liés à l'interface locale. Les conteneurs API et MCP partagent le volume chiffré de démonstration ; Qdrant dispose de son volume. API : un processus, pas plusieurs workers sur le même fichier SQLite. Le stockage transactionnel SQLite est un choix de prototype ; PostgreSQL et MinIO sont des choix possibles du sujet, non des composants revendiqués ici. Pour un atelier multi-utilisateur en production, une migration transactionnelle et un service d'identité seront nécessaires.

`docker compose down` arrête les services et conserve les données. **`docker compose down -v` efface les données de démonstration** : ne l'utiliser que pour une réinitialisation voulue.

## Installation native

Linux : Python 3.12, `tesseract-ocr`, `tesseract-ocr-fra`, `tesseract-ocr-eng`, `fonts-dejavu-core`, `libgomp1`.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/run.py
```

Windows : installer Python 3.12, puis Tesseract et ajouter le dossier de `tesseract.exe` au `PATH`. Exécuter `scripts/install.ps1` dans PowerShell, puis `run.bat`. Le lancement utilise des sous-processus Python portables ; l'environnement Windows n'a pas été exécuté dans les essais Linux fournis.

Le script ouvre API :8000, MCP :8101, Streamlit :8501 et les arrête par Ctrl+C. Les journaux techniques sont dans `.runtime/`. Si un port est occupé, fermer l'autre instance puis relancer ; ne pas tuer un service inconnu. Lancer chaque commande depuis la racine du projet.

## Modèles ouverts locaux

Le pack séparé se décompresse **à la racine d'OrdoPlan** : on doit obtenir `models/vlm/config.json`, `models/embedding/config.json`, `models/reranker_adapted/config.json`, `models/clip_text/` et `models/clip_image/`. Les révisions et licences des modèles sources sont consignées dans `models/models.lock.json`. Le modèle original de reranking, utile pour refaire l'adaptation, se télécharge avec `scripts.download_models reranker`.

```bash
.venv/bin/python -m pip install -r requirements-neural.txt
# Sans le pack, provisionner explicitement :
.venv/bin/python -m scripts.download_models vlm embedding reranker clip_text clip_image
# Sans le pack adapté, produire ensuite le modèle adapté :
.venv/bin/python -m src.reranker.train_neural --epochs 1
```

Dans `.env`, activer `ORDOPLAN_MODEL_MODE=vlm`, `ORDOPLAN_VLM_PATH=models/vlm`, `ORDOPLAN_RETRIEVAL=semantic`, `ORDOPLAN_RERANKER=neural`, puis définir les chemins absolus `ORDOPLAN_EMBEDDING_PATH`, `ORDOPLAN_RERANKER_PATH`, `ORDOPLAN_CLIP_TEXT_PATH`, `ORDOPLAN_CLIP_IMAGE_PATH`. Définir `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` après téléchargement.

Pour Compose : construire d'abord l'image de base, puis utiliser `docker compose -f docker-compose.yml -f docker-compose.neural.yml up --build -d`. Prévoir au moins 8 Go de RAM disponibles ; les limites de concurrence restent faibles. Le premier chargement des encodeurs est plus lent qu'une requête à chaud. Le profil neuronal Compose est fourni séparément et ses essais éventuels sont précisés dans le rapport de déploiement, sans les déduire des essais natifs.

## Telegram

Créer votre bot auprès de BotFather, puis placer `TELEGRAM_BOT_TOKEN` et un long `TELEGRAM_BRIDGE_SECRET` aléatoire dans `.env`. Le même secret doit être transmis à l'API et au bot. Ne jamais le mettre dans Git ni dans une capture. En local, `scripts/run.py` charge `.env` ; lancer le bot depuis un terminal ayant ces variables (`python -m src.bot.telegram_bot`). Avec Compose, activer le profil : `docker compose --profile telegram up -d`.

Depuis le web, créer un code d'association, puis envoyer `/link CODE` en conversation privée. Le serveur rattache le compte à une identité existante. Le code est utilisable une fois, pendant 5 minutes. Les permissions sont revérifiées côté API, y compris pour `/approve` et `/publish`. Aucun compte Telegram n'est autorisé par défaut.

Commandes : `/start`, `/ask`, `/plan`, `/breakdown`, `/urgent`, `/history`, `/orders`, `/draft`, `/approve`, `/publish`, `/cancel`, `/unlink`. Les images sont reçues par envoi de photo. Les groupes ne reçoivent pas de données. Le bot ne crée pas de tickets de maintenance, le domaine étant OrdoPlan.

## Suivi, sauvegarde et rétention

`python -m scripts.log_experiments` enregistre les rapports dans MLflow local. `docker compose --profile tracking up -d mlflow` expose le serveur sur :5000 ; définir ensuite `MLFLOW_TRACKING_URI=http://127.0.0.1:5000`. Les expériences portent sur des métriques, sans documents bruts.

Sauvegarder ensemble la base, les checkpoints et `storage.key`. La perte de cette clé rend les plannings chiffrés illisibles. Une sauvegarde à chaud nécessite l'API de sauvegarde SQLite ou l'arrêt des deux services, afin de préserver les transactions ; ne pas copier seulement un fichier WAL isolé.

`python -m scripts.purge` supprime sessions et codes expirés et conserve l'audit 30 jours. Les publications restent disponibles pour le retour arrière ; leur durée de conservation doit être décidée avec l'atelier. Les documents et photos importés ne sont pas journalisés par défaut. Les disponibilités des opérateurs restent pseudonymisées.
