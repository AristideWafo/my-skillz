---
name: cicd-pipeline-builder
description: >
  Guide and enforce Staff-level CI/CD pipeline design for Jerry (DevOps/Cloud Architect). Trigger whenever Jerry asks to create, review, audit, or improve any pipeline, delivery workflow, deployment strategy, or release process. Also trigger for: GitHub Actions or GitLab CI design, Java/Spring Boot/Docker/Terraform/Ansible pipelines, Blue-Green/Canary/Rolling deployments, GitOps with ArgoCD/FluxCD, artifact promotion, DevSecOps gates (SAST/Trivy/Cosign/Checkov), post-deployment validation, semantic versioning (Nyx), monorepo CI, or DORA metrics. Trigger even if Jerry just says "help me with my pipeline" or "how do I deploy this". Enforces: immutable artifacts, build-once, CI/CD separation, security-by-default, and production-readiness.
---

# CI/CD Pipeline Builder — Staff Engineer Standards

> Penser en **principes de livraison**, pas en outils.  
> La question centrale : *"Comment faire arriver un changement en production rapidement, de façon fiable, reproductible et sécurisée ?"*

---

## Évaluation initiale — Poser les bonnes questions d'abord

Avant tout design, **toujours évaluer le contexte** :

1. **Stack applicative** — Java/Spring Boot ? Node.js ? Go ? Multi-stack ?
2. **Target de déploiement** — ECS Fargate ? Kubernetes ? EC2 ? Lambda ? VPS ?
3. **Environnements** — Combien ? (dev/staging/prod ou plus ?)
4. **CI/CD platform** — GitHub Actions ? GitLab CI ? Jenkins ? autre ?
5. **Registry** — GHCR ? ECR ? DockerHub ? Harbor ?
6. **IaC** — Terraform/Terragrunt ? Pulumi ? CloudFormation ?
7. **Stratégie de déploiement cible** — Rolling ? Blue-Green ? Canary ?
8. **Maturité actuelle** — Existe-t-il un pipeline ? Quels gaps identifiés ?
9. **Contraintes** — Approbations manuelles requises ? Compliance SOC2/PCI ?
10. **Monorepo ou polyrepo ?** — Impacte fortement l'architecture pipeline.

Si plusieurs réponses sont inconnues, **recommander l'architecture la plus conservative** et documenter les hypothèses.

---

## Les 10 Règles Non Négociables

Ces règles s'appliquent quel que soit l'outil, le langage ou la cible :

| # | Règle | Pourquoi |
|---|---|---|
| 1 | **Une seule branche principale** (`main`) | Trunk-Based Development réduit le risque d'intégration |
| 2 | **Build une seule fois** | Garantit que ce qui est testé = ce qui est déployé |
| 3 | **Artefact immuable** | Jamais modifier un artefact après création |
| 4 | **Promouvoir l'artefact, pas rebuilder** | Même image de dev à prod |
| 5 | **CI et CD séparés** | CI produit l'artefact, CD le déploie |
| 6 | **Git est la source de vérité** | Tout état infrastructure décrit dans Git |
| 7 | **Sécurité intégrée, pas ajoutée après** | Shift-left security à chaque gate |
| 8 | **Validation automatique après déploiement** | Smoke test + health check systématiques |
| 9 | **Rollback simple et testé** | Le rollback doit être aussi automatisé que le deploy |
| 10 | **Mesurer pour améliorer** | DORA metrics, pas de feeling subjectif |

---

## Le Pattern Universel CI/CD

```
Developer → Git Push → Pull Request
                              ↓
                    ┌─────────────────────────────────────────┐
                    │               CI                        │
                    │  Lint → Test → Build → Security Scan    │
                    │  → Package Artifact → Publish Registry   │
                    └──────────────────┬──────────────────────┘
                                       ↓ Artifact versionné
                    ┌─────────────────────────────────────────┐
                    │               CD                        │
                    │  Deploy Dev → [Smoke Test]               │
                    │  → Deploy Staging → [Acceptance Test]    │
                    │  → [Approbation manuelle optionnelle]    │
                    │  → Deploy Prod → [Smoke Test + Monitor]  │
                    └─────────────────────────────────────────┘
```

