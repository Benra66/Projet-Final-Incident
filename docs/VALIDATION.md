# Vérifications — 22 novembre 2026

## Vérifié localement

- `python manage.py makemigrations --check --dry-run --settings=config.settings.test` : aucune migration manquante.
- `python manage.py check --settings=config.settings.test` : aucun problème Django.
- `python manage.py test --settings=config.settings.test` : 41 tests passés, 5 tests de laboratoire SQL ignorés volontairement.
- `python -m compileall -q config incidents` : syntaxe Python compilée sans erreur.
- Bandit 1.9.4 (`bandit -q -r config incidents -x incidents/tests -ll`) : aucun résultat de sévérité moyenne/élevée.
- Les configurations YAML de GitHub Actions et de ZAP se parsènt correctement.
- L'application utilise SQLite isolé pour ces vérifications. Aucun test n'a visé Neon.

Relancer les deux premières commandes et la suite de tests après chaque modification. Le dépôt demande Python 3.12, tandis que l'environnement local de cette session est Python 3.10.11. `pip-audit` local ne peut pas résoudre `asgiref==3.13.0` sous Python 3.10; il faut son résultat dans le job CI Python 3.12 avant la mise en production.

## À vérifier dans le pipeline distant

- Tests SQLite et PostgreSQL sur Python 3.12.
- Bandit, pip-audit et Gitleaks sur tout l'historique.
- ZAP authentifié contre l'application locale éphémère et récupération du rapport.
- Protection de branche/environnement et déclenchement Vercel seulement après succès.

Ces jobs sont décrits dans `.github/workflows/pipeline.yml`, mais aucun résultat GitHub Actions ne peut être déclaré avant le push et l'exécution par GitHub. Gitleaks devrait détecter l'historique de configuration sensible connu jusqu'à sa révocation et son assainissement.

## Vérification production requise

La capture Vercel partagée précédemment montrait la version `38b0b32` à l'état `Ready`; elle ne démontre pas l'état actuel. Cette branche de travail n'a pas été déployée. La migration `0003` n'a pas été appliquée à Neon et les comptes du cours n'ont pas été provisionnés dans la base distante. Après mise à jour des secrets et déploiement, vérifier les scénarios de `docs/DEPLOYMENT.md` sans divulguer de valeurs de configuration.

La suite existante conserve cinq cas dans le profil de laboratoire SQL volontairement vulnérable; ils doivent rester isolés de toute base ou URL de production.
