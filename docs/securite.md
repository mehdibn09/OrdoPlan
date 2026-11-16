# Sécurité et confidentialité

## Frontières de confiance

Les utilisateurs, PDF, images, notes libres, textes OCR et réponses d'outils sont des entrées non fiables. Les rôles et ateliers proviennent de sessions serveur. L'utilisateur ne peut pas envoyer un graphe arbitraire, un modèle CP-SAT arbitraire ou des opérations directement à l'endpoint de publication. Les paramètres d'aléa sont structurés et bornés ; les règles de calcul sont du code local.

Le détecteur d'injection est un signal complémentaire. La sécurité ne dépend pas de la réussite d'une détection par mots-clés : une note hostile n'est jamais transformée en contrainte, appel d'outil ou jeton d'approbation. La publication exige indépendamment un accord enregistré côté stockage, le bon utilisateur, le bon atelier, un rôle chef et un contenu inchangé.

## Identités et documents

Mots de passe scrypt avec sel aléatoire ; sessions aléatoires, stockées sous forme de hash, limitées dans le temps et révocables. API et MCP authentifient chaque appel. Les documents sont filtrés avant recherche par atelier et groupe et de nouveau lors de l'ouverture d'un PDF ou d'une image. Les refus ne donnent pas le contenu d'un autre atelier.

Le MCP utilise le SDK v2, Streamable HTTP et une liste de trois outils. Sa protection contre le rebinding DNS autorise seulement les hôtes locaux et le nom interne `mcp`. Le serveur vérifie les droits à chaque fonction et refuse une machine inconnue. Aucun outil de réseau arbitraire, shell, email ou pilotage n'est exposé à l'agent.

## Accord, atomicité et retour arrière

Le brouillon contient l'instance et le planning exacts, un hash SHA-256 canonique et la révision courante du MES. L'accord est lié au hash, au brouillon et à l'utilisateur et expire après cinq minutes. La publication vérifie ces liens dans une transaction SQLite immédiate, recontrôle les contraintes, consomme le jeton et garde la version précédente. Un identifiant unique de brouillon assure l'idempotence, y compris lors de requêtes concurrentes.

Une révision MES différente bloque une publication obsolète. Une annulation invalide le brouillon. Un retour arrière crée un nouveau brouillon et ne réutilise pas un ancien accord. Les jetons ne sont pas conservés dans les états LangGraph, rapports ou captures.

## Données au repos, traces et limites

Les charges de brouillons/imports/publications sont chiffrées Fernet ; les checkpoints utilisent AES. La clé locale est créée en mode 0600, à sauvegarder avec les bases et à exclure de Git. Il ne s'agit pas d'un KMS ni du chiffrement de l'ensemble du disque. Les documents synthétiques et index ne contiennent aucun opérateur réel. Les journaux d'audit conservent des événements techniques, pas les contenus bruts ; les journaux HTTP d'accès sont désactivés.

Limites du code : 3 appels MCP, 6 appels de modèle, 60 s de traitement automatique, 20 s de solveur, 8 Mo par import, 16 mégapixels, 20 pages PDF, 96 tokens de lecture VLM, un processus VLM borné, 2 demandes d'assistant simultanées et une lecture photo simultanée. Les quotas sont appliqués par utilisateur et aux connexions. Les comptes et l'authentification de prototype ne remplacent pas une passerelle d'entreprise.

Les modèles sont provisionnés explicitement puis chargés localement, sans code distant. Le fonctionnement de modèle n'envoie pas de données à une API tierce. Le réseau système du prototype n'est pas un pare-feu industriel ; l'exploitant doit appliquer une politique de sortie réseau et isoler Telegram si nécessaire.

## Vérifications

Les tests couvrent accès inter-ateliers, ouverture d'images, hash modifié, identité différente, rôle insuffisant, accord expiré, annulation, doublon concurrent, révision obsolète, notes OCR hostiles et brouillons chiffrés. `scripts.scan_secrets` cherche des motifs de secrets sans afficher de valeur ; `.env` et `.runtime` sont exclus de la livraison. `pip-audit` produit les instantanés des dépendances et la CI le répète.

Les tests limités ne prouvent pas une sécurité générale. La configuration Telegram réelle, les administrateurs de bases, la distribution des clés et les permissions de l'hôte relèvent d'une qualification supplémentaire avant utilisation hors démonstration.
