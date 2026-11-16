# Guide utilisateur

## Connexion et rôles

Ouvrir http://localhost:8501 et se connecter. `chef` peut consulter, préparer, approuver et publier ; `planif` consulte et prépare ; `lecture` consulte les documents et analyses ; `chef2` appartient à un autre atelier. Le mot de passe commun de démonstration est `OrdoPlan-demo-2026!`. En exploitation réelle, désactiver `ORDOPLAN_DEMO` sur une base neuve et créer des comptes personnels avec `scripts.manage_users`.

## Calculer le planning

Sélectionner `demo` ou une instance de référence, puis **Calculer le planning initial**. Le résultat présente le statut du solveur, le retard pondéré, la fin, les déplacements et le temps de calcul. Le Gantt affiche les réglages en gris. Le tableau détaillé et les exports CSV/JSON permettent de revoir toutes les opérations.

Un statut `OPTIMAL` signifie que toutes les étapes de l'objectif lexicographique ont été démontrées. `FEASIBLE` signifie meilleure solution trouvée dans le temps imparti. Un horizon infaisable ne produit pas un planning à publier. Les opérations gelées ne sont jamais déplacées pour masquer un conflit.

## Réagir à un aléa

Après un calcul, ouvrir le formulaire de replanification. Les minutes sont comptées depuis 08:00 : 150 signifie 10:30. Pour une panne, indiquer machine, début et durée confirmés. Pour l'urgence de démo, sélectionner OF-109. Pour un retard matière, sélectionner l'OF et la nouvelle disponibilité relative au début de l'aléa.

La référence devient le dernier planning proposé. Le résultat conserve les opérations engagées et compare les autres. Une panne au milieu d'une opération gelée peut rendre le modèle infaisable : préciser la situation réelle et les règles de suspension/reprise avec le chef d'atelier. Le prototype ne change pas cette règle de lui-même.

Pour reproduire exactement la démonstration livrée, utiliser `python -m scripts.demo_end_to_end` après démarrage. Le script choisit une frontière valide dans le planning réellement calculé, car plusieurs plannings optimaux peuvent exister selon la version du solveur. Voir `reports/end_to_end.json` pour les horaires observés.

## Importer des documents

Un CSV/Excel doit comporter `id,reference,quantity,due,release,priority`. Les nombres sont des entiers, les quantités strictement positives, les références présentes au catalogue et les identifiants OF uniques. `due` et `release` sont des minutes depuis 08:00. Les durées et éligibilités proviennent des gammes, pas de colonnes libres non vérifiées.

Le PDF est extrait localement, par couche texte en priorité et OCR sinon. Les champs essentiels doivent être confirmés puis reportés dans un export ERP valide avant calcul. L'import PDF ne devient pas automatiquement une règle d'atelier ni une instruction de l'agent.

Pour une photo, envoyer l'afficheur ou un OF papier. Les observations OCR/VLM restent distinctes des valeurs confirmées. L'état « arrêt » ne prouve pas une durée de panne. Une image illisible déclenche une clarification. Une photo lisible peut aussi demander une validation si le VLM et l'OCR divergent. Aucun pourcentage de confiance n'est inventé.

## Poser une question sourcée

Dans **Assistant documentaire**, préciser la machine et la règle recherchée. Exemple : « Quel est le temps de changement de série ALU vers ACIER ? ». La réponse donne un extrait exact et une référence document/page/élément/version. Le bouton d'ouverture contrôle à nouveau l'accès. Une source inaccessible n'est pas révélée par une URL directe.

Le prototype utilise des réponses extractives pour limiter les affirmations non soutenues. Une question hors corpus conduit à une demande de précision. Les instructions malveillantes dans les questions, notes, photos ou outils ne peuvent pas approuver une publication.

## Approuver et publier

Ouvrir **Validation MES** et vérifier le brouillon exact : machines, débuts, fins, réglages et empreinte. Cocher l'accord explicite puis cliquer **Approuver ce contenu**. L'accord expire après 5 minutes. Cliquer ensuite **Publier dans le MES**. Seul un chef d'atelier autorisé le peut.

Une modification de contenu ou une publication MES intervenue entre-temps impose un nouveau brouillon et une nouvelle validation. Réessayer une publication déjà réussie renvoie la même version MES. **Annuler le brouillon** empêche sa publication ultérieure. Un retour à une version antérieure se prépare depuis l'historique et exige lui aussi une nouvelle approbation.

## Messages courants

| Message | Action attendue |
|---|---|
| API indisponible | Vérifier que les trois services sont démarrés |
| MCP indisponible | Lire le journal MCP et vérifier son adresse interne |
| Durée inconnue | Confirmer une durée humaine, sans la déduire de l'afficheur |
| Source manquante | Fournir une gamme/ERP autorisé pour l'atelier |
| Accès refusé | Utiliser un compte autorisé à cet atelier |
| Révision obsolète | Repréparer et approuver le planning courant |
| Aucun planning réalisable | Examiner gel, matières, ressources et horizon avec le chef |
| Quota atteint | Attendre puis relancer une demande |

## Telegram

Associer d'abord le compte depuis l'interface web. Envoyer `/draft ID` pour lire toutes les opérations et le hash ; `/approve ID HASH` constitue l'accord explicite ; `/publish ID` effectue la publication. Ne jamais transmettre de jeton personnel à un autre utilisateur. Les conversations de groupe sont exclues.
