# DORA Metrics — Mesurer et Améliorer la Maturité DevOps

## Les 4 Métriques DORA

*Source : DORA State of DevOps Report (2023) + DevOps Handbook (Kim, Humble, Debois)*

Les hautes performances (Puppet Labs, 25000+ professionnels) montrent :
- **30x plus fréquents** en déploiements
- **200x plus rapides** en lead time
- **60x plus performants** en change success rate
- **168x plus rapides** en MTTR

---

## Tableau de Référence

| Métrique | Elite | High | Medium | Low |
|---|---|---|---|---|
| **Deployment Frequency** | On-demand (plusieurs/jour) | 1x/semaine–1x/jour | 1x/mois–1x/semaine | < 1x/mois |
| **Lead Time for Changes** | < 1 heure | 1 jour–1 semaine | 1 semaine–1 mois | > 1 mois |
| **Change Failure Rate** | 0–5% | 5–10% | 10–15% | > 15% |
| **MTTR** (Mean Time to Restore) | < 1 heure | < 1 jour | 1 jour–1 semaine | > 1 semaine |

---

## Définitions Précises

### 1. Deployment Frequency
**"Combien de fois deployons-nous en production par unité de temps ?"**

- Mesure : nombre de déploiements prod par semaine/jour
- Proxy si pas de tracking : fréquence des merges sur `main`
- **Ce qu'elle révèle** : taille des batches, confiance dans le pipeline, culture de livraison

### 2. Lead Time for Changes
**"Combien de temps entre le premier commit et la mise en production ?"**

- Mesure : `timestamp(prod deploy) - timestamp(first commit on feature)`
- Inclut : code review, CI, CD, approbations
- **Ce qu'elle révèle** : taille des PRs, efficacité du pipeline, bottlenecks organisationnels

### 3. Change Failure Rate
**"Quel pourcentage de déploiements causent une dégradation de service ?"**

- Formule : `(déploiements causant incident) / (total déploiements) × 100`
- Un incident = rollback, hotfix urgent, ou dégradation mesurable
- **Ce qu'elle révèle** : qualité des tests, efficacité des gates, qualité du code

### 4. MTTR (Mean Time to Restore)
**"Combien de temps pour restaurer le service après un incident ?"**

- Mesure : de la détection de l'incident à la restoration complète
- Inclut : détection, diagnostic, fix/rollback, validation
- **Ce qu'elle révèle** : observabilité, onboarding runbooks, capacité de rollback

---

## Instrumenter les DORA Metrics

### GitHub Actions — Lead Time Tracking

```yaml
# Dans le CD workflow final (post-prod deploy)
- name: Track DORA Metrics
  run: |
    # Lead time = maintenant - timestamp du premier commit de la PR
    FIRST_COMMIT=$(git log --oneline origin/main..HEAD | tail -1 | cut -d' ' -f1)
    FIRST_COMMIT_TIME=$(git show -s --format="%ct" "$FIRST_COMMIT")
    DEPLOY_TIME=$(date +%s)
    LEAD_TIME_SECONDS=$((DEPLOY_TIME - FIRST_COMMIT_TIME))
    LEAD_TIME_HOURS=$((LEAD_TIME_SECONDS / 3600))
    
    echo "📊 Lead Time: ${LEAD_TIME_HOURS}h"
    
    # Push vers DataDog / Prometheus Pushgateway / CloudWatch
    aws cloudwatch put-metric-data \
      --namespace "DORA/Metrics" \
      --metric-name "LeadTimeSeconds" \
      --value "$LEAD_TIME_SECONDS" \
      --unit Seconds \
      --dimensions Service=backend,Environment=production
```

### Deployment Frequency — CloudWatch

```python
# Lambda ou script post-deploy
import boto3
from datetime import datetime

cw = boto3.client('cloudwatch')

cw.put_metric_data(
    Namespace='DORA/Metrics',
    MetricData=[
        {
            'MetricName': 'DeploymentCount',
            'Dimensions': [
                {'Name': 'Service', 'Value': 'backend'},
                {'Name': 'Environment', 'Value': 'production'},
            ],
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        }
    ]
)
```

### MTTR — Corrélation incidents / déploiements

```yaml
# Grafana dashboard — MTTR query (Prometheus)
# Temps moyen entre alert firing et alert resolved

sum(increase(alertmanager_resolved_total[30d])) /
sum(increase(alertmanager_fired_total[30d]))

# Change Failure Rate — incidents post-deploy
# incidents dans les 24h suivant un déploiement / total déploiements
```

