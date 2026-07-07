# Référence : Design des Rôles

## Anatomie complète et justification de chaque fichier

### `defaults/main.yml` — La règle fondamentale

Toutes les variables qui peuvent être configurées depuis l'extérieur du rôle. C'est le contrat public du rôle.

```yaml
# roles/nginx/defaults/main.yml
---
# --- Installation ---
nginx_package_name: nginx
nginx_package_state: present

# --- Réseau ---
nginx_listen_port: 80
nginx_listen_port_ssl: 443
nginx_server_name: "{{ inventory_hostname }}"

# --- Performance ---
nginx_worker_processes: "auto"
nginx_worker_connections: 1024
nginx_keepalive_timeout: 65

# --- SSL ---
nginx_ssl_enabled: false
nginx_ssl_cert_path: "/etc/ssl/certs/{{ nginx_server_name }}.crt"
nginx_ssl_key_path: "/etc/ssl/private/{{ nginx_server_name }}.key"

# --- Logging ---
nginx_access_log: "/var/log/nginx/access.log"
nginx_error_log: "/var/log/nginx/error.log"
nginx_log_level: "warn"

# --- Service ---
nginx_service_enabled: true
nginx_service_state: started
```

**Pourquoi chaque variable a une valeur par défaut sensée ?** Un rôle qui échoue si une variable n'est pas définie est un rôle difficile à utiliser. Les valeurs par défaut documentent le comportement attendu et permettent une adoption progressive.

---

### `tasks/main.yml` — Orchestrateur pur

```yaml
# roles/nginx/tasks/main.yml
---
- name: "nginx | Validate variables"
  import_tasks: validate.yml
  tags: always                    # S'exécute même avec --tags spécifique

- name: "nginx | Install"
  import_tasks: install.yml
  tags:
    - nginx
    - nginx-install

- name: "nginx | Configure"
  import_tasks: configure.yml
  tags:
    - nginx
    - nginx-configure

- name: "nginx | Manage SSL"
  import_tasks: ssl.yml
  when: nginx_ssl_enabled | bool
  tags:
    - nginx
    - nginx-ssl

- name: "nginx | Manage service"
  import_tasks: service.yml
  tags:
    - nginx
    - nginx-service
```

**Règle `import_tasks` vs `include_tasks` :**
- `import_tasks` (statique) : les tags se propagent aux sous-tâches, les handlers fonctionnent correctement → **utiliser par défaut**
- `include_tasks` (dynamique) : nécessaire uniquement si le nom du fichier dépend d'une variable (`include_tasks: "{{ ansible_os_family }}.yml"`)

---

### `tasks/validate.yml` — Le gardien

```yaml
# roles/nginx/tasks/validate.yml
---
- name: "nginx | Assert required variables are defined"
  assert:
    that:
      - nginx_listen_port is defined
      - nginx_listen_port | int > 0
      - nginx_listen_port | int < 65536
      - nginx_worker_processes is defined
    fail_msg: |
      nginx role validation failed.
      nginx_listen_port must be a valid port number (1-65535).
      Current value: {{ nginx_listen_port | default('UNDEFINED') }}
  tags: always

- name: "nginx | Assert SSL variables when SSL is enabled"
  assert:
    that:
      - nginx_ssl_cert_path is defined
      - nginx_ssl_key_path is defined
    fail_msg: "nginx_ssl_cert_path and nginx_ssl_key_path are required when nginx_ssl_enabled is true"
  when: nginx_ssl_enabled | bool
  tags: always
```

---

### `tasks/install.yml` — Idempotent par nature

```yaml
# roles/nginx/tasks/install.yml
---
- name: "nginx | Install nginx package"
  ansible.builtin.package:
    name: "{{ nginx_package_name }}"
    state: "{{ nginx_package_state }}"
  notify: "nginx | validate config"

- name: "nginx | Ensure nginx directories exist"
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: root
    group: root
    mode: '0755'
  loop:
    - /etc/nginx/conf.d
    - /etc/nginx/sites-available
    - /etc/nginx/sites-enabled
    - /var/log/nginx
```

---

### `tasks/configure.yml` — Template-driven

