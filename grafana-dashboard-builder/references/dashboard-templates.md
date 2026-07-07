# Templates de dashboards par cas d'usage

Table des matières :
- [API Health](#api-health)
- [DB Performance](#db-performance)
- [Error Monitoring](#error-monitoring)
- [Structure JSON minimale Grafana](#structure-json-minimale-grafana)

Chaque template respecte la règle 3-5 KPI top + hiérarchie top/middle/bottom.

---

## API Health

**Objectif** : un SRE en astreinte comprend en 10s si l'API est en bonne santé.

**TOP (Golden Signals)** :
1. Request Rate (RED - Rate)
2. Error Rate % (RED - Errors)
3. Latency p50/p99 (RED - Duration)
4. Saturation (CPU/mémoire ou thread pool busy)

**MIDDLE** :
- Comparaison vs période équivalente (hier/semaine dernière)
- Répartition par code HTTP (2xx/4xx/5xx)

**BOTTOM (debug)** :
- Latence par endpoint (top 10 les plus lents)
- Erreurs par instance/pod

**Ne PAS inclure** : nombre total de requêtes depuis le déploiement (vanity metric), version du service en gros chiffre décoratif.

---

## DB Performance

**TOP** :
1. Query Latency p99
2. Connections actives / pool max (saturation)
3. Erreurs de connexion / timeouts
4. Replication lag (si applicable)

**MIDDLE** :
- Slow queries (count sur la période)
- Cache hit ratio (si Redis/cache devant la DB)

**BOTTOM** :
- Top requêtes les plus coûteuses (par temps cumulé)
- Locks/deadlocks détectés

**Ne PAS inclure** : métriques disque brutes sans lien avec un seuil d'action (sauf si directement lié à un incident récurrent).

---

## Error Monitoring

**TOP** :
1. Error Rate global (%, lié au SLO error budget)
2. Burn Rate error budget (court terme + long terme)
3. Nombre d'erreurs par service (si multi-service)

**MIDDLE** :
- Tendance error rate sur 24h/7j
- Top erreurs par type/message (groupées)

**BOTTOM** :
- Traces des erreurs récentes (lien vers Tempo si dispo)
- Logs corrélés par trace_id

**Principe** : ce dashboard doit toujours répondre à "sommes-nous en train de consommer notre error budget plus vite que prévu ?" — pas juste lister des erreurs brutes.

---

## Structure JSON minimale Grafana

Squelette à adapter (ne pas générer un JSON complet sans les vraies datasources de Jerry — demander la datasource si absente du contexte) :

```json
{
  "title": "API Health — <service>",
  "tags": ["sre", "api", "<service>"],
  "templating": {
    "list": [
      { "name": "env", "type": "query", "query": "label_values(env)" },
      { "name": "service", "type": "query", "query": "label_values(service)" }
    ]
  },
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": { "h": 6, "w": 6, "x": 0, "y": 0 },
      "targets": [{ "expr": "sum(rate(http_requests_total{service=\"$service\"}[5m]))" }]
    }
  ]
}
```

**Règle** : `gridPos` doit refléter la hiérarchie top/middle/bottom (y croissant = importance décroissante). Un panel TOP a une hauteur (`h`) et une position prioritaire, jamais noyé au milieu de panels secondaires.