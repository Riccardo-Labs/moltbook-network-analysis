# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a thesis project that crawls the Moltbook public API to reconstruct a **conversational graph of AI agents**. The key insight: since Moltbook has no follower/following API, edges are inferred from comment reply threads — if agent A replies to agent B's comment, an edge A→B is recorded.

**Research question (fissata):** esistono gruppi di agenti AI che condividono pattern strutturali, temporali e comportamentali sufficientemente simili da suggerire coordinamento?

Per framing completo, RQ dettagliate, criterio di successo e indice tesi: vedi `docs/thesis_plan.md`.
Per dettaglio feature e policy di preprocessing: vedi `docs/FEATURES.md`.

## Running the Code

```bash
# Activate virtual environment
source venv/Scripts/activate  # Windows (bash)

# Run the full crawler pipeline
python src/crawler.py

# Run feature extraction (SQL-based features)
python src/feature.py

# Launch Jupyter for analysis notebooks
jupyter notebook
```

The crawler is **resumable** — it uses checkpoint queries to skip already-fetched data, so it can be safely interrupted and restarted.

## Architecture

```
crawler.py (main pipeline)
├── config.py       ← all tunable parameters (rate limits, paths, thresholds)
├── db.py           ← all SQLite operations (no raw SQL in crawler.py)
└── Moltbook API    ← https://www.moltbook.com/api/v1 (public, no auth)
        ↓
data/moltbook.db    ← SQLite (fully populated)

src/feature.py      ← calcola le feature SQL-based per ogni agente e le inserisce
                       in agent_features. Lancia da moltbook-thesis/ con:
                       python src/feature.py
```

**4-phase crawler pipeline in `crawler.py`:**
1. **Phase 0** — Fetch all submolts (communities)
2. **Phase 1** — Paginate all posts per submolt
3. **Phase 2** — Fetch comments for posts with ≥ `MIN_COMMENTS_FOR_CRAWL` (=3); each post queried 3 times (sort=best/new/old) to maximize unique comments discovered
4. **Phase 3/4** — Fetch agent profiles for all authors discovered via comments and posts

**Graph edges** come from `comments.parent_id`: when a comment has a non-null `parent_id`, the comment author replied to the parent comment's author, creating a directed edge.

## Database Schema

5 tables in `schema.sql`:
- **agents** — AI agent profiles (nodes), upserted on refetch to capture karma/follower changes
- **posts** — Content with `comments_fetched` flag (0/1) used as checkpoint
- **comments** — `parent_id` is NULL for top-level posts, UUID for replies (the edge source)
- **submolts** — Community metadata
- **agent_features** — feature tabella per ML, popolata in due fasi (vedi sotto)

All DB operations go through `db.py` — never write raw SQL in crawler or notebooks.

## Key Configuration (`src/config.py`)

- `REQUEST_DELAY = 0.4s` — keeps requests under API limit (~150/min vs ~200/min allowed)
- `POSTS_PER_PAGE = 50` — API maximum
- `COMMENT_SORT_ORDERS = ["best", "new", "old"]` — 3 passes per post to maximize edge discovery
- `INCLUDE_GENERAL = True` in crawler.py — whether to include the high-volume "general" submolt (1.56M posts, nessun cap — paginazione completa)

## agent_features — Pipeline di popolamento

La tabella si popola in due fasi distinte:

**Fase 1 — Feature SQL** (`src/feature.py`):
- Calcola per ogni agente: n_posts, n_comments, n_comments_received, active_days, burstiness_posts, hour_entropy, reply_to_post_ratio, self_reply_rate, unique_targets, mean_thread_depth, mean_post_length, std_post_length, type_token_ratio, is_claimed
- `reply_to_post_ratio` è definita come `n_comments / (n_posts + n_comments)` → bounded [0,1]
- Lancia con: `python src/feature.py` dalla root del progetto

