# Résultats expérimentaux détaillés

## Scénarios et validité

| Catégorie | Exécutés | Réussis |
|---|---:|---:|
| lecture | 30 | 30 |
| recherche | 20 | 20 |
| ordonnancement | 30 | 30 |
| replanification | 25 | 25 |
| mcp | 10 | 10 |
| incertitude | 10 | 10 |
| approbation | 10 | 10 |
| injection | 15 | 15 |

## Comparaison des méthodes de recherche

| Configuration | Recall@5 | nDCG@5 | MRR@10 |
|---|---:|---:|---:|
| sans_reranker | 1.0000 | 0.9723 | 0.9625 |
| reranker_regles_initial | 1.0000 | 0.9875 | 0.9833 |
| reranker_local_adapte | 1.0000 | 1.0000 | 1.0000 |
| cross-encoder pretrained | 1.0000 | 1.0000 | 1.0000 |
| cross-encoder adapted | 1.0000 | 1.0000 | 1.0000 |

Les comparaisons légères et neuronales emploient le même découpage documentaire, mais des fonctions de score différentes. Les scores parfaits sur ce jeu facile ne constituent pas une preuve de performance générale. Les résultats restent ceux observés, y compris l'absence de progrès après adaptation.

## Parcours fil rouge

### initial

Optimalité lexicographique démontrée. 0 OF en retard, 0 minutes de retard pondéré. Fin à 13:30. 0 OF déplacés par rapport à la référence.

| OF | Machine | Début | Fin | Réglage min |
|---|---|---|---|---:|
| OF-101 | CNC-A | 08:00 | 09:05 | 0 |
| OF-102 | CNC-A | 09:35 | 10:55 | 30 |
| OF-106 | CNC-A | 10:55 | 12:00 | 0 |
| OF-104 | CNC-A | 12:00 | 13:30 | 0 |
| OF-103 | CNC-B | 08:00 | 08:55 | 0 |
| OF-108 | CNC-B | 09:25 | 10:15 | 30 |
| OF-107 | CNC-B | 10:35 | 12:00 | 20 |
| OF-105 | CNC-B | 12:00 | 13:10 | 0 |
### breakdown

Optimalité lexicographique démontrée. 0 OF en retard, 0 minutes de retard pondéré. Fin à 15:30. 2 OF déplacés par rapport à la référence.

| OF | Machine | Début | Fin | Réglage min |
|---|---|---|---|---:|
| OF-101 | CNC-A | 08:00 | 09:05 | 0 |
| OF-102 | CNC-A | 09:35 | 10:55 | 30 |
| OF-106 | CNC-A | 10:55 | 12:00 | 0 |
| OF-105 | CNC-A | 12:20 | 13:30 | 20 |
| OF-104 | CNC-A | 14:00 | 15:30 | 30 |
| OF-103 | CNC-B | 08:00 | 08:55 | 0 |
| OF-108 | CNC-B | 09:25 | 10:15 | 30 |
| OF-107 | CNC-B | 10:35 | 12:00 | 20 |
### urgent

Optimalité lexicographique démontrée. 2 OF en retard, 60 minutes de retard pondéré. Fin à 16:30. 2 OF déplacés par rapport à la référence. OF-105 : retard de 30 minutes. OF-104 : retard de 30 minutes.

| OF | Machine | Début | Fin | Réglage min |
|---|---|---|---|---:|
| OF-101 | CNC-A | 08:00 | 09:05 | 0 |
| OF-102 | CNC-A | 09:35 | 10:55 | 30 |
| OF-106 | CNC-A | 10:55 | 12:00 | 0 |
| OF-109 | CNC-A | 12:20 | 13:20 | 20 |
| OF-105 | CNC-A | 13:20 | 14:30 | 0 |
| OF-104 | CNC-A | 15:00 | 16:30 | 30 |
| OF-103 | CNC-B | 08:00 | 08:55 | 0 |
| OF-108 | CNC-B | 09:25 | 10:15 | 30 |
| OF-107 | CNC-B | 10:35 | 12:00 | 20 |

## Dossier de preuves

Les JSON conservent les opérations, différences et résultats individuels ; les XML conservent les cas de test exécutés ; les captures montrent l'interface réelle. Les fichiers d'audit décrivent leurs paquets et vulnérabilités connues, pas une garantie absolue de sûreté. Les journaux et jetons locaux ne sont pas redistribués.
