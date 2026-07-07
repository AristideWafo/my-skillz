# Container Security — Hardening Reference

> Principe directeur : **moindre privilège**.
> Un container n'a que les droits strictement nécessaires à sa fonction.

---

## Non-Root User — Obligatoire {#non-root}

Exécuter en root dans un container = si l'app est compromise, l'attaquant a root sur le host (via escape).

```dockerfile
# ✅ Pattern Alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# ...
USER appuser

# ✅ Pattern Debian/Ubuntu
RUN groupadd -r appgroup && useradd -r -g appgroup --no-create-home appuser
USER appuser

# ✅ Pattern minimaliste (UID numérique — fonctionne même sans /etc/passwd)
USER 1001

# ✅ Distroless — non-root par défaut (UID 65532)
FROM gcr.io/distroless/java21
# Non-root par défaut, pas besoin de USER
```

**Vérification** :
```bash
docker run --rm ghcr.io/org/backend whoami     # → appuser (pas root)
docker run --rm ghcr.io/org/backend id         # → uid=1001 gid=1001
```

### Propriété des fichiers

```dockerfile
# Les fichiers doivent appartenir à l'utilisateur non-root AVANT le USER switch
COPY --chown=appuser:appgroup /app/build/ ./
# Ou setter les permissions après
RUN chown -R appuser:appgroup /app && chmod -R 550 /app
```

---

## Read-Only Filesystem — Surface d'Attaque Minimale {#readonly}

Un container en lecture seule ne peut pas être modifié par un attaquant qui exploiterait une vulnérabilité.

```bash
# Lancer en read-only
docker run --read-only \
  --tmpfs /tmp \           # tmpfs pour les fichiers temporaires
  --tmpfs /app/logs \      # tmpfs si l'app écrit des logs locaux (préférer stdout)
  ghcr.io/org/backend
```

```yaml
# Compose
services:
  backend:
    read_only: true
    tmpfs:
      - /tmp
      - /app/temp
```

```yaml
# Kubernetes
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1001
  allowPrivilegeEscalation: false
```

**Prérequis** : l'application ne doit pas écrire sur le filesystem (logs → stdout, uploads → S3/volume).

---

## Linux Capabilities — Moindre Privilège {#capabilities}

Root dans un container dispose de beaucoup de capabilities Linux. On peut les retirer.

```bash
# Retirer TOUTES les capabilities puis re-ajouter seulement celles nécessaires
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \    # Si besoin de binder un port < 1024
  ghcr.io/org/backend
```

```yaml
# Compose
services:
  backend:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE    # Uniquement si nécessaire (port 80/443)
```

```yaml
# Kubernetes
securityContext:
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE
```

**La plupart des applications** n'ont besoin d'aucune capability. `--cap-drop ALL` sans `--cap-add` est souvent suffisant pour une API REST.

---

## Trivy — Scan de Vulnérabilités {#trivy}

Trivy scanne l'image, le filesystem, et la configuration.

### Usage basique

```bash
# Scan d'une image locale
trivy image --severity HIGH,CRITICAL ghcr.io/org/backend:latest

# Scan avec rapport JSON
trivy image --format json --output trivy-report.json ghcr.io/org/backend:latest

# Scan du code source (dépendances)
trivy fs --severity HIGH,CRITICAL .

# Scan IaC (Dockerfile, compose, K8s manifests)
trivy config --severity HIGH,CRITICAL .
```

### Configuration `.trivy.yaml`

```yaml
# .trivy.yaml — à la racine du projet
severity:
  - HIGH
  - CRITICAL
exit-code: 1           # Fail le pipeline si vulnérabilités trouvées
ignore-unfixed: false  # Ne pas ignorer les CVE sans fix disponible
scanners:
  - vuln
  - secret
  - config

# Exceptions documentées
ignorefile: .trivyignore
```

### `.trivyignore` — Exceptions documentées

```
# CVE-2023-XXXXX — Mitigé par la politique réseau (pas d'accès externe)
# Fix prévu dans la version 2.1.0 — ETA 2025-Q1
CVE-2023-XXXXX

# Faux positif — la lib est présente mais le code vulnérable n'est pas utilisé
CVE-2023-YYYYY
```

**Règle** : jamais ignorer sans documentation du pourquoi dans le fichier `.trivyignore`.

### Dans GitHub Actions

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'ghcr.io/org/backend:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'HIGH,CRITICAL'
    exit-code: '1'
    ignore-unfixed: false