**Fase 2 — Feature di rete** (`notebooks/02_popolazione_table_agent_feature.ipynb`):
- Costruisce il grafo NetworkX **senza self-loop** (filtro `AND c.author_name != p.author_name` nella query)
- Calcola: in_degree, out_degree, pagerank, betweenness, local_clustering, egonet_size, egonet_density, reciprocity_local
- Fa UPDATE sulle righe già esistenti in agent_features
- **IMPORTANTE**: i self-loop vanno esclusi — su grafi diretti causano egonet_density > 1.0

## Feature matrix — Pipeline di preprocessing

Dopo `agent_features`, la feature matrix pronta per ML è costruita in 3 notebook:

- `04a_nan_investigation.ipynb` — verifica che tutti i NaN siano strutturali (zero bug)
- `04b_feature_matrix.ipynb` — filtro subset grafo, fillna(0), log1p/log10 transform, produce `data/feature_matrix_graph_v1.parquet`
- `04c_scaling.ipynb` — RobustScaler, produce `data/feature_matrix_scaled_v1.parquet` + `data/scaler_v1.joblib`

**Feature escluse dalla ML matrix** (documentato in `FEATURES.md`):
- `unique_targets`, `egonet_size` → correlazione > 0.9999 con `out_degree`
- `is_claimed` → sbilanciamento 98.6%, usata solo come variabile esplorativa a valle

**Trasformazioni applicate:**
- `log1p`: n_posts, n_comments, n_comments_received, in_degree, out_degree, mean_post_length, std_post_length
- `log10` (con epsilon 1e-8): pagerank, betweenness
- Nessuna trasformazione: feature già bounded in [0,1] o [-1,1]

## Dataset — Stato attuale (giugno 2026) — DEFINITIVO

- Agenti: ~27.107 | Post: ~311.448 | Commenti: ~794.814 | Archi: ~191.671 (senza self-loop)
- Agenti nel grafo conversazionale (con almeno un arco): ~9.096
- Agenti fuori dal grafo: ~18.011 (solo post top-level o sotto soglia MIN_COMMENTS=3)
- Claimed: ~26.738 / 27.107 — il 98.9% è claimed
- Self-loop rimossi: ~3.585 (1.9% degli archi) — agenti che rispondono a se stessi

**LIMITE STRUTTURALE API (documentare in Cap 3):** Dopo ampliamento crawler (maggio 2026), confermato
che il dataset è al massimo raggiungibile. La piattaforma Moltbook impone limiti strutturali che
impediscono di recuperare dati aggiuntivi oltre quelli già presenti. Specificatamente:
- MAX ~300 commenti distinti per post (3 sort × ~100) — cap hard dell'API pubblica
- Tutti i submolt sono stati paginati integralmente; nessuna fonte di post non ancora crawlata
- Il dataset attuale rappresenta la copertura massima ottenibile dall'API pubblica senza auth
Questo va dichiarato come limite metodologico nel Cap 3, quantificando i post con >300 commenti
come stima della frazione di archi non catturati.

## RQ2 — Risultati clustering (giugno 2026, v2)

**Scelta metodologica:** escluse 4 feature di volume puro (`n_posts`, `n_comments`,
`n_comments_received`, `active_days`) dal clustering. Motivazione: volume misura *quanto*
è attivo un agente, non *come* si comporta. Con volume incluso (v1) k-means produceva
un cluster dominante al 64.5% ("inattivi") che oscurava le differenze comportamentali.
Usate 15/19 feature comportamentali. k=15 selezionato automaticamente (silhouette max con k≥8).

- k=15 cluster | silhouette=0.266 | ARI inter-seed=0.960
- Distribuzione bilanciata: max C4=25.8% (2346 agenti), min C8=1.9% (172 agenti)
- Louvain union k-NN (k=10): Q=0.887, n_community alta — struttura comunitaria confermata

## RQ3 — Risultati cross-validation (giugno 2026)

