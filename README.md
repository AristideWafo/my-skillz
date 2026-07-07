# my-skillz

Repository de skills Copilot pour cadrer des taches DevOps/SRE/Platform avec un niveau Senior/Staff.

Ce depot contient des skills reutilisables, chacun avec:
- un fichier `SKILL.md` (role, scope, triggers, methode, standards)
- des references dans `references/` (patterns, anti-patterns, exemples)

## Objectif

Fournir un framework clair pour:
- produire des reponses plus coherentes et actionnables
- imposer des standards techniques (securite, idempotence, maintenabilite)
- eviter les reponses generiques ou hors contexte

## Skills disponibles

- `ansible-project-builder/`: architecture Ansible production-ready (roles, inventories, variables, vault, CI/CD)
- `cicd-pipeline-builder/`: design CI/CD moderne (build once, artifact promotion, DevSecOps gates)
- `docker-builder/`: Dockerfile et Compose durcis, optimises, et deployables
- `grafana-dashboard-builder/`: creation/audit de dashboards Grafana avec approche KISS
- `sre-observability-expert/`: diagnostic incident, observabilite, fiabilite, performance
- `doc-coauthoring/`: guide de co-redaction documentaire

## Structure du repo

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

## Convention d'un skill

Chaque `SKILL.md` devrait contenir au minimum:
- frontmatter YAML: `name`, `description`
- quand declencher le skill (triggers explicites)
- methode de travail (etapes de raisonnement)
- regles non negociables
- anti-patterns frequents
- livrables attendus

Bonnes pratiques:
- rester concret et orienter vers l'action
- preferer les patterns stables plutot que les outils a la mode
- separer la theorie (references) et la methode (SKILL.md)
- garder un style uniforme entre tous les skills

## Ajouter un nouveau skill

1. Creer un dossier `<nouveau-skill>/`.
2. Ajouter `SKILL.md` avec frontmatter + sections standard.
3. Ajouter `references/` avec docs courtes et ciblees.
4. Verifier que les triggers ne chevauchent pas trop les skills existants.
5. Tester le skill sur 2-3 prompts reels.

## Checklist qualite

- scope clair (ce que le skill fait / ne fait pas)
- hypothese de contexte explicite
- recommandations verifiables
- sections references faciles a charger a la demande
- langage simple, sans ambiguite

## Licence

Ce projet est distribue sous licence `MIT`. Voir `LICENSE`.
