# claude-usage — suivi local du quota Claude Pro

CLI Python (stdlib uniquement) qui enregistre, via la **status line native** de Claude Code, la progression de la limite 5 h et de la limite hebdomadaire, puis calcule deltas, vitesses et prévisions. Tout reste local (`~/.claude-usage/usage.db`), aucun réseau.

## Sources de données — ce qui est quoi

| | Donnée | Source | Statut |
|---|---|---|---|
| A | Tokens/coût d'une session | `cost.total_cost_usd` (estimation au prix catalogue) + `context_window.*` (contexte courant, **pas** un cumul) via la status line | Documenté, estimation |
| B | Stats locales | Transcripts `~/.claude/projects/**/*.jsonl` (`claude-usage tokens`) | Format non garanti stable ; lecture seule ; hors app Claude/web |
| C | % réel de l'abonnement | `rate_limits.five_hour/seven_day.used_percentage` (status line) | **Officiel**, documenté |
| D/E | Heures de reset | `rate_limits.*.resets_at` (epoch) | **Officiel**, documenté |

Tokens de session ≠ tokens de conversation ≠ quota : le quota est un pourcentage calculé par Anthropic (pondération modèle/cache/charge non publiée). Les tokens bruts ne s'y convertissent pas. Aucun endpoint non documenté n'est utilisé. Les prévisions sont des **estimations**, toujours étiquetées.

## Limites connues

- `rate_limits` n'est fourni qu'aux abonnés Pro/Max, **après la 1re réponse API** d'une session ; chaque fenêtre peut manquer. Sinon la status line affiche le dernier relevé stocké suffixé `~` (ancien) ou `usage n/d`.
- Pas de relevé sans Claude Code CLI ouvert : l'usage de l'app Claude/web apparaît comme un saut entre deux relevés, attribué à l'intervalle entier (vitesses sous-estimées/lissées).
- Pourcentage au grain fourni par Claude Code ; vitesses bruitées sur peu de relevés → « données insuffisantes » (< 3 relevés ou < 10 min sur 5 h).
- Prévision hebdo = moyenne depuis l'ouverture de fenêtre (nuits incluses) ; fiabilité « faible » avant 24 h d'historique. « Plancher » = % si vous arrêtez d'utiliser Claude.
- Un % qui baisse dans la même fenêtre est ignoré ; un changement de `resets_at` (> 2 min) ouvre une nouvelle fenêtre.

## Architecture

```
Claude Code ──stdin JSON──> claude-usage statusline ──> SQLite (relevés dédoublonnés, heartbeat 5 min)
                                  └─> ligne compacte        └─> metrics.py (calculs purs) ──> status/report/forecast/history
```
`ponr.py` (pur, testé : point of no return) · `store.py` (SQLite, rétention 90 j, purge auto quotidienne) · `metrics.py` (pur, testé) · `cli.py` · `install.py`. Stocké : horodatage, source, type de limite, %, reset, session_id, coût, tokens de contexte, erreurs. Jamais de prompt, chemin ou secret.

## Prérequis / installation

Python ≥ 3.9, Claude Code ≥ 2.1 (testé 2.1.312).

```sh
ln -s "$PWD/bin/claude-usage" ~/.local/bin/claude-usage   # optionnel, pour la CLI
claude-usage install          # dry-run : montre le diff de settings.json
claude-usage install --yes    # applique, sauvegarde settings.json.bak-claude-usage-<ts>
```
Refuse d'écraser une `statusLine` existante sans `--force`. Redémarrer Claude Code ensuite. Pour combiner avec une autre status line, appeler les deux depuis un script wrapper (non fourni, YAGNI).

## Utilisation

| Commande | Rôle |
|---|---|
| `claude-usage status` | % officiel, reset, prévision courte |
| `claude-usage report` | deltas (5 min/1 h/5 h/depuis reset), vitesses (instantanée, 1 h, 5 h, pondérée, fenêtre), prévision |
| `claude-usage forecast` | épuisement estimé, % au reset, confiance |
| `claude-usage ponr` | objectif hebdo encore atteignable ? (point of no return, voir plus bas) |
| `claude-usage history [--hours 24 --type five_hour]` | relevés + delta |
| `claude-usage tokens` | tokens locaux par fenêtre (≠ quota) |
| `claude-usage doctor` | diagnostic (base, dernier relevé, erreurs, statusLine) |
| `claude-usage prune [--days N]` | purge |

