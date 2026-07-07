# Infrastructure — Linux, Docker, Kubernetes, Cloud, Réseau, Bases de données

Table des matières :
- [Linux](#linux)
- [Docker](#docker)
- [Kubernetes](#kubernetes)
- [Cloud (AWS/Azure/GCP/OVH/Scaleway/OpenStack)](#cloud)
- [Réseau](#reseau)
- [Reverse Proxy](#reverse-proxy)
- [Bases de données & messaging](#bases-de-donnees)

---

## Linux

Diagnostic dans l'ordre KISS : **ressources → process → réseau → syscalls**.

| Besoin | Commande | Ce qu'elle révèle |
|---|---|---|
| CPU/mémoire globale | `top`, `htop`, `vmstat 1` | Saturation, load average, swap |
| I/O disque | `iostat -x 1`, `sar -d` | Latence disque, %util |
| Process suspect | `ps aux --sort=-%cpu`, `lsof -p <pid>` | Consommation, fichiers ouverts |
| Réseau connexions | `ss -tulpn`, `netstat -tulpn` | Ports ouverts, connexions établies |
| Trace syscalls | `strace -p <pid> -c` | Appels système lents/en boucle |
| Capture paquets | `tcpdump -i any port 443 -w cap.pcap` | Analyse réseau fine (à ouvrir dans Wireshark) |
| Résolution DNS | `dig +trace domain`, `nslookup domain` | Chaîne de résolution, TTL |
| Route réseau | `traceroute`, `ip route` | Saut réseau en échec |
| Logs système | `journalctl -u service -f --since "10 min ago"` | Logs systemd temps réel |
| Firewall | `iptables -L -n -v`, `nft list ruleset` | Règles bloquantes |
| Ressources cgroup | `systemd-cgtop`, `cat /sys/fs/cgroup/.../memory.max` | Limites cgroup v2 |

**Anti-pattern** : lancer `strace`/`tcpdump` en prod sans limiter la durée/le volume (`-c`, `timeout 30s`) → risque de saturer I/O ou disque.

---

## Docker

Principes : image légère, immuable, reproductible.

- **Multi-stage build** → réduire la taille finale, ne jamais shipper les outils de build
- **Layer caching** → ordonner le Dockerfile du moins volatil (deps) au plus volatil (code)
- **Rootless** → éviter `USER root` en prod, définir un user non-privilégié
- **Healthcheck** obligatoire pour tout service critique :
```dockerfile
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1
```
- **Image scanning** : Trivy/Hadolint en CI, bloquant sur HIGH/CRITICAL
- **Networking** : réseau `bridge` custom par stack, jamais `--network host` sauf besoin justifié
- **OCI / signing** : Cosign pour signer les images avant push registry

**Diagnostic conteneur qui crash** :
```bash
docker logs --tail 100 <container>
docker inspect <container> --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
docker stats <container>  # vérifier limite mémoire atteinte
```
`OOMKilled: true` → augmenter la limite mémoire OU corriger une fuite, pas les deux à l'aveugle : mesurer d'abord avec `docker stats` / cgroup.

---

## Kubernetes

### Ordre de diagnostic standard
```
kubectl get pods -n <ns> -o wide          # état global, node, restarts
kubectl describe pod <pod> -n <ns>        # events, probes, limits
kubectl logs <pod> -n <ns> --previous     # logs du crash précédent
kubectl top pod <pod> -n <ns>             # conso réelle vs requests/limits
```

### Probes — piège fréquent
| Probe | Rôle | Erreur classique |
|---|---|---|
| `startupProbe` | Laisse du temps au démarrage lent (JVM) | Absente → liveness tue le pod avant la fin du boot |
| `livenessProbe` | Redémarre si bloqué | Trop stricte → crash loop |
| `readinessProbe` | Retire du Service si pas prêt | Absente → trafic envoyé à un pod pas prêt |

### Scheduling
- **Requests/Limits** : toujours définir des `requests` réalistes (mesurées, pas devinées) → base du scheduling et du QoS class (Guaranteed/Burstable/BestEffort)
- **Affinity/Anti-affinity** : répartir les replicas entre AZ/nodes pour la résilience
- **Taints/Tolerations** : isoler des workloads (ex : nodes GPU, spot instances)
- **PDB (PodDisruptionBudget)** : obligatoire pour éviter qu'un drain de node ne tue tous les replicas d'un coup

### Autoscaling
- **HPA** sur métrique custom (RPS, latence) plutôt que CPU seul si le service est I/O-bound
- **VPA** en mode `Off`/recommendation d'abord, jamais en `Auto` sans validation — risque de restart intempestif
- **Cluster Autoscaler** : vérifier `PodDisruptionBudget` et `terminationGracePeriodSeconds` avant d'activer le scale-down agressif

### Réseau K8s
- **NetworkPolicy** : deny-by-default puis whitelist explicite (Zero Trust)
- **CNI** : Calico/Cilium pour politiques avancées ; vérifier compatibilité avant de choisir
- **CSI** : StorageClass adaptée au besoin (io2/gp3 selon perf requise)

**Anti-pattern** : augmenter les replicas avant d'avoir vérifié que le bottleneck n'est pas une dépendance externe (DB, API tierce) qui ne scale pas avec les pods.

---

## Cloud (AWS/Azure/GCP/OVH/Scaleway/OpenStack)

Approche : raisonner par **besoin fonctionnel**, pas par service spécifique. AWS pris comme référence (expertise principale de Jerry), les mêmes principes s'appliquent aux autres clouds.

| Besoin | Service AWS typique | Point d'attention SRE |
|---|---|---|
| Compute conteneurisé | ECS Fargate / EKS | Fargate = moins d'ops, EKS = plus de contrôle |
| Compute event-driven | Lambda | Cold start, timeout, concurrency limits |
| Load balancing L7 | ALB | Health check path, target group deregistration delay |
| Load balancing L4 | NLB | Pour TCP brut, faible latence |
| DNS + failover | Route53 | Health checks + routing policy (failover/latency/weighted) |
| Cache | ElastiCache (Redis) | Eviction policy, cluster mode selon besoin HA |
| DB relationnelle | RDS | Multi-AZ pour HA, read replicas pour scale lecture |
| Queue/découplage | SQS | DLQ obligatoire, visibility timeout aligné sur le traitement |
| Pub/sub | SNS / EventBridge | EventBridge pour routage par règles, SNS pour fan-out simple |
| CDN | CloudFront | Cache headers corrects sinon origin surchargée |
| Réseau isolé | VPC | Segmentation subnets public/private, NAT Gateway = coût à surveiller |
| Accès sécurisé | IAM | Least privilege, jamais de clé statique si un rôle IAM suffit |

**Principe transverse cloud** : toujours vérifier s'il existe un service managé natif avant de déployer/opérer soi-même un équivalent (ex : ElastiCache avant Redis auto-géré).

---

## Réseau

Diagnostic par couche (modèle mental utile, pas forcément OSI strict) :

1. **Connectivité** : `ping`, `traceroute` → la route existe-t-elle ?
2. **DNS** : `dig`, `nslookup` → résolution correcte, bon TTL ?
3. **Transport** : `ss`, `netstat` → port ouvert, connexion établie ?
4. **TLS** : `openssl s_client -connect host:443` → certificat valide, chaîne complète ?
5. **Application** : logs HTTP, codes retour, latence

Concepts à maîtriser : TCP handshake/retransmission, TLS handshake (impact latence), HTTP/2 multiplexing vs HTTP/1.1 head-of-line blocking, HTTP/3-QUIC (UDP, évite ce blocage), CIDR pour le sizing des subnets, NAT (coût et limite de connexions sortantes), MTU/MSS (fragmentation = latence cachée).

**Anti-pattern fréquent** : diagnostiquer une "lenteur applicative" sans avoir éliminé le DNS et le TLS handshake comme causes (souvent 30-60% de la latence perçue sur des appels externes).

---

## Reverse Proxy

| Outil | Cas d'usage privilégié |
|---|---|
| **Nginx** | Standard généraliste, statique + reverse proxy simple |
| **Traefik** | Auto-discovery Docker/K8s, certificats Let's Encrypt automatiques |
| **HAProxy** | Load balancing L4/L7 haute performance, health checks avancés |
| **Caddy** | Simplicité, HTTPS automatique par défaut (bon choix KISS pour petits projets) |
| **Envoy** | Service mesh, observabilité fine (métriques par route), gRPC |

Choix KISS : ne pas introduire Envoy/service mesh pour un besoin que Traefik/Nginx couvre déjà.

---

## Bases de données & messaging

| Techno | Point de vigilance SRE |
|---|---|
| PostgreSQL | `pg_stat_activity` pour connexions bloquantes, vacuum régulier, connection pooling (PgBouncer) |
| MySQL | Slow query log activé, `SHOW ENGINE INNODB STATUS` pour locks |
| Redis | Politique d'éviction explicite, surveiller `maxmemory`, latence `SLOWLOG` |
| MongoDB | Index manquants = cause n°1 de lenteur, `explain()` systématique |
| Kafka | Lag consumer = métrique clé, partitionnement aligné sur le débit cible |
| RabbitMQ | Queue qui grossit = consumer trop lent ou down, DLQ pour messages en échec |

**Principe** : avant d'ajouter un cache/une queue, vérifier que le problème n'est pas résolu plus simplement par un index manquant ou une requête N+1.