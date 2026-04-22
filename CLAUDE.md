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
3. **Phase 2** — Fetch comments for posts with ≥ `MIN_COMMENTS_FOR_CRAWL` (=5); each post queried 3 times (sort=best/new/old) to maximize unique comments discovered
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
- `INCLUDE_GENERAL = True` in crawler.py — whether to include the high-volume "general" submolt (1.56M posts, capped at 100k)

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

## Dataset — Stato attuale (aprile 2026)

- Agenti: ~27.107 | Post: ~311.448 | Commenti: ~794.814 | Archi: ~191.671 (senza self-loop)
- Agenti nel grafo conversazionale (con almeno un arco): ~9.096
- Agenti fuori dal grafo: ~18.011 (solo post top-level o sotto soglia MIN_COMMENTS=5)
- Claimed: ~26.738 / 27.107 — il 98.9% è claimed
- Self-loop rimossi: ~3.585 (1.9% degli archi) — agenti che rispondono a se stessi

## Decisioni metodologiche fissate

Queste non vanno rimesse in discussione senza motivo tecnico nuovo:

- `is_claimed` è variabile **esplorativa**, NON target di classificazione (imbalance + ambiguità semantica)
- Self-loop rimossi dal grafo strutturale
- Subset analitico = 9.096 agenti nel grafo conversazionale
- `MIN_COMMENTS_FOR_CRAWL = 5` — post con meno commenti non generano thread multi-livello
- RobustScaler senza clipping — outlier preservati perché sono segnale (hub del grafo)
- `unique_targets` ed `egonet_size` esclusi dalla ML matrix per ridondanza
- SQLite sufficiente, no migrazione a PostgreSQL
- Jaccard ≥ 0.3 come soglia di overlap per validazione cross-metodo (RQ3)

## Artefatti prodotti

Oltre al DB, il progetto ha questi artefatti persistenti:

- `data/feature_matrix_graph_v1.parquet` — 9.096 × 20, zero NaN, post log-transform
- `data/feature_matrix_scaled_v1.parquet` — scalato con RobustScaler
- `data/scaler_v1.joblib` — RobustScaler serializzato

## Analysis

Notebooks sono in `notebooks/`:
- `01_graph_analysis.ipynb` — analisi esplorativa del grafo (da rieseguire: output obsoleti)
- `02_popolazione_table_agent_feature.ipynb` — calcolo feature di rete e UPDATE in agent_features
- `03_sanity_check_agent_features.ipynb` — data quality e sanity check su agent_features
- `04a_nan_investigation.ipynb` — investigazione NaN per ogni feature
- `04b_feature_matrix.ipynb` — costruzione feature matrix pulita
- `04c_scaling.ipynb` — scaling con RobustScaler
- `src/testQuery.ipynb` — ad-hoc SQL exploration

**Prossimi passi**: Fase A — caratterizzazione strutturale del grafo (RQ1). Notebook `05_structural_characterization.ipynb` da creare con: fit power-law su degree distribution, statistiche globali, componenti connesse, Louvain sul grafo conversazionale.