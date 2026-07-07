# Dockerfile Patterns — Référence Concrète

> Ces patterns appliquent les 4 propriétés (Reproductible, Immutable, Sécurisé, Observable).
> Adapter le runtime selon la stack réelle. Les principes sont universels.

---

## Choisir sa Base Image {#bases}

### Hiérarchie par taille et sécurité

```
ubuntu / debian      ← Très lourd, éviter sauf cas particulier
    ↓
*-slim / *-alpine    ← Bonne base générale (Alpine ~5MB, slim ~50MB)
    ↓
distroless           ← Pas de shell, pas de package manager → surface minimale
    ↓
scratch              ← Binaire seul (Go statique uniquement)
```

**Alpine vs Slim** :
- Alpine utilise `musl libc` (peut causer des problèmes avec certaines libs JVM native)
- Slim (Debian) est compatible avec plus de packages, légèrement plus lourd
- Pour la JVM : préférer `eclipse-temurin:21-jre` (Temurin = OpenJDK certifié, pas de licence Oracle)

```dockerfile
# JVM — production
FROM eclipse-temurin:21-jre-alpine          # ~180MB

# JVM — sécurité maximale (pas de shell)
FROM gcr.io/distroless/java21-debian12      # ~130MB

# Node
FROM node:22.18.0-alpine                    # ~120MB

# Go — binaire statique
FROM scratch                                # 0MB de base

# Python
FROM python:3.12-slim                       # ~130MB

# Nginx
FROM nginx:1.27.4-alpine                    # ~40MB
```

---

## Spring Boot — Multi-Stage avec Layertools {#spring-boot}

### Pattern recommandé — Spring Boot 3.x + Gradle

```dockerfile
# ═══════════════════════════════════════
# Stage 1 — Build
# ═══════════════════════════════════════
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app

# Layer cache : copier les fichiers de dépendances AVANT le code source
COPY gradlew ./
COPY gradle/ gradle/
# Pré-télécharger les dépendances (cache si pom/gradle ne change pas)
RUN ./gradlew --no-daemon dependencies --configuration runtimeClasspath

COPY src/ src/
COPY build.gradle.kts settings.gradle.kts ./

RUN ./gradlew bootJar --no-daemon -x test

# ═══════════════════════════════════════
# Stage 2 — Extraction des layers Spring Boot
# Spring Boot layertools découpe le JAR en layers par fréquence de changement
# ═══════════════════════════════════════
FROM eclipse-temurin:21-jdk-alpine AS extractor
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

# ═══════════════════════════════════════
# Stage 3 — Runtime minimal
# ═══════════════════════════════════════
FROM eclipse-temurin:21-jre-alpine AS runtime

# Créer un utilisateur dédié (jamais root)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copier les layers dans l'ordre de stabilité (moins fréquent → plus fréquent)
# dependencies : frameworks, libs stables → rarement invalidé
COPY --from=extractor --chown=appuser:appgroup /app/dependencies/ ./
# spring-boot-loader : Spring internals → rarement invalidé
COPY --from=extractor --chown=appuser:appgroup /app/spring-boot-loader/ ./
# snapshot-dependencies : SNAPSHOT libs → parfois invalidé
COPY --from=extractor --chown=appuser:appgroup /app/snapshot-dependencies/ ./
# application : code métier → invalidé à chaque commit
COPY --from=extractor --chown=appuser:appgroup /app/application/ ./

USER appuser

EXPOSE 8080

# Labels OCI pour la traçabilité
LABEL org.opencontainers.image.title="backend" \
      org.opencontainers.image.source="https://github.com/org/backend" \
      org.opencontainers.image.vendor="Aristide Wafo"

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health \
      | grep -q '"status":"UP"' || exit 1

# Forme exec obligatoire (pas de shell form) — permet au PID 1 de recevoir les signaux
ENTRYPOINT ["java", \
            "-XX:+UseContainerSupport", \
            "-XX:MaxRAMPercentage=75.0", \
            "org.springframework.boot.loader.launch.JarLauncher"]
```

