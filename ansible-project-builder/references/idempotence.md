# Référence : Idempotence

## Définition opérationnelle Staff Engineer

Un playbook est idempotent si et seulement si :
1. Exécuté deux fois de suite sur le même système → même état final
2. **La deuxième exécution produit 0 `changed`**

"Ça ne casse pas au deuxième run" n'est pas suffisant. Zéro changed = standard.

---

## Modules à privilégier

### Toujours préférer les modules déclaratifs

```yaml
# Filesystem
file:        # mkdir, chmod, chown, symlink, touch
copy:        # copier un fichier
template:    # déployer un template Jinja2
blockinfile: # gérer un bloc dans un fichier (avec markers)
lineinfile:  # gérer une ligne (utiliser avec précaution)

# Packages
package:     # abstraction cross-distro
apt:         # Debian/Ubuntu
yum/dnf:     # RHEL/CentOS
pip:         # Python packages

# Services
service:     # gérer un service systemd/init
systemd:     # contrôle plus fin (daemon-reload, etc.)

# Users/Groups
user:
group:

# Network
uri:         # HTTP requests (healthchecks, API calls)
get_url:     # télécharger un fichier

# Database
postgresql_db:
postgresql_user:
mysql_db:
mysql_user:
```

---

## `changed_when` — Patterns corrects

```yaml
# PATTERN 1 : tâche qui ne modifie jamais l'état
- name: Check nginx config validity
  command: nginx -t
  changed_when: false           # Cette commande ne modifie rien
  failed_when: result.rc != 0
  register: result

# PATTERN 2 : changed seulement si output contient un marqueur
- name: Run logrotate
  command: /usr/sbin/logrotate /etc/logrotate.conf
  register: logrotate_result
  changed_when: '"rotating" in logrotate_result.stdout'
  failed_when: logrotate_result.rc not in [0, 1]

# PATTERN 3 : changed basé sur le return code
- name: Import GPG key
  command: gpg --import /tmp/key.gpg
  register: gpg_result
  changed_when: gpg_result.rc == 0 and "not changed" not in gpg_result.stderr

# PATTERN 4 : stat + condition pour éviter les runs inutiles
- name: Check if migration is needed
  stat:
    path: /opt/app/.migration-done
  register: migration_marker

- name: Run database migration
  command: /opt/app/migrate.py
  when: not migration_marker.stat.exists

- name: Mark migration as done
  file:
    path: /opt/app/.migration-done
    state: touch
  when: migration_result is changed
```

---

## Anti-patterns d'idempotence — Les plus dangereux

### 1. Timestamp dans les templates

```jinja2
{# MAUVAIS : régénère le fichier à chaque run #}
# Configuration generated at {{ ansible_date_time.iso8601 }}
worker_processes {{ nginx_worker_processes }};

{# BON : pas de timestamp, ou généré une seule fois #}
# Managed by Ansible — do not edit manually
worker_processes {{ nginx_worker_processes }};
```

### 2. Génération de secrets dans les tasks

```yaml
# MAUVAIS : génère un secret différent à chaque run
- name: Generate app secret
  command: openssl rand -hex 32
  register: app_secret
  # → always changed, secret change à chaque déploiement = sessions invalides

# BON : générer une fois et persister
- name: Check if secret exists
  stat:
    path: /etc/myapp/.secret-key
  register: secret_file

- name: Generate app secret
  command: openssl rand -hex 32
  register: generated_secret
  when: not secret_file.stat.exists
  no_log: true

- name: Store secret permanently
  copy:
    content: "{{ generated_secret.stdout }}"
    dest: /etc/myapp/.secret-key
    mode: '0400'
    owner: appuser
  when: not secret_file.stat.exists
  no_log: true
```

### 3. `service: state: started` au lieu de `state: started` avec handler

```yaml
# MAUVAIS : "started" ne redémarre pas si la config a changé
- name: Start nginx
  service:
    name: nginx
    state: started    # Si nginx tourne déjà avec une vieille config → changed=no mais config non appliquée

# BON : service enabled + started dans les tasks, reload via handler
- name: Enable and start nginx
  service:
    name: nginx
    state: started
    enabled: true
  # Le handler s'occupe du reload si la config a changé
```

### 4. `git clone` sans gestion de la version

```yaml
# MAUVAIS : toujours "changed" si la branche a de nouveaux commits
- name: Clone repository
  git:
    repo: https://github.com/myorg/myapp.git
    dest: /opt/myapp
    version: main    # main change constamment → always changed

# BON : version fixée (tag ou SHA)
- name: Deploy application
  git:
    repo: https://github.com/myorg/myapp.git
    dest: /opt/myapp
    version: "v2.4.1"    # Immuable → idempotent
    force: false
```

### 5. `shell` pour des opérations disponibles en module

```yaml
# MAUVAIS
- shell: mkdir -p /opt/myapp                 # Always changed
- shell: chmod 755 /opt/myapp               # Always changed
- shell: chown appuser:appuser /opt/myapp   # Always changed

# BON : une seule tâche, idempotente
- file:
    path: /opt/myapp
    state: directory
    mode: '0755'
    owner: appuser
    group: appuser
```

### 6. `lineinfile` pour des fichiers de config complexes

```yaml
# MAUVAIS pour les configs structurées : brittle, ordre non garanti
- lineinfile:
    path: /etc/nginx/nginx.conf
    line: "worker_processes 4;"
- lineinfile:
    path: /etc/nginx/nginx.conf
    line: "worker_connections 1024;"

# BON : template pour les fichiers de config
- template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify: "nginx config changed"
```

`lineinfile` est acceptable pour des fichiers système que tu ne peux pas complètement gérer (ex: `/etc/hosts`, `/etc/sudoers`). Pour les configs applicatives, utiliser `template`.

---

## Vérifications post-déploiement — Obligatoires

```yaml
# À la fin de chaque playbook de déploiement
- name: Verify service is running and healthy
  uri:
    url: "http://{{ inventory_hostname }}/health"
    status_code: 200
    timeout: 10
  register: health_check
  until: health_check.status == 200
  retries: 5
  delay: 10
  delegate_to: localhost

- name: Verify service responds correctly
  uri:
    url: "http://{{ inventory_hostname }}/api/v1/status"
    status_code: 200
    return_content: true
  register: api_check
  delegate_to: localhost

- name: Assert expected response
  assert:
    that:
      - '"status" in api_check.json'
      - 'api_check.json.status == "ok"'
    fail_msg: "Service deployed but health check failed: {{ api_check.json }}"
```