# OrdoPlan

Assistant d'ordonnancement multimodal et agentique pour un **atelier fictif**. Le solveur CP-SAT calcule les séquences et les dates ; le contrôleur Python les vérifie ; le chef d'atelier approuve le contenu exact avant sa publication dans un MES simulé.

Le projet reprend la structure du dépôt d'exemple fourni (agent, API, auth, ingestion, LLM, MCP, reranker, schémas, interface) avec des modules propres à l'ordonnancement. Aucun code automobile, corpus ou résultat de ce dépôt n'est repris. La feuille MAINTiDOC fournit les quatre jalons pédagogiques ; les tickets y sont adaptés en brouillons de planning pour le domaine OrdoPlan.

## Démarrer en trois commandes

Prérequis : Docker Desktop avec Compose, 4 Go de RAM disponibles et ports locaux 8000/8501 libres.

```bash
docker compose -f docker-compose.compact.yml up --build -d
docker compose -f docker-compose.compact.yml ps
# Ouvrir http://localhost:8501
```

Compte de démonstration : **chef** / **OrdoPlan-demo-2026!**. Autres comptes : `planif` (prépare), `lecture` (consulte), `chef2` (autre atelier). Ce mot de passe est public et réservé au prototype local.

API : http://localhost:8000/docs. Le profil compact regroupe les trois processus et utilise Qdrant local. Arrêt : `docker compose -f docker-compose.compact.yml down` (le volume reste conservé). La variante à services séparés est fournie dans `docker-compose.yml` : `docker compose up --build -d`.

Sans Docker, avec Python 3.12 et Tesseract :

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run.py
```

Sous Windows : `powershell -ExecutionPolicy Bypass -File scripts/install.ps1`, puis `run.bat`. Voir [l'installation complète](docs/installation.md) pour Tesseract, les modèles et Telegram.

## Deux profils explicites

| Profil | Lecture | Recherche | Reranking | Conditions |
|---|---|---|---|---|
| Démonstration CPU, par défaut | OCR local + validation humaine | Qdrant avec vecteurs de caractères, recherche lexicale et descriptions des pages | Petit reranker supervisé local | Aucun poids à télécharger, pas de service de modèle |
| IA locale | VLM SmolVLM + OCR, désaccord soumis à validation | Embeddings multilingues + CLIP texte-image | Cross-encoder multilingue réellement adapté | Installer `requirements-neural.txt` et extraire le pack de modèles |

Le profil CPU n'est pas présenté comme équivalent à un VLM ou à BGE-M3. Le profil IA utilise des modèles ouverts comparables, plus petits pour les essais CPU. Qwen2.5-VL-7B est une cible matérielle non évaluée ici. Aucun planning n'est généré par le modèle dans les deux profils.

## Parcours rapide

1. Ouvrir **Atelier & planning** et calculer `demo`.
2. Ouvrir **Replanifier après un aléa**. Une panne ne doit pas chevaucher une opération gelée ; le script de démonstration calcule une frontière valide (voir `docs/demonstration.md`).
3. Ajouter l'urgence OF-109, comparer les retards et les déplacements.
4. Dans **Validation MES**, lire le Gantt et toutes les lignes, confirmer le contenu, approuver puis publier.
5. Dans **Documents & photos**, essayer l'afficheur, l'OF papier, l'image illisible et l'injection.
6. Dans **Assistant documentaire**, demander le réglage ALU → ACIER et ouvrir le PDF cité.

## Vérifier et reproduire

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.evaluate
.venv/bin/python -m scripts.ingest --verify
.venv/bin/python -m src.reranker.evaluate_reranker
.venv/bin/python -m scripts.scan_secrets
.venv/bin/python -m scripts.log_experiments
```

Entraînement réel du petit modèle neuronal, après provisionnement :

```bash
.venv/bin/python -m pip install -r requirements-neural.txt
.venv/bin/python -m scripts.download_models reranker
.venv/bin/python -m src.reranker.train_neural --epochs 1
```

Les 1 000 triplets sont séparés **par document** (600 entraînement, 200 validation, 200 test). Les annotations synthétiques ont été contrôlées automatiquement, sans validation industrielle. Le benchmark est facile car les questions citent des titres : le rapport ne prétend pas démontrer un gain général de fine-tuning.

## Contenu livré

- `src/` : API, orchestration LangGraph, MCP, solveur, contrôleur, RAG, lecture locale, sécurité, Streamlit et bot Telegram.
- `data/` : 40 PDF synthétiques et pages visuelles, corpus avec métadonnées, 50 instances + démo, CSV/Excel, images, 1 000 triplets, 150 scénarios.
- `models/` : reranker léger adapté et verrou de révision ; poids neuronaux dans le pack séparé.
- `prompts/` : cinq prompts versionnés ; copies compatibles avec la structure `configs/prompts/` de l'exemple.
- `reports/` : résultats exécutés, métriques, entraînement réel, tests XML, captures et rapports de déploiement.
- `docs/` : architecture, modèle mathématique, installation, guides, limites, matrice des livrables, démonstration, jalons et soutenance.
- `.github/workflows/ci.yml` : tests, évaluation, contrôle de secrets et audit des dépendances.

## Résultats et périmètre

Lire `reports/evaluation.json`, `reports/neural_reranker_metrics.json` et le rapport final pour les mesures exactes et leurs conditions. Le jeu de 150 scénarios teste les composants ; les essais réseau API/MCP, l'interface et le VLM sont consignés séparément. L'absence d'échec sur ce jeu n'est pas une garantie industrielle.

L'atelier est mono-site, avec une opération par OF, des durées déterministes et des machines homogènes pour une gamme donnée. Une panne qui interrompt une opération gelée est signalée comme infaisable ; les suspensions/reprises ne sont pas inventées. Les sources et temps doivent être validés avec un atelier avant un usage réel. Le bot est livré et testé côté logique/identité ; une conversation Telegram réelle nécessite votre jeton personnel et un réseau externe.

Documentation de départ : [installation](docs/installation.md), [guide utilisateur](docs/guide_utilisateur.md), [architecture](docs/cadrage_et_architecture.md), [modèle](docs/modele_optimisation.md), [limites](docs/fiche_de_limites.md), [livrables L1 à L4](docs/matrice_conformite.md).