- **Criterio Jaccard ≥ 0.3 su ≥ 3 cluster: non soddisfatto formalmente** (0/15)
- Motivazione della difficoltà: con cluster piccoli (173-2346) e K fisso, il Jaccard
  massimo raggiungibile per cluster <500 agenti è geometricamente limitato
- **Lift max OddBall: 4.53x** (C12) rispetto al baseline random
- **Lift max IsolationForest: 21.13x** (C0, C10) — C0 e C10 concentrano il 50%+
  delle top-500 anomalie pur rappresentando solo 2-3% del totale agenti
- NMI IsolationForest K=500: 0.0595

**Cluster più anomali per metodo:**
- OddBall: C12 (n=518), C6 (n=659), C13 (n=1499)
- IsolationForest: C0 (n=213, lift 21x), C10 (n=253, lift 21x), C3 (n=392)

## Decisioni metodologiche fissate

Queste non vanno rimesse in discussione senza motivo tecnico nuovo:

- `is_claimed` è variabile **esplorativa**, NON target di classificazione (imbalance + ambiguità semantica)
- Self-loop rimossi dal grafo strutturale
- Subset analitico = 9.096 agenti nel grafo conversazionale
- `MIN_COMMENTS_FOR_CRAWL = 3` — abbassato da 5 a 3 su indicazione del relatore per ampliare il dataset; soglia 1-2 scartata perché post eliminati/vuoti causano errori 500; post con 0 commenti restano esclusi (nessun arco possibile)
- RobustScaler senza clipping — outlier preservati perché sono segnale (hub del grafo)
- `unique_targets` ed `egonet_size` esclusi dalla ML matrix per ridondanza
- SQLite sufficiente, no migrazione a PostgreSQL
- Jaccard ≥ 0.3 come soglia di overlap per validazione cross-metodo (RQ3)

## Artefatti prodotti — aggiornato giugno 2026

- `data/feature_matrix_graph_v1.parquet` — 9.096 × 20, zero NaN, post log-transform
- `data/feature_matrix_scaled_v1.parquet` — scalato con RobustScaler
- `data/scaler_v1.joblib` — RobustScaler serializzato
- `docs/results_rq1.md` — tabella risultati RQ1 (prodotta da nb 05)
- `docs/results_rq2.md` — tabella risultati RQ2 (prodotta da nb 06)
- `data/cluster_assignments_v1.parquet` — (agent_id, cluster_id), k=5 k-means, 9096 righe
- `data/similarity_network_v1.pkl` — union k-NN graph (k=10, cosine similarity)
- `figures/05_degree_distribution_powerlaw.png` — fit power-law in/out/total degree
- `figures/05_component_size_distribution.png` — distribuzione componenti connesse
- `figures/05_community_size_distribution.png` — distribuzione community Louvain baseline

## Analysis — stato notebook

| Notebook | Contenuto | Stato |
|---|---|---|
| `01_graph_analysis.ipynb` | analisi esplorativa grafo | output obsoleti, NON rieseguire |
| `02_popolazione_table_agent_feature.ipynb` | feature di rete NetworkX → agent_features | COMPLETATO |
| `03_sanity_check_agent_features.ipynb` | data quality sanity check | COMPLETATO |
| `04a_nan_investigation.ipynb` | verifica NaN strutturali | COMPLETATO |
| `04b_feature_matrix.ipynb` | costruzione feature matrix | COMPLETATO |
| `04c_scaling.ipynb` | RobustScaler | COMPLETATO |
| `05_structural_characterization.ipynb` | RQ1 — caratterizzazione strutturale | **COMPLETATO** — risultati in `docs/results_rq1.md` |
| `06_similarity_network.ipynb` | RQ2 — similarity network + Louvain | **COMPLETATO** — risultati in `docs/results_rq2.md` |
| `07_cross_validation.ipynb` | RQ3 — OddBall + IsolationForest + Jaccard cross-validation | **COMPLETATO** — risultati in `docs/results_rq3.md` |
| `src/testQuery.ipynb` | ad-hoc SQL exploration | utility |

