# Docker Compose Patterns — Référence

> Compose = orchestration locale et de développement.
> Production = ECS, Kubernetes, ou `docker compose pull + up -d` depuis une image registry (jamais `build:` en prod).

---

## Override Pattern — Base + Dev + Prod {#override}

Le pattern professionnel : un fichier de base, des surcharges par environnement.

```
compose.yml              ← définition de base (partagée)
compose.override.yml     ← dev (appliqué automatiquement par docker compose)
compose.prod.yml         ← prod (appliqué explicitement)
```

### `compose.yml` — Définition de base

```yaml
services:
  backend:
    image: ghcr.io/org/backend:${IMAGE_TAG:-latest}
    environment:
      SPRING_DATASOURCE_URL: ${DB_URL}
      SPRING_PROFILES_ACTIVE: ${APP_PROFILE:-default}
    networks:
      - backend-net
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/actuator/health"]
      interval: 30s
      timeout: 5s
      start_period: 60s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16.3-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-appdb}
      POSTGRES_USER: ${DB_USER:-app}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-app}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.4-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - backend-net
    healthcheck:
      test: ["CMD", "redis-cli", "--pass", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

networks:
  backend-net:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### `compose.override.yml` — Dev (appliqué automatiquement)

```yaml
# Appliqué par défaut avec `docker compose up`
# Jamais committer les secrets - utiliser .env.dev

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder    # Stop au stage builder pour hot-reload
    volumes:
      - .:/app           # Bind mount : hot-reload local
      - /app/build       # Exclure le dossier build (monté par le container)
    environment:
      SPRING_PROFILES_ACTIVE: dev
      JAVA_TOOL_OPTIONS: >
        -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005
    ports:
      - "8080:8080"
      - "5005:5005"    # Port debug JDWP
    restart: "no"       # Pas de restart en dev (masque les erreurs)

  postgres:
    ports:
      - "5432:5432"    # Exposer en dev pour pgAdmin / DBeaver

  redis:
    ports:
      - "6379:6379"
```

### `compose.prod.yml` — Prod

```yaml
# Usage : docker compose -f compose.yml -f compose.prod.yml up -d

services:
  backend:
    image: ghcr.io/org/backend:${IMAGE_TAG}    # Tag obligatoire en prod
    # Pas de build, pas de volumes, pas de ports exposés directement
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
    restart: always

  postgres:
    # Pas de ports exposés en prod (accès via réseau interne uniquement)
    deploy:
      resources:
        limits:
          memory: 512M
```

### Utilisation

```bash
# Dev (override automatique)
docker compose up

# Prod (avec fichier prod explicite)
docker compose -f compose.yml -f compose.prod.yml up -d

# Validation avant déploiement
docker compose -f compose.yml -f compose.prod.yml config
```

---

## Compose Profiles — Services Optionnels {#profiles}

Les profils permettent d'activer/désactiver des services selon le contexte.

```yaml
services:
  backend:
    image: ghcr.io/org/backend:latest
    # Pas de profile → toujours démarré

  postgres:
    image: postgres:16-alpine
    # Pas de profile → toujours démarré

  # Services de développement — activés uniquement avec --profile dev
  maildev:
    image: maildev/maildev
    profiles: [dev]
    ports:
      - "1080:1080"    # Interface web emails de test

  pgadmin:
    image: dpage/pgadmin4:latest
    profiles: [dev]
    ports:
      - "5050:80"

  # Services de monitoring — activés avec --profile monitoring
  prometheus:
    image: prom/prometheus:latest
    profiles: [monitoring]
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    profiles: [monitoring]
```

```bash
# Démarrer avec dev tools
docker compose --profile dev up

# Démarrer avec monitoring
docker compose --profile monitoring up

# Tout ensemble
docker compose --profile dev --profile monitoring up
```

---

## Réseaux — Isolation par Domaine {#networks}

### Principe : les services qui ne se parlent pas ne se voient pas

```yaml
services:
  frontend:
    networks:
      - frontend-net    # Communique avec le proxy
      - backend-net     # Communique avec l'API

  backend:
    networks:
      - backend-net     # Communique avec DB et cache

  postgres:
    networks:
      - backend-net     # Accessible seulement depuis backend-net

  nginx:
    networks:
      - frontend-net    # Reverse proxy : internet → frontend
    ports:
      - "80:80"
      - "443:443"

networks:
  frontend-net:
    driver: bridge
  backend-net:
    driver: bridge
    internal: false    # Mettre true pour bloquer accès internet depuis ce réseau
