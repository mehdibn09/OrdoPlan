# Protocole expérimental

## Données

Le corpus est synthétique et versionné : 40 PDF, pages visuelles, métadonnées et droits. L'atelier 2 fournit quatre documents pour les essais d'isolation. Les 50 instances font varier quantités, échéances, poids et disponibilités matière autour d'un atelier à huit OF. Les sources des variantes sont les exports synthétiques incorporés aux instances.

Les 1 000 triplets associent une question, un passage positif et un négatif lexical voisin. La séparation porte sur les documents, y compris les négatifs : 24 documents d'entraînement, 8 de validation, 8 de test ; 25 questions par document. L'annotation est vérifiée automatiquement par l'identifiant exact du titre demandé et l'intégrité des sources. Elle n'est pas une annotation métier par expert.

## Comparaisons de recherche

Le rapport léger compare vecteurs TF-IDF sans reranking, règles initiales et reranker local appris. Le rapport neuronal compare le cross-encoder multilingue original au même modèle après adaptation ciblée de deux couches et de la tête, BCE sur paires positives/négatives, AdamW 2e-5, une époque, batch 8, longueur 128, graine 2026, CPU deux threads. Le jeu de test n'est pas utilisé pour le gradient ni pour choisir une hyperparamétrisation.

Les métriques sont Recall@5, nDCG@5 et MRR@10. Une seule source documentaire est déclarée pertinente par requête, les autres documents du même split sont candidats. Cette formulation à titres explicites est facile et n'évalue pas une recherche ouverte réaliste. L'absence de gain après adaptation doit être conservée dans le rapport, sans promesse d'amélioration.

## 150 scénarios de composants

| Catégorie | Nombre | Vérifications |
|---|---:|---|
| Lecture | 30 | 10 images d'OF OCR, 10 CSV, 5 PDF, 5 entrées invalides |
| Recherche | 20 | Document attendu dans les 5 premiers, citations exactes et ACL |
| Ordonnancement | 30 | Couverture, contraintes, métriques CP-SAT comparées à FIFO/EDD et référence manuelle |
| Replanification | 25 | 10 pannes, 10 urgences, 5 retards matière, gel et validité |
| MCP métier | 10 | Commandes, états machines et refus d'accès ; service directement appelé |
| Incertitude | 10 | Sources manquantes et preuve d'infaisabilité |
| Approbation | 10 | Liens d'identité/contenu, expiration, annulation, idempotence et restauration |
| Injection | 15 | Notes OF, OCR et notes d'outil sans effet sur le planning ni publication |

Chaque scénario produit un résultat individuel, un temps et les preuves numériques dans `reports/evaluation.json`, avec un export CSV. Le programme s'arrête avec un code non nul si un cas échoue. Les compteurs sont calculés depuis les résultats, sans score prédéfini.

## Essais complémentaires

Les tests unitaires et API sont distincts de ces 150 scénarios. Les tests API utilisent un transport MCP remplacé par son service métier pour isoler les erreurs. `scripts.demo_end_to_end` vérifie ensuite réellement le transport Streamable HTTP, LangGraph, l'accord et la publication. Les captures du navigateur attestent connexion, calcul et recherche documentaire.

Le profil embeddings/CLIP/reranker neuronal est essayé localement, avec un rapport de chargement à froid. Le VLM est essayé sur une image contrôlée et son texte brut est conservé. Une transcription incomplète ne devient pas un succès de lecture. Le taux exact après correction humaine, la clarté par un praticien, 30 photos réelles et les ressources GPU n'ont pas été mesurés.

## Interprétation

Les temps de composants ne sont pas des temps de réponse d'une plateforme multi-utilisateur. Les percentiles ne sont pas mélangés entre solveur, API, OCR et modèles à froid. Une comparaison sur des données synthétiques ne prouve pas une supériorité industrielle. La référence manuelle est une séquence explicitement fixée et sérialisée, pas l'avis d'un planificateur professionnel.

Les rapports d'audit des dépendances indiquent leur périmètre et l'état observé au moment de l'exécution. La CI doit poursuivre ces contrôles. Une mise à jour de dépendance ou de modèle nécessite les tests appropriés et une nouvelle mesure si elle modifie le résultat.
