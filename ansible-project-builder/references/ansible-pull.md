# Référence : Ansible Pull — Architecture & Sécurité

## Wrapper Script de Production

```bash
#!/bin/bash
# /usr/local/bin/ansible-pull-run.sh
# À installer via le rôle base-os, mode 0755, owner root

set -euo pipefail

# --- Configuration (override via /etc/ansible/pull.conf si existant) ---
REPO_URL="${ANSIBLE_PULL_REPO:-git@github.com:myorg/infrastructure.git}"
BRANCH="${ANSIBLE_PULL_BRANCH:-v2.4.1}"          # TAG versionné, jamais main en prod
PLAYBOOK="${ANSIBLE_PULL_PLAYBOOK:-playbooks/local.yml}"
VAULT_PASS_FILE="${ANSIBLE_VAULT_PASS_FILE:-/etc/ansible/.vault-pass}"
LOG_DIR="/var/log/ansible"
LOG_FILE="$LOG_DIR/pull-$(date +%Y%m%d-%H%M%S).log"
LOCK_FILE="/var/run/ansible-pull.lock"
MAX_LOG_DAYS=7
AWS_REGION="${AWS_REGION:-eu-west-1}"
METRICS_NAMESPACE="Ansible/Pull"

mkdir -p "$LOG_DIR"
chmod 750 "$LOG_DIR"

# --- Lock : éviter les exécutions concurrentes ---
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$(date -Iseconds) INFO: ansible-pull already running, skipping" | tee -a "$LOG_FILE"
    exit 0
fi

cleanup() {
    local exit_code=$?
    rm -f "$LOCK_FILE"
    find "$LOG_DIR" -name "pull-*.log" -mtime +"$MAX_LOG_DAYS" -delete 2>/dev/null || true

    # Envoyer métriques CloudWatch
    if command -v aws &>/dev/null; then
        aws cloudwatch put-metric-data \
            --namespace "$METRICS_NAMESPACE" \
            --metric-data \
            "[{\"MetricName\":\"ExitCode\",\"Value\":$exit_code,\"Dimensions\":[{\"Name\":\"Host\",\"Value\":\"$(hostname -f)\"}]},
              {\"MetricName\":\"Duration\",\"Value\":$(($(date +%s) - START_TIME)),\"Unit\":\"Seconds\",\"Dimensions\":[{\"Name\":\"Host\",\"Value\":\"$(hostname -f)\"}]}]" \
            --region "$AWS_REGION" 2>/dev/null || true
    fi

    exit "$exit_code"
}
trap cleanup EXIT

START_TIME=$(date +%s)

echo "$(date -Iseconds) INFO: Starting ansible-pull" | tee -a "$LOG_FILE"
echo "$(date -Iseconds) INFO: Repo: $REPO_URL, Branch: $BRANCH" | tee -a "$LOG_FILE"

# Récupérer le vault pass depuis AWS SSM si le fichier n'existe pas
if [[ ! -f "$VAULT_PASS_FILE" ]]; then
    echo "$(date -Iseconds) INFO: Fetching vault password from SSM" | tee -a "$LOG_FILE"
    aws ssm get-parameter \
        --name "/ansible/vault-pass/$(hostname -d | cut -d. -f1)" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region "$AWS_REGION" > "$VAULT_PASS_FILE"
    chmod 400 "$VAULT_PASS_FILE"
fi

# Exécution ansible-pull
ansible-pull \
    --url "$REPO_URL" \
    --checkout "$BRANCH" \
    --inventory localhost, \
    --vault-password-file "$VAULT_PASS_FILE" \
    --accept-host-key \
    --clean \
    --full \
    "$PLAYBOOK" \
    2>&1 | tee -a "$LOG_FILE"

echo "$(date -Iseconds) INFO: ansible-pull completed" | tee -a "$LOG_FILE"
```

---

## Cron Configuration — Via Rôle Ansible

```yaml
# roles/ansible-pull/tasks/main.yml
---
- name: "ansible-pull | Install ansible-pull runner script"
  template:
    src: ansible-pull-run.sh.j2
    dest: /usr/local/bin/ansible-pull-run
    mode: '0755'
    owner: root
    group: root

- name: "ansible-pull | Configure cron job"
  cron:
    name: "ansible-pull configuration management"
    minute: "*/{{ ansible_pull_interval_minutes | default(15) }}"
    hour: "*"
    job: "/usr/local/bin/ansible-pull-run >> /var/log/ansible/pull-cron.log 2>&1"
    user: root
    state: present

- name: "ansible-pull | Configure logrotate"
  template:
    src: ansible-pull-logrotate.j2
    dest: /etc/logrotate.d/ansible-pull
    mode: '0644'
```

---

## Prometheus Exporter — Monitoring du Drift

