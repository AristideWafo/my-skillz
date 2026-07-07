# Référence : Performance & Scalabilité

## ansible.cfg — Paramètres Performance

```ini
[defaults]
# Parallélisme
forks                   = 50        # Défaut 5 → trop lent pour 50+ hôtes
                                    # Pour 500+ hôtes : 100-200 selon le controller

# Facts
gather_facts            = false     # Désactiver par défaut
fact_caching            = redis
fact_caching_connection = redis://redis-internal:6379/0
fact_caching_timeout    = 3600      # 1h pour infra dynamique, 86400 pour infra stable

[ssh_connection]
pipelining              = true      # x3-5 plus rapide : une seule connexion SSH par tâche
ssh_args                = -C -o ControlMaster=auto -o ControlPersist=60s
transfer_method         = smart
```

---

## gather_facts — Stratégie par Play

```yaml
# MAUVAIS : facts activés partout (défaut)
# Sur 500 hôtes → 500 connexions SSH juste pour collecter des facts

# BON : désactivé par défaut, activé explicitement avec subset
- hosts: webservers
  gather_facts: false     # Pas besoin de facts pour ce play
  roles:
    - nginx               # Toutes les variables viennent de group_vars

- hosts: databases
  gather_facts: true
  gather_subset:
    - min                 # OS, hostname, architecture seulement
    - network             # IPs et interfaces
    # Pas de "hardware" ni "virtual" — très lents
  roles:
    - postgresql
```

**`gather_subset` disponibles par vitesse (du plus rapide au plus lent) :**
- `min` — OS, hostname, architecture (très rapide)
- `network` — IPs, interfaces, DNS
- `distribution` — distro + version + package manager
- `virtual` — VM type detection (lent)
- `hardware` — CPU, RAM, disques (très lent)
- `all` — tout (utiliser uniquement si vraiment nécessaire)

---

## strategy et serial — Rolling Deployments

```yaml
# Déploiement séquentiel sur 100 serveurs = ~100x plus lent qu'un rolling 10%

# Rolling update recommandé pour les déploiements
- hosts: webservers
  strategy: linear        # Toujours linear pour les déploiements avec serial
  serial:
    - 1                   # 1 serveur en premier (canary)
    - 10%                 # Puis 10% du pool
    - 50%                 # Puis 50%
    - 100%                # Puis le reste
  max_fail_percentage: 5  # Stopper si >5% des serveurs échouent

# Pour les tâches indépendantes sans rolling (ex: fact collection, patch OS)
- hosts: all
  strategy: free          # Chaque hôte avance à son rythme — plus rapide
  gather_facts: true
  tasks:
    - name: Collect system information
      setup:
```

---

## async — Opérations Longues

```yaml
# Sans async : SSH timeout si la tâche dépasse ControlPersist (60s par défaut)
# Pour les opérations > 60s : toujours utiliser async

# MAUVAIS pour les longues migrations
- name: Run database migration
  command: /opt/app/migrate.py
  # → peut timeout après 60s

# BON : async avec polling
- name: Start database migration (async)
  command: /opt/app/migrate.py
  async: 1800         # Timeout max : 30 minutes
  poll: 0             # Fire and forget (vérification manuelle après)
  register: migration_job

- name: Check migration status
  async_status:
    jid: "{{ migration_job.ansible_job_id }}"
  register: job_result
  until: job_result.finished
  retries: 60
  delay: 30
  failed_when: job_result.failed

# Pattern fire-and-forget pour des opérations sur beaucoup d'hôtes
- name: Trigger backup on all servers (async)
  command: /usr/local/bin/backup.sh
  async: 3600
  poll: 0
  register: backup_jobs

- name: Wait for all backups to complete
  async_status:
    jid: "{{ item.ansible_job_id }}"
  register: results
  until: results.finished
  retries: 120
  delay: 30
  loop: "{{ backup_jobs.results }}"
  when: item.ansible_job_id is defined
```

---

## delegate_to — Optimisation

```yaml
# MAUVAIS : loop sur 500 hôtes avec delegate_to localhost
# → 500 tâches séquentielles sur le controller
- name: Register each server in load balancer
  uri:
    url: "https://lb.internal/api/backends"
    method: POST
    body: '{"host": "{{ inventory_hostname }}"}'
  delegate_to: localhost
  loop: "{{ groups['webservers'] }}"

# BON : run_once pour les opérations d'orchestration
- name: Register all servers in load balancer (batch)
  uri:
    url: "https://lb.internal/api/backends/batch"
    method: POST
    body:
      hosts: "{{ groups['webservers'] }}"
  delegate_to: localhost
  run_once: true
```

---

## Optimisation pour 500+ Serveurs

### Architecture recommandée

```
┌─────────────────────────────────────────────────┐
│  500+ serveurs — Architecture optimisée          │
│                                                   │
│  Controller principal                             │
│  ├── forks: 200                                  │
│  ├── pipelining: true                            │
│  └── Ansible Pull activé sur les nœuds          │
│                                                   │
│  Cache Redis (HA)                                │
│  └── Facts cachés 24h pour infra stable          │
│                                                   │
│  Bastion SSH                                     │
│  └── ProxyCommand pour les zones isolées         │
└─────────────────────────────────────────────────┘
```

### Profiling des playbooks

```bash
# Activer le profiling dans ansible.cfg
callbacks_enabled = timer, profile_tasks, profile_roles

# Output après un run :
# =====================================================
# Playbook Statistics
# =====================================================
# nginx : install              : 45.23s
# nginx : configure            : 12.87s
# postgresql : configure       : 8.92s
# gather_facts                 : 4.21s   ← souvent trop élevé
```

### Limiter les runs pendant les tests

```bash
# Tester sur 1 seul hôte avant d'appliquer à tous
ansible-playbook site.yml -i inventories/production/ --limit web-prod-01

# Tester sur un groupe limité
ansible-playbook site.yml -i inventories/production/ --limit "webservers[0:5]"

# Tester sur un hôte d'un groupe de façon random
ansible-playbook site.yml -i inventories/production/ --limit "{{ groups['webservers'] | random }}"
```