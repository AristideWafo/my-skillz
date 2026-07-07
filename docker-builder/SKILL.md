---
name: docker-builder
description: >
  Guide and enforce expert-level Docker image design, Dockerfile patterns, and Docker Compose architecture for Jerry. Trigger whenever Jerry asks about Dockerfiles, Docker Compose, containerization, image building, container security, image optimization, or multi-stage builds. Also trigger for: writing or reviewing a Dockerfile, designing a Compose stack, optimizing image size or build time, securing containers, setting up healthchecks, choosing a base image, managing dev vs prod environments with Compose, or thinking about production-ready containerization. Trigger even if Jerry just says "help me containerize this", "review my Dockerfile", or "my image is too big". Enforces: single responsibility, immutable images, explicit tags, non-root execution, layer cache strategy, observable containers, and build-once deploy-everywhere.
---

# Docker Builder — Expert Standards

> La bonne question n'est pas *"Comment écrire un Dockerfile ?"*
> mais *"Comment construire une image reproductible, sécurisée, maintenable et déployable partout ?"*
>
> Un Dockerfile est un contrat entre le build et le runtime. Il doit être lisible dans 6 mois sans se souvenir de rien.

---

## Évaluation initiale — Contexte avant design

Avant d'écrire une seule ligne de Dockerfile :

