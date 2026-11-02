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
`store.py` (SQLite, rétention 90 j, purge auto quotidienne) · `metrics.py` (pur, testé) · `cli.py` · `install.py`. Stocké : horodatage, source, type de limite, %, reset, session_id, coût, tokens de contexte, erreurs. Jamais de prompt, chemin ou secret.

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
| `claude-usage history [--hours 24 --type five_hour]` | relevés + delta |
| `claude-usage tokens` | tokens locaux par fenêtre (≠ quota) |
| `claude-usage doctor` | diagnostic (base, dernier relevé, erreurs, statusLine) |
| `claude-usage prune [--days N]` | purge |

Status line : `5h 72% (+5) | W 68% (+1) | Reset sam. 11:00` (défaut) ; `--format long` → `Session 5h: 72% (+5) | Reset: 1h40 | Semaine: 68% (+1) | Reset: sam. 11:00`. Chaque valeur est suivie du **delta de rythme** `(±N)` : points de quota consommés moins part de fenêtre écoulée. `5h 72% (+5)` = 5 points d'avance sur une consommation linéaire (limite atteinte avant le reset si le rythme tient) ; `W 40% (-10)` = 10 points de marge. Calcul linéaire sur toute la fenêtre (nuits comprises), donc le delta hebdomadaire est souvent négatif tant que l'usage n'est pas continu ; estimation, pas une donnée officielle. Pas de réseau, écriture SQLite seulement si la valeur change (ou toutes les 5 min), ~50 ms, sort toujours en code 0.

Unités : deltas en points de % du quota officiel, vitesses en pts/h — jamais mélangés avec des tokens.

## Désinstallation

```sh
claude-usage uninstall --yes            # retire uniquement une statusLine claude-usage (sauvegarde)
claude-usage uninstall --yes --purge    # + supprime ~/.claude-usage
rm ~/.local/bin/claude-usage            # lien optionnel
```

## Diagnostic

`claude-usage doctor` ; `echo '{}' | claude-usage statusline` ; tests : `python3 -m unittest discover -s tests`. « jamais » comme dernier relevé = pas de `rate_limits` reçu (plan non Pro/Max ou aucune réponse API encore). Variables : `CLAUDE_USAGE_HOME` (base), `CLAUDE_CONFIG_DIR`.
