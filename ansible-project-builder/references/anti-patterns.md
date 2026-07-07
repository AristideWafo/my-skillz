# Référence : Les 50 Anti-patterns Ansible en Entreprise

## Criticité : 🔴 Critique (à corriger immédiatement) | 🟠 Important | 🟡 Recommandé

---

## Structure (1-15)

**1. 🔴 `group_vars/` à la racine du projet**
Les group_vars sont partagées entre tous les environnements. Une variable modifiée pour dev impacte prod.
→ Correction : déplacer dans `inventories/<env>/group_vars/`

**2. 🔴 Variables sans préfixe de rôle**
Collision garantie dès 5+ rôles. `port: 8080` dans deux rôles = comportement indéterminé.
→ Correction : `nginx_listen_port: 80`, `postgresql_port: 5432`

**3. 🔴 Secrets en clair dans le repo**
Rotation immédiate des secrets, activation vault ou secret manager.
→ Vérification : `git log -p | grep -iE '(password|secret|token|key)' | grep '^\+'`

**4. 🔴 `vars/main.yml` pour des variables configurables**
Variables impossibles à surcharger depuis l'inventaire (priorité 14 > 3-9).
→ Correction : déplacer dans `defaults/main.yml`

**5. 🔴 Un seul inventaire pour tous les environnements**
Risque de déployer sur prod en ciblant le mauvais groupe.
→ Correction : `inventories/production/`, `inventories/staging/`, `inventories/development/`

**6. 🟠 Rôle monolithique (fait tout)**
Impossible à réutiliser partiellement. Violation du principe de responsabilité unique.
→ Règle : si le rôle ne peut pas être décrit en une phrase sans "et", le découper.

**7. 🟠 Logique dans `site.yml`**
`site.yml` doit contenir uniquement des `import_playbook`. La logique est dans les rôles.

**8. 🟠 Requirements.yml sans versions figées**
`ansible-galaxy install` sans version = build non reproductible.
→ `version: ">=8.0.0"` minimum, `version: "8.2.1"` idéal en production.

**9. 🟠 Noms de handlers génériques**
`restart nginx` dans deux rôles différents → collision. Le premier handler défini "gagne".
→ Correction : utiliser `listen: "nginx config changed"` avec noms qualifiés.

**10. 🟠 Pas de tags sur les tâches**
Impossible de rejouer une partie du playbook sans tout exécuter.
→ Tags sur toutes les tâches : `tags: [nginx, nginx-configure]`

**11. 🟠 `ansible-pull -C main` en production**
`main` est une branche mutable. Un commit cassé en prod = toutes les machines cassées au prochain run.
→ Correction : cibler un tag git versionné et immuable.

**12. 🟡 Tout dans `tasks/main.yml`**
Fichier de 500+ lignes illisible. Découper en `install.yml`, `configure.yml`, `service.yml`.

**13. 🟡 Pas de `meta/main.yml`**
Dépendances implicites non documentées. Un nouveau contributeur ne sait pas dans quel ordre jouer les rôles.

**14. 🟡 Fichiers statiques sans commentaire dans `files/`**
"Pourquoi ce fichier existe-t-il ?" sans réponse = bombe à retardement.

**15. 🟡 Pas de `README.md` dans les rôles**
Variables non documentées = le rôle ne peut pas être utilisé sans lire le code.

---

## Idempotence (16-25)

**16. 🔴 `command`/`shell` sans `changed_when`**
Toujours marqué `changed` même si rien n'a changé. Déclenche les handlers inutilement.
→ Correction : `changed_when: false` ou condition sur l'output.

**17. 🟠 Timestamp dans les templates**
`# Generated at {{ ansible_date_time.iso8601 }}` → fichier toujours régénéré.
→ Supprimer les timestamps des templates. Utiliser `# Managed by Ansible — do not edit`.

**18. 🟠 Génération de secrets dans les tâches (sans persistance)**
`command: openssl rand -hex 32` → nouveau secret à chaque run = sessions invalides.
→ Générer une fois, persister dans un fichier ou un secret manager.

**19. 🟠 `git` sans version fixée**
```yaml
git:
  version: main   # ← toujours changed si main a bougé
```
→ Utiliser un tag ou SHA.

**20. 🟠 `service: state: started` au lieu d'un handler**
Ne recharge pas la config si elle a changé. Le service tourne mais avec l'ancienne config.
→ Utiliser `started + enabled` dans les tasks, `reloaded` dans les handlers.

**21. 🟠 `lineinfile` pour des fichiers de config complexes**
Brittle, ordre non garanti, diff difficile à lire.
→ Utiliser `template` pour les configs applicatives.

**22. 🟠 `ignore_errors: true` sans commentaire**
Masque les vraies erreurs. Le playbook "réussit" mais le système est dans un état inconnu.
→ Toujours justifier avec un commentaire. Préférer `failed_when` conditionnel.

**23. 🟡 Pas de vérification post-déploiement**
Déployer sans valider que le service répond correctement après.
→ Ajouter `uri` ou `wait_for` avec `assert` après chaque déploiement.