1. **Langage / runtime** — JVM ? Node ? Go ? Python ? (impacte le choix de la base et du multi-stage)
2. **Type d'artefact** — fat JAR ? binaire statique ? bundle npm ? (impacte la stratégie de layers)
3. **Target de déploiement** — ECS Fargate ? Kubernetes ? VPS ? (impacte les contraintes sécurité)
4. **Contrainte de taille** — réseau lent ? registry payant à la taille ? (distroless / alpine ?)
5. **Multi-plateforme ?** — ARM + AMD64 ? (impacte le build pipeline)
6. **Compose pour quoi ?** — dev local ? stack complète ? prod ? (Compose n'est pas un outil de prod)

---

## Les 4 Propriétés d'une Image Production-Ready

Toute décision dans un Dockerfile doit servir au moins une de ces propriétés :

### 1. Reproductible
Même code source + même Dockerfile = même image, toujours, partout.
- Tags d'images de base **épinglés** (`node:22.18.0-alpine`, jamais `node:latest`)
- Dépendances verrouillées (`package-lock.json`, `pom.xml` avec versions fixes)
- Build déterministe (pas d'`apt upgrade` sans version)

### 2. Immutable
Après le build, l'image ne change plus. La configuration arrive à l'exécution.
- Toute configuration via `ENV` ou variables d'environnement injectées au runtime
- Pas de `RUN echo "env=prod" >> config.yml` dans le Dockerfile
- Même image identique en dev, staging, prod — seul l'environnement change

### 3. Sécurisée
Surface d'attaque minimale, privilèges minimaux.
- Utilisateur non-root (toujours)
- Image de base minimale (pas `ubuntu` pour une API)
- Pas de secrets dans le Dockerfile ou les layers
- Tags épinglés = builds reproductibles = surface de CVE connue

### 4. Observable
L'orchestrateur doit savoir si le container est vivant et sain.
- `HEALTHCHECK` défini dans le Dockerfile
- Logs sur `stdout`/`stderr` (jamais dans un fichier à l'intérieur du container)
- Labels OCI pour la traçabilité (`version`, `maintainer`, `source`)

---

## Le Modèle Mental : Le Layer Cake

Chaque instruction `RUN`, `COPY`, `ADD` crée une couche. Docker cache les couches.
La règle : **ce qui change souvent va en bas, ce qui change rarement va en haut.**

```
FROM base-image           ← change rarement (base OS/runtime)
    ↓
COPY dependency-file .    ← change peu (pom.xml, package.json)
RUN install-dependencies  ← invalidé seulement si dep-file change
    ↓
COPY source-code .        ← change souvent
RUN build                 ← invalidé à chaque changement de code
    ↓
USER non-root
HEALTHCHECK
ENTRYPOINT / CMD
```

Si `COPY . .` apparaît avant `RUN install`, **chaque changement de code invalide toute l'installation des dépendances**. C'est l'anti-pattern le plus fréquent.

---

## Multi-Stage Build — Le Pattern Obligatoire

Une image de build contient des outils (compilateur, maven, gradle, npm) qui ne doivent **jamais** aller en production.

```
Stage BUILD    → image lourde avec tous les outils
                        ↓ COPY --from=builder (seulement l'artefact)
Stage RUNTIME  → image minimale, juste ce qui s'exécute
```

L'image finale ne contient que ce qui est nécessaire à l'exécution.
Résultat typique : 500MB → 80MB.

→ Patterns multi-stage par stack (Spring Boot layertools, Node, Go, distroless) :
   `view /home/claude/docker-builder/references/dockerfile.md`
   Sections : Bases l.8 · Spring Boot l.49 · Node l.147 · Go l.187 · Distroless l.223 · Layers l.247 · .dockerignore l.294 · Healthcheck l.340 · ENTRYPOINT l.366 · BuildKit l.394

---

## Choisir sa Base Image

| Besoin | Image recommandée | Éviter |
|---|---|---|
| JVM production | `eclipse-temurin:21-jre-alpine` | `ubuntu` + apt install java |
| JVM haute sécurité | `gcr.io/distroless/java21` | Toute image non-officielle |
| Node.js | `node:22-alpine` | `node:latest` |
| Go | `scratch` ou `distroless/static` | Toute base avec shell |
| Python | `python:3.12-slim` | `python:3.12` (trop lourd) |
| Nginx | `nginx:1.27-alpine` | `ubuntu` + apt install nginx |

**Règle absolue** : toujours une image officielle Docker Hub, toujours un tag de version explicite.

---

## Docker Compose — Ce que c'est, ce que ce n'est pas

**Compose est un outil d'orchestration locale**, pas un outil de déploiement en production.

```
✅ Compose fait :             ❌ Compose ne fait pas :
- Dev local multi-services     - Déploiement prod (utiliser ECS, K8s)
- Tests d'intégration          - Haute disponibilité
- Stack de démo                - Load balancing avancé
- CI avec services annexes     - Auto-scaling
```

**Pattern production** : le CI build l'image → la push au registry → le serveur fait `docker pull` + redémarre. On ne rebuild jamais en production.

→ Patterns Compose (override, profils, réseaux, volumes, dev/prod) :
   `view /home/claude/docker-builder/references/compose.md`
   Sections : Override l.8 · Profiles l.158 · Réseaux l.210 · Volumes l.257 · Healthchecks l.300 · Dev l.333 · Prod l.360 · Env vars l.388

---

## Les 6 Questions d'Or

Avant tout `docker build` ou `docker compose up`, valider :

1. **Est-ce reproductible ?** — Reconstruire dans 6 mois donne la même image ?
2. **Est-ce immutable ?** — La config arrive via env vars, pas baked dans l'image ?
3. **Est-ce sécurisé ?** — Non-root, pas de secrets dans les layers, image minimale ?
4. **Est-ce observable ?** — Healthcheck défini, logs sur stdout ?
5. **Puis-je déployer la même image en dev, staging et prod ?** — Si non, c'est un problème de config, pas d'image.
6. **Puis-je comprendre ce Dockerfile dans 6 mois sans me souvenir de rien ?** — Commentaires, structure logique, pas de RUN chaînés illisibles ?

---

## Anti-patterns — Signal d'Alarme Immédiat

| Anti-pattern | Criticité | Principe violé | Correction |
|---|---|---|---|
| `FROM ubuntu` pour une API | 🔴 | Sécurité + Taille | Image officielle minimale |
| `FROM node:latest` | 🔴 | Reproductible | Tag de version épinglé |
| `COPY . .` avant `RUN npm install` | 🔴 | Layer cache | Copier `package.json` d'abord |
| Secrets dans `ENV` ou `RUN` | 🔴 | Sécurité | Docker secrets ou secret manager |
| `USER root` (implicite ou explicite) | 🔴 | Sécurité | `RUN useradd + USER` |
| Pas de `.dockerignore` | 🟠 | Performance + Sécurité | Exclure `.git`, `node_modules`, `.env` |
| Pas de `HEALTHCHECK` | 🟠 | Observable | Ajouter avant `ENTRYPOINT` |
| Build sans multi-stage | 🟠 | Taille + Sécurité | Séparer build et runtime |
| `docker build` en production | 🟠 | Immutable | Build en CI, deploy depuis registry |
| `ADD url http://...` | 🟡 | Reproductible | `RUN curl` ou `COPY --from` |
| Pas de labels OCI | 🟡 | Observable | Ajouter `LABEL org.opencontainers.image.*` |
| `RUN apt-get update && apt-get install` sans version | 🟡 | Reproductible | Épingler les versions de packages |

---

## Sécurité Container — Principes

→ Hardening complet (capabilities, read-only FS, Trivy, Hadolint, runtime limits) :
   `view /home/claude/docker-builder/references/security.md`
   Sections : Non-root l.8 · Read-only FS l.47 · Capabilities l.82 · Trivy l.118 · Hadolint l.191 · Runtime l.254 · Secrets l.292 · Checklist l.325

Résumé des principes :
- **Principe du moindre privilège** : un container n'a que les droits dont il a besoin
- **Surface d'attaque minimale** : moins il y a dans l'image, moins il y a à exploiter
- **Immutabilité du filesystem** : le container ne devrait pas pouvoir s'écrire lui-même
- **Isolation réseau** : les services qui n'ont pas besoin de se parler ne doivent pas se voir

---

## Checklist — Image Production-Ready

**Dockerfile**
- [ ] Image de base officielle avec tag de version épinglé ?
- [ ] Multi-stage build (séparation build / runtime) ?
- [ ] `COPY dependency-file` avant `COPY source` (layer cache) ?
- [ ] `.dockerignore` présent et complet ?
- [ ] Utilisateur non-root (`USER`) défini ?
- [ ] `HEALTHCHECK` présent ?
- [ ] Labels OCI (`version`, `source`, `maintainer`) ?
- [ ] Pas de secrets dans les layers ?
- [ ] `ENTRYPOINT` avec forme exec (`["java", "-jar"]`, pas shell form) ?

**Compose**
- [ ] Override files séparés (base + dev + prod) ?
- [ ] Variables dans `.env`, pas hardcodées dans le YAML ?
- [ ] Réseaux nommés et dédiés par domaine fonctionnel ?
- [ ] Volumes nommés pour les données persistantes ?
- [ ] `healthcheck` + `depends_on: service_healthy` pour l'ordre de démarrage ?
- [ ] Pas de `build:` dans le Compose de production ?

---

## Ce que ce Skill Produit

**Dockerfile complet** — Multi-stage, non-root, healthcheck, labels, layer-optimisé, adapté au runtime fourni.

**Review critique** — Audit d'un Dockerfile ou Compose existant avec criticité (🔴/🟠/🟡), principe violé, et correction concrète ligne par ligne.

**Architecture Compose** — Structure base + override dev/prod, réseaux, volumes, profils.

**Optimisation** — Réduction de taille d'image, accélération du build par layer strategy et BuildKit cache.

**Security upgrade** — Identification des failles dans un Dockerfile existant et corrections.