```

**Résultat** : postgres n'est pas accessible depuis nginx. Le frontend n'accède pas directement à postgres.

### DNS interne

Dans un réseau Compose, les services se joignent par leur **nom de service** :
```yaml
# Dans le backend, la DB est accessible via :
SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/appdb
#                                        ↑ nom du service Compose
```

---

## Volumes — Persistance des Données {#volumes}

### Named volumes (recommandé pour les données)

```yaml
volumes:
  postgres_data:          # Géré par Docker, persist entre les `docker compose down`
    driver: local
  redis_data:
  elasticsearch_data:

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # Attention : docker compose down --volumes supprime les données !
```

### Bind mounts (dev uniquement)

```yaml
services:
  backend:
    volumes:
      - .:/app                      # Code source local → container (hot-reload)
      - /app/build                  # Exclure le dossier build du bind mount
      - ./config:/app/config:ro     # Config en lecture seule
```

**Règle** : les bind mounts sont pour le dev. En prod, tout vient de l'image ou de volumes nommés.

### Initialisation DB

```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro  # Scripts SQL exécutés au premier démarrage
```

---

## Healthchecks + depends_on {#healthchecks}

Le `depends_on` simple ne garantit pas que le service est **prêt** — seulement qu'il a **démarré**.

```yaml
services:
  backend:
    depends_on:
      postgres:
        condition: service_healthy    # Attend que postgres soit HEALTHY (pas juste started)
      redis:
        condition: service_healthy

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

**Sans `condition: service_healthy`**, le backend démarrerait avant que postgres soit prêt → erreurs de connexion au démarrage.

---

## Pattern Dev — Hot Reload {#dev}

Pour les frameworks avec hot-reload (Spring DevTools, Nodemon, etc.) :

```yaml
# compose.override.yml (dev)
services:
  backend:
    build:
      context: .
      target: builder     # Utiliser le stage de build, pas le runtime final
    volumes:
      - ./src:/app/src    # Monter le code source
    environment:
      SPRING_DEVTOOLS_RESTART_ENABLED: "true"
      SPRING_DEVTOOLS_LIVERELOAD_ENABLED: "true"
    command: ./gradlew bootRun    # Override de ENTRYPOINT pour le dev

  # Watcher Node.js
  frontend:
    volumes:
      - ./frontend:/app
    command: npm run dev          # Nodemon / Vite dev server
```

---

## Pattern Production — Pull depuis Registry {#prod}

```bash
# Sur le serveur de production — jamais de build ici

# 1. Configurer les variables d'environnement
export IMAGE_TAG=v1.4.2
export DB_PASSWORD=$(aws ssm get-parameter --name /prod/db/password --with-decryption --query Parameter.Value --output text)

# 2. Pull la nouvelle image
docker compose -f compose.yml -f compose.prod.yml pull backend

# 3. Redémarrer le service (zero-downtime si réplica > 1)
docker compose -f compose.yml -f compose.prod.yml up -d --no-deps backend

# 4. Vérifier le healthcheck
docker compose ps
docker compose logs --tail=50 backend

# 5. Rollback si problème
export IMAGE_TAG=v1.3.9
docker compose -f compose.yml -f compose.prod.yml up -d --no-deps backend
```

**Règle d'or** : le serveur de production ne doit jamais avoir de code source. Il ne fait que `pull` et `up`.

---

## Gestion des Variables d'Environnement {#env}

### Fichiers .env par environnement

```
.env.dev      ← valeurs de développement (peut contenir des secrets locaux)
.env.staging  ← staging
.env.prod     ← NE PAS COMMITTER (contient de vrais secrets)
```

```bash
# Usage
docker compose --env-file .env.dev up
docker compose --env-file .env.staging -f compose.yml -f compose.prod.yml up -d
```

### .env de base (valeurs par défaut)

```env
# .env — valeurs par défaut (committé, jamais de secrets)
IMAGE_TAG=latest
DB_NAME=appdb
DB_USER=app
APP_PROFILE=default
```

### .env.dev (local, non committé)

```env
# .env.dev — gitignored
IMAGE_TAG=local
DB_PASSWORD=devpassword123
REDIS_PASSWORD=devredis
APP_PROFILE=dev
```

Ajouter `.env.*` sauf `.env` au `.gitignore`.

---

## Structure de Fichiers Professionnelle

```
project/
├── Dockerfile                    ← Image principale
├── Dockerfile.dev                ← (optionnel) Image de dev avec outils supplémentaires
├── .dockerignore
│
├── compose.yml                   ← Définition de base
├── compose.override.yml          ← Dev (auto-appliqué)
├── compose.prod.yml              ← Prod (appliqué explicitement)
├── compose.ci.yml                ← CI (services pour les tests)
│
├── .env                          ← Valeurs par défaut (committé)
├── .env.dev.example              ← Template (committé)
├── .env.dev                      ← Valeurs locales (gitignored)
│
├── config/
│   ├── nginx/
│   │   └── nginx.conf
│   └── prometheus/
│       └── prometheus.yml
│
├── db/
│   └── init/
│       └── 01-schema.sql        ← Init SQL (dev uniquement)
│
└── src/
```