```yaml
# roles/nginx/tasks/configure.yml
---
- name: "nginx | Deploy main configuration"
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: '0644'
    validate: nginx -t -c %s    # Validation avant deploy
  notify: "nginx config changed"

- name: "nginx | Deploy default vhost"
  ansible.builtin.template:
    src: default.conf.j2
    dest: /etc/nginx/conf.d/default.conf
    owner: root
    group: root
    mode: '0644'
  notify: "nginx config changed"
```

---

### `handlers/main.yml` — Zéro collision, zero-downtime

```yaml
# roles/nginx/handlers/main.yml
---
# Utiliser `listen` pour éviter les collisions de noms entre rôles
# et pour chaîner des handlers

- name: "nginx | validate config before reload"
  ansible.builtin.command: nginx -t
  changed_when: false
  listen: "nginx config changed"

- name: "nginx | reload service"
  ansible.builtin.service:
    name: nginx
    state: reloaded         # reload = zero-downtime. restart uniquement si modules changent
  listen: "nginx config changed"
```

**Pourquoi `listen` plutôt que `name` dans `notify` ?**
Si deux rôles ont un handler nommé `restart nginx`, le comportement est indéterminé. `listen` est un topic découplé du nom — le rôle nginx écoute `"nginx config changed"`, le rôle postgresql écoute `"postgresql config changed"`. Aucune collision possible.

---

### `meta/main.yml` — Le contrat de dépendances

```yaml
# roles/nginx/meta/main.yml
---
galaxy_info:
  role_name: nginx
  author: myorg
  description: Install and configure nginx web server
  min_ansible_version: "2.14"
  platforms:
    - name: Ubuntu
      versions:
        - "22.04"
        - "24.04"

dependencies:
  - role: base-os              # base-os doit être joué avant nginx
    allow_duplicates: false    # Ne pas rejouer si déjà exécuté dans le play
```

---

## Granularité idéale — La règle de la phrase unique

**Test de granularité** : si tu ne peux pas décrire ton rôle en une seule phrase sans le mot "et", il fait trop de choses.

```
✅ "Configure and manage nginx as a reverse proxy"
✅ "Install and configure PostgreSQL server"
✅ "Deploy application artifacts from S3 to target hosts"

❌ "Install nginx, configure SSL, deploy the app, and set up monitoring"
   → Découper en : nginx / ssl-certificates / app-deploy / monitoring-agent
```

---

## Exemple mauvais rôle vs bon rôle

### MAUVAIS — Rôle monolithique

```yaml
# roles/setup_app/tasks/main.yml
- apt:
    name: [nginx, postgresql, nodejs, redis]   # Responsabilités multiples

- git:
    repo: "{{ repo }}"         # Variable générique, pas de version
    dest: /opt/app

- service:
    name: "{{ item }}"
    state: started             # Not idempotent — "started" ≠ "running after config change"
  loop: [nginx, postgresql, redis]
```

Problèmes : 4 responsabilités, variables sans préfixe, pas de version git, pas de tags, handlers absents.

### BON — Rôles composables

```yaml
# site.yml ou webservers.yml
roles:
  - role: base-os
  - role: firewall
  - role: nginx
    vars:
      nginx_listen_port: 80
      nginx_ssl_enabled: true
  - role: app-deploy
    vars:
      app_deploy_name: myapp
      app_deploy_version: "v2.4.1"   # Version explicite, jamais main en prod
  - role: monitoring-agent
```

Chaque rôle est indépendamment testable, réutilisable, et remplaçable.

---

## Dépendances entre rôles — Patterns recommandés

### Pattern 1 : meta/main.yml (dépendances déclaratives)
```yaml
# Avantage : automatique
# Inconvénient : toujours exécuté, même si déjà joué
dependencies:
  - role: base-os
    allow_duplicates: false
```

### Pattern 2 : Import explicite dans le playbook (recommandé pour la clarité)
```yaml
# webservers.yml
- hosts: webservers
  roles:
    - base-os         # Joué en premier, explicitement
    - firewall
    - nginx
```

### Pattern 3 : `include_role` conditionnel
```yaml
- name: Install monitoring if enabled
  include_role:
    name: monitoring-agent
  when: monitoring_enabled | default(false) | bool
```