**Pourquoi layertools ?** Spring Boot découpe le JAR en 4 layers ordonnés par fréquence de changement. Résultat : si seul le code métier change, seul le layer `application` est re-pushé (quelques KB au lieu de tout le JAR).

### Pattern Maven (alternative)

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
# Copier pom.xml seul d'abord pour cacher les dépendances
COPY pom.xml .
RUN mvn dependency:go-offline -q
COPY src/ src/
RUN mvn package -DskipTests -q

FROM eclipse-temurin:21-jre-alpine AS runtime
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder --chown=appuser:appgroup /app/target/app.jar app.jar
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-jar", "app.jar"]
```

---

## Node.js — Multi-Stage {#nodejs}

```dockerfile
# ═══════════════════════════════════════
# Stage 1 — Dépendances (cache optimisé)
# ═══════════════════════════════════════
FROM node:22.18.0-alpine AS deps
WORKDIR /app
# Copier UNIQUEMENT les fichiers de dépendances pour cacher le npm ci
COPY package.json package-lock.json ./
RUN npm ci --omit=dev    # --omit=dev : pas de devDependencies en prod

# ═══════════════════════════════════════
# Stage 2 — Build (si TypeScript ou build step)
# ═══════════════════════════════════════
FROM node:22.18.0-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build        # TypeScript, Vite, etc.

# ═══════════════════════════════════════
# Stage 3 — Runtime
# ═══════════════════════════════════════
FROM node:22.18.0-alpine AS runtime
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --chown=appuser:appgroup package.json .
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
ENTRYPOINT ["node", "dist/index.js"]
```

---

## Go — Binaire Statique {#go}

```dockerfile
# ═══════════════════════════════════════
# Stage 1 — Build (avec module cache)
# ═══════════════════════════════════════
FROM golang:1.23-alpine AS builder
WORKDIR /app

# Copier go.mod et go.sum avant le code (cache des modules)
COPY go.mod go.sum ./
RUN go mod download

COPY . .
# CGO_ENABLED=0 → binaire statique sans dépendances externes
# GOOS=linux → cross-compilation si build sur Mac/Windows
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w" \        # -s -w : strip debug symbols → image plus petite
    -o api ./cmd/api/

# ═══════════════════════════════════════
# Stage 2 — Runtime minimal (scratch = 0 bytes de base)
# ═══════════════════════════════════════
FROM scratch AS runtime
# Copier les certificats CA pour les appels HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
# Copier uniquement le binaire
COPY --from=builder /app/api /api
EXPOSE 8080
ENTRYPOINT ["/api"]
```

**Résultat** : image finale = binaire seul (~10-20MB). Pas de shell, pas de package manager, surface d'attaque quasi nulle.

---

## Distroless — Surface Minimale {#distroless}

Pour les cas où la sécurité prime sur la debuggabilité :

```dockerfile
FROM eclipse-temurin:21-jdk AS builder
# ... build normal ...

FROM gcr.io/distroless/java21-debian12 AS runtime
# Pas de shell, pas d'apt, pas de useradd (distroless est non-root par défaut)
WORKDIR /app
COPY --from=extractor /app/dependencies/ ./
COPY --from=extractor /app/spring-boot-loader/ ./
COPY --from=extractor /app/application/ ./
EXPOSE 8080
# USER 1000 (non-root, défaut distroless)
ENTRYPOINT ["org.springframework.boot.loader.launch.JarLauncher"]
```

**Avantages distroless** : pas de shell = pas possible d'exec dans le container = surface d'attaque minimale. Idéal pour la production Kubernetes.
**Inconvénient** : debugging très difficile (prévoir un debug image séparé si besoin).

---

## Ordre des Layers — Stratégie Cache {#layers}

### Principe universel

```dockerfile
# ✅ CORRECT — du moins fréquent au plus fréquent

