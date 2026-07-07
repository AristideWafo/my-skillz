---
name: ansible-project-builder
description: >
  Guide and enforce Senior/Staff-level Ansible project architecture, structure, and patterns for Jerry (Cloud Architect/DevOps at Société Générale, EPITECH Master Cloud). Use this skill whenever Jerry asks to create, review, scaffold, refactor, or audit any Ansible project, playbook, role, inventory, variable structure, CI/CD pipeline, or Ansible Pull architecture. Also trigger for: structuring a new Ansible repo, reviewing an existing one, writing a role, deciding between push vs pull mode, designing variable hierarchies, setting up Molecule tests, configuring vault, or designing a CI/CD pipeline for Ansible. Trigger even if Jerry just says "set up ansible for my project" or "help me with my ansible role" — don't wait for explicit architectural language. This skill enforces Staff Engineer standards: idempotence, security, scalability to 500+ hosts, multi-environment separation, and long-term maintainability.
---

# Ansible Project Builder — Staff Engineer Standards

> Référence pour un ingénieur intermédiaire-avancé visant les pratiques Senior/Staff.
> Contexte : Jerry — Cloud Architect/DevOps @SG, multi-cloud AWS/Azure, projets multi-hôtes multi-environnements.

----

## Lecture de Projet Existant — Approche Sélective

Avant de lire les fichiers d'un projet fourni :
1. Construire la carte d'inventaire (quels groupes, quels hôtes)
2. Identifier les rôles impactés par la demande
3. Lire uniquement ces rôles (pas tous les rôles du projet)
4. Charger uniquement les variables pertinentes (group_vars du groupe concerné)
5. Ignorer les playbooks non liés à la demande

---

## Évaluation initiale — Poser les bonnes questions d'abord

Avant de scaffolder ou de conseiller, **toujours évaluer le contexte** :

1. **Scope** — Nombre d'hôtes cibles ? (< 20 / 20-200 / 200+)
2. **Mode** — Push (controller centralisé) ou Pull (ansible-pull via cron) ?
3. **Environnements** — Combien ? (dev/staging/prod ou plus complexe ?)
4. **Équipe** — Solo ou multi-contributeurs ?
5. **Secrets** — AWS SSM / HashiCorp Vault / Ansible Vault fichier ?
6. **CI/CD** — GitHub Actions / GitLab CI / autre ?
7. **Maturité actuelle** — Structure existante à revoir ou projet from scratch ?

Si la réponse à plusieurs de ces points est inconnue, **scaffolder la structure la plus conservative** (multi-inventaires, rôles granulaires, vault par env) et documenter les hypothèses.

---

## Structure de Projet — La Référence

Utiliser systématiquement cette structure. Ne jamais dévier sans justification explicite.

```
infrastructure/
├── ansible.cfg                         # Config globale documentée
├── requirements.yml                    # Collections + rôles, versions FIGÉES
│
├── inventories/
│   ├── production/
│   │   ├── hosts.yml                   # YAML uniquement (jamais INI)
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── main.yml            # Variables universelles, aucun secret
│   │   │   │   └── vault.yml           # Secrets chiffrés vault
│   │   │   └── <group>/
│   │   │       ├── main.yml
│   │   │       └── vault.yml
│   │   └── host_vars/
│   │       └── <hostname>/
│   │           ├── main.yml
│   │           └── vault.yml
│   ├── staging/                        # Même structure exacte
│   └── development/                    # Même structure exacte
│
├── playbooks/
│   ├── site.yml                        # Import-only, ZÉRO logique
│   ├── <domain>.yml                    # Ex: webservers.yml, databases.yml
│   └── operations/
│       ├── rotate-secrets.yml
│       ├── patch-os.yml
│       └── drain-node.yml
│
├── roles/
│   └── <rolename>/                     # Voir structure de rôle ci-dessous
│
├── plugins/
│   ├── filter/                         # Filtres Jinja2 custom
│   ├── lookup/                         # Lookups custom
│   └── callback/                       # Reporting, Slack, ARA
│
└── tests/
    └── molecule/
```

**Règle absolue** : les `group_vars` et `host_vars` sont DANS l'inventaire, jamais à la racine du projet. Un `group_vars/` à la racine = shared entre tous les environnements = anti-pattern critique.

---

## Structure de Rôle — La Référence

