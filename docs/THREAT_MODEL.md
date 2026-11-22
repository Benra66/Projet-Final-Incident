# Modèle de menace — Incident Desk

## Périmètre et hypothèses

Le navigateur échange avec Django, qui lit et écrit les incidents et les comptes dans PostgreSQL. GitHub Actions vérifie le code et déclenche, sur demande après succès des contrôles, un déploiement Vercel. Les paramètres de production sont fournis par l'environnement privé Vercel. Le site utilise des données de cours fictives. Les administrateurs Django et les opérateurs de la base sont des comptes de confiance.

Les permissions sont vérifiées côté serveur. Le rôle « administrateur Incident Desk » est un membre du personnel non superutilisateur; ses capacités applicatives ne lui donnent pas automatiquement tous les pouvoirs Django. Les reporters voient leurs incidents, les analystes leurs propres incidents et ceux qui leur sont affectés, et les administrateurs applicatifs tous les incidents.

## Menaces prioritaires

| ID | Scénario et actif | Risque | Contrôle et preuve disponible | État / risque restant |
|---|---|---|---|---|
| T1 — divulgation d'incident | Un reporter lit un incident d'un autre compte en modifiant son URL. | Élevé | Queryset filtré selon le rôle; test de refus sur la vue détail et filtre de liste. | Contrôle local testé; vérifier également les comptes et données après migration en production. |
| T2 — action avec privilèges excessifs | Un reporter supprime ou modifie un incident; un utilisateur choisit le déclarant ou attribue à un compte arbitraire. | Élevé | Permissions Django, propriétaire fixé côté serveur, formulaire d'affectation limité aux analystes actifs, transitions d'état autorisées, test de suppression et d'affectation. | Vérifié localement; configurer groupes sur les comptes de production. |
| T3 — vol/abus de compte | Essais répétés de mots de passe ou session réutilisée après connexion/déconnexion. | Élevé | Django Axes limite les échecs; les sessions tournent à la connexion et sont invalidées à la déconnexion; cookies sécurisés en production. | Tests locaux passants; surveiller les verrouillages et vérifier les attributs de cookie en ligne. |
| T4 — contenu actif ou falsification de requête | Un incident/commentaire contient du HTML actif, ou une requête cross-site modifie les données. | Élevé | Échappement Django, texte brut, CSRF actif, mutations en POST, tests XSS/CSRF. | Vérifié localement; le scan DAST isolé n'a pas encore été exécuté sur GitHub Actions. |
| T5 — compromission des identifiants | Une URL de base ou clé de signature divulguée donne accès à Neon ou permet de forger des sessions. | Critique | Les valeurs ont été retirées du fichier courant et les nouveaux paramètres sont documentés comme secrets Vercel. | **Ouvert** : des valeurs ont figuré dans l'historique Git. Révoquer/renouveler la clé Django et le mot de passe Neon, modifier les variables Vercel, puis assainir l'historique avec l'accord des collaborateurs avant de déclarer la correction terminée. |
| T6 — code vulnérable publié | Dépendance, secret ou faille détectable passe dans une mise en production. | Élevé | Pipeline configuré pour tests SQLite/PostgreSQL, Bandit, pip-audit, Gitleaks, ZAP authentifié local et publication manuelle après succès. | Configurer les protections de branche/environnement et le deploy hook GitHub/Vercel; le secret scan échouera tant que l'historique exposé n'est pas assaini. Aucun résultat CI distant n'est encore disponible. |
| T7 — fuite via configuration ou hôte | Un hôte usurpé, une connexion DB non TLS ou une mauvaise séparation preview/production expose les données. | Élevé | Hôtes/origines explicites, paramètres de production fail-closed, PostgreSQL TLS requis, paramètres Vercel privés. | Valider les valeurs de production et isoler Preview; aucun test live n'a été effectué depuis ce dépôt. |

## Réponse et exploitation

1. Révoquer d'abord les secrets divulgués et vérifier les variables Vercel.
2. Appliquer les migrations avec la révision vérifiée et la base Neon explicitement sélectionnée; ne jamais lancer la suite de tests contre cette base.
3. Provisionner les comptes de cours depuis un shell privé, puis vérifier leur rôle et les accès négatifs avec deux comptes de test.
4. Pour livrer, exiger les contrôles CI, vérifier l'identifiant du commit Vercel et réaliser les essais de fumée de `DEPLOYMENT.md`.
5. En cas de problème, revenir au code précédent après examen de la compatibilité du schéma; un rollback applicatif ne défait pas les migrations.

## Risques résiduels acceptés pour le cours

- Pas de MFA, de portail de récupération de compte, ni de journal centralisé/alertes opérationnelles.
- Le journal d'audit applicatif ne remplace pas une piste inviolable administrée séparément.
- Les mesures anti-brute-force et les contrôles automatiques doivent être confirmés sur la plateforme réelle.
- Les avertissements HSTS `includeSubDomains` et `preload` sont conservés volontairement pendant le déploiement initial.
- Le scanner DAST n'est pas un certificat d'absence de vulnérabilités; son rapport et les faux positifs doivent être triés après chaque exécution.
