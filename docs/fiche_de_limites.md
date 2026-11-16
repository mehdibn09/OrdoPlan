# Fiche de limites et conditions d'utilisation

Version 1.0.0 — prototype pédagogique, données entièrement fictives.

## Usages autorisés

Étudier l'ordonnancement d'un petit atelier, comparer des règles, démontrer un RAG sourcé, analyser une photo à confirmer, expérimenter un reranker et vérifier un workflow d'approbation. La publication touche uniquement le MES de démonstration. Aucun outil de pilotage ou de sécurité machine n'est exposé.

## Hypothèses et couverture

Deux CNC dans le fil rouge, jusqu'à 30 OF et 8 machines dans les schémas ; les performances au maximum de ces bornes ne sont pas garanties. Les centres CNC et tours CN figurent dans le corpus. Les familles de matière sont ALU/ACIER. Chaque OF comporte une seule opération, sans préemption, avec durée déterministe, une gamme connue et des temps identiques sur ses machines éligibles. Le réglage occupe la machine ; opérateurs et outillages sont réservés pendant la production seulement.

Les opérations commencées, y compris le réglage, restent gelées. Une panne qui les traverse est déclarée incompatible. Le modèle ne simule ni suspension, ni pièce perdue, ni rebut, ni réparation, ni sous-traitance, ni fabrication multi-opérations avec précédences. Les indisponibilités, compétences et arrivées matière doivent être saisies avant calcul.

## Lecture, recherche et explication

Le petit VLM CPU a montré des lectures incomplètes. Une lecture OCR seule exige toujours validation ; la comparaison OCR/VLM n'est pas une preuve de vérité. Les pages synthétiques et la typographie contrôlée sont plus faciles que des photographies industrielles. L'exactitude des champs après correction humaine n'a pas été mesurée auprès de praticiens.

Le profil léger cherche des mots, des caractères et des descriptions de pages, et ne revendique pas une recherche CLIP réelle. Le profil IA locale intègre un encodeur multilingue, un vrai CLIP apparié et un cross-encoder adapté ; il a été essayé localement, avec des limites de taille et de temps. Le modèle Qwen2.5-VL-7B/GPU de 24 Go n'a pas été provisionné ni évalué.

Les réponses documentaires sont des extraits sourcés ; leur mise en contexte reste à apprécier. Les explications numériques sont calculées, puis mises en texte par un gabarit versionné. Elles ne constituent pas une analyse causale exhaustive des arbitrages ni une justification économique par expert. Le contrôleur d'infaisabilité n'identifie pas un noyau minimal de contraintes en conflit.

## Évaluation et adaptation

Les 1 000 triplets sont synthétiques, vérifiés automatiquement et séparés par document. Ils ne sont pas relus par un expert industriel. Les requêtes citent des titres, ce qui rend le benchmark facile. Les résultats du fine-tuning doivent être lus tels quels : aucune amélioration n'est démontrée lorsque les scores avant/après sont identiques. Les données et scripts permettent de reproduire l'expérience et d'ajouter ensuite de vraies paraphrases difficiles.

Le jeu de 150 scénarios teste les composants ; il ne représente pas 150 essais de VLM sur photos réelles ni 150 conversations Telegram. Les latences de composants, du parcours API/MCP et du chargement neuronal sont consignées séparément. La relecture de clarté par un praticien et l'entretien terrain n'ont pas eu lieu. Les mesures CPU/GPU complètes en production restent à établir.

## Déploiement et confidentialité

SQLite chiffré, Qdrant et comptes locaux suffisent à une démonstration sur une machine. La haute disponibilité, l'annuaire d'entreprise, la gestion de clés externe, le chiffrement de disques/volumes et l'intégration à un vrai ERP/MES ne sont pas implémentés. Les comptes et le mot de passe public de démo doivent être désactivés sur une base neuve avant toute autre utilisation.

L'audit de dépendances est un instantané, pas une garantie permanente. La CI doit continuer de l'exécuter. Les poids de modèles suivent leurs licences propres ; PyMuPDF implique des obligations AGPL/commerciales selon l'usage. Les sources synthétiques sont autorisées par construction et ne contiennent pas de données personnelles réelles.

Le bot nécessite des secrets personnels non fournis. Sa logique et l'association des identités peuvent être testées sans messages externes ; une mise en service réelle nécessite votre compte et une vérification de bout en bout sur Telegram. Il ne doit pas être présenté comme déjà connecté à votre compte.

## Conditions avant usage réel

Faire valider gammes, changements de série, calendriers, contraintes de compétences, matières, sûreté et priorités par l'atelier ; enrichir l'évaluation avec des cas réels autorisés ; mesurer le matériel retenu ; configurer identité, sauvegarde, rétention et contrôle réseau ; intégrer un MES de test ; conserver l'approbation humaine. OrdoPlan reste une aide à la décision et ne garantit pas la tenue du planning.
