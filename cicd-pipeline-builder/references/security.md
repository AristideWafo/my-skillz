# Security Gates — DevSecOps Reference

## Supply Chain Security — Le Pipeline Complet

```
┌──────────────────────────────────────────────────────────────────┐
│                    SHIFT-LEFT SECURITY                            │
├──────────────────────────────────────────────────────────────────┤
│ IDE          │ Pre-commit hooks (detect-secrets, gitleaks)        │
│ PR           │ SAST (Semgrep, SpotBugs), Secret scanning          │
│ Build        │ SCA / Dependency Check (OWASP, Dependabot)         │
│ Image Build  │ Hadolint (Dockerfile lint), Base image scan        │
│ Image Push   │ Trivy scan, Cosign sign, SBOM generation           │
│ Deploy       │ IaC scan (Checkov, tfsec) avant apply              │
│ Runtime      │ DAST (OWASP ZAP), WAF, Runtime security (Falco)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml — à la racine du repo
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: check-json
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
```

---

## SAST — Static Application Security Testing

### Semgrep (polyvalent, gratuit)

```yaml
- name: Semgrep SAST
  uses: semgrep/semgrep-action@v1
  with:
    config: >-
      p/java
      p/secrets
      p/owasp-top-ten
      p/spring-boot
  env:
    SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_TOKEN }}
```

### SpotBugs + FindSecBugs (Java spécifique)

```kotlin
// build.gradle.kts
plugins {
    id("com.github.spotbugs") version "6.0.6"
}

spotbugs {
    effort = com.github.spotbugs.snom.Effort.MAX
    reportLevel = com.github.spotbugs.snom.Confidence.LOW
    excludeFilter = file("config/spotbugs-exclude.xml")
}

dependencies {
    spotbugsPlugins("com.h3xstream.findsecbugs:findsecbugs-plugin:1.13.0")
}
```

---

## Dependency Scanning (SCA)

### OWASP Dependency Check

```kotlin
// build.gradle.kts
plugins {
    id("org.owasp.dependencycheck") version "9.0.7"
}

dependencyCheck {
    failBuildOnCVSS = 7.0f   // Fail sur CVSS >= 7 (High)
    formats = listOf("HTML", "SARIF", "JSON")
    suppressionFile = "config/owasp-suppressions.xml"
    nvd {
        apiKey = System.getenv("NVD_API_KEY") ?: ""
    }
}
```

### GitHub Dependabot (automatique)

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "gradle"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      spring-boot:
        patterns: ["org.springframework.boot*"]
  
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
```

---

## Container Security — Trivy

### Configuration complète

```yaml
# .trivyignore — exceptions documentées
# CVE-2023-XXXXX — Mitigated by network policy, no external access
# CVE-2023-YYYYY — Fixed in next base image release (ETA 2024-Q1)

# GitHub Actions step
- name: Trivy — Full Image Scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: '${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'MEDIUM,HIGH,CRITICAL'    # MEDIUM pour visibilité
    exit-code: '1'                       # Bloquant sur HIGH/CRITICAL
    ignore-unfixed: false                # Ne pas ignorer même si pas de fix
    vuln-type: 'os,library'
    scanners: 'vuln,secret,config'       # Vulns + secrets + misconfigs

- name: Upload Trivy SARIF to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'
```

### Trivy local (dev)

```bash
# Scan d'une image locale
trivy image --severity HIGH,CRITICAL backend:local

# Scan du filesystem
trivy fs --severity HIGH,CRITICAL .

# Scan config (Dockerfile, K8s manifestes)
trivy config --severity HIGH,CRITICAL .
```

---

## Image Signing — Cosign (Sigstore)

**Garantit que l'image en production est exactement celle buildée par le CI.**

```yaml
# Dans le CI après push
- name: Install Cosign
  uses: sigstore/cosign-installer@v3
  with:
    cosign-release: 'v2.2.2'

- name: Sign image (Keyless via OIDC)
  run: |
    cosign sign --yes \
      --rekor-url https://rekor.sigstore.dev \
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
  env:
    COSIGN_EXPERIMENTAL: "true"    # Sigstore TUF root

# Vérification avant déploiement
- name: Verify image signature
  run: |
    cosign verify \
      --certificate-identity-regexp "https://github.com/org/repo/.*" \
      --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