Status line : `5h 72% (+5) | W 68% (+1) | Reset sam. 11:00 | PONR 🟢 +5pp` (défaut) ; `--format long` → `Session 5h: 72% (+5) | Reset: 1h40 | Semaine: 68% (+1) | Reset: sam. 11:00 | PONR: 🟢 +5pp`. Segment PONR détaillé plus bas, désactivable (`"statusline": false`). Chaque valeur est suivie du **delta de rythme** `(±N)` : points de quota consommés moins part de fenêtre écoulée. `5h 72% (+5)` = 5 points d'avance sur une consommation linéaire (limite atteinte avant le reset si le rythme tient) ; `W 40% (-10)` = 10 points de marge. Calcul linéaire sur toute la fenêtre (nuits comprises), donc le delta hebdomadaire est souvent négatif tant que l'usage n'est pas continu ; estimation, pas une donnée officielle. Pas de réseau, écriture SQLite seulement si la valeur change (ou toutes les 5 min), ~50 ms, sort toujours en code 0.

Unités : deltas en points de % du quota officiel, vitesses en pts/h — jamais mélangés avec des tokens.

## Point of No Return (objectif hebdo)

Question : « au rythme actuel, pourrai-je encore atteindre mon objectif hebdo avant le reset, ou une partie du quota sera-t-elle forcément perdue ? ». Le quota hebdo ne se consomme qu'à travers les fenêtres 5h : chaque heure où la fenêtre 5h n'est pas utilisée détruit de la capacité ; consommer la déplace vers le % hebdo sans perte.

| Grandeur | Calcul | Nature |
|---|---|---|
| `k` | ΣΔhebdo / ΣΔ5h sur les intervalles d'une même fenêtre 5h (14 derniers jours, ≥ 15 pts 5h observés) | appris, confiance faible < 40 pts, moyenne < 150, bonne au-delà |
| capacité 5h | reste de la fenêtre 5h courante (via son `resets_at`) + 100 pts par tranche de 5h jusqu'au reset hebdo, rythme max supposé 20 pts 5h/h pour les tranches finales coupées par le reset hebdo | meilleur cas |
| `max_reachable` | min(100, hebdo + k × capacité) | estimation |
| distance | max_reachable − objectif (pp, ≤ 100 − objectif) | estimation |
| marge brute | hebdo + k × capacité − objectif, non plafonnée | base tendance/ETA |
| vitesse d'approche | −pente (moindres carrés) de la marge brute échantillonnée toutes les 15 min sur `trend_hours` (≥ 2 h, ≥ 4 points, semaine courante seulement) | pp/h, > 0 = la marge fond |
| ETA | marge brute / vitesse, si > 0.1 pp/h, objectif pas encore atteint et avant le reset | affichée seulement si confiance ≠ faible |

États : 🟢 atteignable (ou objectif déjà atteint) ; 🟠 distance < `orange_margin_pp` **ou** ETA < `orange_eta_h` ; 🔴 distance < 0 = inatteignable même en saturant chaque fenêtre 5h restante. Le rouge ne dépend jamais d'un usage élevé, seulement du maximum atteignable. Status line : `… | PONR 🟠 +3pp | ETA 3h20`, `PONR 🔴 -8pp`, `PONR ?` tant que `k` n'est pas mesurable.

Configuration (`~/.claude-usage/config.json`, optionnel ; clé inconnue ou invalide → défaut, listée par `doctor` ; `statusline: false` retire le segment) :
```json
{"weekly_target": 95, "orange_margin_pp": 2, "orange_eta_h": 12, "trend_hours": 12, "statusline": true}
```

Limites du modèle : `k` dépend du modèle utilisé (Opus/Sonnet) et des règles Anthropic, non publiées ; capacité = meilleur cas (fenêtres enchaînées sans sommeil, la fenêtre suivante démarre dès la fin de la précédente) ; tranche coupée par le reset hebdo = rythme max supposé de 20 pts 5h/h ; `k` ré-appris à chaque rendu (pas de cache) ; tendance = comportement des dernières heures, nuits incluses ; trous d'observation gérés par état en escalier (une fenêtre 5h expirée pendant un trou compte comme capacité perdue). Aucune migration : tout se dérive de `limit_samples`.

## Désinstallation

```sh
claude-usage uninstall --yes            # retire uniquement une statusLine claude-usage (sauvegarde)
claude-usage uninstall --yes --purge    # + supprime ~/.claude-usage
rm ~/.local/bin/claude-usage            # lien optionnel
```

## Diagnostic

`claude-usage doctor` ; `echo '{}' | claude-usage statusline` ; tests : `python3 -m unittest discover -s tests`. « jamais » comme dernier relevé = pas de `rate_limits` reçu (plan non Pro/Max ou aucune réponse API encore). Variables : `CLAUDE_USAGE_HOME` (base), `CLAUDE_CONFIG_DIR`.
