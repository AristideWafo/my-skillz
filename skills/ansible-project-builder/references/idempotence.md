# Idempotence decisions

Read this reference when a second run changes unexpectedly or when using imperative commands.

## Diagnose the change

For each unexpected change, determine whether it comes from:

- a module receiving unstable input;
- a template with timestamps, random values, or nondeterministic ordering;
- a command without accurate `changed_when`;
- a service action executed directly instead of through a handler;
- an unpinned remote source;
- external state that changes between runs;
- check-mode behavior that differs from a real run.

## Prefer state descriptions

Use a module that describes the desired state when it represents the operation correctly. Do not replace a clear command with a complex module workaround solely to satisfy style.

For read-only commands:

```yaml
- name: Check service configuration
  ansible.builtin.command: /usr/bin/service --check-config
  register: service_config_check
  changed_when: false
```

For commands that may change state, derive `changed_when` from a reliable result and make reruns safe. `changed_when: false` is not a valid way to hide a mutation.

## Generated values

Generate credentials, tokens, or keys only when absent and store them in the approved secret system. Regenerating on every run is both non-idempotent and operationally dangerous.

## Service changes

Notify a handler only when configuration or package state changes. Validate configuration before the handler performs a disruptive action.

## Check mode

Support check mode when modules can predict changes accurately. When an operation cannot be simulated, state the limitation and avoid claiming that a dry-run proves safety.

## Validation

Run the affected play twice in an isolated or safe target. The second run should report no unexpected changes. For intentionally recurring operations, document the reason and test that repeated execution remains safe.
