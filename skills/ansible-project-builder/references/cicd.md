# Ansible validation in CI

Read this reference for Ansible-specific checks. Use the CI/CD skill when redesigning the wider delivery system.

## Version the toolchain

Pin or constrain Ansible, ansible-lint, Molecule, Python, drivers, collections, and roles in the project's dependency mechanism. Update them intentionally and review porting guides before changing supported major versions.

## Useful validation layers

Select the layers relevant to the change:

1. YAML parsing and repository formatting rules.
2. `ansible-playbook --syntax-check` with representative inventory and variables.
3. `ansible-lint` using the repository's configured profile.
4. Inventory parsing and representative effective-variable checks.
5. Molecule or role integration scenarios.
6. Check mode and diff against an isolated environment where modules support it.
7. A real first run and idempotence run in a disposable target.
8. A staged, bounded rollout with service verification.

Do not claim production readiness from lint and syntax checks alone.

## CI safety

- Do not expose vault credentials or cloud access to untrusted pull-request code.
- Pin third-party CI actions or workflow dependencies to reviewed immutable revisions.
- Keep production deployment separate from ordinary validation and require the intended authorization.
- Bound jobs with timeouts and retain useful failure evidence without publishing secrets.

## Molecule

Test observable role behavior: packages, files, permissions, service state, listeners, and idempotence. Avoid tests that merely duplicate the role's implementation line by line.

## Done

The pipeline proves affected content parses, follows configured rules, behaves correctly in representative targets, and fails safely. Report validations that require external inventory, credentials, or a production window.
