# Variable placement and precedence

Read this reference when deciding where configuration belongs or diagnosing an override.

## Choose scope from ownership

| Scope | Use for |
|---|---|
| Role defaults | Public role inputs with safe defaults |
| Inventory group variables | Configuration shared by a real inventory group or environment |
| Inventory host variables | Exceptional host-specific configuration |
| Play variables/files | Values owned by a specific orchestration flow |
| Role variables | Internal constants callers should not override; use sparingly |
| Extra variables | Intentional operator override, not routine configuration storage |

Ansible can load `group_vars` and `host_vars` relative to inventories and playbooks. Choose deliberately: inventory-local placement improves environment isolation; playbook-local placement can be appropriate for orchestration-owned policy.

## Naming

Prefix role-owned public variables when collision is plausible. Use names that describe the domain rather than encoding one environment.

Keep sensitive values identifiable by placement and access control; a `vault_` prefix is a convention, not protection.

## Required values

Do not invent placeholder defaults for required secrets, identifiers, or endpoints. Validate required inputs near the start of the role or play, but avoid validation that runs during unrelated tagged operations.

## Precedence

Before changing a value, find every definition and determine which one wins for the affected host. Use `ansible-inventory --host` or `--graph --vars` when safe and applicable. Do not fix precedence problems by adding a higher-precedence duplicate unless that ownership is intentional.

## Structured data

Prefer one owned structure when fields change together. Avoid deep merge behavior unless the repository explicitly defines and tests it; implicit merges can make the final value hard to reason about.

## Version-dependent behavior

Variable precedence and plugin behavior can change across Ansible versions. Verify the repository's supported version and current official documentation before encoding a precedence table or plugin-specific assumption.

## Done

Each changed variable has a clear owner and scope, the effective value is verified for representative hosts, secrets are not exposed, and no accidental duplicate definition remains.