```python
#!/usr/bin/env python3
# /usr/local/bin/ansible-pull-exporter.py
# Expose métriques pour Prometheus scraping

import os
import re
import time
import glob
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_DIR = "/var/log/ansible"
PORT = 9115

def parse_last_run():
    """Parse le log ansible-pull le plus récent"""
    logs = sorted(glob.glob(f"{LOG_DIR}/pull-*.log"), reverse=True)
    if not logs:
        return None

    last_log = logs[0]
    stat = os.stat(last_log)
    mtime = stat.st_mtime

    with open(last_log, 'r') as f:
        content = f.read()

    exit_code = 0 if "ansible-pull completed" in content else 1
    changed = len(re.findall(r'changed=(\d+)', content))
    failed = len(re.findall(r'failed=(\d+)', content))

    return {
        'timestamp': mtime,
        'exit_code': exit_code,
        'changed_tasks': changed,
        'failed_tasks': failed
    }

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/metrics':
            self.send_response(404)
            self.end_headers()
            return

        result = parse_last_run()
        hostname = os.uname().nodename
        now = time.time()

        metrics = []
        if result:
            age = now - result['timestamp']
            metrics.extend([
                f'ansible_pull_last_success_timestamp_seconds{{host="{hostname}"}} {result["timestamp"]}',
                f'ansible_pull_last_run_exit_code{{host="{hostname}"}} {result["exit_code"]}',
                f'ansible_pull_last_run_age_seconds{{host="{hostname}"}} {age:.0f}',
                f'ansible_pull_changed_tasks_total{{host="{hostname}"}} {result["changed_tasks"]}',
                f'ansible_pull_failed_tasks_total{{host="{hostname}"}} {result["failed_tasks"]}',
            ])

        body = '\n'.join(metrics) + '\n'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass  # Silence HTTP logs

if __name__ == '__main__':
    server = HTTPServer(('', PORT), MetricsHandler)
    server.serve_forever()
```

---

## Alerting Prometheus — Règles de Drift

```yaml
# monitoring/rules/ansible-pull.yml
---
groups:
  - name: ansible-pull
    rules:
      - alert: AnsiblePullNotRunning
        expr: time() - ansible_pull_last_success_timestamp_seconds > 3600
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "Ansible Pull not running on {{ $labels.host }}"
          description: |
            Ansible Pull hasn't completed successfully on {{ $labels.host }} for
            {{ $value | humanizeDuration }}. Configuration drift risk.
            Check logs: /var/log/ansible/ on the target host.
          runbook: "https://wiki.internal/runbooks/ansible-pull-failure"

      - alert: AnsiblePullFailing
        expr: ansible_pull_last_run_exit_code != 0
        for: 2m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Ansible Pull failing on {{ $labels.host }}"
          description: |
            Ansible Pull is returning non-zero exit code on {{ $labels.host }}.
            Immediate investigation required.

      - alert: AnsiblePullHighChangedCount
        expr: ansible_pull_changed_tasks_total > 10
        for: 0m
        labels:
          severity: info
          team: infrastructure
        annotations:
          summary: "High number of changes detected on {{ $labels.host }}"
          description: |
            {{ $value }} tasks changed on last run — possible configuration drift
            or a large update was applied.
```

---

## Playbook local.yml — Structure pour Pull Mode

```yaml
# playbooks/local.yml — playbook ciblant localhost uniquement
---
- name: Apply base configuration
  hosts: localhost
  connection: local    # Pas de SSH — exécution locale
  become: true
  gather_facts: true
  gather_subset:
    - min
    - network

  roles:
    - role: base-os
      tags: [base-os, always]
    - role: monitoring-agent
      tags: [monitoring]
    - role: firewall
      tags: [firewall, security]

  # Rôle conditionnel selon le groupe de l'hôte (via custom fact ou variable)
  tasks:
    - name: Apply webserver configuration
      include_role:
        name: nginx
      when: "'webserver' in group_names or ansible_local.host_role.role == 'webserver'"
      tags: [nginx, webserver]
```

---

## Gestion du Rollback en Pull Mode

**Stratégie 1 : Pin sur un tag git (recommandé)**
```bash
# Rollback = changer la variable ANSIBLE_PULL_BRANCH sur les nœuds
# Via AWS SSM Parameter Store (mis à jour depuis le controller)
aws ssm put-parameter \
    --name "/ansible/pull/branch" \
    --value "v2.3.9" \          # Revenir au tag précédent
    --type String \
    --overwrite

# Les nœuds liront le nouveau tag au prochain run de cron
# (max 15 min de délai si cron toutes les 15 min)
```

**Stratégie 2 : Playbook de rollback push d'urgence**
```yaml
# playbooks/operations/emergency-rollback.yml
---
- name: Emergency rollback — override ansible-pull branch
  hosts: "{{ target_hosts | default('all') }}"
  become: true
  tasks:
    - name: Update ansible-pull branch to rollback version
      lineinfile:
        path: /etc/ansible/pull.conf
        regexp: '^ANSIBLE_PULL_BRANCH='
        line: "ANSIBLE_PULL_BRANCH={{ rollback_version }}"

    - name: Trigger immediate ansible-pull run
      command: /usr/local/bin/ansible-pull-run
      async: 600
      poll: 30
```