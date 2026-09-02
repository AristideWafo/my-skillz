# Ansible role decisions

Read this reference when creating or refactoring a role.

## Boundary

A role should own one coherent capability with a stable input contract. Split a role when components have independent lifecycle, ownership, or reuse; keep them together when separation would only add indirection.

Preserve a repository's coherent role layout. Common directories such as `tasks`, `handlers`, `defaults`, `vars`, `templates`, `files`, `meta`, and `molecule` are optional unless the role uses them.

## Entrypoint

Keep `tasks/main.yml` readable. Split task files when categories are independently understandable or conditionally included; do not create one-file-per-task layouts.

Prefer static imports when the task graph should be parsed predictably. Use dynamic includes when runtime conditions genuinely choose content.

## Inputs

- Define caller-configurable inputs in `defaults/main.yml`.
- Validate only required or safety-critical constraints.
- Explain the input and failure rather than exposing a raw expression.
- Avoid `tags: always` on validation that should not run for unrelated operations.

```yaml
- name: Validate listener settings
  ansible.builtin.assert:
    that:
      - web_listen_port | int >= 1
      - web_listen_port | int <= 65535
    fail_msg: web_listen_port must be between 1 and 65535
```

## Handlers

Handlers run in definition order. Validate before reload or restart, or validate in the changing task before notification.

```yaml
- name: Deploy service configuration
  ansible.builtin.template:
    src: service.conf.j2
    dest: /etc/service/service.conf
    owner: root
    group: root
    mode: "0644"
    validate: /usr/bin/service --check-config %s
  notify: Reload service

handlers:
  - name: Reload service
    ansible.builtin.service:
      name: service
      state: reloaded
```

Use unique handler names or `listen` topics when several roles can notify related operations.

## Dependencies

Declare role dependencies only when the dependent role must always run. Prefer explicit playbook composition when ordering varies by use case.

## Done

The role has a clear boundary, documented inputs, no hidden environment assumptions, safe handler behavior, an idempotence check, and tests proportional to its impact.