FROM base:tag                              # (1) Base image — change rarement
RUN apt-get install -y libX               # (2) OS packages — change peu
COPY <dependency-file> .                   # (3) Manifest de dépendances — change parfois
RUN <install-dependencies>                 # (4) Installation — invalidée si (3) change
COPY <source-code> .                       # (5) Code — change souvent
RUN <build>                               # (6) Build — invalidé si (5) change
USER non-root                             # (7) Sécurité — fixe
HEALTHCHECK ...                           # (8) Observable — fixe
ENTRYPOINT [...]                          # (9) Commande — fixe
```

### Le piège le plus fréquent

```dockerfile
# ❌ MAUVAIS — chaque changement de code invalide npm install
COPY . .
RUN npm install

# ✅ CORRECT — npm install n'est invalidé que si package.json change
COPY package.json package-lock.json ./
RUN npm install
COPY . .
```

### Combiner les RUN pour réduire les layers

```dockerfile
# ❌ 3 layers inutiles
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# ✅ 1 seul layer — && chaîné + nettoyage dans le même RUN
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl wget \
    && rm -rf /var/lib/apt/lists/*
```

---

## .dockerignore — Toujours Présent {#dockerignore}

Le `.dockerignore` évite d'envoyer des fichiers inutiles (ou dangereux) au Docker daemon.
Sans lui, `.git` (potentiellement très lourd) et `.env` (secrets !) sont inclus dans le contexte.

```dockerignore
# VCS
.git
.gitignore
.github

# IDE
.idea
.vscode
*.iml

# Build artifacts
target/
build/
dist/
out/
*.class
*.jar

# Node
node_modules/
npm-debug.log

# Secrets et config locale
.env
.env.*
*.pem
*.key

# Docker files eux-mêmes (pas besoin dans le contexte)
Dockerfile*
docker-compose*
compose*.yml

# Documentation
*.md
docs/
```

---

## HEALTHCHECK — Toujours Présent {#healthcheck}

Sans healthcheck, Docker (et Kubernetes) ne sait pas si le container a crashé "silencieusement".

```dockerfile
# Spring Boot Actuator
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health \
      | grep -q '"status":"UP"' || exit 1

# API générique
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fs http://localhost:8080/health || exit 1

# Node.js simple
HEALTHCHECK --interval=30s --timeout=3s \
  CMD node -e "require('http').get('http://localhost:3000/health', r => r.statusCode === 200 ? process.exit(0) : process.exit(1))"
```

**Paramètres** :
- `--start-period` : temps de grâce au démarrage (JVM lente = mettre 60s)
- `--interval` : fréquence de vérification
- `--retries` : nb d'échecs avant UNHEALTHY

---

## ENTRYPOINT vs CMD — La Bonne Distinction {#entrypoint}

```dockerfile
# ❌ Shell form — le processus principal est /bin/sh, pas votre app
# Les signaux (SIGTERM) ne sont pas transmis à l'application → shutdown brutal
ENTRYPOINT java -jar app.jar

# ✅ Exec form — votre app est directement PID 1
# Reçoit les signaux correctement → graceful shutdown
ENTRYPOINT ["java", "-jar", "app.jar"]

# ENTRYPOINT = commande fixe
# CMD = arguments par défaut (overridable à l'exécution)
ENTRYPOINT ["java", "-jar", "app.jar"]
CMD ["--spring.profiles.active=default"]  # override possible : docker run img --spring.profiles.active=prod
```

**Tini / dumb-init** — utile si l'app n'est pas PID 1-aware ou si elle crée des processus enfants :

```dockerfile
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--", "java", "-jar", "app.jar"]
```

Tini gère le problème des zombie processes et transmet correctement les signaux.

---

## BuildKit — Cache Avancé {#buildkit}

BuildKit (activé par défaut depuis Docker 23+) offre des montages de cache qui survivent entre les builds.

```dockerfile
# Gradle — cache du répertoire .gradle entre les builds (ne pas committer ce cache)
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew bootJar --no-daemon -x test

# Maven
RUN --mount=type=cache,target=/root/.m2 \
    mvn package -DskipTests -q

# npm
RUN --mount=type=cache,target=/root/.npm \
    npm ci --cache /root/.npm
```

**Avantage** : le cache persiste entre les builds locaux **et** dans les runners CI (GitHub Actions gha cache). Un second build à froid = aussi rapide qu'un build avec cache chaud.

```yaml
# GitHub Actions — activer le cache BuildKit
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```