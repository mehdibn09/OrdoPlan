# Modèle d'optimisation et contrôleur

## Hypothèses

Une opération non préemptive par OF. La quantité multiplie le temps unitaire connu. Une gamme conserve la même durée sur ses machines éligibles. Les dates sont des minutes entières depuis 08:00 dans un horizon borné. Les échéances sont souples et les disponibilités matière sont des bornes dures. Les réglages occupent la machine immédiatement avant la production, sans interruption ; les outils et opérateurs sont réservés pendant la production seulement.

Les familles ALU/ACIER commandent les changements : 30 minutes ALU→ACIER, 20 minutes ACIER→ALU, zéro pour une même famille. Les valeurs sont sourcées dans `regles_reglage.pdf`. Un autre atelier doit fournir sa propre matrice complète ; une transition absente est rejetée.

## Variables

Pour chaque OF i : début s_i, fin e_i, durée p_i = quantité_i × temps_unitaire_i. Pour chaque machine éligible m : x_im binaire de sélection ; réglage g_im ; début du bloc b_im = s_i − g_im ; intervalle optionnel [b_im,e_i[ de taille p_i+g_im. Pour chaque arc consécutif i→j sur m : a_ijm binaire. Un nœud fictif représente le premier et dernier OF.

## Contraintes

1. Somme_m x_im = 1 et e_i = s_i+p_i. Les machines non éligibles n'ont aucune variable d'affectation.
2. `AddCircuit` impose une séquence par machine. Un OF non sélectionné possède une boucle sur lui-même.
3. Un arc i→j impose s_j ≥ e_i + changement(f_i,f_j) et g_jm égal au changement. Le premier OF utilise la famille initiale de la machine.
4. `NoOverlap` sur les blocs de production/réglage et les indisponibilités machine. Le réglage ne traverse donc pas une panne ou une maintenance.
5. `NoOverlap` sur les intervalles de production des OF partageant un outil unique ou un opérateur, et sur leurs absences.
6. s_i ≥ réception_matière_i. Pour une opération future, b_im ≥ instant_courant. Les opérations déjà commencées, y compris un réglage engagé, sont gelées exactement.
7. 0 ≤ b_im ≤ s_i < e_i ≤ horizon. Les OF gelés conservent machine, début, fin et réglage.

## Objectif lexicographique

T = somme_i poids_i × max(0,e_i−échéance_i).

D = somme_i déjà planifiés |s_i−ancien_début_i| + 60 × indicatrice(machine changée).

C = max_i e_i.

Résoudre successivement min T, min D si une référence existe, puis min C. Chaque étape fixe une borne supérieure à la meilleure valeur précédente. Le budget global de résolution est borné à 20 secondes, partagé entre les étapes. Le coefficient 60 est une pénalité de stabilité en minutes équivalentes, pas un temps physique ajouté à la production.

`OPTIMAL` n'est affiché que si toutes les étapes aboutissent avec preuve d'optimalité. Si une étape fournit seulement une solution réalisable ou qu'une étape suivante manque de temps, l'état est `FEASIBLE`. La borne primaire est conservée ; l'absence de solution après un budget court n'est pas qualifiée d'infaisabilité démontrée. `INFEASIBLE` est réservé à la preuve du solveur.

## Contrôleur indépendant

`src/solver/checker.py` n'importe pas OR-Tools. Il vérifie couverture unique des OF, éligibilité, durée, réglage selon la séquence triée, absence de chevauchement, indisponibilités, ressources uniques, disponibilités matière, instant courant, horizon et gel. Il ne modifie aucune solution. Une violation bloque la présentation et la publication.

Les métriques et les écarts sont recalculés en Python depuis les opérations. Les affirmations chiffrées de l'explication viennent uniquement de ces objets. Les tests corrompent volontairement une durée, une machine, un réglage, une ressource et un gel pour vérifier que le contrôleur détecte chaque classe d'erreur.

## Références et impossibilités

FIFO trie par disponibilité et identifiant ; EDD trie par échéance, puis place chaque opération au plus tôt sur une machine réalisable. Elles respectent le même contrôleur. Une référence manuelle fixe une séquence issue de la démo et place ses tâches de manière série ; ce n'est pas une expertise industrielle.

Une panne qui chevauche une opération gelée rend les contraintes incompatibles. Le prototype signale les familles de conflits à examiner (gel, horizon, matières, ressources) et demande un assouplissement humain. Il ne calcule pas de noyau minimal d'insatisfaisabilité et ne propose pas de suspendre automatiquement une opération ; cette limite figure dans la fiche d'utilisation.