**24. 🟡 `until`/`retries` avec délai trop court**
`delay: 1` sur une centaine d'hôtes = DDoS sur ton propre service.
→ `delay` d'au moins 5-10 secondes selon le service.

**25. 🟡 Notify sur des tâches qui ne changent jamais**
Handler déclaré mais jamais déclenché = code mort trompeur.

---

## Variables (26-33)

**26. 🔴 `--extra-vars` avec secrets en CLI**
Visible dans `ps aux`, dans l'historique bash, et dans les logs CI.
→ Lire depuis un secret manager ou un vault file.

**27. 🟠 Variables définie dans plusieurs niveaux sans documentation**
Savoir laquelle s'applique nécessite de connaître l'ordre de priorité par cœur.
→ Documenter la variable source canonique dans le README du rôle.

**28. 🟠 Variables booléennes avec double négation**
`nginx_no_ssl: false` → logique inversée, bug garanti.
→ `nginx_ssl_enabled: true`

**29. 🟠 `set_fact` excessif**
Transformer toutes les variables en facts → ordre d'exécution imprévisible.
→ Utiliser `set_fact` uniquement pour les valeurs calculées dynamiquement.

**30. 🟡 Variables métier dans `group_vars/all`**
Une variable nginx dans `all` → visible et potentiellement conflictuelle sur les serveurs postgresql.
→ Scope au groupe approprié.

**31. 🟡 Pas de validation des variables en entrée de rôle**
Valeurs invalides → erreurs cryptiques à mi-exécution.
→ `assert` avec `tags: always` au début de chaque rôle.

**32. 🟡 Variables dans le playbook au lieu de l'inventaire**
```yaml
- hosts: all
  vars:
    db_host: "prod-db-01.internal"  # ← appartient à l'inventaire
```

**33. 🟡 Pas de valeur par défaut sensée dans `defaults/`**
Un rôle sans defaults force l'opérateur à définir toutes les variables.

---

## Secrets (34-38)

**34. 🔴 Un seul vault password pour tous les environnements**
Compromission staging = compromission prod.
→ Vault ID différent par environnement.

**35. 🔴 Vault passwords dans le repo (même chiffrés)**
Les vault passwords ne doivent jamais être dans le repo.
→ Distribuer via SSM, HashiCorp Vault, ou 1Password Secrets.

**36. 🔴 `no_log: false` sur des tâches avec secrets**
Les secrets apparaissent en clair dans les logs et ARA.
→ `no_log: true` sur toute tâche manipulant un secret.

**37. 🟠 Pas de rotation des vault passwords**
Un employé qui part conserve l'accès aux secrets Ansible.
→ Rotation annuelle minimum, immédiate lors d'un départ.

**38. 🟠 Clés SSH d'ingénieur utilisées comme clés Ansible**
La clé personnelle d'un ingénieur ne doit pas avoir accès à tous les serveurs.
→ Clé SSH dédiée au runner Ansible, rotée indépendamment des clés personnelles.

---

## Performance (39-43)

**39. 🟠 `forks = 5` (défaut) sur 50+ hôtes**
40x plus lent que nécessaire.
→ `forks = 50` minimum pour les infras de taille moyenne.

**40. 🟠 Pas de `pipelining = true`**
3 connexions SSH par tâche au lieu d'une.
→ `pipelining = true` dans `[ssh_connection]`.

**41. 🟠 Pas de cache de facts**
Reconnexion à chaque hôte pour recollecte les facts à chaque run.
→ `fact_caching = redis` avec TTL adapté.

**42. 🟡 `gather_facts = true` partout par défaut**
Sur 500 serveurs → 500 connexions SSH juste pour des facts inutilisés.
→ `gather_facts = false` par défaut, activer explicitement avec `gather_subset`.

**43. 🟡 Pas de `serial` sur les déploiements applicatifs**
Déployer sur tous les serveurs simultanément = downtime complet si un bug est introduit.
→ `serial: [1, 10%, 50%, 100%]` avec `max_fail_percentage: 5`.

---

## CI/CD & Opérations (44-50)

**44. 🟠 Pas de dry-run (`--check --diff`) avant apply en prod**
→ Toujours exécuter `--check --diff` et valider le diff avant apply.

**45. 🟠 ansible-lint absent du pipeline**
→ `ansible-lint --profile production` dans la CI, bloquant.

**46. 🟠 Molecule absent ou non maintenu**
→ Molecule skeleton pour chaque rôle, exécuté dans la CI sur push.

**47. 🟠 Déploiement automatique en prod sur merge main**
→ Approbation manuelle requise pour la production (GitHub Environments).

**48. 🟡 Logs ansible non centralisés**
Chaque run local → logs perdus → audit impossible.
→ ARA ou équivalent pour centraliser tous les run logs.

**49. 🟡 Pas de notification sur les échecs de déploiement**
Un playbook qui échoue à 3h du matin et personne n'est notifié.
→ Callback Slack/PagerDuty sur `v2_playbook_on_stats` avec erreurs.

**50. 🟡 Pas de plan de rollback documenté et testé**
"Comment on revient en arrière ?" sans réponse = nuit blanche garantie.
→ Playbook `operations/rollback.yml` testé en staging avant chaque déploiement major.