**Règle de séparation CI/CD** : CI produit un artefact `backend:1.4.2`. CD prend cet artefact et le promeut à travers les environnements **sans jamais le reconstruire**.

---

## Artifact Promotion Pattern

```
Build image → backend:1.4.2
  ↓
Registry (GHCR / ECR)
  ↓
Deploy DEV    → Tests automatisés → ✅
  ↓
Deploy STAGING → Tests fonctionnels → ✅
  ↓
[Gate: Approbation manuelle]
  ↓
Deploy PROD → Smoke Test → Monitor
```

L'artefact est **identique** à chaque étape. Seule la configuration (env vars, secrets) change par environnement.

---

## Immutable Artifact Pattern

```yaml
# ❌ ANTI-PATTERN — modifier un conteneur en place
docker exec container apt install truc

# ✅ BON PATTERN — nouvelle image à chaque changement
docker build -t backend:1.4.3 .
docker push ghcr.io/org/backend:1.4.3
```

Corollaire : **jamais de `latest` en production**. Toujours un tag sémantique (`v1.4.2`, SHA commit, ou les deux).

---

## Stratégies de Déploiement

→ Détails complets dans `references/patterns.md`

| Stratégie | Rollback | Risque | Use Case |
|---|---|---|---|
| Rolling Update | Lent | Moyen | Kubernetes par défaut |
| Blue-Green | Instantané | Faible | Prod critique, zero-downtime |
| Canary | Auto-rollback | Très faible | Feature progressive, trafic partiel |
| Feature Flags | Immédiat (toggle) | Quasi nul | Découplement deploy/release |

**Recommandation par contexte** :
- **ECS Fargate** → Blue-Green avec CodeDeploy ou task replacement
- **Kubernetes** → Canary avec Argo Rollouts ou Flagger
- **VPS** → Blue-Green manuel ou Rolling simple
- **Lambda** → Traffic shifting (weighted aliases)

---

## Security Gates — DevSecOps

Chaque gate doit **bloquer** le pipeline si elle échoue :

```
SAST (Semgrep / SpotBugs)          → sur le code source
Dependency Scan (OWASP Dep-Check)  → sur les dépendances
Container Scan (Trivy)             → sur l'image Docker
IaC Scan (Checkov / tfsec)        → sur Terraform/Ansible
Image Signing (Cosign)             → après push en registry
DAST (OWASP ZAP)                   → sur l'env de staging
```

→ Configuration complète dans `references/security.md`

---

## Post-Deployment Validation — Pattern Obligatoire

Souvent oublié. Doit être **systématique** :

```bash
# Smoke test minimal — à adapter selon la stack
for i in 1 2 3; do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    https://api.example.com/actuator/health)
  
  if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "✅ Health check $i passed"
  else
    echo "❌ Health check $i failed (HTTP $HTTP_STATUS)"
    # Déclencher rollback automatique
    exit 1
  fi
  sleep 5
done
```

Pattern complet : `Deploy → Smoke Test (3x) → Health Check → Monitoring Validation → [Rollback si échec]`

---

## Pipelines par Stack Technique

→ Templates complets et prêts à l'emploi dans `references/pipelines.md`

| Stack | Section |
|---|---|
| Java / Spring Boot (GitHub Actions) | `pipelines.md#java-github-actions` |
| Docker générique | `pipelines.md#docker` |
| Terraform / Terragrunt | `pipelines.md#terraform` |
| Ansible | `pipelines.md#ansible` |
| GitOps (ArgoCD) | `pipelines.md#gitops-argocd` |
| Monorepo (path filtering) | `pipelines.md#monorepo` |
| Semantic Versioning (Nyx) | `pipelines.md#semver` |

---

## GitOps Pattern

Au lieu de `kubectl apply` dans le pipeline :

```
CI Pipeline
  ↓ Push image v1.4.2
  ↓ Met à jour le manifeste Kubernetes dans le repo Git
  ↓ (kustomize patch ou Helm values.yaml)
ArgoCD / FluxCD
  ↓ Détecte le changement dans le repo
  ↓ Synchronise le cluster automatiquement
  ↓ Health check post-sync
```

**Avantages** : auditabilité complète, rollback = `git revert`, environnement décrit entièrement dans Git.

---

## Secrets Management dans les Pipelines

