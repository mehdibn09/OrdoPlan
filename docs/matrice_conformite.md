# Matrice des livrables et écarts explicites

Les quatre étapes forment une seule application. « Livré » désigne un code, document ou artefact présent ; les conditions d'exécution et validations non effectuées sont distinguées. Les choix technologiques proposés comme possibilités dans le sujet ne sont pas tous des obligations : SQLite chiffré est retenu pour les métadonnées du prototype, au lieu de PostgreSQL/MinIO.

| Référence | Livrable adapté à OrdoPlan | Emplacement et preuve | État |
|---|---|---|---|
| L1.1 | Cadrage et architecture | `docs/cadrage_et_architecture.md`, diagramme du rapport | Livré |
| L1.2 | Pipeline d'ingestion | `src/ingestion/`, `scripts/ingest.py`, 40 PDF et manifeste | Exécuté |
| L1.3 | Index Qdrant et métadonnées | `src/rag/retriever.py`, `data/index_local/`, `data/corpus/chunks.json` | Index léger livré, sémantique reconstruit depuis les poids |
| L1.4 | FastAPI et chaîne RAG LangChain | `src/api/main.py`, `src/rag/retriever.py` | Testé |
| L1.5 | Interface Streamlit | `src/ui/app.py`, captures `reports/interface_*.png` | Testée au navigateur |
| L1.6 | Tests documentaires et d'accès | `tests/test_documents.py`, `tests/test_api_endpoints.py`, rapports XML | Exécutés |
| L2.1 | Analyse photo VLM + OCR | `src/llm/`, `src/ingestion/pdf_parser.py`, `reports/vlm_smoke.json` | Modèle local essayé ; lectures incomplètes explicites |
| L2.2 | RAG multimodal | `src/rag/visual.py`, RRF et encodeurs appariés | Essai local avec modèles ouverts |
| L2.3 | 800–1 500 exemples d'adaptation | `data/training/triplets.jsonl`, manifeste, 1 000 triplets | Contrôle automatique ; sans validation experte |
| L2.4 | Reranker adapté et versionné | `models/reranker_local_v1.json`, pack `reranker_adapted`, script neuronal | Entraînement réel réalisé |
| L2.5 | Comparaison avant/après | `reports/retrieval_metrics.json`, `reports/neural_reranker_metrics.json` | Résultats observés, pas de gain neuronal démontré |
| L2.6 | V2 texte + photo | Onglets documents et photos | Fonctionnel ; champs à confirmer |
| L3.1 | Graphe d'états LangGraph | `src/agent/graph.py`, checkpoints chiffrés | Interruption et reprise testées |
| L3.2 | Serveur MCP MES/ERP | `src/mcp_server/server.py`, SDK MCP v2 | Transport réel testé |
| L3.3 | Client MCP intégré | `src/mcp_server/client.py` | Exécuté dans le parcours HTTP |
| L3.4 | Brouillon de publication de planning | `Store.prepare`, sortie `proposed_action` | Remplace le ticket de maintenance |
| L3.5 | Validation humaine et accès | Hash, identité, atelier, rôle, expiration, révision, idempotence | Tests unitaires/API et transport réel |
| L3.6 | Démonstration complète | `scripts/demo_end_to_end.py`, `reports/end_to_end.json` | Exécutée |
| L4.1 | Bot Telegram | `src/bot/telegram_bot.py` et association d'identités | Code livré ; jeton personnel et essai Telegram réel requis |
| L4.2 | Backend intégré avec identités | Sessions, rôles, ateliers, association à usage unique | Testé |
| L4.3 | Docker Compose et installation | Dockerfiles, Compose, scripts Linux/Windows, `docs/installation.md` | État réel du build dans le rapport de déploiement |
| L4.4 | Tests automatisés et sécurité | `tests/`, CI, scénarios d'injection et d'approbation | Exécutés localement |
| L4.5 | Évaluation et performances | 150 cas, CSV/JSON, métriques, latences séparées | Exécutée ; portée synthétique |
| L4.6 | Documentation utilisateur et technique | README, guides, modèle, sécurité, limites, rapport | Livrée |
| L4.7 | Démonstration et soutenance | Scénario, questions du jury, support PPTX/PDF | Livrés |

## Exigences propres à OrdoPlan

| Exigence | Réalisation |
|---|---|
| CP-SAT et contrôleur indépendant | `src/solver/cp_sat.py`, `checker.py` |
| Machines alternatives, réglages, ressources, matière, gel | Intervalles optionnels, circuits et NoOverlap ; tests de corruption |
| Objectif retard, stabilité, fin | Résolution lexicographique en étapes bornées |
| 50 instances, règles simples et comparaison | `data/instances`, FIFO/EDD, référence manuelle simplifiée et résultats |
| Publication approuvée, doublon et retour arrière | Transaction atomique, jeton lié au hash/utilisateur, révisions et restauration approuvée |
| 3 MCP, 6 modèles, 60 s, solveur borné | Budgets dans le code et tests de dépassement |
| Incertitude et sources | Clarification, sources structurées, ACL avant récupération et ouverture |
| MLOps | MLflow, verrous de versions, prompts, CI et audits exécutés |

## Validations non substituables à du code

L'entretien avec un chef d'atelier, la validation experte des 1 000 annotations, la relecture de clarté, le benchmark GPU de 24 Go et une intégration à un vrai MES n'ont pas été effectués. Ils ne sont pas présentés comme acquis. Les questions du jeu synthétique sont faciles et le VLM compact est limité. Les états du déploiement et de Telegram sont explicités dans les rapports plutôt que déduits de l'existence des scripts.
