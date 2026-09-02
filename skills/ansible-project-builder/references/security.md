# Ansible security decisions

Read this reference for credentials, privilege escalation, remote content, or sensitive output.

## Secrets

- Reuse the repository's approved secret manager or Ansible Vault convention.
- Keep vault passwords, tokens, private keys, decrypted files, and temporary credentials outside version control.
- Limit secret access by environment and role; do not share one broad credential merely for convenience.
- Use `no_log: true` when task arguments or results contain secrets, but remember that it also hides debugging evidence.
- Avoid persisting secrets with `set_fact` unless their lifecycle and cache behavior are understood.

## Privilege

Set `become` at the narrowest practical scope. Use an unprivileged connection user and grant only required escalation commands where the platform supports it.

Explicitly set owner, group, and mode for sensitive files. Account for umask and temporary-file behavior on the controller and target.

## Remote content

- Pin collections, roles, packages, archives, and Git revisions according to the project's update policy.
- Verify downloaded artifacts with signatures or checksums when integrity matters.
- Treat templates and variables from untrusted contributions as code that can influence commands and file paths.
- Quote and validate values passed to shells; prefer `command` with argument lists or modules when suitable.

## Inventory and logs

Inventories can reveal topology, usernames, internal addresses, and group membership. Apply repository and artifact access controls accordingly. Ensure CI artifacts and diffs do not publish decrypted variables.

## Destructive operations

Before deletion, rotation, revocation, database change, or fleet-wide restart, identify the exact target set, backup or recovery path, batch size, and authorization. Use `--limit`, serial execution, and confirmation gates when they reduce real risk.

## Validation

Review the diff for credentials and overbroad privilege, test with the intended execution identity, verify secret lookups without printing values, and confirm cleanup of decrypted or temporary material.
