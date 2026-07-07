---
name: ansible-project-builder
description: >
  Guide and enforce Senior/Staff-level Ansible project architecture, structure, and patterns for <Skills user> (Cloud Architect/DevOps at Societe Generale, EPITECH Master Cloud). Use this skill whenever <Skills user> asks to create, review, scaffold, refactor, or audit any Ansible project, playbook, role, inventory, variable structure, CI/CD pipeline, or Ansible Pull architecture. Also trigger for: structuring a new Ansible repo, reviewing an existing one, writing a role, deciding between push vs pull mode, designing variable hierarchies, setting up Molecule tests, configuring vault, or designing a CI/CD pipeline for Ansible. Trigger even if <Skills user> just says "set up ansible for my project" or "help me with my ansible role" - do not wait for explicit architectural language. This skill enforces Staff Engineer standards: idempotence, security, scalability to 500+ hosts, multi-environment separation, and long-term maintainability.
---

# Ansible Project Builder - Staff Engineer Standards

> Reference for intermediate-to-advanced engineers targeting Senior/Staff practices.
> Context: <Skills user> - Cloud Architect/DevOps @SG, AWS/Azure multi-cloud, multi-host, multi-environment projects.

---

## Reading an Existing Project - Selective Approach

Before reading files from a provided project:
1. Build the inventory map (which groups, which hosts)
2. Identify roles impacted by the request
3. Read only those roles (not all roles in the project)
4. Load only relevant variables (group_vars for the impacted group)
5. Ignore unrelated playbooks

---

## Initial Assessment - Ask the Right Questions First

Before scaffolding or advising, always assess context:

1. Scope - Number of target hosts? (< 20 / 20-200 / 200+)
2. Mode - Push (centralized controller) or Pull (ansible-pull via cron)?
3. Environments - How many? (dev/staging/prod or more complex?)
4. Team - Solo or multiple contributors?
5. Secrets - AWS SSM / HashiCorp Vault / file-based Ansible Vault?
6. CI/CD - GitHub Actions / GitLab CI / other?
7. Current maturity - Existing structure to review or greenfield project?

If several answers are unknown, scaffold the most conservative structure (multi-inventory, granular roles, vault per environment) and document assumptions.

---

## Project Structure - The Reference

Use this structure systematically. Do not deviate without explicit justification.

```text
infrastructure/
├── ansible.cfg                         # Documented global config
├── requirements.yml                    # Collections + roles, PINNED versions
│
├── inventories/
│   ├── production/
│   │   ├── hosts.yml                   # YAML only (never INI)
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── main.yml            # Universal vars, no secrets
│   │   │   │   └── vault.yml           # Encrypted secrets
│   │   │   └── <group>/
│   │   │       ├── main.yml
│   │   │       └── vault.yml
│   │   └── host_vars/
│   │       └── <hostname>/
│   │           ├── main.yml
│   │           └── vault.yml
│   ├── staging/                        # Same exact structure
│   └── development/                    # Same exact structure
│
├── playbooks/
│   ├── site.yml                        # Import-only, ZERO logic
│   ├── <domain>.yml                    # Ex: webservers.yml, databases.yml
│   └── operations/
│       ├── rotate-secrets.yml
│       ├── patch-os.yml
│       └── drain-node.yml
│
├── roles/
│   └── <rolename>/                     # See role structure below
│
├── plugins/
│   ├── filter/                         # Custom Jinja2 filters
│   ├── lookup/                         # Custom lookups
│   └── callback/                       # Reporting, Slack, ARA
│
└── tests/
    └── molecule/
```

Absolute rule: group_vars and host_vars must be inside the inventory, never at project root. A root-level group_vars directory means shared state across environments and is a critical anti-pattern.

---

## Role Structure - The Reference

```text
roles/<rolename>/
├── defaults/main.yml     # ALL configurable variables with defaults
├── files/                # Static files (no templating)
├── handlers/main.yml     # Handlers only
├── meta/main.yml         # Dependencies, OS compatibility, galaxy_info
├── tasks/
│   ├── main.yml          # Imports only - import_tasks by category
│   ├── validate.yml      # Validation assertions (tags: always)
│   ├── install.yml
│   ├── configure.yml
│   └── service.yml
├── templates/            # Jinja2 files
├── tests/molecule/
└── vars/main.yml         # Internal constants ONLY (rare usage)
```

For detailed component logic, see references/roles.md

---

## Variables - Non-Negotiable Rules

Naming convention:
```yaml
# Always prefix with role name
nginx_listen_port: 80               # Public variable
nginx_ssl_enabled: true
__nginx_config_path: "/etc/nginx"  # Role-private variable

# Vault secrets: vault_ prefix
vault_nginx_ssl_cert: "..."

# Custom facts: fact_ prefix
nginx_fact_version: "1.24"
```

defaults vs vars rule:
- defaults/main.yml: everything that should be externally configurable (99% of cases)
- vars/main.yml: constants that should never be changed (rare, ex: fixed system paths)

Required role input validation:
```yaml
# tasks/validate.yml - always imported with tags: always
- name: "{{ role_name }} | Validate required variables"
  assert:
    that:
      - rolename_var is defined
      - rolename_var | length > 0
    fail_msg: "rolename_var is required. See role README."
  tags: always
```

For full variable precedence order and edge cases, see references/variables.md

---

## Idempotence - Zero-Changed Standard

Test: a full second run must produce 0 changed. If not, it is not production-acceptable.

