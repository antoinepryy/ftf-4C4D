# Prototype — infrastructure de calcul distribué (4C4D + Align.)

Date: 2026-06-23
Statut: design validé

## Objectif

Prototype local d'une infrastructure SaaS de calcul distribué. Un service de
calcul lourd (image Docker « 4C4D + Align. ») est exécuté à la demande pour
plusieurs clients, chaque run produisant des *checkpoints* stockés dans un S3
par client. Le but est de valider l'architecture d'industrialisation de cette
prestation de calcul distribuée.

Le vrai calcul 4C4D n'est pas disponible : le prototype le remplace par un
**worker stub** respectant le même contrat d'entrée/sortie, pour que la vraie
image puisse être branchée plus tard sans changer l'infrastructure.

### Hors périmètre (prototype)

- Authentification / gestion d'identité
- Billing, facturation, quotas
- Auto-scaling / orchestration cloud (k8s)
- Le vrai algorithme 4C4D + Align. (remplacé par un stub)

## Architecture

Tout tourne via `docker-compose`. Cinq services :

```
client (curl) ──POST run──▶ API (FastAPI) ──enqueue──▶ Redis (broker Celery)
       ◀──run_id / état──         │                          │ consume
                                  │ metadata                 ▼
                            Postgres (runs)  ◀─status──  Worker (Celery)
                                                              │ docker run
                                                              ▼
                                                     stub compute container
                                                    read/write │
                                                               ▼
                                                     MinIO (S3 local)
```

| Service        | Rôle                                                        |
|----------------|-------------------------------------------------------------|
| `api`          | API REST FastAPI. Crée les runs, les enqueue, expose l'état |
| `worker`       | Worker Celery. Lance le container de calcul, suit son état  |
| `redis`        | Broker / backend Celery                                     |
| `postgres`     | Metadata des runs (state store)                             |
| `minio`        | S3 local (stockage checkpoints par client)                  |
| `minio-init`   | Job one-shot : crée le bucket `ftf` au démarrage            |

L'image `stub-compute` est construite séparément (pas un service long-running) ;
le worker l'instancie à la demande.

### Décisions clés

- **Le worker lance un vrai container** (docker-out-of-docker) via le SDK Docker,
  avec le socket `/var/run/docker.sock` monté dans le worker. Fidèle au modèle de
  prod où un job = un container. C'est l'élément central que le prototype valide.
- **Postgres** comme state store des runs (proche prod), distinct de Redis (broker).
- **Isolation par préfixe S3** dans un bucket unique `ftf`.

## Composants

### 1. Image stub-compute (contrat I/O)

Container éphémère, lancé une fois par run. Remplace la vraie image 4C4D.

**Entrée** (variables d'environnement) :

- `CLIENT_ID`, `RUN_ID`
- `NBR_PTS`, `STEP`, `ACTIVE_CHECKPOINT` (optionnel)
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`

**Logique** :

1. Si `ACTIVE_CHECKPOINT` est défini → télécharge ce checkpoint depuis S3 et
   l'utilise comme état de départ (reprise).
2. Simule la charge de calcul : durée ∝ `NBR_PTS / STEP`, écrit des checkpoints
   incrémentaux à intervalles réguliers.
3. Pousse chaque checkpoint vers S3 (voir layout ci-dessous).
4. Code de sortie 0 = succès, ≠ 0 = échec (le worker en déduit l'état du run).

**Sortie S3** : objets JSON `ckpt_000.json`, `ckpt_001.json`, … sous le préfixe
du run.

> Contrat figé : la vraie image 4C4D devra accepter les mêmes variables et écrire
> au même endroit. C'est le seul point de couplage entre infra et calcul.

### 2. Layout S3

Bucket unique `ftf`, isolation par préfixe :

```
ftf/
  clients/<client_id>/
    runs/<run_id>/
      checkpoints/
        ckpt_000.json
        ckpt_001.json
        ...
```

**Reprise** : `active_checkpoint` référence une clé checkpoint d'un run antérieur
du même client. Le worker la transmet au container, qui la lit depuis S3 avant de
calculer. Cas d'usage : Run #2 repart du dernier checkpoint de Run #1.

### 3. API REST (FastAPI)

| Méthode + route                               | Effet                                              |
|-----------------------------------------------|----------------------------------------------------|
| `POST /clients/{client_id}/runs`              | Crée un run, l'enqueue. Body `{nbr_pts, step, active_checkpoint?}`. Retourne `{run_id, status: "queued"}` |
| `GET /clients/{client_id}/runs/{run_id}`      | État du run + liste des clés checkpoints produites |
| `GET /clients/{client_id}/runs`               | Historique des runs du client                      |

États d'un run : `queued | running | done | failed`.

Validation : `nbr_pts > 0`, `step > 0`. `active_checkpoint`, si fourni, doit
exister dans S3 (sinon 400).

### 4. Worker (tâche Celery)

1. Reçoit `run_id` depuis la queue.
2. Passe le run à `running` dans Postgres.
3. Lance le container `stub-compute` via le SDK Docker, params + creds MinIO en env.
4. Attend la fin du container, lit son code de sortie.
5. Succès → `done` + enregistre les clés checkpoints (listées depuis S3) ;
   échec → `failed` + message d'erreur.

### 5. Modèle de données (Postgres)

Table `runs` :

| Colonne             | Type        | Note                                  |
|---------------------|-------------|---------------------------------------|
| `run_id`            | uuid PK     |                                       |
| `client_id`         | text        | indexé                                |
| `nbr_pts`           | int         |                                       |
| `step`              | int         |                                       |
| `active_checkpoint` | text null   | clé S3 du checkpoint de reprise       |
| `status`            | text        | queued/running/done/failed            |
| `checkpoints`       | jsonb       | liste des clés produites              |
| `error`             | text null   |                                       |
| `created_at`        | timestamptz |                                       |
| `updated_at`        | timestamptz |                                       |

## Flux de données (run nominal)

1. Client `POST /clients/c1/runs {nbr_pts: 1000, step: 10}`.
2. API insère le run (`queued`) dans Postgres, enqueue `run_id`, répond `run_id`.
3. Worker consomme, passe à `running`, lance le container.
4. Container calcule, pousse `ckpt_*.json` vers `clients/c1/runs/<run_id>/checkpoints/`.
5. Container sort 0 ; worker passe le run à `done`, enregistre les clés.
6. Client `GET .../runs/<run_id>` → `done` + liste des checkpoints.

## Gestion des erreurs

- **Container échoue** (exit ≠ 0) → run `failed`, message stocké, pas de retry auto
  dans le prototype.
- **active_checkpoint introuvable** → rejeté en 400 à la création (vérif S3).
- **Worker / Docker indisponible** → la tâche Celery échoue ; le run reste
  `running` puis est marqué `failed` par un timeout (durée max configurable).
- **S3 indisponible** → le container sort en erreur → run `failed`.

## Tests

- **Contrat stub** : le container lit `active_checkpoint` et écrit au bon préfixe S3.
- **API** : `POST` crée un run `queued` ; validation des params ; 400 si
  `active_checkpoint` absent.
- **Worker** : transition d'états ; mapping exit code → done/failed.
- **End-to-end** : run → `done` → checkpoints présents dans MinIO.
- **Reprise** : Run #2 avec `active_checkpoint` du Run #1 lit bien le checkpoint source.

## Évolutions futures (post-prototype)

- Brancher la vraie image 4C4D (mêmes variables d'env, même layout S3).
- Auth + billing + quotas par client.
- Bucket par client (isolation forte) au lieu du préfixe.
- Pool de workers / auto-scaling, retries, dead-letter queue.
