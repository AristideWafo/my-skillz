# Référence : Sécurité Ansible

## Vault — Configuration Multi-Environnement

```bash
# Créer les vault passwords (générés aléatoirement, stockés dans SSM/Vault)
openssl rand -base64 32 > ~/.vault-pass-prod
openssl rand -base64 32 > ~/.vault-pass-staging
chmod 400 ~/.vault-pass-prod ~/.vault-pass-staging

# Chiffrer par environnement avec vault-id
ansible-vault encrypt \
    --vault-id production@~/.vault-pass-prod \
    inventories/production/group_vars/all/vault.yml

ansible-vault encrypt \
    --vault-id staging@~/.vault-pass-staging \
    inventories/staging/group_vars/all/vault.yml

# ansible.cfg — déclarer les vault IDs
[defaults]
vault_identity_list = production@~/.vault-pass-prod, staging@~/.vault-pass-staging
```

**Distribuer les vault passwords via SSM, jamais par email ou Slack :**
```bash
aws ssm put-parameter \
    --name "/ansible/vault-pass/production" \
    --value "$(cat ~/.vault-pass-prod)" \
    --type SecureString \
    --key-id "alias/ansible-secrets" \
    --region eu-west-1
```

---

## AWS Secrets Manager — Intégration

```yaml
# Lookup direct depuis un playbook ou un rôle
- name: Retrieve PostgreSQL password
  set_fact:
    postgresql_password: "{{ lookup('amazon.aws.aws_secret',
                                    'prod/postgresql/master-password',
                                    region='eu-west-1') }}"
  no_log: true    # OBLIGATOIRE

# Récupérer plusieurs secrets en une fois
- name: Retrieve application secrets
  set_fact:
    app_secrets: "{{ lookup('amazon.aws.aws_secret',
                             'prod/myapp/secrets',
                             region='eu-west-1',
                             return_content=true) | from_json }}"
  no_log: true
```

**Politique IAM pour le runner Ansible :**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": [
        "arn:aws:secretsmanager:eu-west-1:ACCOUNT:secret:prod/*",
        "arn:aws:ssm:eu-west-1:ACCOUNT:parameter/ansible/*"
      ]
    }
  ]
}
```

---

## HashiCorp Vault — Intégration

```yaml
# Authentification via AWS IAM (recommandé — zéro token statique)
- name: Retrieve secret from HashiCorp Vault
  set_fact:
    db_password: "{{ lookup('community.hashi_vault.hashi_vault',
                             'secret/data/prod/postgresql/password',
                             auth_method='aws_iam',
                             role='ansible-runner',
                             url='https://vault.internal:8200') }}"
  no_log: true
```

```ini
# ansible.cfg — configuration globale Vault
[hashi_vault]
url             = https://vault.internal:8200
auth_method     = aws_iam
role_id         = ansible-runner
verify          = true                    # Toujours vérifier le certificat TLS
```

---

## `no_log` — Règles d'Application

```yaml
# OBLIGATOIRE sur toute tâche qui manipule des secrets

# 1. Tâches set_fact avec secrets
- set_fact:
    db_password: "{{ vault_db_password }}"
  no_log: true

# 2. Tâches de connexion à des services
- uri:
    url: https://api.example.com/endpoint
    headers:
      Authorization: "Bearer {{ api_token }}"
  no_log: true

# 3. Tâches de création d'utilisateurs avec mot de passe
- user:
    name: appuser
    password: "{{ vault_appuser_password | password_hash('sha512') }}"
  no_log: true

# 4. Tâches de configuration avec secrets inline
- template:
    src: config.yml.j2
    dest: /etc/myapp/config.yml
  no_log: true
  # Si le template contient des secrets, no_log sur le template lui-même
  # et surtout pas de diff: true sur cette tâche

# ATTENTION : no_log: true masque TOUT le output de la tâche en cas d'erreur.
# Sur les tâches complexes, wrapper avec un bloc pour capturer les erreurs sans exposer les secrets.
```

---

## SSH — Configuration Sécurisée

```ini
# ansible.cfg
[ssh_connection]
# Ne JAMAIS désactiver StrictHostKeyChecking en production
ssh_args = -C -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/ansible/known_hosts

# Utiliser un known_hosts partagé géré par le rôle base-os
# Pas de ~/.ssh/known_hosts personnel qui peut être corrompu ou absent en CI
```

**Gestion des clés SSH :**
```yaml
# roles/base-os/tasks/ssh.yml
---
# Clé SSH Ansible dédiée (ne pas réutiliser les clés personnelles)
- name: "base-os | Deploy ansible runner SSH authorized key"
  authorized_key:
    user: "{{ ansible_user }}"
    key: "{{ vault_ansible_runner_public_key }}"
    state: present
    exclusive: false    # Ne pas supprimer les autres clés existantes

# Rotation annuelle : créer une nouvelle clé, déployer, puis supprimer l'ancienne
```

---

## Permissions des Fichiers — Checklist

```yaml
# Vérifier les permissions sensibles via le rôle de hardening
- name: "security | Secure ansible configuration files"
  file:
    path: "{{ item.path }}"
    mode: "{{ item.mode }}"
    owner: "{{ item.owner | default('ansible') }}"
    group: "{{ item.group | default('ansible') }}"
  loop:
    - { path: "/etc/ansible/.vault-pass",  mode: "0400" }
    - { path: "/etc/ansible/ansible.cfg",  mode: "0640" }
    - { path: "/var/log/ansible",          mode: "0750" }
  loop_control:
    label: "{{ item.path }}"
```

---

## Audit — Traçabilité des Runs

```yaml
# Utiliser ARA pour l'audit complet
# Installation
pip install ara

# ansible.cfg
[defaults]
callback_plugins = $(python3 -m ara.setup.callback_plugins)
action_plugins   = $(python3 -m ara.setup.action_plugins)

[ara]
api_server        = https://ara.internal.company.com
api_timeout       = 30
api_username      = ansible-runner
api_password      = "{{ vault_ara_api_password }}"
default_labels    = ["environment={{ environment_name }}", "team={{ team_name }}"]
```

ARA enregistre automatiquement : qui a lancé le playbook, quels hôtes, quelles tâches ont changé, quel était le diff exact, durée, exit code.