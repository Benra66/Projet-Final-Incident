# Jalons du projet et état d'avancement

| Étape | Livrable | État actuel |
|---|---|---|
| 1. Vérification locale | Connexion, création de compte et incident, migrations et tests | Application vérifiée avec la configuration de test SQLite; 41 tests passent localement après le dernier ajout (5 tests du laboratoire SQL sont ignorés hors du profil isolé). Connexion à PostgreSQL de production non vérifiée dans cette session. |
| 2. Versionnement | Code fonctionnel dans GitHub | Dépôt Git connecté et commit de départ identifié. Changements présents dans l'arbre de travail, pas encore poussés. Historique Git contient des valeurs sensibles à faire tourner avant de publier la nouvelle version. |
| 3. Déploiement cloud | Vercel + PostgreSQL Neon, schéma appliqué | Vercel déployait historiquement `38b0b32`; la capture fournie indiquait `Ready`. Aucun état actuel ni accès à Vercel/Neon vérifié ici. La migration `0003` n'est pas appliquée à Neon. |
| 4. Compte reporter | `Nazairefabsimple` | Commande de provisionnement écrite; aucun compte de production créé depuis ce dépôt. |
| 5. Compte administrateur | `Nazairefabadmin`, personnel mais non superutilisateur | Commande écrite et droits minimaux définis; aucun compte de production créé depuis ce dépôt. |
| Sécurité | Contrôles statiques et dynamiques, revue des rôles | Contrôle d'accès, journal d'audit, commentaire texte, protections CSRF/XSS et limitation des tentatives implémentés et testés localement. Analyse Bandit, audit des dépendances et DAST prévus dans CI, sans rapport distant encore obtenu. |
| Final — CI/CD | Pipeline et livraison contrôlée | Workflow préparé; il requiert les secrets et protections GitHub/Vercel ainsi que l'assainissement de l'historique avant de pouvoir réussir de bout en bout. |
| Final — page CV | CV interactif comme accueil | Page responsive française avec navigation, sections repliables et impression PDF ajoutée. |
| Final — rôles | Reporter/analyste/admin; moindre privilège | Groupes, permissions, restrictions par objet et suppression réservée à l'admin implémentés; tests d'accès négatif inclus. |

## Actions restantes hors du dépôt

1. Renouveler les identifiants qui figuraient dans l'historique Git et les configurer dans les paramètres privés Vercel.
2. Assainir l'historique partagé après coordination, puis pousser la branche et obtenir un résultat CI distant vert.
3. Configurer l'environnement GitHub `production`, le Deploy Hook et la désactivation des déploiements directs qui contourneraient la CI.
4. Après déploiement du commit de la migration, appliquer `migrate` à la base Neon choisie et provisionner les comptes avec des secrets transmis par environnement privé.
5. Vérifier la production avec deux rôles et consigner le commit servi, le rapport DAST et les résultats de fumée.