```yaml
# Rule: every command/shell task must define changed_when explicitly
- name: Check nginx config
  command: nginx -t
  changed_when: false               # Never changes system state
  failed_when: result.rc != 0

# Rule: prefer declarative modules
- name: Ensure directory exists     # file > command mkdir
  file:
    path: /opt/myapp
    state: directory
    mode: "0755"
    owner: "{{ app_user }}"
```

Common idempotence anti-patterns: see references/idempotence.md

---

## Handlers - The Most Dangerous Trap

```yaml
# ALWAYS use listen to avoid cross-role collisions
handlers:
  - name: "nginx | reload configuration"
    service:
      name: nginx
      state: reloaded               # reload > restart (zero-downtime)
    listen: "nginx config changed"

  - name: "nginx | validate before reload"
    command: nginx -t
    changed_when: false
    listen: "nginx config changed" # Runs first because of handler order

# In tasks:
- name: Deploy nginx config
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify: "nginx config changed"
```

---

## Security - Mandatory Standards

Vault per environment:
```bash
# Different vault IDs per env - never one global vault password
ansible-vault encrypt --vault-id prod@~/.vault-pass-prod inventories/production/group_vars/all/vault.yml
ansible-vault encrypt --vault-id staging@~/.vault-pass-staging inventories/staging/group_vars/all/vault.yml
```

AWS SSM secrets (recommended for AWS infra):
```yaml
- name: Get secret from SSM
  set_fact:
    db_password: "{{ lookup('amazon.aws.aws_ssm', '/prod/db/password', region='eu-west-1') }}"
  no_log: true   # REQUIRED on every task handling secrets
```

Use no_log: true on any task handling secrets. No exceptions.

For HashiCorp Vault integration and SSH key management, see references/security.md

---

## Performance - ansible.cfg Settings

```ini
[defaults]
forks              = 50
# Default 5 is too slow for 50+ hosts
gather_facts       = false
# Disable by default, enable explicitly when needed
fact_caching       = redis
# Cache facts to avoid reconnecting every run
fact_caching_connection = redis://redis-internal:6379/0
fact_caching_timeout = 3600

[ssh_connection]
pipelining         = true
# 3x-5x faster (fewer SSH round-trips)
ssh_args           = -C -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=yes
```

For serial, strategy, and async tuning on 200+ hosts, see references/performance.md

---

## CI/CD - Minimum Acceptable Pipeline

```text
Lint (yamllint + ansible-lint)
  -> Molecule tests (per role, OS matrix)
    -> Dry-run --check --diff (staging)
      -> Deploy staging
        -> Manual approval
          -> Deploy production (rolling)
```

ansible-lint config (.ansible-lint):
```yaml
profile: production
skip_list:
  - yaml[line-length]
exclude_paths:
  - molecule/
```

For a complete GitHub Actions workflow and Molecule config, see references/cicd.md

---

## Ansible Pull - Specific Architecture

Use Pull mode when:
- 200+ identical nodes (autoscaling groups, edge nodes)
- No inbound SSH allowed
- Automatic config drift remediation is required

Pull critical points:
- Lock file required (avoid concurrent runs)
- Secrets via AWS SSM or IAM role (never vault files in repo)
- Target a versioned git tag, never main in production
- Monitoring: alert if last_success > 1 hour

For full wrapper script and Pull monitoring architecture, see references/ansible-pull.md

---

## Content Generation - What This Skill Produces

When <Skills user> asks to create or scaffold, produce:

### Full project scaffold
Create full tree with commented starter files, ansible.cfg, requirements.yml, site.yml, a base inventory, and a common role skeleton.

### Full role
All role files (defaults, split tasks, handlers, meta, templates, molecule) with concrete domain examples (nginx, postgresql, monitoring agent, etc.).

### Critical review
Audit provided structure and list anti-patterns with severity (Critical / Important / Recommended) and concrete fixes.

### Operations playbook
Targeted playbook with tags, serial, post-deployment validation, and built-in rollback.

---

## Anti-Patterns - Immediate Red Flags

Report as soon as detected, with severity and correction:

| Anti-pattern | Severity | Action |
|---|---|---|
| group_vars at project root | Critical | Move to inventories/<env>/group_vars/ |
| Variables without role prefix | Critical | Rename with <rolename>_ |
| Plain-text secrets in repo | Critical | Vault + secret manager immediately |
| vars/main.yml used for public configs | Critical | Move to defaults/main.yml |
| command/shell without changed_when | Important | Add changed_when: false or condition |
| Single vault password for all envs | Important | One vault ID per environment |
| Logic in site.yml | Important | Import-only; logic belongs in roles |
| ansible-pull -C main in production | Important | Target a versioned tag |
| forks = 5 on 50+ hosts | Recommended | Raise to at least 50 |
| Missing pipelining = true | Recommended | Enable in ansible.cfg |
| No Molecule tests for roles | Recommended | Add molecule skeleton |
| Generic handler names | Recommended | Prefix with role name + listen |

Full list of 50 anti-patterns: see references/anti-patterns.md

---

## Quick Pre-Commit Checklist

- [ ] Second playbook run -> 0 changed?
- [ ] All variables use a role prefix?
- [ ] No plain-text secrets (git grep -i password)?
- [ ] changed_when on all command/shell tasks?
- [ ] no_log: true on all secret-handling tasks?
- [ ] Tags present on tasks?
- [ ] Handlers use listen with qualified names?
- [ ] meta/main.yml filled in?
- [ ] Molecule tests pass locally?
- [ ] ansible-lint passes with production profile?
