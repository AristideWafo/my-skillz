# Patterns CI/CD — Référence Architecturale

## Table of Contents

- [Trunk Based Development](#trunk-based-development)
- [Artifact Promotion détaillé](#artifact-promotion)
- [Blue-Green Deployment](#blue-green)
- [Canary Deployment](#canary)
- [Progressive Delivery](#progressive-delivery)
- [Feature Flags](#feature-flags)
- [GitOps avancé](#gitops-avance)
- [Ephemeral Environments](#ephemeral-environments)
- [Database Migrations en CD](#database-migrations)
- [Rollback Strategies](#rollback)
- [Pipeline Gates](#pipeline-gates)
- [Reusable Workflows](#reusable-workflows)

---

## Trunk Based Development {#trunk-based-development}

**Le standard actuel** — validé par Google, Facebook, Netflix.

```
# ✅ BON
main
  ↑ PR (durée : 1-3 jours max)
feature/login-oauth
feature/payment-stripe

# ❌ ANTI-PATTERN — Git flow classique
release/2.4
develop
integration
qa
hotfix/critical-bug
feature/login-oauth  ← vivant depuis 3 semaines
```

**Règles Trunk-Based** :
1. Une seule branche principale (`main` / `trunk`)
2. Feature branches courtes : **< 2 jours idéalement, 1 semaine maximum**
3. Feature incomplète ? → Feature Flag, pas une longue branche
4. Pas de `develop`, `staging`, `release` branches persistantes
5. Tags Git pour les versions, pas des branches

**Commit Conventional** (requis pour semantic versioning) :
```
feat(auth): implement JWT refresh token rotation
fix(api): handle null response in payment service
feat!: drop support for API v1 (BREAKING CHANGE)
chore(ci): add Trivy scan to pipeline
docs(readme): update deployment instructions
perf(db): add index on users.email column
```

---

## Artifact Promotion détaillé {#artifact-promotion}

```
╔══════════════════════════════════════════════════════════════╗
║  CI  │  Build image backend:1.4.2                            ║
║      │  → Run unit tests against image                        ║
║      │  → Trivy scan → Cosign sign                            ║
║      │  → Push to Registry (GHCR / ECR)                       ║
╠══════════════════════════════════════════════════════════════╣
║  DEV │  Deploy backend:1.4.2                                  ║
║      │  → Integration tests (automatisés)                      ║
║      │  → Smoke test                                           ║
║      │  → ✅ Promoted to: STAGING                              ║
╠══════════════════════════════════════════════════════════════╣
║  STG │  Deploy backend:1.4.2 (même image)                      ║
║      │  → Acceptance tests (Cypress / Playwright)              ║
║      │  → Performance test (k6 / Gatling)                      ║
║      │  → Security DAST (OWASP ZAP)                            ║
║      │  → ✅ Promoted to: PRODUCTION (gate manuel)             ║
╠══════════════════════════════════════════════════════════════╣
║ PROD │  Deploy backend:1.4.2 (même image)                      ║
║      │  → Smoke test prod                                       ║
║      │  → Monitoring 15min (error rate, latency, saturation)   ║
║      │  → ✅ Release confirmée                                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Tagging strategy** :
```bash
# Tags appliqués à la même image
backend:sha-a1b2c3d4          # Immutable, toujours disponible
backend:1.4.2                  # Semantic version
backend:1.4                    # Floating minor
backend:latest                 # ⚠️ Seulement pour dev, jamais en prod

# En production, toujours déployer par digest SHA256
ghcr.io/org/backend@sha256:abc123...
```

---

## Blue-Green Deployment {#blue-green}

**Principe** : deux environnements de production identiques. Seul le load balancer bascule.

```
             Load Balancer
                  │
        ┌─────────┴─────────┐
        ↓                   ↓
  ┌──────────┐        ┌──────────┐
  │  BLUE    │        │  GREEN   │
  │ v1.3.0  │        │ v1.4.2   │
  │ (LIVE)   │        │ (STANDBY)│
  └──────────┘        └──────────┘

Étapes :
1. GREEN = déployer v1.4.2 (pas encore de trafic)
2. Smoke test sur GREEN via URL interne
3. Basculer LB : Blue → Green (0 downtime)
4. Monitor Green pendant 15-30 min
5. Si problème : rollback LB vers Blue en < 30 secondes
6. Si OK : Blue devient le nouveau standby
```

**Sur ECS Fargate avec CodeDeploy** :

```yaml
# appspec.yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: backend
          ContainerPort: 8080
        PlatformVersion: LATEST
Hooks:
  - BeforeAllowTraffic: "ValidateBeforeTraffic"    # Lambda health check
  - AfterAllowTraffic: "ValidateAfterTraffic"       # Smoke test post-bascule
```

**Sur Kubernetes avec `kubectl` ou ArgoCD** :

```yaml
# Service pointe vers Blue (label selector)
apiVersion: v1
kind: Service
metadata:
  name: backend-prod
spec:
  selector:
    app: backend
    slot: blue    # ← Changer en 'green' pour basculer
  ports:
    - port: 8080
```

---

## Canary Deployment {#canary}

**Principe** : déployer progressivement à un sous-ensemble d'utilisateurs/trafic.

```
          Load Balancer / Ingress
               │
     ┌─────────┴──────────┐
     ↓                    ↓
  ┌──────────┐      ┌──────────┐
  │  STABLE  │      │  CANARY  │
  │ v1.3.0   │      │ v1.4.2   │
  │  95%     │      │   5%     │
  └──────────┘      └──────────┘

Progression :
  5% → Monitor (error rate, latency, p99) → OK ?
    20% → Monitor → OK ?
      50% → Monitor → OK ?
        100% → Promotion complète
```

**Avec Argo Rollouts** :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: backend
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 10m}
        - setWeight: 25
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: backend-canary
        - setWeight: 50
        - pause: {duration: 15m}
        - setWeight: 100
      canaryService: backend-canary
      stableService: backend-stable
      trafficRouting:
        istio:
          virtualService:
            name: backend-vsvc
---
# AnalysisTemplate — rollback automatique si error rate > 5%
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: success-rate
      interval: 2m
      successCondition: result[0] >= 0.95
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[2m]))
            /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[2m]))
```

---

## Progressive Delivery {#progressive-delivery}

Extension du Canary avec des métriques automatiques de go/no-go.

**Stack recommandée** :
- Kubernetes + Argo Rollouts (ou Flagger)
- Prometheus + Grafana pour les métriques
- Istio ou Linkerd pour le traffic splitting

**Métriques surveillées** :
```
Latence p99 < 200ms         → OK
Error rate (5xx) < 1%       → OK
CPU < 80%                   → OK
Memory < 85%                → OK
Custom business metric      → OK (ex: transactions/min)

Si une métrique échoue → rollback automatique vers stable
```

---

## Feature Flags {#feature-flags}

**Découpler déploiement et release** — le pattern le plus puissant pour le risque.

```
Deploy v1.4.2 (feature_payment_v2 = false par défaut)
    ↓
Activer pour 5% des users (staff d'abord)
    ↓
Monitor métriques business
    ↓
Activer pour 25%... 50%... 100%
    ↓
Cleanup : supprimer le flag du code
```

**Outils** :
- Open source : Unleash, Flagsmith, OpenFeature
- Cloud : LaunchDarkly, AWS AppConfig, Split.io

**Exemple Spring Boot** :

```java
@Service
public class PaymentService {
    
    @Autowired
    private Unleash unleash;
    
    public PaymentResult processPayment(PaymentRequest request) {
        if (unleash.isEnabled("payment-v2", UnleashContext.builder()
                .userId(request.getUserId())
                .build())) {
            return paymentV2Processor.process(request);  // Nouvelle logique
        }
        return legacyPaymentProcessor.process(request);  // Ancienne logique
    }
}
```

---

## GitOps avancé {#gitops-avance}

**Repository structure recommandée** :

```
k8s-manifests/
├── base/                        # Manifestes de base (Kustomize)
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml   # Patches dev (replicas=1, resources faibles)
│   │   └── patch-image.yaml
│   ├── staging/
│   │   └── kustomization.yaml   # Patches staging
│   └── production/
│       └── kustomization.yaml   # Patches prod (replicas=3, PDB, HPA)
└── argocd-apps/
    ├── backend-dev.yaml
    ├── backend-staging.yaml
    └── backend-prod.yaml
```

**Stratégie multi-repo** :
- **App repo** : source code → CI produit l'image
- **GitOps repo** : manifestes K8s → ArgoCD synchronise

**ApplicationSet (ArgoCD) — multi-env automatique** :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: backend-all-envs
spec:
  generators:
    - list:
        elements:
          - env: dev
            cluster: dev-cluster
            namespace: backend-dev
          - env: staging
            cluster: staging-cluster
            namespace: backend-staging
          - env: prod
            cluster: prod-cluster
            namespace: backend-prod
  template:
    metadata:
      name: 'backend-{{env}}'
    spec:
      source:
        repoURL: https://github.com/org/k8s-manifests
        targetRevision: main
        path: 'overlays/{{env}}'
      destination:
        server: '{{cluster}}'
        namespace: '{{namespace}}'
```

---

## Ephemeral Environments {#ephemeral-environments}

**Preview environments par Pull Request** — très utilisé pour les reviews.

```yaml
# .github/workflows/preview.yml
name: Preview Environment

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy preview
        run: |
          PREVIEW_URL="https://pr-${{ github.event.number }}.preview.example.com"
          
          # Déployer avec un namespace K8s isolé
          kubectl create namespace pr-${{ github.event.number }} --dry-run=client -o yaml | kubectl apply -f -
          
          helm upgrade --install \
            backend-pr-${{ github.event.number }} ./charts/backend \
            --namespace pr-${{ github.event.number }} \
            --set image.tag=${{ github.sha }} \
            --set ingress.host=pr-${{ github.event.number }}.preview.example.com

      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: ${{ github.event.number }},
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚀 Preview environment deployed: https://pr-${{ github.event.number }}.preview.example.com'
            });

  cleanup-preview:
    if: github.event.action == 'closed'
    runs-on: ubuntu-latest
    steps:
      - name: Destroy preview
        run: |
          kubectl delete namespace pr-${{ github.event.number }} --ignore-not-found
```

---

## Database Migrations en CD {#database-migrations}

**Pattern Expand-Contract** — le seul safe pour zero-downtime :

```
Phase 1 — EXPAND (compatible avec old + new code)
  → Ajouter la nouvelle colonne nullable
  → Ajouter le nouveau endpoint

Phase 2 — MIGRATE (data migration)
  → Backfill les données existantes
  → Les deux colonnes coexistent

Phase 3 — CONTRACT (après que l'ancien code est retiré)
  → Supprimer l'ancienne colonne
  → Supprimer l'ancien endpoint
```

**Avec Flyway (Spring Boot)** :

```yaml
# Dans le pipeline, AVANT le déploiement
- name: Run database migrations
  run: |
    ./gradlew flywayMigrate \
      -Dflyway.url=${{ secrets.DB_URL }} \
      -Dflyway.user=${{ secrets.DB_USER }} \
      -Dflyway.password=${{ secrets.DB_PASSWORD }}
      
# TOUJOURS : migrations avant code, rollback si échec
```

---

## Rollback Strategies {#rollback}

**Priorité : rollback doit être aussi simple que le déploiement.**

| Stratégie | Vitesse | Comment |
|---|---|---|
| Load balancer bascule (Blue-Green) | < 30s | Pointer LB vers l'env stable |
| Feature flag off | < 5s | Toggle le flag |
| `git revert` + pipeline | 5-10 min | Si GitOps actif |
| ECS: previous task definition | 2-3 min | `aws ecs update-service --task-definition :PREVIOUS` |
| K8s: `kubectl rollout undo` | 1-2 min | Rollback au ReplicaSet précédent |
| Helm: `helm rollback` | 1-2 min | `helm rollback backend 1` |

**Rollback automatique — script** :

```bash
#!/usr/bin/env bash
# auto-rollback.sh — à appeler si smoke test échoue

set -euo pipefail

SERVICE="${1:?Service name required}"
CLUSTER="${2:?Cluster name required}"
MAX_WAIT=300

echo "🔄 Initiating rollback for $SERVICE in $CLUSTER..."

# Récupérer la task definition précédente
CURRENT_TASK=$(aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].taskDefinition' \
  --output text)

TASK_FAMILY=$(echo "$CURRENT_TASK" | cut -d'/' -f2 | cut -d':' -f1)
CURRENT_REVISION=$(echo "$CURRENT_TASK" | cut -d':' -f2)
PREVIOUS_REVISION=$((CURRENT_REVISION - 1))

echo "Current: $TASK_FAMILY:$CURRENT_REVISION"
echo "Rolling back to: $TASK_FAMILY:$PREVIOUS_REVISION"

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$TASK_FAMILY:$PREVIOUS_REVISION" \
  --force-new-deployment

aws ecs wait services-stable \
  --cluster "$CLUSTER" \
  --services "$SERVICE"

echo "✅ Rollback completed successfully"
```

---

## Pipeline Gates {#pipeline-gates}

**Gates = points de contrôle qui bloquent la progression si les critères ne sont pas atteints.**

```
AUTOMATIC GATES (bloquants, pas d'intervention humaine) :
├── Tests passed (unit + integration)
├── Security scan clean (Trivy, Semgrep)
├── Coverage > seuil (ex: 80%)
├── Performance baseline non dégradée
└── Smoke test post-déploiement

MANUAL GATES (approbation humaine requise) :
├── Déploiement en production (toujours)
├── Déploiement en semaine de peak (ex: Black Friday)
└── Changements breaking (DB schema, API contracts)

SCHEDULED GATES (fenêtres de maintenance) :
└── Maintenance window : ex: prod uniquement entre 22h-06h
```

**GitHub Environments pour gates manuels** :

```yaml
deploy-prod:
  environment:
    name: production
    url: https://api.example.com
  # GitHub bloque ici si required reviewers n'ont pas approuvé
  # Configurer dans Settings > Environments > protection rules
```

---

## Reusable Workflows {#reusable-workflows}

**DRY principle pour les pipelines** — un workflow central, tous les projets l'appellent.

**Workflow central** : `.github/workflows/build-java.yml` dans le repo `org/.github`

```yaml
# Reusable workflow (appelé depuis d'autres repos)
on:
  workflow_call:
    inputs:
      service:
        type: string
        required: true
      java-version:
        type: string
        default: '21'
      registry:
        type: string
        default: 'ghcr.io'
    secrets:
      REGISTRY_TOKEN:
        required: true
    outputs:
      image-digest:
        description: "Published image digest"
        value: ${{ jobs.build.outputs.digest }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      # ... pipeline standardisé
```

**Appel depuis un projet** :

```yaml
jobs:
  ci:
    uses: org/.github/.github/workflows/build-java.yml@main
    with:
      service: payment-service
      java-version: '21'
    secrets:
      REGISTRY_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Avantages** : mise à jour du pipeline en un seul endroit pour tous les projets.