```yaml
# ❌ ANTI-PATTERN — secrets en clair dans le workflow
env:
  DB_PASSWORD: "mysecretpassword"

# ✅ BON PATTERN — GitHub Actions Secrets + OIDC pour AWS
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions-role
    aws-region: eu-west-1
    # Pas de credentials statiques — OIDC uniquement

- name: Get secret from SSM
  run: |
    DB_PASSWORD=$(aws ssm get-parameter \
      --name /prod/db/password \
      --with-decryption \
      --query Parameter.Value \
      --output text)
    echo "::add-mask::$DB_PASSWORD"
```

**Règle** : Jamais de credentials statiques dans les variables d'environnement CI. OIDC + secret manager (AWS SSM, HashiCorp Vault) systématiquement.

---

## Pipeline Caching — Performance

```yaml
# Java / Maven
- uses: actions/cache@v3
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}

# Docker layers (BuildKit)
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

Le cache peut **diviser par 3** le temps de build. Toujours clé le cache sur le fichier de dépendances (`pom.xml`, `package-lock.json`, `go.sum`).

---

## DORA Metrics — Mesurer la Maturité

→ Détails et benchmarks dans `references/dora.md`

| Métrique | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment Frequency | On-demand | 1/semaine | 1/mois | < 1/mois |
| Lead Time for Changes | < 1 heure | < 1 jour | 1 sem–1 mois | > 1 mois |
| Change Failure Rate | < 5% | < 10% | 10–15% | > 15% |
| MTTR | < 1 heure | < 1 jour | < 1 semaine | > 1 sem |

*Source : DORA State of DevOps Report + DevOps Handbook (Kim, Humble, Debois)*

---

## Anti-patterns — Signal d'Alarme Immédiat

| Anti-pattern | Criticité | Correction |
|---|---|---|
| Rebuilder l'image à chaque env | 🔴 | Build once, promote everywhere |
| `latest` en production | 🔴 | Tags sémantiques versionnés |
| Credentials AWS statiques en CI | 🔴 | OIDC + IAM Role |
| Pas de smoke test post-déploiement | 🔴 | Ajouter health check + auto-rollback |
| CI et CD dans le même job | 🟠 | Séparer les workflows |
| Secrets dans les variables d'env | 🟠 | AWS SSM / Vault |
| Branches feature vivant > 1 semaine | 🟠 | Trunk-Based Development |
| `docker push :latest` uniquement | 🟠 | Tag `sha-${GITHUB_SHA::8}` + semver |
| Plan Terraform sans review | 🟠 | Gate manuel sur apply |
| Pas de cache CI | 🟡 | Maven/npm/Docker layer cache |
| Tests uniquement en local | 🟡 | Tests dans environnement isolé CI |
| Pipeline monolithique | 🟡 | Jobs parallèles par domaine |

---

## Checklist Avant Mise en Production

- [ ] Build produit un artefact unique avec tag versionné ?
- [ ] L'artefact n'est **jamais reconstruit** entre les environnements ?
- [ ] Credentials AWS via OIDC (pas de clés statiques) ?
- [ ] Trivy scan configuré et bloquant sur HIGH/CRITICAL ?
- [ ] Image signée avec Cosign ?
- [ ] Smoke test post-déploiement avec rollback automatique ?
- [ ] Variables par environnement (jamais hardcodées dans le pipeline) ?
- [ ] Pipeline idempotent (re-run sans effets de bord) ?
- [ ] Approbation manuelle avant prod ?
- [ ] Rollback documenté et testé ?
- [ ] DORA metrics instrumentées ?

---

## Ce que ce Skill Produit

Quand Jerry demande de créer ou améliorer un pipeline :

**Pipeline complet** — Workflow GitHub Actions ou GitLab CI prêt à copier, adapté à la stack, avec jobs parallèles, caches, security gates, et smoke tests.

**Review critique** — Audit du pipeline existant avec criticité (🔴/🟠/🟡) et correction concrète pour chaque gap.

**Architecture decision** — Choix de stratégie de déploiement justifié selon les contraintes (SLA, équipe, plateforme).

**Security upgrade** — Ajout des gates DevSecOps manquants dans un pipeline existant.

**DORA baseline** — Identification des métriques à instrumenter et objectifs réalistes.