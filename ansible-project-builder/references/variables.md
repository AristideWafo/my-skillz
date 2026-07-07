# Référence : Gestion des Variables

## Ordre de priorité complet (du moins au plus prioritaire)

```
1.  role defaults          (roles/x/defaults/main.yml)       ← plus facile à overrider
2.  inventory group_vars   (inventories/prod/group_vars/all/)
3.  inventory group_vars   (inventories/prod/group_vars/<group>/)
4.  inventory host_vars    (inventories/prod/host_vars/<host>/)
5.  play vars              (vars: dans le playbook)
6.  role vars              (roles/x/vars/main.yml)            ← DIFFICILE à overrider
7.  set_facts / registered vars
8.  extra vars             (-e "key=val")                     ← TOUJOURS vainqueur
```

**Le piège `vars/main.yml`** : les variables dans `roles/x/vars/main.yml` (niveau 6) écrasent les `group_vars` (niveaux 2-4). Si tu mets une variable dans `vars/main.yml` en pensant que l'opérateur pourra la surcharger depuis l'inventaire, il ne pourra pas. C'est l'erreur de variable #1 en entreprise.

---

## Conventions de nommage — Règles strictes

```yaml
# 1. TOUJOURS préfixer par le nom du rôle
nginx_listen_port: 80                    # ✅ clair, sans collision
port: 80                                 # ❌ collision garantie avec d'autres rôles

# 2. Variables "privées" au rôle (usage interne uniquement)
__nginx_default_config_template: "nginx.conf.j2"   # Double underscore = privé

# 3. Secrets vault : préfixe vault_
vault_postgresql_password: "..."         # Chiffré dans vault.yml

# 4. Facts custom définis via set_fact
nginx_fact_installed_version: "1.24"    # Préfixe _fact_ pour distinguer des vars config

# 5. Variables booléennes : nommage affirmatif
nginx_ssl_enabled: true                  # ✅
nginx_no_ssl: false                      # ❌ double négation confuse

# 6. Variables de liste : pluriel
nginx_upstream_servers: []
nginx_allowed_ips: []
```

---

## group_vars — Structure recommandée

```
inventories/production/group_vars/
├── all/
│   ├── main.yml       # Variables universelles, jamais de secrets
│   └── vault.yml      # Secrets vault (ansible-vault encrypt)
├── webservers/
│   ├── main.yml
│   └── vault.yml
└── databases/
    ├── main.yml
    └── vault.yml
```

**Ce qui va dans `all/main.yml` :**
```yaml
---
# Variables vraiment universelles — s'appliquent à TOUS les hôtes
environment_name: production
ansible_python_interpreter: /usr/bin/python3
timezone: "Europe/Paris"
ntp_servers:
  - ntp1.internal.company.com
  - ntp2.internal.company.com

# Paramètres de base communs
base_os_admin_users:
  - name: ansible
    uid: 990
    shell: /bin/bash
    authorized_keys:
      - "ssh-ed25519 AAAA... ansible@controller"
```

**Ce qui NE va PAS dans `all/main.yml` :**
- Variables qui ne s'appliquent qu'à un groupe spécifique
- Secrets (→ `vault.yml`)
- Variables de rôle qui ont déjà un `default/` correct

---

## host_vars — Quand les utiliser

`host_vars` pour les exceptions à la règle de groupe. Si plus de 30% des hôtes ont des `host_vars`, c'est le signe que la structure de groupes est mal conçue.

```yaml
# inventories/production/host_vars/db-prod-01/main.yml
---
# Cet hôte est le primary PostgreSQL — configuration spécifique
postgresql_role: primary
postgresql_max_connections: 500           # Override du défaut du groupe

# Cas d'usage légitimes pour host_vars :
# - Adresses IP ou FQDN spécifiques
# - Rôles de réplication (primary/replica)
# - Matériel différent (RAM, CPU) nécessitant des tunings différents
# - Hôte legacy avec des contraintes spécifiques
```

---

## Validation des variables — Template complet

```yaml
# roles/<rolename>/tasks/validate.yml
---
- name: "{{ role_name }} | Validate required string variables"
  ansible.builtin.assert:
    that:
      - item.value is defined
      - item.value | string | length > 0
    fail_msg: "Variable '{{ item.name }}' is required and must be a non-empty string."
  loop:
    - { name: "rolename_hostname", value: "{{ rolename_hostname | default('') }}" }
    - { name: "rolename_port", value: "{{ rolename_port | default('') }}" }
  tags: always

- name: "{{ role_name }} | Validate port range"
  ansible.builtin.assert:
    that:
      - rolename_port | int > 0
      - rolename_port | int < 65536
    fail_msg: "rolename_port must be between 1 and 65535. Got: {{ rolename_port }}"
  tags: always

- name: "{{ role_name }} | Validate environment-specific constraints"
  ansible.builtin.assert:
    that:
      - rolename_version != "latest"      # Interdit en production
      - rolename_version is regex('^v\d+\.\d+\.\d+$')   # Doit être un semver
    fail_msg: |
      In production, rolename_version must be a semantic version tag (e.g., v1.2.3).
      'latest' is never acceptable in production.
      Current value: {{ rolename_version }}
  when: environment_name == "production"
  tags: always
```

---

## Éviter les conflits — Stratégies

### Stratégie 1 : Préfixage systématique (obligatoire)
Voir conventions ci-dessus.

### Stratégie 2 : Inventaire des variables publiques
Maintenir un `README.md` dans chaque rôle listant toutes les variables `defaults/` :

```markdown
## Variables

| Variable | Default | Description |
|---|---|---|
| `nginx_listen_port` | `80` | Port HTTP d'écoute |
| `nginx_ssl_enabled` | `false` | Activer HTTPS |
| `nginx_worker_processes` | `"auto"` | Nombre de workers nginx |
```

### Stratégie 3 : Ne jamais redéfinir une variable dans plusieurs endroits
Si une variable est définie dans `group_vars/all` ET dans `defaults/main.yml`, c'est une ambiguïté. La règle : une variable a UN seul endroit canonique de définition.

```yaml
# Mauvais : défini dans group_vars/all ET dans defaults/
# group_vars/all/main.yml
nginx_listen_port: 80

# roles/nginx/defaults/main.yml
nginx_listen_port: 80   # Redondant, source de confusion

# Bon : défini uniquement dans defaults/ (le rôle est la source de vérité)
# roles/nginx/defaults/main.yml
nginx_listen_port: 80

# group_vars/webservers/main.yml — override uniquement si nécessaire
nginx_listen_port: 8080   # Override explicite pour ce groupe
```