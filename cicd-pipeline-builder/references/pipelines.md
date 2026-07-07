# Pipelines Reference — Templates Production-Ready

## Table of Contents

- [Java / Spring Boot — GitHub Actions](#java-github-actions)
- [Docker générique](#docker)
- [Terraform / Terragrunt](#terraform)
- [Ansible](#ansible)
- [GitOps — ArgoCD](#gitops-argocd)
- [Monorepo (path filtering)](#monorepo)
- [Semantic Versioning (Nyx)](#semver)
- [GitLab CI — Java](#gitlab-java)

---

## Java / Spring Boot — GitHub Actions {#java-github-actions}

Architecture : `CI workflow` (build + test + publish) + `CD workflow` (deploy par env).

### CI Workflow — `.github/workflows/ci.yml`

```yaml
name: CI — Build & Publish

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─────────────────────────────────────────────────
  # JOB 1 : Tests & Code Quality
  # ─────────────────────────────────────────────────
  test:
    name: Test & Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Java 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'  # ou 'maven'

      - name: Run tests
        run: ./gradlew test --parallel

      - name: SAST — Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: "p/java"

      - name: Dependency vulnerability scan
        run: ./gradlew dependencyCheckAnalyze
        # OWASP Dependency Check via Gradle plugin
        continue-on-error: false

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-reports
          path: build/reports/tests/

  # ─────────────────────────────────────────────────
  # JOB 2 : Build Artifact (conditionnel — main uniquement)
  # ─────────────────────────────────────────────────
  build:
    name: Build & Push Image
    runs-on: ubuntu-latest
    needs: [test]
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
      id-token: write    # OIDC pour signing Cosign

    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-tag: ${{ steps.meta.outputs.tags }}
      version: ${{ steps.semver.outputs.version }}

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # Requis pour Nyx / git history

      - name: Setup Java 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Build JAR
        run: ./gradlew bootJar --no-daemon

      - name: Semantic Versioning (Nyx)
        id: semver
        run: |
          ./gradlew nyxInfer
          VERSION=$(./gradlew nyxShow -q | grep "version:" | awk '{print $2}')
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Setup Docker BuildKit
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-
            type=semver,pattern={{version}},value=${{ steps.semver.outputs.version }}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build and Push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          platforms: linux/amd64,linux/arm64    # Multi-arch
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true    # SLSA provenance attestation
          sbom: true          # Software Bill of Materials

      - name: Container Security Scan — Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
          format: 'sarif'
          exit-code: '1'
          severity: 'HIGH,CRITICAL'
          ignore-unfixed: false
          output: 'trivy-results.sarif'

      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Sign image with Cosign
        uses: sigstore/cosign-installer@v3
        
      - name: Sign the image
        run: |
          cosign sign --yes \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
        env:
          COSIGN_EXPERIMENTAL: "true"

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        if: startsWith(github.ref, 'refs/tags/')
        with:
          tag_name: ${{ steps.semver.outputs.version }}
          generate_release_notes: true
```

### CD Workflow — `.github/workflows/deploy-staging.yml`

```yaml
name: CD — Deploy Staging

on:
  workflow_run:
    workflows: ["CI — Build & Publish"]
    types: [completed]
    branches: [main]

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: staging    # GitHub Environment avec protection rules
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN_STAGING }}
          aws-region: eu-west-1

      - name: Get image digest from CI
        id: get-digest
        run: |
          # Récupérer le digest depuis l'artifact du workflow précédent
          DIGEST=$(aws ecr describe-images \
            --repository-name my-app \
            --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageDigest' \
            --output text)
          echo "digest=$DIGEST" >> "$GITHUB_OUTPUT"

      - name: Deploy to ECS Fargate (Blue-Green)
        run: |
          aws ecs update-service \
            --cluster staging-cluster \
            --service my-app-staging \
            --task-definition my-app-staging \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster staging-cluster \
            --services my-app-staging

      - name: Smoke Test — Post-deployment validation
        run: |
          ENDPOINT="https://staging.api.example.com"
          for i in 1 2 3; do
            STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
              "$ENDPOINT/actuator/health" || echo "000")
            
            if [ "$STATUS" = "200" ]; then
              echo "✅ Smoke test $i/$i passed"
            else
              echo "❌ Smoke test failed (HTTP $STATUS) — triggering rollback"
              aws ecs update-service \
                --cluster staging-cluster \
                --service my-app-staging \
                --task-definition my-app-staging:PREVIOUS
              exit 1
            fi
            sleep 10
          done
          echo "🚀 Deployment to staging successful"
```

---

## Docker générique {#docker}

```yaml
name: Docker Build & Scan

on:
  push:
    branches: [main]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Hadolint — Dockerfile lint
        uses: hadolint/hadolint-action@v3.1.0
        with:
          dockerfile: Dockerfile
          failure-threshold: warning

      - name: Setup BuildKit
        uses: docker/setup-buildx-action@v3

      - name: Build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false     # Build local pour scan
          load: true
          tags: app:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: app:${{ github.sha }}
          severity: 'HIGH,CRITICAL'
          exit-code: '1'
```

**Multi-stage Dockerfile (Spring Boot)** :

```dockerfile
# Stage 1 — Build
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY gradlew ./
COPY gradle/ gradle/
RUN ./gradlew --no-daemon dependencies   # Cache dépendances
COPY . .
RUN ./gradlew bootJar --no-daemon

# Stage 2 — Extract layers (Spring Boot layertools)
FROM builder AS extractor
RUN java -Djarmode=layertools -jar build/libs/*.jar extract

# Stage 3 — Runtime (image minimale)
FROM eclipse-temurin:21-jre-alpine AS runtime
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=extractor --chown=appuser:appgroup /app/dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /app/spring-boot-loader/ ./
COPY --from=extractor --chown=appuser:appgroup /app/snapshot-dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /app/application/ ./
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health | grep '"status":"UP"' || exit 1
```

---

## Terraform / Terragrunt {#terraform}

```yaml
name: Terraform CI/CD

on:
  push:
    branches: [main]
    paths: ['infrastructure/**']
  pull_request:
    paths: ['infrastructure/**']

jobs:
  validate:
    name: Validate & Plan
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      pull-requests: write
    
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~1.7"

      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: eu-west-1

      - name: Terraform Format Check
        run: terraform fmt -check -recursive infrastructure/

      - name: Terraform Validate
        working-directory: infrastructure/
        run: |
          terraform init -backend=false
          terraform validate

      - name: TFLint
        uses: terraform-linters/setup-tflint@v4
        
      - run: tflint --recursive

      - name: Checkov — IaC Security Scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: infrastructure/
          framework: terraform
          soft_fail: false
          output_format: sarif
          output_file_path: checkov.sarif

      - name: tfsec
        uses: aquasecurity/tfsec-action@v1.0.3
        with:
          working_directory: infrastructure/
          soft_fail: false

      - name: Terraform Plan
        id: plan
        working-directory: infrastructure/
        run: |
          terraform init
          terraform plan -out=tfplan -input=false
        env:
          TF_VAR_environment: ${{ github.event_name == 'push' && 'staging' || 'dev' }}

      - name: Comment PR with Plan
        uses: actions/github-script@v7
        if: github.event_name == 'pull_request'
        with:
          script: |
            const output = `#### Terraform Plan 📋\n\`\`\`\n${{ steps.plan.outputs.stdout }}\`\`\``;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });

  apply:
    name: Apply — Production
    runs-on: ubuntu-latest
    needs: [validate]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production    # Require manual approval

    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN_PROD }}
          aws-region: eu-west-1

      - name: Terraform Apply
        working-directory: infrastructure/
        run: |
          terraform init
          terraform apply -auto-approve -input=false tfplan
```

---

## Ansible {#ansible}

```yaml
name: Ansible CI/CD

on:
  push:
    branches: [main]
    paths: ['ansible/**']

jobs:
  lint:
    name: Lint & Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Ansible + tools
        run: |
          pip install ansible ansible-lint yamllint --break-system-packages

      - name: yamllint
        run: yamllint ansible/

      - name: ansible-lint
        run: ansible-lint --profile production ansible/

      - name: Syntax check
        run: |
          ansible-playbook ansible/playbooks/site.yml \
            --syntax-check \
            -i ansible/inventories/staging/

  molecule:
    name: Molecule Tests
    runs-on: ubuntu-latest
    needs: [lint]
    strategy:
      matrix:
        role: [common, nginx, postgresql]  # Rôles à tester
    steps:
      - uses: actions/checkout@v4

      - name: Install Molecule
        run: pip install molecule molecule-docker ansible --break-system-packages

      - name: Run Molecule
        working-directory: ansible/roles/${{ matrix.role }}
        run: molecule test
        env:
          PY_COLORS: '1'
          ANSIBLE_FORCE_COLOR: '1'

  deploy-staging:
    name: Deploy Staging
    runs-on: ubuntu-latest
    needs: [molecule]
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Configure SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H "${{ vars.STAGING_BASTION }}" >> ~/.ssh/known_hosts

      - name: Install Ansible
        run: pip install ansible --break-system-packages

      - name: Deploy — Check mode first
        run: |
          ansible-playbook ansible/playbooks/site.yml \
            -i ansible/inventories/staging/ \
            --check --diff \
            --vault-password-file <(echo "${{ secrets.VAULT_PASSWORD }}")

      - name: Deploy — Apply
        run: |
          ansible-playbook ansible/playbooks/site.yml \
            -i ansible/inventories/staging/ \
            --vault-password-file <(echo "${{ secrets.VAULT_PASSWORD }}")
```

---

## GitOps — ArgoCD {#gitops-argocd}

### Pattern : CI push image → update manifeste → ArgoCD sync

**CI Job — Update manifeste après build** :

```yaml
  update-manifests:
    name: Update GitOps Manifests
    runs-on: ubuntu-latest
    needs: [build]
    steps:
      - uses: actions/checkout@v4
        with:
          repository: org/k8s-manifests    # Repo GitOps séparé
          token: ${{ secrets.GITOPS_PAT }}
          path: manifests

      - name: Update image tag
        run: |
          cd manifests
          # Avec kustomize
          cd overlays/staging
          kustomize edit set image \
            backend=ghcr.io/org/backend:${{ needs.build.outputs.version }}
          
          # Ou avec yq directement sur Helm values
          yq -i '.image.tag = "${{ needs.build.outputs.version }}"' \
            charts/backend/values-staging.yaml

      - name: Commit and push
        run: |
          cd manifests
          git config user.email "ci@company.com"
          git config user.name "CI Bot"
          git add .
          git diff --staged --quiet || \
            git commit -m "chore: update backend to ${{ needs.build.outputs.version }}"
          git push
```

**ArgoCD Application manifest** :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: backend-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests
    targetRevision: main
    path: overlays/staging
  destination:
    server: https://kubernetes.default.svc
    namespace: backend-staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 3
      backoff:
        duration: 5s
        maxDuration: 3m
  # Notification sur sync failure
  notifications:
    slack-on-sync-failed: slack:devops-alerts
```

---

## Monorepo — Path Filtering {#monorepo}

```yaml
name: Monorepo CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    name: Detect Changes
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.changes.outputs.backend }}
      frontend: ${{ steps.changes.outputs.frontend }}
      infrastructure: ${{ steps.changes.outputs.infrastructure }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            backend:
              - 'services/backend/**'
              - 'shared/libs/**'
            frontend:
              - 'services/frontend/**'
            infrastructure:
              - 'infrastructure/**'
              - '.github/workflows/**'

  build-backend:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    uses: ./.github/workflows/build-java.yml   # Reusable workflow
    with:
      service: backend
      registry: ghcr.io/org

  build-frontend:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    uses: ./.github/workflows/build-node.yml
    with:
      service: frontend

  deploy-infra:
    needs: detect-changes
    if: needs.detect-changes.outputs.infrastructure == 'true'
    uses: ./.github/workflows/terraform.yml
```

---

## Semantic Versioning — Nyx {#semver}

Configuration `build.gradle.kts` :

```kotlin
plugins {
  id("com.mooltiverse.oss.nyx") version "3.0.2"
}

nyx {
  preset = "simple"
  releaseLenient = true
  releasePrefix = "v"
  
  commitMessageConventions {
    conventionalCommits {
      expression = "(?m)^(?<type>build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\\((?<scope>.+)\\))?(!)?:\\s(?<title>.+)$"
      bumpExpressions = mapOf(
        "major" to "(?s)(?m)^.+!:.*|^BREAKING CHANGE:.*",
        "minor" to "(?s)(?m)^feat.*",
        "patch" to "(?s)(?m)^fix|perf|refactor.*"
      )
    }
  }
}
```

**Tags git attendus** :
- `feat:` → bump minor (1.x.0)
- `fix:` → bump patch (1.0.x)
- `feat!:` ou `BREAKING CHANGE:` → bump major (x.0.0)

---

## GitLab CI — Java {#gitlab-java}

```yaml
# .gitlab-ci.yml
variables:
  REGISTRY: registry.gitlab.com
  IMAGE: $CI_REGISTRY_IMAGE
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"

stages:
  - test
  - build
  - security
  - deploy-staging
  - deploy-prod

cache:
  key: "$CI_PROJECT_ID-gradle"
  paths:
    - .gradle/

test:
  stage: test
  image: eclipse-temurin:21-jdk
  script:
    - ./gradlew test --parallel
  artifacts:
    reports:
      junit: build/test-results/test/*.xml

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $IMAGE:$CI_COMMIT_SHA .
    - docker push $IMAGE:$CI_COMMIT_SHA
  only:
    - main

trivy-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - trivy image --exit-code 1 --severity HIGH,CRITICAL $IMAGE:$CI_COMMIT_SHA
  only:
    - main

deploy-staging:
  stage: deploy-staging
  environment:
    name: staging
    url: https://staging.api.example.com
  script:
    - echo "Deploying $IMAGE:$CI_COMMIT_SHA to staging"
    # kubectl set image ou aws ecs update-service
  only:
    - main

deploy-prod:
  stage: deploy-prod
  environment:
    name: production
    url: https://api.example.com
  script:
    - echo "Deploying $IMAGE:$CI_COMMIT_SHA to production"
  when: manual    # Gate manuel obligatoire
  only:
    - main
```