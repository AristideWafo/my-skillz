---
name: grafana-dashboard-builder
description: >
  Cree, audite et simplifie des dashboards Grafana selon une philosophie KISS stricte, pour
  Jerry (Cloud Architect/DevOps). Trigger sur : creer un dashboard, dashboard Grafana, dashboard
  JSON, review/audit de dashboard, "ce dashboard est trop charge", panels, PromQL/LogQL pour
  dashboard, variables Grafana, alerting base sur SLO/burn rate, alert fatigue, dashboard
  incident response, "quelle metrique garder", simplifier un dashboard existant. Trigger meme
  sans le mot "dashboard" explicite si Jerry decrit un ecran de monitoring surcharge ou demande
  quelles metriques afficher pour un service. Ne PAS utiliser pour la theorie observabilite
  generale (SLI/SLO, choix de stack, OpenTelemetry) - rediriger vers le skill
  sre-observability-expert pour ca, ce skill-ci est uniquement l'action dashboard.
---

# Grafana Dashboard Builder — KISS : créer, auditer, simplifier

> Règle d'or : **"Si ça n'aide pas à détecter ou résoudre un incident plus vite,
> ça n'a pas sa place sur le dashboard."**

Ce skill fait **3 choses seulement** : créer des dashboards utiles, auditer des dashboards existants, simplifier tout ce qui est trop complexe. Rien d'autre.

Pour la théorie observabilité (Golden Signals, SLI/SLO/SLA, choix de stack, corrélation logs/traces/metrics) → voir le skill `sre-observability-expert`. Ce skill-ci ne réexplique pas la théorie, il l'applique à la construction concrète de dashboards.

---

## Méthode obligatoire — dans cet ordre

Ne jamais commencer par "quels panels ajouter". Toujours partir du besoin :

1. **Comprendre le système** — quel service, quelle architecture, quelles dépendances ?
2. **Identifier l'objectif business** — qu'est-ce que ce dashboard doit permettre de décider ?
3. **Définir le SLO concerné** (ou le demander si absent — ne pas inventer un SLO)
4. **Choisir les métriques minimales** qui servent ce SLO — pas plus
5. **Construire** le dashboard avec la hiérarchie de lisibilité (voir plus bas)
6. **Challenger chaque panel** avec les questions du Dashboard Critic
7. **Simplifier** — retirer tout ce qui ne passe pas le test du Critic

Si Jerry demande directement "crée-moi un dashboard pour X" sans contexte, poser une seule question ciblée si nécessaire (ex : "cible SRE en garde ou dashboard produit pour la direction ?") plutôt que de deviner.

---

## Règles KISS strictes — non négociables

**1 dashboard = 1 objectif.** Exemples valides : "API Health", "DB Performance", "Error Monitoring". Un dashboard qui mélange ces sujets doit être scindé.

### Interdictions
- Plus de 10 panels sur un seul dashboard
- Dashboard multi-sujets ("tout sur un écran")
- Requête PromQL/LogQL complexe sans commentaire justifiant pourquoi elle ne peut pas être plus simple
- Duplication de la même métrique sous deux formes différentes sur le même dashboard
- Graphique décoratif qui ne sert aucune décision (jauge esthétique, compteur vanity)

### Règles de simplification
- Une métrique qui ne sert pas une décision → **supprimer**
- Un dashboard qui nécessite une explication orale pour être compris → **trop complexe**
- Si un SRE doit réfléchir pour comprendre l'écran → **mauvais design**
- Cible : **3 à 5 KPI maximum** par dashboard, le reste en détail accessible en drill-down

---

## Dashboard Critic — à appliquer sur CHAQUE panel

Avant d'ajouter ou de garder un panel, répondre aux 4 questions. Si une seule reste sans réponse claire → supprimer ou déplacer en dashboard de debug secondaire.

1. **Pourquoi cette métrique existe-t-elle ?**
2. **Quel incident permet-elle de détecter ?**
3. **Quelle action déclenche-t-elle si elle sort de la norme ?**
4. **Est-elle corrélée à un SLO existant ?**

En audit d'un dashboard existant : passer chaque panel par ce filtre et produire une liste 🔴 (à supprimer) / 🟡 (à questionner avec Jerry) / 🟢 (justifié).

---

## Hiérarchie de lisibilité — structure standard

```
┌─────────────────────────────────────┐
│  TOP — KPIs (3-5 max)                │  ← lisible en 10 secondes
│  Golden Signals du service            │
├─────────────────────────────────────┤
│  MIDDLE — Tendances                  │  ← contexte temporel
│  Comparaison période, %, évolution    │
├─────────────────────────────────────┤
│  BOTTOM — Debug détaillé             │  ← pour investigation active
│  Breakdown par instance/endpoint/pod  │
└─────────────────────────────────────┘
```

**Test de validation** : un SRE en astreinte doit comprendre l'état du système en **10 secondes** en regardant seulement la section TOP. Si ce n'est pas le cas, le dashboard a échoué à son objectif "incident response".

Templates de panels prêts à l'emploi par cas d'usage → `references/dashboard-templates.md`

---

## Pratique Grafana — l'essentiel, pas plus

- **JSON structuré** : versionné en Git, provisionné (jamais un dashboard critique édité uniquement en UI en prod)
- **Variables** : utiliser pour factoriser par env/service/namespace — mais une variable qui complique la lecture sans réduire le nombre de dashboards n'a pas de valeur
- **PromQL/LogQL de base** : privilégier les requêtes simples et lisibles ; une requête à 5 lignes avec 3 agrégations imbriquées doit être justifiée ou découpée en recording rule
- **Panels "noisy"** : détecter les graphiques dont la ligne bouge en permanence sans seuil clair — souvent un signal de bruit plutôt qu'une métrique actionnable

Cheatsheet requêtes → `references/promql-logql-cheatsheet.md`

---

## Alerting intelligent — lié au dashboard, pas séparé

- Alertes **basées sur SLO/burn rate**, jamais sur un seuil technique arbitraire ("CPU > 80%" sans lien avec un impact utilisateur)
- **Burn rate multi-fenêtre** (courte + longue) pour équilibrer réactivité et faux positifs
- **Une alerte = une action possible.** Si personne ne sait quoi faire en la recevant, elle ne devrait pas exister
- **Alert fatigue** = signal d'alarme immédiat qu'il y a trop d'alertes non actionnables → auditer avec le Dashboard Critic (mêmes 4 questions, appliquées aux alertes)

---

## Anti-patterns — révision rapide

| Anti-pattern | Correction |
|---|---|
| Dashboard "tout sur un écran" (>10 panels, plusieurs sujets) | Scinder en dashboards mono-objectif |
| Métrique sans SLO associé | Retirer ou relier explicitement à un SLO |
| Alerte sur seuil technique random | Reformuler en alerte SLO/burn rate |
| Requête PromQL complexe non commentée | Simplifier ou documenter pourquoi c'est nécessaire |
| Panel décoratif (gauge esthétique sans seuil actionnable) | Supprimer |
| Dashboard jamais mis à jour depuis un incident | Revoir après chaque postmortem (lien avec `sre-observability-expert`) |

---

## Ce que ce skill produit

**Création** — dashboard structuré (JSON ou description de panels) avec 3-5 KPI top, hiérarchie top/middle/bottom, requêtes commentées.

**Audit** — review panel par panel avec verdict 🔴/🟡/🟢 via le Dashboard Critic, recommandations de suppression/simplification.

**Simplification** — d'un dashboard existant trop chargé vers une version réduite testée sur "compréhensible en 10 secondes".

**Toujours répondre en français**, sauf demande explicite contraire.