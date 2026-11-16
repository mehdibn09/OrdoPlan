# Notes de soutenance

## 1. OrdoPlan

- Assistant d'ordonnancement multimodal et agentique
- Planifier. Comprendre. Valider.
- Atelier fictif · version 1.0.0

## 2. Le problème d'atelier

- Des commandes, des ressources limitées et des aléas
- Une panne ou une urgence impose un arbitrage rapide
- Un planning calculé, vérifié et approuvé

## 3. Un périmètre explicite

- 2 CNC · 8 OF · familles ALU / ACIER · outil unique
- Pas de commande d'automate ou de machine
- La publication touche un MES de démonstration

## 4. Séparer les responsabilités

- Le solveur décide des séquences et des dates
- Le modèle lit ; le contrôleur vérifie
- Le chef d'atelier approuve le contenu exact

## 5. Des données reproductibles

- 40 PDF synthétiques · deux familles d'équipements
- 50 instances + fil rouge · exports CSV/Excel et photos
- 1 000 triplets · séparation par document · 150 scénarios

## 6. Le modèle de contraintes

- Éligibilités, réglages et NoOverlap machine
- Outillage et opérateur uniques, matière et indisponibilités
- Opérations engagées gelées ; aucune correction silencieuse

## 7. Trois objectifs, dans cet ordre

- 1. Minimiser le retard pondéré
- 2. Minimiser les déplacements et changements de machine
- 3. Minimiser la date de fin ; optimal seulement si prouvé

## 8. RAG et preuves

- Filtrage atelier/rôle avant recherche et à l'ouverture
- Texte + vecteurs + CLIP → RRF → reranking
- Réponse extractive sourcée ; écarts chiffrés par le code

## 9. Photographie et incertitude

- OCR local + VLM à poids ouverts
- Un arrêt observé ne donne pas une durée de panne
- Lecture incomplète ou désaccord → validation humaine

## 10. Une adaptation réellement exécutée

- Cross-encoder multilingue ; deux couches et tête adaptées
- 600 triplets d'entraînement, 200 validation, 200 test
- Scores avant/après identiques : aucun gain démontré

## 11. Planning initial

- Optimalité lexicographique démontrée. 0 OF en retard, 0 minutes de retard pondéré. Fin à 13:30. 0 OF déplacés par rapport à la référence.
- Toutes les contraintes sont revérifiées indépendamment

## 12. Panne confirmée

- Optimalité lexicographique démontrée. 0 OF en retard, 0 minutes de retard pondéré. Fin à 15:30. 2 OF déplacés par rapport à la référence.
- La frontière d'arrêt vient du planning réellement calculé

## 13. Urgence et arbitrage

- Optimalité lexicographique démontrée. 2 OF en retard, 60 minutes de retard pondéré. Fin à 16:30. 2 OF déplacés par rapport à la référence. OF-105 : retard de 30 minutes. OF-104 : retard de 30 minutes.
- Les retards sont produits par le solveur, pas par le modèle

## 14. MCP et accord humain

- Trois outils : commandes, état machine, publication
- Interruption LangGraph avant l'action sensible
- Hash + utilisateur + atelier + révision ; expiration et idempotence

## 15. Sécurité vérifiée

- Accès inter-ateliers refusé, y compris pour les PDF/images
- Notes et OCR hostiles sans effet sur les contraintes
- Jeton absent, modifié ou expiré : publication bloquée

## 16. Résultats observés

- 150/150 scénarios de composants réussis
- 30 plannings valides, 0 contrainte violée ; CP-SAT ≤ FIFO/EDD
- 25 replanifications ; p95 solveur 0.127 s sur ces cas

## 17. Limites à présenter

- Données synthétiques et requêtes de recherche faciles
- Petit VLM CPU insuffisant ; pas de benchmark GPU ni d'entretien terrain
- Mono-opération, pas de suspension/reprise ; Telegram réel à configurer

## 18. Livraison et suite

- Code, données, tests, Docker, guides et modèles locaux
- Rapports calculés et support de démonstration
- Avant usage réel : qualifier les règles et les sources avec l'atelier