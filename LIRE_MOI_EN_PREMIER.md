# OrdoPlan — démarrer ici

Le projet livré est un prototype pédagogique fonctionnel sur atelier fictif. Il respecte la séparation entre lecture documentaire, calcul par solveur, contrôle indépendant et approbation humaine.

## Choisir les fichiers

- **OrdoPlan_Complet.zip** : dépôt source, 40 PDF et pages visuelles, 50 instances plus la démo, CSV/Excel, 1 000 triplets, 150 scénarios, index léger, modèles légers adaptés, tests, prompts, Docker, guides, rapport et soutenance.
- **OrdoPlan_Documents.zip** : rapport de 26 pages en PDF et DOCX, 18 diapositives en PPTX et PDF, documentation et notes de démonstration.
- **OrdoPlan_Modeles_Locaux.zip** : environ 2,17 Go de poids pour le profil IA locale, à extraire à la racine du dossier OrdoPlan. Le profil de démonstration CPU fonctionne sans ce pack.
- **OrdoPlan_Historique_Git.bundle** : instantané versionné du code et des données, sans poids lourds ni secrets. Le ZIP suffit pour commencer.
- **SHA256SUMS.txt** : empreintes des archives et des documents pour vérifier les téléchargements.

## Lancer le prototype

1. Décompresser OrdoPlan_Complet.zip et ouvrir un terminal dans le dossier OrdoPlan.
2. Installer et démarrer Docker Desktop avec Compose.
3. Exécuter :

```bash
docker compose -f docker-compose.compact.yml up --build -d
```

4. Ouvrir http://localhost:8501.
5. Se connecter avec **chef** et le mot de passe public de démonstration **OrdoPlan-demo-2026!**.

Le premier build télécharge les dépendances. Prévoir 10 Go de disque libre et 4 Go de mémoire disponibles ; davantage pour le profil neuronal. L'API documentée est accessible sur http://localhost:8000/docs. L'alternative Python 3.12 et les scripts Windows/Linux sont décrits dans docs/installation.md.

## Vérifications observées

68 tests unitaires/API réussis, 150 scénarios de composants réussis, aucun planning proposé en violation des contraintes sur les instances testées. Le parcours HTTP + véritable MCP, l'approbation et le réessai idempotent passent également dans le conteneur de construction. Les configurations Compose sont validées ; la topologie à quatre conteneurs n'a pas été démarrée simultanément dans cet environnement à disque VFS limité.

Le reranker multilingue a réellement été adapté. Le jeu synthétique à titres explicites est facile : aucun gain neuronal avant/après n'y est démontré. Le petit VLM produit des lectures incomplètes ; le système demande une validation et ne transforme pas une observation incertaine en planning.

## Ce qui exige une configuration personnelle ou une validation terrain

Le bot Telegram nécessite votre jeton et une association de compte ; aucune session Telegram réelle n'a été effectuée. Les temps d'atelier, l'entretien métier, les annotations expertes, le matériel GPU et un vrai ERP/MES restent à qualifier avant usage industriel. Les limites et leur incidence figurent dans le rapport et docs/fiche_de_limites.md. Aucun planning n'est publié sans accord du chef d'atelier et aucune machine n'est pilotée.

Commencer la soutenance par docs/demonstration.md. Les mesures détaillées et preuves sont dans reports/. Les PDF du sujet et le ZIP du camarade ne sont pas redistribués.
