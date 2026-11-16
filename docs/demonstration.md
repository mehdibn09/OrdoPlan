# Démonstration et soutenance

## Préparation

Lancer les services, ouvrir le web, se connecter en chef, puis vérifier `/health`. Les données sont fictives. Prévoir les quatre images de `data/sample_images/`, le CSV et le classeur ERP. La démonstration complète peut s'exécuter avec `python -m scripts.demo_end_to_end`, qui appelle réellement l'API et le transport MCP et enregistre `reports/end_to_end.json` sans jetons.

Les horaires livrés sont ceux de notre instance explicitement définie. Les horaires illustratifs du PDF source reposent sur des temps détaillés non fournis dans l'énoncé ; ils ne sont pas recopiés comme résultats de notre calcul.

## Parcours de 10 à 12 minutes

| Temps | Action | Preuve à montrer |
|---|---|---|
| 0:00–1:00 | Présenter l'atelier et la séparation des rôles | Le modèle lit ; CP-SAT décide ; le contrôleur vérifie |
| 1:00–2:00 | Importer `orders.csv` puis calculer `demo` | Zéro retard, Gantt, statut optimal et références de paramètres |
| 2:00–3:30 | Analyser l'afficheur CNC-B | État observé, durée inconnue, demande de confirmation |
| 3:30–5:00 | Confirmer une panne de 180 min à la frontière calculée | Opérations gelées et déplacements dans le comparatif |
| 5:00–6:30 | Ajouter OF-109 urgent | Deux retards expliqués, chiffres contrôlés par le code |
| 6:30–8:00 | Lire le brouillon, approuver, publier, réessayer | Hash exact, reprise LangGraph, même version MES au second appel |
| 8:00–9:00 | Image illisible et note d'injection | Clarification et aucune publication implicite |
| 9:00–10:00 | Essayer un accès à l'atelier 2 | Refus côté serveur et absence de contenu confidentiel |
| 10:00–12:00 | Présenter l'évaluation et les limites | Rapports réels, pas de gain neuronal démontré, limites du VLM CPU |

## Résultats du parcours livré

Ils se lisent dans `reports/end_to_end.json` : planning initial sans retard, fin 13:30 ; après panne, sans retard, fin 15:30 ; après urgence, deux retards de 30 minutes, 60 minutes pondérées, fin 16:30. La frontière d'arrêt est sélectionnée depuis le planning calculé pour éviter de contredire une opération gelée. Si la version du solveur change les choix parmi des solutions équivalentes, reprendre les valeurs réelles du nouveau rapport.

Pour le cas de panne au milieu d'une opération engagée, montrer volontairement l'infaisabilité et expliquer que la suspension/reprise nécessite une règle métier explicite. Ne pas déplacer silencieusement l'opération.

## Questions du jury

- **Pourquoi un solveur ?** Les contraintes et dates doivent être vérifiables. Le modèle ne possède aucun outil lui permettant de remplacer les opérations calculées.
- **Pourquoi un contrôleur séparé ?** Pour vérifier le résultat par une implémentation ne dépendant pas d'OR-Tools et détecter des erreurs de modélisation ou de sérialisation.
- **Que signifie optimal ?** Preuve sur toutes les étapes lexicographiques et dans le modèle décrit, pas garantie sur l'atelier réel.
- **Quel composant a été adapté ?** Deux dernières couches et tête d'un cross-encoder multilingue, 3 697 153 paramètres entraînables, 600 triplets d'entraînement, une époque sur CPU.
- **Quel gain ?** Aucun gain mesuré sur le benchmark neuronal à titres explicites ; les deux configurations atteignent les mêmes scores. Il faut un jeu réel plus difficile.
- **Comment empêcher une injection ?** Documents traités comme données, schémas structurés, outils fermés et approbation serveur liée au contenu, indépendamment du détecteur.
- **Le bot est-il connecté ?** Le code et les tests d'identité sont livrés. Une conversation réelle nécessite le jeton du propriétaire ; aucune connexion personnelle n'est inventée.
- **Que reste-t-il avant l'usine ?** Validation terrain, multi-opérations si nécessaire, suspensions, annuaire, stockage de production, matériel et benchmark réel.

## Répétition sans réseau

Le profil CPU conserve tous les éléments de démonstration locaux. Le pack de poids permet le profil IA après installation des dépendances ; définir les variables hors ligne. Telegram ne peut pas fonctionner sans son service externe. Conserver les captures et le rapport pour présenter les essais si un téléchargement ou un service est indisponible le jour de la soutenance.
