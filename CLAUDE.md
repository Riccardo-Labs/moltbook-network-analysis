# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thesis project crawling Moltbook (moltbook.com), a social platform per agenti AI, per ricostruire un **grafo conversazionale** degli agenti e cercare evidenza di coordinamento comportamentale.

**Research question:** esistono gruppi di agenti AI che condividono pattern strutturali, temporali e comportamentali sufficientemente simili da suggerire coordinamento?

**Stato:** analisi completata (giugno 2026). Fase attiva: scrittura tesi.

Per dettaglio feature e policy di preprocessing: vedi `docs/FEATURES.md`.

---

## Running the Code

```bash
source venv/Scripts/activate  # Windows (bash)
python src/crawler.py          # pipeline crawling
python src/feature.py          # feature extraction SQL
jupyter notebook               # analisi
```

Il crawler è **resumable** — usa checkpoint queries, può essere interrotto e riavviato.

---

## Architecture

```
crawler.py (main pipeline)
├── config.py       ← parametri tunable (rate limits, paths, soglie)
├── db.py           ← tutte le operazioni SQLite (no raw SQL fuori da qui)
└── Moltbook API    ← public, no auth
        ↓
data/moltbook.db    ← SQLite (dataset definitivo)

src/feature.py      ← feature SQL-based → agent_features
notebooks/          ← analisi ML e grafici
```

**Pipeline crawler 4 fasi:**
1. Phase 0 — Fetch tutti i submolt (community)
2. Phase 1 — Pagina tutti i post per submolt
3. Phase 2 — Fetch commenti per post con ≥ `MIN_COMMENTS_FOR_CRAWL` (=3); ogni post 3 volte (sort=best/new/old)
4. Phase 3/4 — Fetch profili agenti per tutti gli autori scoperti

**Archi del grafo** da `comments.parent_id`: se A risponde al commento di B → arco A→B.

---

## Database Schema

5 tabelle in `schema.sql`:
- **agents** — profili agenti (nodi). `id` = UUID API. `name` = username univoco. Upserted su refetch.
- **posts** — contenuto con flag `comments_fetched` (0/1) come checkpoint
- **comments** — `parent_id` NULL per top-level, UUID per risposte (fonte degli archi)
- **submolts** — metadati community
- **agent_features** — feature ML, popolata in due fasi

**IMPORTANTE:** `agents.id` (UUID) ≠ `agents.name` (username). Il grafo usa `name` come nodo. La feature matrix usa `id` come `agent_id`. Il join richiede `SELECT id, name FROM agents`.

---

## Pipeline Feature Engineering

### Fase 1 — Feature SQL (`src/feature.py`)
n_posts, n_comments, n_comments_received, active_days, burstiness_posts, hour_entropy,
reply_to_post_ratio, self_reply_rate, unique_targets, mean_thread_depth,
mean_post_length, std_post_length, type_token_ratio, is_claimed

`reply_to_post_ratio = n_comments / (n_posts + n_comments)` → bounded [0,1]

### Fase 2 — Feature di rete (`notebooks/02_...`)
in_degree, out_degree, pagerank, betweenness, local_clustering, egonet_size, egonet_density, reciprocity_local

Grafo costruito **senza self-loop** (`AND c.author_name != p.author_name`).
Self-loop rimossi perché causano egonet_density > 1.0 su grafi diretti.

### Fase 3 — Feature matrix (`notebooks/04a/b/c`)
- `04a` — verifica NaN strutturali
- `04b` — filtro subset grafo, fillna(0), trasformazioni log, → `feature_matrix_graph_v1.parquet`
- `04c` — RobustScaler → `feature_matrix_scaled_v1.parquet` + `scaler_v1.joblib`

**Feature escluse dalla ML matrix:**
- `unique_targets`, `egonet_size` → correlazione > 0.9999 con `out_degree`
- `is_claimed` → sbilanciamento 98.6%, usata solo esplorativa a valle

**Trasformazioni:**
- `log1p`: n_posts, n_comments, n_comments_received, in_degree, out_degree, mean_post_length, std_post_length
- `log10` (con epsilon 1e-8): pagerank, betweenness

---

## Dataset — DEFINITIVO (giugno 2026)

- Agenti: ~27.107 | Post: ~311.448 | Commenti: ~794.814
- Archi (senza self-loop): ~191.671 | Self-loop rimossi: ~3.585 (1.9%)
- Agenti nel grafo conversazionale (≥1 arco): **9.096** — subset analitico
- Claimed: 98.9%

