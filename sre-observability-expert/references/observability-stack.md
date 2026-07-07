# Stack d'observabilité — OpenTelemetry, Prometheus, Grafana, Loki, Tempo, ELK

Table des matières :
- [OpenTelemetry](#opentelemetry)
- [Prometheus](#prometheus)
- [Grafana](#grafana)
- [Loki](#loki)
- [Tempo](#tempo)
- [Elasticsearch / Kibana](#elasticsearch--kibana)
- [Choisir sa stack — décision KISS](#choisir-sa-stack)

---

## OpenTelemetry

Standard vendor-neutral pour logs/metrics/traces. Toujours préférer OTel à une instrumentation propriétaire quand le choix est possible.

**Architecture type** :
```
App (SDK OTel) → OTel Collector (Receiver → Processor → Exporter) → Backend (Prometheus/Tempo/Loki)
```

- **Receivers** : OTLP (natif), Prometheus scrape, Jaeger (legacy)
- **Processors** : `batch` (perf), `memory_limiter` (éviter OOM du collector), `resource` (enrichir avec metadata infra)
- **Sampling** : head-based (simple, perte d'info) vs **tail-based** (décision après avoir vu tout le trace, plus précis mais plus coûteux) — tail sampling seulement si le volume de traces le justifie
- **Semantic Conventions** : respecter les noms standards (`http.method`, `service.name`) pour rester interopérable entre backends

**Principe KISS** : démarrer avec un Collector unique en mode `batch` + sampling simple ; n'introduire le tail sampling ou une topologie multi-collector que si le volume/coût le justifie réellement.

---

## Prometheus

Modèle pull, séries temporelles (metric + labels).

### Types de métriques
| Type | Usage |
|---|---|
| Counter | Valeur qui ne fait qu'augmenter (ex : requêtes totales) |
| Gauge | Valeur qui monte/descend (ex : mémoire utilisée) |
| Histogram | Distribution + quantiles calculés côté requête (`histogram_quantile`) |
| Summary | Quantiles calculés côté client — éviter si agrégation multi-instance nécessaire |
| Native Histogram | Meilleure précision, moins de cardinalité que les histograms classiques — à privilégier si version Prometheus récente |

### PromQL essentiel
```promql
# Taux d'erreur sur 5 minutes
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# Latence p99 depuis un histogram
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Burn rate error budget (fenêtre courte + longue combinées, pattern Google SRE)
```

### Cardinalité — piège n°1
Ne jamais utiliser en label une valeur à cardinalité illimitée (user_id, request_id, IP brute) → explosion mémoire du TSDB. Vérifier avec `prometheus_tsdb_symbol_table_size_bytes` et le nombre de séries actives.

### Recording Rules vs Alert Rules
- **Recording rules** : pré-calculer les requêtes coûteuses/fréquentes (dashboards)
- **Alert rules** : déclenchement sur seuil, toujours lié à un SLO, jamais un seuil arbitraire sans justification

### Fédération / Remote Write
N'introduire une fédération multi-cluster ou du remote write vers un stockage long terme (Mimir/Thanos) que si le besoin de rétention/cross-cluster est réel — sinon un Prometheus local suffit (KISS).

---

## Grafana

- **Dashboards** : chaque panel doit répondre à une question précise (pas de "dashboard fourre-tout")
- **Variables** : templating par env/service pour un dashboard réutilisable
- **Alerting** : centraliser dans Grafana ou dans Prometheus Alertmanager, pas les deux en parallèle sur le même signal (duplication de bruit)
- **Provisioning** : dashboards as code (JSON/YAML versionné en Git), jamais édités uniquement en UI en prod

Datasources typiques : Prometheus (metrics), Loki (logs), Tempo (traces), Mimir (metrics long terme), Pyroscope (profiling continu).

---

## Loki

Logs indexés par **labels** seulement (pas full-text index) → coût très inférieur à Elasticsearch, adapté si les requêtes se filtrent bien par label (service, namespace, level).

- **LogQL** : proche de PromQL
```logql
{namespace="prod", app="backend"} |= "ERROR" | json | line_format "{{.message}}"
```
- **Labels** : garder un set de labels limité et stable (comme Prometheus) — ne pas mettre de champ à haute cardinalité en label, le mettre dans le contenu du log et parser via pipeline
- **Retention/Compaction** : définir une politique claire par criticité de log (app logs courts, audit logs longs)

**Choix Loki vs Elasticsearch** : Loki si les logs sont bien structurés et filtrables par label ; Elasticsearch si recherche full-text complexe/ad-hoc nécessaire.

---

## Tempo

Backend de traces distribuées, généralement couplé à OTel + Grafana.

- **Span** : unité de travail (un appel, une requête DB)
- **Trace** : ensemble de spans liés par un `trace_id`
- **Sampling** : cohérent avec la config du Collector OTel en amont
- **Dependencies** : la vue "service graph" dérivée des traces aide à repérer les dépendances cachées entre services

**Corrélation** : la vraie valeur vient de la corrélation logs ↔ traces ↔ métriques via `trace_id` exposé dans les logs structurés. Sans cette corrélation, avoir les 3 piliers séparément a peu de valeur ajoutée.

---

## Elasticsearch / Kibana

Plus lourd à opérer que Loki mais recherche full-text riche.

- **Index/Shard/Replica** : dimensionner selon le volume — trop de shards petits = overhead cluster
- **ILM (Index Lifecycle Management)** : hot → warm → cold → delete, automatiser sinon coût de stockage qui dérive
- **Mapping/Analyzer** : définir un mapping explicite en prod (éviter le dynamic mapping incontrôlé qui peut faire exploser le nombre de champs)
- **Query DSL** : privilégier `filter` (mis en cache, pas de scoring) à `must` quand le scoring de pertinence n'est pas nécessaire

**Kibana** : Discover pour l'exploration ad-hoc, Lens pour les dashboards visuels, Alerting couplé aux règles de détection.

---

## Choisir sa stack — décision KISS

| Contexte | Stack recommandée |
|---|---|
| Petite équipe, budget limité, K8s | Prometheus + Grafana + Loki + Tempo (stack "LGTM", légère à opérer) |
| Besoin fort de recherche full-text sur logs | Ajouter Elasticsearch/Kibana en complément, pas en remplacement des métriques |
| Multi-cluster, rétention longue | Ajouter Mimir/Thanos pour les métriques — seulement si le besoin est confirmé |
| Démarrage d'un nouveau service | OTel SDK dès le départ (metrics + traces + logs corrélés par trace_id) plutôt que rajouter l'instrumentation après coup |

**Principe directeur** : ne jamais recommander la stack la plus complète — recommander celle qui répond au besoin mesuré avec le moins de composants à opérer.