## Risultati RQ1 (già disponibili — da `docs/results_rq1.md`)

- Nodi: 9.085 | Archi: 60.651 | Densità: 0.000735
- α total degree = 2.149 ± 0.033 (vs Holtz gen-2026: 1.70 → rete "normalizzata")
- α in-degree = 2.433 | α out-degree = 1.876
- Avg clustering = 0.144 (range umano tipico: 0.05–0.17)
- Reciprocità = 0.261 (vs Holtz 0.197 → più dialogo bidirezionale nel tempo)
- APL campionato = 3.72 (vs Holtz 2.91 su grafo più piccolo)
- Small-world sigma = 194.61 → **small-world fortissimo confermato**
- Modularity Q Louvain = 0.417 → struttura comunitaria significativa
- 37 community, GCC 98.4%

## SPRINT FINALE — 5–12 giugno 2026 (obiettivo: tesi completa)

Deadline hard: 16 giugno. Target ideale: 12 giugno per lasciare margine per raffinamenti.

### Giorno 1–2 (5–6 giu) — Notebook 06: RQ2 Similarity Network
Creare `notebooks/06_similarity_network.ipynb`:
1. Carica `feature_matrix_scaled_v1.parquet`
2. Costruisci k-NN graph cosine similarity (sweep k ∈ {5,10,15,20}, scegli k con motivazione)
3. Louvain sulla similarity network → cluster candidati con sensitivity analysis (3 seed)
4. Caratterizzazione cluster: heatmap profili medi, distribuzione dimensioni
5. Salva `data/cluster_assignments_v1.parquet` (agent_id, cluster_id, silhouette opzionale)
6. Salva `data/similarity_network_v1.gpickle`

### Giorno 3 (7 giu) — Notebook 07: RQ3 Cross-validation
Creare `notebooks/07_cross_validation.ipynb`:
- OddBall custom: egonet (n_edges, n_triangles) → fit power-law → anomaly score
- Anomaly detection alternativa: LOF o IsolationForest su feature_matrix_scaled se PyGOD ha problemi dipendenze
- Jaccard tra cluster RQ2 e top-K anomalie → verifica criterio successo (≥3 cluster con Jaccard ≥ 0.3)
- NMI come metrica secondaria tra le due partizioni
Creare `notebooks/08_rq4_claimed.ipynb`:
- Proporzione unclaimed per cluster vs baseline 1.1% → chi si discosta?

### Giorno 4–5 (8–9 giu) — Scrittura tesi Cap 3, 4, 5, 6
Struttura file tesi: scegliere formato con relatore (LaTeX o Word). Scrivere in italiano.
- Cap 3 (Dataset e metodologia): crawler, schema DB, limite API strutturale, feature engineering, pipeline scaling
- Cap 4 (RQ1): usare direttamente `docs/results_rq1.md` + figure notebook 05
- Cap 5 (RQ2): usare risultati notebook 06
- Cap 6 (RQ3): usare risultati notebook 07

### Giorno 6–7 (10–11 giu) — Scrittura Cap 1, 2, 7, 8 + presentazione
- Cap 1 (Introduzione): framing Moltbook, RQ principale, struttura tesi
- Cap 2 (Background): bot detection, CIB framework, letteratura Moltbook (Holtz, MoltGraph, Price)
- Cap 7 (Discussione): sintesi risultati, limite API, validità hedging "coordinamento"
- Cap 8 (Conclusioni): risposta alle RQ, contributo originale, lavori futuri
- Presentazione slide: 1 slide per RQ + risultati chiave

### Giorno 8+ (12–16 giu) — Revisione, raffinamenti, presentazione
- Revisione con supervisore (punti aperti: baseline umana RQ1, MoltGraph ground truth)
- Appendice A: dettaglio 19 feature (da FEATURES.md)
- Lucido: quantificare post >300 commenti (stima archi mancanti per limite API)