**LIMITE STRUTTURALE API:** dataset al massimo raggiungibile. Cap hard: ~300 commenti distinti per post (3 sort × ~100). Tutti i submolt già paginati integralmente. Documentare in Cap 3 come limite metodologico, quantificando i post con >300 commenti.

---

## Iter Metodologico — Decisioni Adottate

### Clustering (RQ2) — iter v1 → v2

**v1 (fallito):** mutual k-NN su tutte le 19 feature → 1139 cluster, mediana size=1.
Root cause: mutual k-NN troppo restrittivo su feature heavy-tailed → 1085 componenti isolate.
**Fix:** switch a k-means.

**v1 k-means (inadeguato):** k-means con tutte le 19 feature, k=5 → C0 dominante al 64.5% ("inattivi").
Root cause: le 4 feature di volume (n_posts, n_comments, n_comments_received, active_days) catturavano solo l'attività quantitativa, non il comportamento.
**Fix:** escluse feature di volume, forzato k≥8.

**v2 definitivo:** k-means su 15 feature comportamentali, k=15 (silhouette max con k≥8), seed=999.
- silhouette=0.266 | ARI inter-seed=0.960 | cluster bilanciati (max 25.8%)
- Louvain su union k-NN (k=10) come validazione alternativa: Q=0.887

### Anomaly detection (RQ3) — scelta metodi

**OddBall** (strutturale): ego-network (degree, triangoli) → fit power-law → residual score.
Motivazione: cattura anomalie topologiche indipendentemente dalle feature.

**IsolationForest** (feature-based): 300 estimators, contamination=0.10 su 19 feature.
Motivazione: complementare a OddBall, cattura anomalie nello spazio feature.
IsolationForest scelto su LOF per scalabilità e robustezza su alta dimensionalità.

**Criterio cross-validation:** Jaccard ≥ 0.3 su ≥ 3 cluster — pre-registrato.
Criterio formale non soddisfatto (0/15). Difesa: lift >> 1 è la metrica corretta con cluster di dimensioni
variabili. Lift max IsoForest: 21.13x (C0, C10).

### Layer interpretativi (nb08) — decisioni

**Assortatività:** r≈0 globale, ma rapporto intra/inter=2.11x e lift intra C0=480x, C10=455x.
Interpretazione: nessuna segregazione globale, ma C0 e C10 sono "bolle" conversazionali forti.

**NMI Louvain vs k-means:** 0.075 — dimensioni ortogonali. Atteso in multi-layer: comportamento e
struttura conversazionale catturano aspetti diversi. Non è un risultato negativo.

**Feature importance:** Kruskal-Wallis con η² come effect size.
Top discriminanti: betweenness (η²=0.728), burstiness_posts (0.705), out_degree (0.703).
Tutte le 15 feature hanno p=0. η²>0.7 = effect size enormi → cluster ben separati.

---

## Risultati Finali per RQ

### RQ1 — Caratterizzazione strutturale (nb05)
- Nodi: 9.085 | Archi: 60.651 | Densità: 0.000735
- α total degree = 2.149 ± 0.033 (Holtz 2026: 1.70 → rete "normalizzata" nel tempo)
- α in-degree = 2.433 | α out-degree = 1.876
- Avg clustering = 0.144 | Reciprocità = 0.261 (Holtz: 0.197 → più dialogo bidirezionale)
- APL = 3.72 | Small-world sigma = **194.61** → small-world fortissimo
- Q Louvain = 0.417 → struttura comunitaria significativa | 37 community | GCC 98.4%

### RQ2 — Clustering comportamentale (nb06)
- k=15 cluster su 15 feature comportamentali | silhouette=0.266 | ARI=0.960
- C4 più grande (2346, 25.8%) | C8 più piccolo (172, 1.9%)
- Louvain su union k-NN: Q=0.887 → struttura community nella similarity network

### RQ3 — Cross-validation anomaly detection (nb07)
- Criterio Jaccard ≥ 0.3: non soddisfatto (0/15) — geometricamente limitato da cluster piccoli
- **Lift max OddBall: 4.53x** (C12) | **Lift max IsolationForest: 21.13x** (C0, C10)
- C0 e C10: concentrano >50% top-500 anomalie pur essendo 2-3% del totale agenti
- NMI IsoForest K=500: 0.0595

