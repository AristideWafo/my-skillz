# Fiabilité & Opérations — Incidents, Chaos Engineering, DR, Capacity Planning, FinOps

Table des matières :
- [Gestion d'incident](#gestion-dincident)
- [Postmortem / RCA](#postmortem--rca)
- [Patterns de résilience](#patterns-de-resilience)
- [Chaos Engineering](#chaos-engineering)
- [Disaster Recovery](#disaster-recovery)
- [Capacity Planning](#capacity-planning)
- [FinOps](#finops)

---

## Gestion d'incident

### Cycle de vie standard
```
Détection (alerte/signalement) → Triage (sévérité) → Mobilisation
  → Diagnostic (méthode 8 étapes du SKILL.md principal)
  → Mitigation (stopper l'impact, pas forcément corriger la cause)
  → Résolution → Communication → Postmortem
```

**Principe clé** : en incident, **mitiger avant de corriger**. Rollback ou failover est presque toujours plus rapide et plus sûr qu'un correctif à chaud sous pression.

### Runbook — structure minimale
```markdown
## Alerte : <nom>
**Symptôme observé** :
**Impact business** :
**Vérifications immédiates** (dans l'ordre) :
1. ...
**Mitigation rapide** :
**Escalade si non résolu en X min** : contact / équipe
```
Un runbook doit être écrit **dès la 2e occurrence** d'une même alerte — sinon dépendance à la mémoire humaine (violation du principe KISS n°8).

### Communication en incident
- Un seul canal de vérité (ex : thread Slack dédié), timestampé
- Statut régulier même sans nouvelle info ("toujours en investigation") — évite les questions redondantes
- Escalade définie par sévérité, pas au feeling

---

## Postmortem / RCA

**Blameless obligatoire** : le postmortem cherche des causes systémiques, pas un coupable.

### Structure
```markdown
# Postmortem — <titre>
## Résumé (2-3 lignes)
## Impact (durée, users/services affectés, SLO consommé)
## Timeline (horodatée, factuelle)
## Cause racine (Five Whys)
## Ce qui a bien fonctionné
## Ce qui a mal fonctionné
## Actions correctives (owner + deadline obligatoires)
```

### Five Whys — exemple d'application
```
Pourquoi le service est down ? → OOM Killed
Pourquoi OOM ? → Fuite mémoire sur le endpoint /export
Pourquoi une fuite ? → Connexions DB non fermées en cas d'exception
Pourquoi non fermées ? → Absence de try-with-resources sur ce chemin de code
Pourquoi absent ? → Pas de review checklist sur la gestion des ressources
```
→ L'action corrective porte sur la **dernière cause systémique actionnable**, pas sur le symptôme initial.

**Anti-pattern** : postmortem sans action assignée avec deadline → 90% de chances qu'il se reproduise (constat DevOps Handbook).

---

## Patterns de résilience

| Pattern | Rôle | Piège courant |
|---|---|---|
| **Circuit Breaker** | Arrêter d'appeler un service défaillant | Seuils mal calibrés → ouverture trop tardive ou trop agressive |
| **Retry** | Réessayer un appel transitoire | Sans backoff exponentiel + jitter → amplifie une panne (retry storm) |
| **Timeout** | Éviter l'attente infinie | Timeout absent = thread pool épuisé en cascade |
| **Bulkhead** | Isoler les ressources par dépendance | Un pool de connexions partagé = une dépendance lente bloque tout |
| **Rate Limiting** | Protéger un service de la surcharge | Absent = un client agressif dégrade tout le monde |
| **Graceful Degradation** | Dégrader un service plutôt que le couper | Non prévu en amont = tout ou rien en cas de panne partielle |

**Principe** : ces patterns se combinent (ex : Retry + Circuit Breaker + Timeout ensemble), mais n'introduire que ceux justifiés par un incident réel ou un risque identifié — pas systématiquement partout (YAGNI).

---

## Chaos Engineering

Objectif : valider la résilience **avant** que la panne réelle n'arrive, pas générer du chaos gratuit.

### Démarche KISS
1. Définir l'état stable mesurable (ex : latence p99 < 200ms, error rate < 1%)
2. Formuler une hypothèse ("si le pod X meurt, le trafic bascule sans impact SLO")
3. Injecter la panne en **environnement contrôlé d'abord** (staging), puis prod avec blast radius limité
4. Comparer aux métriques de l'état stable
5. Corriger si hypothèse invalidée, documenter si validée

Expériences typiques : kill pod, latence réseau injectée, saturation CPU/mémoire, panne AZ simulée, panne dépendance externe (mock).

**Anti-pattern** : faire du chaos engineering en prod sans avoir d'abord un monitoring capable de détecter l'impact en temps réel — on injecte une panne qu'on ne peut pas mesurer.

---

## Disaster Recovery

### Métriques clés
- **RTO (Recovery Time Objective)** : durée max acceptable d'indisponibilité
- **RPO (Recovery Point Objective)** : perte de données max acceptable

### Stratégies par ordre de coût croissant
| Stratégie | RTO/RPO | Coût |
|---|---|---|
| Backup/Restore | Heures/jours | 💰 |
| Pilot Light (infra minimale en veille) | Dizaines de minutes | 💰💰 |
| Warm Standby (infra réduite active) | Minutes | 💰💰💰 |
| Multi-site Active-Active | Quasi nul | 💰💰💰💰 |

**Principe KISS** : ne pas viser le Multi-site Active-Active si le RTO/RPO métier tolère un Warm Standby — le coût opérationnel et financier doit être justifié par le besoin réel, pas par défaut.

**Backup** : tester la restauration régulièrement — un backup jamais restauré n'est pas un backup validé.

---

## Capacity Planning

Démarche : **mesurer la tendance avant d'autoscaler ou de sur-provisionner**.

1. Baseline actuelle (CPU/mémoire/IO/réseau sur une période représentative, pics inclus)
2. Tendance de croissance (linéaire ? saisonnière ? événementielle ?)
3. Marge de sécurité réaliste (pas 10x "au cas où")
4. Coût du sur-provisionnement vs coût d'un incident de saturation
5. Load testing / stress testing pour valider les limites réelles avant qu'elles ne soient atteintes en prod

**Anti-pattern** : dimensionner sur une estimation "à la louche" sans données historiques — toujours mesurer avant de provisionner.

---

## FinOps

Le coût est un signal SRE comme un autre — pas un sujet séparé.

- **Rightsizing** : instances/pods dimensionnés sur l'usage réel mesuré, pas sur une estimation initiale jamais révisée
- **Reserved Instances / Savings Plans** : pour la charge stable et prévisible
- **Spot Instances** : pour workloads tolérants à l'interruption (batch, CI runners) — jamais pour du stateful critique sans stratégie de reprise
- **Budgets/Cost Explorer** : alerter sur une dérive de coût comme sur une dérive de latence — même logique d'observabilité appliquée au coût

**Principe** : une architecture "élégante" mais dont le coût opérationnel n'est jamais mesuré n'est pas une architecture KISS.