```

**Admission Controller Kubernetes (Policy Enforcement)** :

```yaml
# Kyverno policy — reject unsigned images
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-images
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-image-signature
      match:
        resources:
          kinds: [Pod]
          namespaces: [production]
      verifyImages:
        - imageReferences:
            - "ghcr.io/org/*"
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/org/backend/.github/workflows/*"
                    issuer: "https://token.actions.githubusercontent.com"
```

---

## SBOM — Software Bill of Materials

**Requis pour compliance SLSA Level 2+**

```yaml
# Généré automatiquement avec docker/build-push-action
- name: Build and Push with SBOM
  uses: docker/build-push-action@v5
  with:
    sbom: true          # Génère SBOM au format SPDX ou CycloneDX
    provenance: true    # SLSA Level 3 provenance
    push: true
    tags: ${{ steps.meta.outputs.tags }}

# Attacher le SBOM à l'image dans le registry
- name: Attach SBOM
  run: |
    syft scan ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
      -o cyclonedx-json=sbom.json
    cosign attest --yes \
      --predicate sbom.json \
      --type cyclonedx \
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
```

---

## IaC Security — Checkov & tfsec

### Checkov (Terraform + Ansible + Kubernetes)

```yaml
- name: Checkov IaC Scan
  uses: bridgecrewio/checkov-action@master
  with:
    directory: infrastructure/
    framework: terraform,ansible,kubernetes
    soft_fail: false
    output_format: cli,sarif
    output_file_path: console,checkov.sarif
    skip_check: >
      CKV_AWS_144,
      CKV_AWS_91
      # CKV_AWS_144: S3 cross-region replication — not required for non-critical data
      # CKV_AWS_91: S3 access logging — handled at CloudTrail level
```

### tfsec (Terraform spécifique)

```yaml
- name: tfsec
  uses: aquasecurity/tfsec-action@v1.0.3
  with:
    working_directory: infrastructure/
    format: sarif
    sarif_file: tfsec.sarif
    soft_fail: false
    additional_args: >
      --exclude aws-s3-enable-bucket-logging
```

---

## DAST — Dynamic Application Security Testing

```yaml
# À exécuter sur l'environnement staging après déploiement
- name: OWASP ZAP Full Scan
  uses: zaproxy/action-full-scan@v0.9.0
  with:
    target: 'https://staging.api.example.com'
    rules_file_name: 'config/zap-rules.tsv'
    cmd_options: '-a'   # Ajuster cookies/auth si nécessaire
    artifact_name: 'zap-report'
    
# Pour API REST avec OpenAPI spec
- name: ZAP API Scan
  uses: zaproxy/action-api-scan@v0.7.0
  with:
    target: 'https://staging.api.example.com/v3/api-docs'
    format: openapi
    fail_action: false    # Warning seulement (adapter selon maturité)
```

---

## Secrets Management — AWS SSM + OIDC

```yaml
# ✅ Pattern recommandé — OIDC sans credentials statiques
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
    role-session-name: GitHubActions-${{ github.run_id }}
    aws-region: eu-west-1
    # Pas de aws-access-key-id / aws-secret-access-key

- name: Get secrets from SSM
  run: |
    DB_URL=$(aws ssm get-parameter \
      --name "/prod/database/url" \
      --with-decryption \
      --query 'Parameter.Value' \
      --output text)
    echo "::add-mask::$DB_URL"    # Masquer dans les logs
    echo "DB_URL=$DB_URL" >> "$GITHUB_ENV"
```

**IAM Trust Policy pour GitHub OIDC** :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:org/repo:*"
        }
      }
    }
  ]
}
```

---

## Kubernetes Runtime Security — Falco

**Détection d'anomalies en runtime** (au-delà des gates CI/CD) :

```yaml
# Falco rule — alerter si un shell spawn dans un container prod
- rule: Unexpected shell spawned in container
  desc: Alert when a shell process is spawned in a production container
  condition: >
    spawned_process and
    container.id != host and
    proc.name in (bash, sh, zsh, dash) and
    container.image.repository startswith "ghcr.io/org/" and
    not proc.pname in (java, python, node)
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name image=%container.image.repository
    shell=%proc.name parent=%proc.pname)
  priority: WARNING
  tags: [runtime, security]
```

---

## Security Scorecard — Checklist Complète

| Gate | Outil | Seuil bloquant | Phase |
|---|---|---|---|
| Secret scan | detect-secrets / Gitleaks | 0 secrets | Pre-commit |
| SAST | Semgrep | 0 HIGH | PR |
| Dependency CVE | OWASP Dep-Check | CVSS ≥ 7 | Build |
| Dockerfile lint | Hadolint | error level | Build |
| Container scan | Trivy | HIGH + CRITICAL | Post-build |
| IaC scan | Checkov + tfsec | HIGH | Pre-apply |
| Image signing | Cosign | Obligatoire | Post-push |
| SBOM | Syft / BuildKit | Généré + attaché | Post-push |
| DAST | OWASP ZAP | Paramétrable | Post-staging-deploy |
| Runtime | Falco | Alerting | Runtime prod |