### RQ — Layer interpretativi (nb08)
- Assortatività r = -0.0043 (quasi zero globale)
- Rapporto intra/inter conversazionale = **2.11x**
- **Intra-cluster lift C0 = 480x | C10 = 455x** → bolle conversazionali
- NMI Louvain vs k-means = 0.075 (dimensioni distinte, non ortogonali completamente)
- Feature più discriminanti: betweenness (η²=0.728), burstiness_posts (0.705), out_degree (0.703)

**Finding chiave della tesi:** C0 (n=213) e C10 (n=253) sono double-flagged:
1. IsolationForest lift 21x (RQ3) → anomali nello spazio feature
2. Intra-cluster lift 480x/455x (nb08) → si parlano quasi esclusivamente tra loro
Multi-dimensional evidence di coordinamento.

---

## Cluster Fingerprints (per Cap 5)

Feature top-8 per η²: betweenness, burstiness_posts, out_degree, reciprocity_local, egonet_density, mean_thread_depth, in_degree, pagerank

| Cluster | n | Tratto alto | Tratto basso | Nome suggerito |
|---|---|---|---|---|
| **C0** | 213 | betweenness +2.78, pagerank +2.57, out_degree +2.41 | egonet_density | **Hub anomali** |
| C1 | 372 | — | burstiness -1.60, betweenness -0.36 | Quieti regolari |
| C2 | 386 | burstiness +2.27, in_degree +0.43 | mean_thread_depth | Burster |
| C3 | 392 | reciprocity_local +2.11, betweenness +1.45 | burstiness | Conversatori bidirezionali |
| C4 | 2346 | valori medi su tutto | — | Mainstream |
| C5 | 421 | da verificare fingerprint | — | — |
| C6 | 659 | da verificare fingerprint | — | — |
| C7 | 175 | da verificare fingerprint | — | — |
| C8 | 172 | da verificare fingerprint | — | — |
| C9 | 432 | da verificare fingerprint | — | — |
| **C10** | 253 | da verificare fingerprint | — | **Hub anomali 2** |
| C11 | 725 | da verificare fingerprint | — | — |
| C12 | 518 | da verificare fingerprint | — | — |
| C13 | 1499 | da verificare fingerprint | — | — |
| C14 | 533 | da verificare fingerprint | — | — |

Fingerprint completo in `docs/results_rq_interpretive.md`.

---

## Struttura Tesi (bozza)

**Cap 1 — Introduzione**
- Moltbook come caso studio unico: social network nativo AI, dati pubblici
- RQ principale e perché è rilevante (crescita agenti autonomi, rischio coordinamento)
- Contributo originale: dataset crawlato da zero + pipeline multi-layer
- Struttura della tesi

**Cap 2 — Background e letteratura correlata**
- Bot detection e Coordinated Inauthentic Behavior (CIB) — framework teorico
- Letteratura su Moltbook: Holtz (gen-2026), MoltGraph, Price
- Confronto con approcci esistenti: perché il nostro è diverso (no ground truth, rete nativa AI)
- Metriche di rete per rilevazione coordinamento

**Cap 3 — Dataset e metodologia**
- Architettura crawler (4 fasi, resumable, rate limiting)
- Schema DB, scelte di design (SQLite, upsert, checkpoint)
- Limite strutturale API — quantificazione archi mancanti
- Pipeline feature engineering (fase SQL + fase rete)
- Preprocessing: trasformazioni log, RobustScaler, feature escluse per ridondanza

**Cap 4 — RQ1: Caratterizzazione strutturale**
- Power-law degree distribution (α=2.149)
- Small-world sigma=194.61 — confronto con letteratura
- Reciprocità 0.261 vs Holtz 0.197 — evoluzione temporale
- Struttura comunitaria Q=0.417, 37 community

**Cap 5 — RQ2: Clustering comportamentale**
- Motivazione esclusione feature volume (iter v1→v2)
- Selezione k=15 via sweep silhouette
- Stabilità ARI=0.960 inter-seed
- Heatmap profili cluster + naming (fingerprint)
- Validazione Louvain su similarity network

**Cap 6 — RQ3 + Layer interpretativi: Convergenza delle evidenze**
- OddBall vs IsolationForest: approcci complementari
- Lift come metrica primaria (giustificazione vs Jaccard)
- Layer assortatività: rapporto intra/inter=2.11x
- Double-flagging C0 e C10: anomalia feature + isolamento conversazionale
- NMI Louvain vs k-means: dimensioni ortogonali come risultato positivo
- Feature importance Kruskal-Wallis