```
roles/<rolename>/
├── defaults/main.yml     # TOUTES les variables configurables, avec valeurs par défaut
├── files/                # Fichiers statiques (pas de templating)
├── handlers/main.yml     # Handlers uniquement
├── meta/main.yml         # Dépendances, compatibilité OS, galaxy_info
├── tasks/
│   ├── main.yml          # Import uniquement — import_tasks par catégorie
│   ├── validate.yml      # Assertions de validation (tags: always)
│   ├── install.yml
│   ├── configure.yml
│   └── service.yml
├── templates/            # Fichiers Jinja2
├── tests/molecule/
└── vars/main.yml         # Constantes internes UNIQUEMENT (usage rare)
```

Pour la logique détaillée de chaque composant → voir `references/roles.md`

---

## Variables — Règles Non Négociables

**Convention de nommage :**
```yaml
# Toujours préfixer par le nom du rôle
nginx_listen_port: 80           # Variable publique
nginx_ssl_enabled: true
__nginx_config_path: "/etc/nginx"   # Variable "privée" au rôle

# Secrets vault : préfixe vault_
vault_nginx_ssl_cert: "..."

# Facts custom : préfixe fact_
nginx_fact_version: "1.24"
```

**Règle `defaults/` vs `vars/` :**
- `defaults/main.yml` → tout ce qui doit être configurable depuis l'extérieur (99% des cas)
- `vars/main.yml` → constantes qui ne doivent JAMAIS être changées (rare, ex: paths système figés)

**Validation obligatoire en entrée de rôle :**
```yaml
# tasks/validate.yml — toujours importé avec tags: always
- name: "{{ role_name }} | Validate required variables"
  assert:
    that:
      - rolename_var is defined
      - rolename_var | length > 0
    fail_msg: "rolename_var is required. See role README."
  tags: always
```

Pour l'ordre de priorité complet des variables et les cas piège → voir `references/variables.md`

---

## Idempotence — Standard Zéro Changed

**Le test** : un second run complet doit produire **0 changed**. Si ce n'est pas le cas, ce n'est pas acceptable en production.

```yaml
# Règle : tout command/shell doit avoir changed_when explicite
- name: Check nginx config
  command: nginx -t
  changed_when: false           # Ne modifie jamais l'état du système
  failed_when: result.rc != 0

# Règle : préférer les modules déclaratifs
- name: Ensure directory exists   # file > command mkdir
  file:
    path: /opt/myapp
    state: directory
    mode: '0755'
    owner: "{{ app_user }}"
```

Anti-patterns d'idempotence courants → voir `references/idempotence.md`

---

## Handlers — Le Piège le Plus Dangereux

```yaml
# TOUJOURS utiliser listen pour éviter les collisions entre rôles
handlers:
  - name: "nginx | reload configuration"
    service:
      name: nginx
      state: reloaded          # reload > restart (zero-downtime)
    listen: "nginx config changed"

  - name: "nginx | validate before reload"
    command: nginx -t
    changed_when: false
    listen: "nginx config changed"   # S'exécute en premier grâce à l'ordre

# Dans les tasks :
- name: Deploy nginx config
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify: "nginx config changed"
```

---

## Sécurité — Standards Obligatoires

**Vault par environnement :**
```bash
# Vault ID différent par env — jamais un seul vault password global
ansible-vault encrypt --vault-id prod@~/.vault-pass-prod inventories/production/group_vars/all/vault.yml
ansible-vault encrypt --vault-id staging@~/.vault-pass-staging inventories/staging/group_vars/all/vault.yml
```

**Secrets AWS SSM (recommandé pour infra AWS) :**
```yaml
- name: Get secret from SSM
  set_fact:
    db_password: "{{ lookup('amazon.aws.aws_ssm', '/prod/db/password', region='eu-west-1') }}"
  no_log: true   # OBLIGATOIRE sur toutes les tâches avec secrets
```

**`no_log: true`** sur toute tâche qui manipule un secret. Sans exception.

Pour l'intégration HashiCorp Vault et la gestion SSH → voir `references/security.md`

---

## Performance — Paramètres ansible.cfg

```ini
[defaults]
forks              = 50          # Défaut 5 → trop lent pour 50+ hôtes
gather_facts       = false       # Désactiver par défaut, activer explicitement
fact_caching       = redis       # Cache facts (évite reconnexion à chaque run)
fact_caching_connection = redis://redis-internal:6379/0
fact_caching_timeout = 3600

[ssh_connection]
pipelining         = true        # x3-5 plus rapide (réduction connexions SSH)
ssh_args           = -C -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=yes
```

