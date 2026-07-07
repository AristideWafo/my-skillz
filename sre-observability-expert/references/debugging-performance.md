# Debugging & Performance — Outils, méthode, JVM/Java

Table des matières :
- [Méthode de debugging](#methode-de-debugging)
- [Lecture logs/traces/métriques](#lecture-logstracesmetriques)
- [Dumps (heap, thread, core)](#dumps)
- [Réseau bas niveau](#reseau-bas-niveau)
- [Performance & profiling](#performance--profiling)
- [JVM / Java (contexte Spring Boot)](#jvm--java)

---

## Méthode de debugging

Toujours dans cet ordre (cohérent avec la méthode de raisonnement du SKILL.md principal) :

1. **Logs** — le plus rapide à consulter, souvent suffisant
2. **Métriques** — pour situer dans le temps et confirmer l'ampleur
3. **Traces** — pour localiser précisément le span/service en cause
4. **Dump/profiling** — seulement si 1-3 ne suffisent pas (plus coûteux, souvent nécessite d'agir sur le process live)

**Anti-pattern** : sauter directement à un heap dump ou un `strace` en prod sans avoir d'abord regardé logs/métriques — coût et risque inutiles.

---

## Lecture logs/traces/métriques

- **Logs** : chercher d'abord le pattern (erreur répétée ? corrélée à un déploiement/pic de trafic ?) avant le détail d'une seule ligne
- **Traces** : identifier le span le plus long dans la trace complète — c'est souvent lui la cause, pas le service qui a levé l'erreur visible
- **Métriques** : toujours comparer à une baseline (même heure, jour équivalent) — une valeur seule sans référence ne dit rien

---

## Dumps

| Dump | Quand | Commande (Java/JVM) |
|---|---|---|
| Heap Dump | Fuite mémoire suspectée | `jmap -dump:live,format=b,file=heap.hprof <pid>` |
| Thread Dump | Blocage/deadlock suspecté | `jstack <pid>` ou `kill -3 <pid>` |
| Core Dump | Crash natif | `ulimit -c unlimited` avant relance, puis analyse avec `gdb` |

**Heap Dump** : analyser avec Eclipse MAT ou VisualVM, chercher les objets à forte rétention (dominator tree).
**Thread Dump** : chercher les threads en `BLOCKED` avec la même ressource verrouillée → deadlock ; chercher les threads `RUNNABLE` en boucle → CPU spin.

**Attention prod** : un heap dump sur une JVM avec un gros heap peut geler l'application plusieurs secondes/minutes — planifier si possible, prévenir l'impact.

---

## Réseau bas niveau

- `tcpdump -i any -w capture.pcap port <port>` → toujours limiter avec `-c <count>` ou `timeout` en prod
- **Wireshark** (analyse offline du pcap) : chercher les retransmissions TCP, les handshakes TLS lents, les résolutions DNS répétées
- `perf` : profiling CPU au niveau noyau/syscalls, utile pour des lenteurs non expliquées par l'application elle-même
- **Flamegraph** : générer depuis `perf record` ou un profiler applicatif (async-profiler pour Java) pour visualiser où le temps CPU est réellement passé

---

## Performance & profiling

Ordre de diagnostic performance :

1. **Où est le temps passé ?** (CPU, I/O, réseau, attente lock, GC) — ne pas deviner, profiler
2. **Latence vs Throughput** : optimiser l'un peut dégrader l'autre — clarifier l'objectif avant d'optimiser
3. **Caching** : vérifier le hit ratio avant d'ajouter un niveau de cache supplémentaire
4. **Compression** : gain réseau vs coût CPU — mesurer, ne pas activer par défaut partout
5. **Connection Pooling** : taille du pool alignée sur la capacité réelle du backend, pas un chiffre arbitraire

**Load Testing vs Stress Testing** :
- Load Testing = valider le comportement à la charge attendue
- Stress Testing = trouver le point de rupture (utile pour la capacity planning)

---

## JVM / Java (contexte Spring Boot)

Lecture de logs/JVM sans être développeur Java :

- **GC logs** : `-Xlog:gc*` → chercher les pauses longues (Full GC fréquent = pression mémoire réelle)
- **Actuator** (Spring Boot) : `/actuator/health`, `/actuator/metrics`, `/actuator/prometheus` — première source à vérifier avant tout dump
- **Thread pool épuisé** : symptôme classique = latence qui monte en escalier puis timeouts en cascade → corréler avec `/actuator/metrics/tomcat.threads.busy` ou équivalent
- **OOM** : distinguer `OutOfMemoryError: Java heap space` (heap trop petit ou fuite) de `OutOfMemoryError: Metaspace` (classloading excessif, souvent un leak de classes dynamiques)

**Principe KISS appliqué au debugging Java** : `/actuator` + logs structurés + métriques suffisent dans la majorité des cas — réserver heap/thread dump aux cas où ces sources ne permettent pas de conclure.