- name: Upload Trivy scan results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'
```

---

## Hadolint — Linter Dockerfile {#hadolint}

Hadolint analyse le Dockerfile et détecte les anti-patterns de sécurité et de best practices.

```bash
# Installation
docker run --rm -i hadolint/hadolint < Dockerfile

# Avec configuration
hadolint --config .hadolint.yaml Dockerfile
```

### `.hadolint.yaml`

```yaml
# .hadolint.yaml
failure-threshold: warning   # Fail sur warning ou plus grave

ignore:
  - DL3008  # apt-get without version pinning (acceptable si justifié)

trustedRegistries:
  - gcr.io
  - ghcr.io
  - registry.gitlab.com
  - docker.io
```

### Erreurs Hadolint fréquentes

```dockerfile
# DL3007 — Éviter :latest
FROM node:latest          # ❌ DL3007
FROM node:22-alpine       # ✅

# DL3008 — Épingler les versions apt
RUN apt-get install curl          # ❌ DL3008
RUN apt-get install curl=8.4.0    # ✅

# DL3009 — Nettoyer après apt-get
RUN apt-get install curl                                  # ❌ DL3009
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*                        # ✅

# DL4006 — Utiliser SHELL pour les pipes
RUN wget -O - https://example.com | tar xz    # ❌ DL4006
SHELL ["/bin/sh", "-o", "pipefail", "-c"]
RUN wget -O - https://example.com | tar xz    # ✅
```

### Dans GitHub Actions

```yaml
- name: Hadolint — Dockerfile lint
  uses: hadolint/hadolint-action@v3.1.0
  with:
    dockerfile: Dockerfile
    failure-threshold: warning
    config: .hadolint.yaml
```

---

## Limites Runtime — Protéger le Host {#runtime}

Sans limites, un container peut monopoliser toutes les ressources du host (DoS accidentel ou malveillant).

```yaml
# Compose
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'          # Maximum 2 vCPU
          memory: 1G           # Maximum 1GB RAM
        reservations:
          cpus: '0.5'          # Garantit 0.5 vCPU
          memory: 256M         # Garantit 256MB RAM
```

```yaml
# Kubernetes
resources:
  limits:
    cpu: "2"
    memory: "1Gi"
  requests:
    cpu: "500m"
    memory: "256Mi"
```

**JVM et les containers** : sans configuration, la JVM voit la RAM du host, pas celle du container.
```dockerfile
# UseContainerSupport (activé par défaut Java 11+)
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
# MaxRAMPercentage=75.0 → utilise 75% de la mémoire allouée au container
```

---

## Gestion des Secrets — Ne Jamais dans l'Image {#secrets}

```dockerfile
# ❌ Le secret est dans un layer de l'image — récupérable avec docker history
RUN curl -H "Authorization: Bearer $API_KEY" https://api.example.com/config

# ✅ BuildKit secret mount — secret injecté à l'exécution, pas dans les layers
RUN --mount=type=secret,id=api_key \
    API_KEY=$(cat /run/secrets/api_key) \
    && curl -H "Authorization: Bearer $API_KEY" https://api.example.com/config
```

```bash
# Build avec secret
docker buildx build --secret id=api_key,src=~/.secrets/api_key .
```

```yaml
# Docker Swarm Secrets (production)
services:
  backend:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password  # Lire depuis le fichier, pas ENV

secrets:
  db_password:
    external: true
```

---

## Checklist Sécurité Complète {#checklist}

**Image**
- [ ] Image de base officielle, tag épinglé (pas `:latest`) ?
- [ ] Multi-stage build (pas d'outils de build en runtime) ?
- [ ] Utilisateur non-root défini ?
- [ ] Pas de secrets dans les layers (vérifier `docker history`) ?
- [ ] `.dockerignore` présent (exclut `.env`, `.git`, `*.pem`) ?
- [ ] Trivy scan propre (0 HIGH/CRITICAL non justifié) ?
- [ ] Hadolint sans warning bloquant ?

**Runtime**
- [ ] `--cap-drop ALL` (ou équivalent Compose/K8s) ?
- [ ] `read_only: true` si l'app ne doit pas écrire ?
- [ ] Limites CPU et mémoire définies ?
- [ ] `-XX:+UseContainerSupport` si JVM ?
- [ ] Ports exposés uniquement ceux nécessaires ?

**Réseau**
- [ ] Réseaux Compose isolés par domaine ?
- [ ] Pas d'accès direct à la DB depuis internet ?
- [ ] TLS terminé au niveau du proxy/load balancer ?

**Secrets**
- [ ] Aucun secret en variable d'environnement hardcodée ?
- [ ] Secrets injectés au runtime via AWS SSM, Vault, ou Docker secrets ?