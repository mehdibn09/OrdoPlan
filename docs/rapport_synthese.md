# Rapport de réalisation — OrdoPlan

Projet intégrateur d'IA générative multimodale et agentique. Version livrée 1.0.0, 16 novembre 2026.

## Résumé exécutif

OrdoPlan est un prototype fonctionnel d'aide à l'ordonnancement d'un atelier fictif. Il lit un carnet ERP, consulte des documents autorisés, calcule un planning par CP-SAT, vérifie indépendamment les contraintes, explique les écarts et interrompt le workflow avant toute publication MES. La décision d'ordonnancement appartient au solveur. La lecture documentaire et les observations visuelles n'accordent jamais d'autorisation de publication.

La réalisation couvre API FastAPI, Streamlit/Plotly, LangChain/LangGraph, véritable serveur et client MCP v2, Qdrant, OCR local, VLM ouvert, encodeurs multilingues/CLIP, adaptation réelle d'un cross-encoder, approbation liée au contenu, versions MES et retour arrière. Deux profils permettent un démarrage léger et une expérimentation complète des modèles locaux. Le bot Telegram et son association d'identité sont fournis ; son activation réelle requiert les secrets personnels du propriétaire.

Le dépôt contient 40 PDF synthétiques et 87 passages, 50 instances plus le fil rouge, des CSV/Excel et images, 1 000 triplets séparés par document et 150 scénarios. Les documents industriels, entretiens terrain et annotations expertes n'ont pas été inventés. Les choix et écarts au sujet sont détaillés dans la matrice de conformité et la fiche de limites.

## Vérifications observées

- 68 tests unitaires et API réussis dans la suite finale.
- 150/150 scénarios de composants réussis ; 0 contrainte violée dans les 30 plannings de référence.
- Retard pondéré inférieur ou égal à FIFO et EDD dans respectivement 30 et 30 cas sur 30.
- Replanification : p95 du solveur 0.127 s sur 25 aléas synthétiques.
- Les temps de composants ont une médiane de 0.090 s et un p95 de 0.359 s ; ce ne sont pas des latences multi-utilisateurs de production.
- Parcours HTTP + MCP réel réussi, approbation et réessai idempotent vérifiés. Latence p95 de ce parcours de requêtes : 0.298 s dans les conditions décrites dans le JSON.
- Embeddings multilingues + CLIP + reranker adapté essayés localement ; le VLM compact a produit des transcriptions insuffisantes et le système maintient la validation humaine.
- Les audits finaux du socle et de l'environnement complet ne signalent pas de vulnérabilité connue au moment de leur exécution ; la CI doit continuer ces contrôles.

## Lecture de ces résultats

L'adaptation du cross-encoder a réellement entraîné 3,697,153 paramètres pendant 288.7 s sur CPU, une époque, 600 triplets. nDCG@5 et MRR@10 sont identiques avant/après (1.000 et 1.000 pour nDCG@5). Aucun gain neuronal n'est démontré. Le jeu à titres explicites manque de difficulté et ne permet pas de généraliser à l'atelier réel.

La suite de 150 cas comprend 10 images OCR, des exports, PDF et rejets, et non 30 lectures VLM de photos industrielles. Les tests du transport, du navigateur et des modèles sont séparés et accompagnés de preuves. Le matériel GPU de 24 Go n'a pas été évalué.