**Cap 7 — Discussione**
- Sintesi evidenze multi-layer
- Hedging "coordinamento": cosa possiamo e non possiamo concludere senza ground truth
- Limite API come limite metodologico dichiarato
- Confronto con Holtz: evoluzione rete nel tempo (α, reciprocità)
- Validità dei cluster come archetipi comportamentali

**Cap 8 — Conclusioni**
- Risposta alle RQ
- Contributo originale (dataset + pipeline)
- Lavori futuri: ground truth, temporal analysis, API con auth

---

## Decisioni Metodologiche Fissate

Non rimettere in discussione senza motivo tecnico nuovo:

- `is_claimed` variabile **esplorativa**, NON target di classificazione
- Self-loop rimossi dal grafo strutturale
- Subset analitico = 9.096 agenti nel grafo conversazionale
- `MIN_COMMENTS_FOR_CRAWL = 3` — abbassato da 5 su indicazione relatore; soglia 1-2 scartata per errori 500
- RobustScaler senza clipping — outlier preservati (sono segnale: hub del grafo)
- `unique_targets`, `egonet_size` esclusi per ridondanza con `out_degree`
- SQLite sufficiente, no migrazione PostgreSQL
- Jaccard ≥ 0.3 come soglia (pre-registrata); difesa via lift quando non soddisfatta
- Feature volume escluse dal clustering: misurano *quanto*, non *come*
- IsolationForest scelto su LOF per scalabilità

---

## Notebook Status

| Notebook | Contenuto | Stato |
|---|---|---|
| `01_graph_analysis.ipynb` | analisi esplorativa grafo | output obsoleti, NON rieseguire |
| `02_popolazione_table_agent_feature.ipynb` | feature rete NetworkX → agent_features | COMPLETATO |
| `03_sanity_check_agent_features.ipynb` | data quality sanity check | COMPLETATO |
| `04a_nan_investigation.ipynb` | verifica NaN strutturali | COMPLETATO |
| `04b_feature_matrix.ipynb` | costruzione feature matrix | COMPLETATO |
| `04c_scaling.ipynb` | RobustScaler | COMPLETATO |
| `05_structural_characterization.ipynb` | RQ1 | COMPLETATO — `docs/results_rq1.md` |
| `06_similarity_network.ipynb` | RQ2 — k-means clustering comportamentale | COMPLETATO — `docs/results_rq2.md` |
| `07_cross_validation.ipynb` | RQ3 — OddBall + IsolationForest + Jaccard | COMPLETATO — `docs/results_rq3.md` |
| `08_interpretive_analysis.ipynb` | Layer interpretativi — assortatività, NMI, feature importance | COMPLETATO — `docs/results_rq_interpretive.md` |
| `src/testQuery.ipynb` | ad-hoc SQL exploration | utility |

---

## Artefatti Prodotti

| File | Contenuto |
|---|---|
| `data/feature_matrix_graph_v1.parquet` | 9096 × 20, zero NaN, post log-transform |
| `data/feature_matrix_scaled_v1.parquet` | scalato RobustScaler |
| `data/scaler_v1.joblib` | RobustScaler serializzato |
| `data/cluster_assignments_v1.parquet` | (agent_id UUID, cluster_id), k=15, 9096 righe |
| `data/similarity_network_v1.pkl` | union k-NN graph (k=10, cosine similarity) |
| `docs/results_rq1.md` | risultati RQ1 |
| `docs/results_rq2.md` | risultati RQ2 (sweep k, cluster sizes) |
| `docs/results_rq3.md` | risultati RQ3 (Jaccard, NMI, lift) |
| `docs/results_rq_interpretive.md` | risultati nb08 (assortatività, NMI, fingerprints) |
| `figures/05_degree_distribution_powerlaw.png` | power-law fit |
| `figures/05_component_size_distribution.png` | distribuzione componenti |
| `figures/05_community_size_distribution.png` | community Louvain baseline |
| `figures/06_kmeans_sweep.png` | sweep k silhouette |
| `figures/06_cluster_heatmap.png` | heatmap profili cluster |
| `figures/06_cluster_size_distribution.png` | distribuzione dimensioni cluster |
| `figures/06_cluster_pca.png` | PCA cluster |
| `figures/08_intercluster_flow.png` | matrice 15×15 flussi + lift |
| `figures/08_louvain_vs_kmeans.png` | confusion matrix 37×15 |
| `figures/08_feature_importance.png` | Kruskal-Wallis η² ranking |
| `figures/08_cluster_fingerprints.png` | heatmap z-score top-8 feature |
