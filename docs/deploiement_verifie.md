# Déploiement vérifié et reproductibilité

## Résultats exécutés

L'image de démonstration a été construite avec Python 3.12.14 et les dépendances du socle figées. Le build vérifié utilise `RUN_SMOKE_TEST=1` : il exécute les 68 tests unitaires/API, puis démarre réellement FastAPI, MCP et Streamlit sous l'utilisateur non administrateur `ordoplan`. Le scénario HTTP/MCP s'exécute ensuite jusqu'à l'approbation, la publication et son réessai idempotent. Le contrôle de santé de l'interface répond correctement.

Les résultats extraits du conteneur sont conservés dans `reports/unit-tests.xml`, `reports/end_to_end.json` et `reports/deployment.json`. Les preuves natives antérieures sont conservées séparément avec le préfixe `native-`. Les captures du navigateur sont issues de l'application native avec la même interface ; elles vérifient aussi l'affichage du Gantt et des références.

Commande de vérification reproductible :

```bash
docker build --build-arg RUN_SMOKE_TEST=1 -t ordoplan:1.0.0 .
```

Pour le fonctionnement courant, le build par défaut n'installe pas les outils de tests supplémentaires. Il crée les identités de démonstration au premier démarrage. Les états de tests du build vérifié sont créés dans un dossier temporaire puis supprimés ; aucun jeton utilisateur ni clé de test n'est nécessaire à la livraison.

## Variante recommandée pour démarrer

```bash
docker compose -f docker-compose.compact.yml up --build -d
# Interface : http://localhost:8501 ; API : http://localhost:8000/docs
```

Le profil compact regroupe les trois processus avec Qdrant local. Le volume conserve brouillons, approbations, versions MES et index. Les ports sont liés à l'interface locale.

## Portée des essais

Le fichier `docker-compose.yml` à services séparés et le fichier compact ont été validés par `docker compose config`. La topologie complète à quatre conteneurs n'a pas été lancée simultanément dans cet environnement de 8 Go de disque utilisant le pilote VFS : les copies de couches y dépassent l'espace disponible. Le fonctionnement des trois services a été vérifié dans le conteneur de build, et non déduit de la seule compilation de l'image.

Le profil neuronal a été essayé nativement avec les poids locaux ; la surcharge Compose neuronale est fournie, mais n'a pas été exécutée en conteneur. Les profils MLflow serveur et Telegram réel nécessitent leur configuration propre. Aucune mesure GPU ni intégration à un MES industriel n'est revendiquée.

La version légère de PyMuPDF retenue pour la distribution est 1.26.7, corrigée et sans moteur optionnel de layout ; les 68 tests en conteneur utilisent ce socle. Les essais natifs initiaux utilisaient PyMuPDF 2.1, dont les moteurs supplémentaires étaient inutiles au prototype. L'audit du verrou de distribution ne signale pas de vulnérabilité connue au moment du contrôle.

## Réseau d'installation

L'environnement de construction des essais utilise un certificat de confiance de session monté comme secret BuildKit pour installer les paquets en conservant la vérification TLS. Ce certificat n'est pas incorporé aux couches et aucun réglage propre à cette session n'est imposé au Dockerfile livré. Sur une installation standard, le Dockerfile normal utilise la chaîne de confiance du système.

Les téléchargements de paquets et modèles sont des opérations de provisionnement. Après installation, l'inférence utilise les chemins locaux, et non une API de modèle tierce. Telegram reste un service réseau optionnel explicitement configuré.