Pour la configuration `serial`, `strategy`, `async` sur 200+ hôtes → voir `references/performance.md`

---

## CI/CD — Pipeline Minimum Acceptable

```
Lint (yamllint + ansible-lint)
  → Molecule tests (par rôle, matrix OS)
    → Dry-run --check --diff (staging)
      → Deploy staging
        → Approbation manuelle
          → Deploy production (rolling)
```

**ansible-lint config (`.ansible-lint`) :**
```yaml
profile: production
skip_list:
  - yaml[line-length]
exclude_paths:
  - molecule/
```

Pour le workflow GitHub Actions complet et la config Molecule → voir `references/cicd.md`

---

## Ansible Pull — Architecture Spécifique

Utiliser Pull quand :
- 200+ nœuds identiques (autoscaling groups, edge nodes)
- Pas de connexion SSH entrante possible
- Besoin de configuration drift remediation automatique

**Points critiques Pull :**
- Lock file obligatoire (éviter exécutions concurrentes)
- Secrets via AWS SSM ou IAM role (jamais de vault file dans le repo)
- Cibler un **tag git versionné**, jamais `main` en production
- Monitoring : alerte si last_success > 1 heure

Pour le wrapper script complet et l'architecture monitoring Pull → voir `references/ansible-pull.md`

---

## Génération de Contenu — Ce que ce Skill Produit

Quand Jerry demande de créer ou scaffolder quelque chose, produire :

### Scaffold complet de projet
Créer l'arborescence avec fichiers initiaux commentés, `ansible.cfg`, `requirements.yml`, `site.yml`, un inventaire de base, et un rôle `common` skeleton.

### Rôle complet
Tous les fichiers du rôle (`defaults`, `tasks/` découpées, `handlers`, `meta`, `templates`, `molecule/`) avec exemples concrets adaptés au domaine (nginx, postgresql, monitoring-agent, etc.).

### Review critique
Auditer la structure fournie et lister les anti-patterns avec criticité (🔴 Critique / 🟠 Important / 🟡 Recommandé) et la correction concrète.

### Playbook d'opération
Playbook ciblé avec tags, serial, validation post-déploiement, et rollback intégré.

---

## Anti-patterns — Signal d'Alarme Immédiat

À signaler dès qu'ils apparaissent, avec criticité et correction :

| Anti-pattern | Criticité | Action |
|---|---|---|
| `group_vars/` à la racine du projet | 🔴 | Déplacer dans `inventories/<env>/group_vars/` |
| Variables sans préfixe de rôle | 🔴 | Renommer avec `<rolename>_` |
| Secrets en clair dans le repo | 🔴 | Vault + secret manager immédiatement |
| `vars/main.yml` pour configs publiques | 🔴 | Déplacer dans `defaults/main.yml` |
| `command`/`shell` sans `changed_when` | 🟠 | Ajouter `changed_when: false` ou condition |
| Un seul vault password pour tous les envs | 🟠 | Vault ID par environnement |
| Logique dans `site.yml` | 🟠 | Import-only, logique dans les rôles |
| `ansible-pull -C main` en production | 🟠 | Cibler un tag versionné |
| `forks = 5` sur 50+ hôtes | 🟡 | Passer à 50 minimum |
| Pas de `pipelining = true` | 🟡 | Activer dans `ansible.cfg` |
| Pas de Molecule sur les rôles | 🟡 | Ajouter molecule skeleton |
| Handlers avec noms génériques | 🟡 | Préfixer par nom de rôle + `listen` |

Liste complète des 50 anti-patterns → voir `references/anti-patterns.md`

---

## Checklist Rapide Avant Commit

- [ ] Second run du playbook → 0 `changed` ?
- [ ] Toutes les variables ont un préfixe de rôle ?
- [ ] Aucun secret en clair (`git grep -i password`) ?
- [ ] `changed_when` sur tous les `command`/`shell` ?
- [ ] `no_log: true` sur toutes les tâches avec secrets ?
- [ ] Tags présents sur les tâches ?
- [ ] Handlers utilisent `listen` avec noms qualifiés ?
- [ ] `meta/main.yml` renseigné ?
- [ ] Molecule test passant localement ?
- [ ] `ansible-lint` sans erreur profile production ?