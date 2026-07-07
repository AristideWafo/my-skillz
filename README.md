# my-skillz

A Copilot skills repository to frame DevOps/SRE/Platform tasks with Senior/Staff-level standards.

This repository contains reusable skills, each with:
- a `SKILL.md` file (role, scope, triggers, method, standards)
- references in `references/` (patterns, anti-patterns, examples)

## Purpose

Provide a clear framework to:
- produce more consistent and actionable outputs
- enforce technical standards (security, idempotence, maintainability)
- avoid generic or out-of-context responses

## Available Skills

- `ansible-project-builder/`: production-ready Ansible architecture (roles, inventories, variables, vault, CI/CD)
- `cicd-pipeline-builder/`: modern CI/CD design (build once, artifact promotion, DevSecOps gates)
- `docker-builder/`: hardened, optimized, and deployable Dockerfile/Compose patterns
- `grafana-dashboard-builder/`: Grafana dashboard creation and audit with a strict KISS approach
- `sre-observability-expert/`: incident diagnosis, observability, reliability, and performance
- `doc-coauthoring/`: documentation co-authoring guidance

## Repository Structure

```text
my-skillz/
├── README.md
├── <skill-name>/
│   ├── SKILL.md
│   └── references/
│       └── *.md
└── doc-coauthoring/
    └── doc-coauthoring.md
```

## Skill Convention

Each `SKILL.md` should include at least:
- YAML frontmatter: `name`, `description`
- when to trigger the skill (explicit triggers)
- working method (reasoning steps)
- non-negotiable rules
- common anti-patterns
- expected deliverables

Best practices:
- stay concrete and action-oriented
- prefer stable patterns over trendy tools
- separate theory (references) from execution method (`SKILL.md`)
- keep style and structure consistent across skills

## Add a New Skill

1. Create a `<new-skill>/` folder.
2. Add a `SKILL.md` file with frontmatter + standard sections.
3. Add a `references/` directory with short, targeted docs.
4. Ensure triggers do not overlap too much with existing skills.
5. Test the skill on 2-3 real prompts.

## Quality Checklist

- clear scope (what the skill does / does not do)
- explicit context assumptions
- verifiable recommendations
- reference sections easy to load on demand
- simple, unambiguous language

## License

This project is released under the `MIT` license. See `LICENSE`.