---

## Outils DORA Clés en Main

### LinearB (ex-GitStream)

Dashboard DORA automatique depuis GitHub/GitLab :
- Lead time automatique par PR/commit
- Deployment frequency depuis tags/releases
- Pas de configuration pipeline requise

### DORA Metrics avec GitHub Insights

```yaml
# GitHub Actions — exemple avec Four Keys (Google)
- name: Send deployment event to Four Keys
  uses: GoogleCloudPlatform/fourkeys-action@v1
  with:
    event: deployment
    service: backend
    environment: production
    status: ${{ job.status }}
```

### Tableau de Bord Minimal — Grafana

```json
{
  "panels": [
    {
      "title": "Deployment Frequency (last 30d)",
      "type": "stat",
      "targets": [{
        "expr": "sum(increase(deployments_total{env='production'}[30d]))"
      }]
    },
    {
      "title": "Lead Time P50 (hours)",
      "type": "stat",
      "targets": [{
        "expr": "histogram_quantile(0.5, lead_time_seconds_bucket{env='production'}) / 3600"
      }]
    },
    {
      "title": "Change Failure Rate (%)",
      "type": "stat",
      "targets": [{
        "expr": "100 * rollbacks_total / deployments_total"
      }]
    },
    {
      "title": "MTTR P50 (hours)",
      "type": "stat",
      "targets": [{
        "expr": "histogram_quantile(0.5, mttr_seconds_bucket) / 3600"
      }]
    }
  ]
}
```

---

## Roadmap d'Amélioration DORA

**Partir de Low → Medium → High → Elite**

### Low → Medium (3-6 mois)
Objectifs immédiats :
- [ ] Automatiser tous les tests (unit + integration)
- [ ] Pipeline CI fonctionnel (build + test + scan)
- [ ] Un environnement staging dédié
- [ ] Rollback documenté et testé
- [ ] Déploiements hebdomadaires minimum
- [ ] Alertes de monitoring basiques (uptime, errors)

### Medium → High (6-12 mois)
- [ ] Trunk-Based Development adopté
- [ ] Feature flags pour découpler deploy/release
- [ ] DORA metrics instrumentées et visibles
- [ ] Lead time < 1 semaine
- [ ] Déploiements quotidiens
- [ ] Post-mortems systématiques après incidents

### High → Elite (12-24 mois)
- [ ] Canary ou Blue-Green systématique en prod
- [ ] Progressive Delivery avec rollback automatique
- [ ] Lead time < quelques heures
- [ ] Déploiements on-demand (plusieurs/jour)
- [ ] Chaos Engineering pour tester la résilience
- [ ] Platform Engineering : self-service pour les devs

---

## Corrélation DORA et Business Impact

*Données DORA Report 2023 (25000+ organisations)*

| Profil | Probabilité d'atteindre les objectifs biz | Employee Satisfaction |
|---|---|---|
| Elite | 2x plus probable | 🟢 Très élevée |
| High | 1.5x plus probable | 🟡 Élevée |
| Medium | Référence | 🟠 Moyenne |
| Low | 0.5x moins probable | 🔴 Faible |

**Métriques business corrélées** :
- 50% plus de croissance du market cap sur 3 ans (performers vs non-performers)
- 50% moins de temps passé sur les problèmes de sécurité
- 2.2x plus likely de recommander leur employeur (NPS interne)
- Burnout significativement réduit chez les équipes Elite

---

## Anti-patterns qui Dégradent les DORA Metrics

| Anti-pattern | Métrique impactée | Impact |
|---|---|---|
| Long-lived feature branches (> 1 semaine) | Lead Time ↑↑ | Batches larges = risque élevé |
| Tests manuels uniquement | CFR ↑↑, Freq ↓↓ | Lent + instable |
| Déploiement manuel (SSH, ClickOps) | Freq ↓↓ | Bottleneck humain |
| Pas de rollback automatique | MTTR ↑↑ | Restauration lente |
| Monitoring post-mortem uniquement | MTTR ↑↑ | Détection tardive |
| Freezes de code fréquentes | Freq ↓↓ | Accumulation de risque |
| PRs de > 500 lignes | Lead Time ↑↑, CFR ↑↑ | Review difficile |
| Builds > 15 min | Lead Time ↑↑ | Friction développeurs |

**Règle : builds CI doivent être < 10 minutes.** Au-delà, les développeurs contournent (push direct, désactivation de checks).