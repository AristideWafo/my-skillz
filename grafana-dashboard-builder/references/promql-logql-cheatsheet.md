# Cheatsheet PromQL / LogQL pour dashboards

Requêtes de base, volontairement simples (cohérent avec la règle KISS : privilégier la lisibilité à l'exhaustivité).

---

## PromQL — Golden Signals

```promql
# Rate (RED)
sum(rate(http_requests_total{service="$service"}[5m])) by (service)

# Errors % (RED)
sum(rate(http_requests_total{service="$service", status=~"5.."}[5m]))
/
sum(rate(http_requests_total{service="$service"}[5m]))

# Duration p99 (RED, depuis histogram)
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{service="$service"}[5m])) by (le)
)

# Saturation (USE) — exemple CPU pod
sum(rate(container_cpu_usage_seconds_total{pod=~"$service.*"}[5m])) by (pod)
/
sum(kube_pod_container_resource_limits{resource="cpu", pod=~"$service.*"}) by (pod)
```

## PromQL — Error Budget / Burn Rate

```promql
# Burn rate fenêtre courte (1h) — SLO 99.9%
(
  sum(rate(http_requests_total{status=~"5..", service="$service"}[1h]))
  /
  sum(rate(http_requests_total{service="$service"}[1h]))
) / (1 - 0.999)

# Idem fenêtre longue (6h) — à combiner avec la fenêtre courte pour l'alerte
# Alerte typique : burn rate court > 14.4 ET burn rate long > 14.4 (pattern Google SRE 2%/1h)
```

## PromQL — Saturation DB / Connection Pool

```promql
# Connexions actives vs max
pg_stat_activity_count{state="active"} / pg_settings_max_connections

# Slow queries (exemple exporter Postgres)
rate(pg_stat_statements_calls{query=~".*"}[5m])
```

---

## LogQL — Error Monitoring

```logql
# Taux d'erreur par service depuis les logs
sum by (service) (
  rate({namespace="prod"} |= "ERROR" [5m])
)

# Top messages d'erreur groupés
sum by (message) (
  count_over_time({namespace="prod"} |= "ERROR" | json | line_format "{{.message}}" [1h])
)

# Corrélation avec trace_id pour drill-down depuis un dashboard error
{namespace="prod"} |= "ERROR" | json | trace_id="$trace_id"
```

---

## Règles d'usage dans un dashboard

- Toute requête PromQL/LogQL affichée dans un panel doit tenir en **une ligne lisible** ou être accompagnée d'un commentaire expliquant pourquoi elle est complexe
- Préférer une **recording rule** à une requête PromQL lourde répétée sur plusieurs dashboards (performance + lisibilité)
- Ne jamais utiliser un label à cardinalité illimitée (`user_id`, `request_id`) dans une requête de dashboard — voir `sre-observability-expert/references/observability-stack.md` pour le détail cardinalité