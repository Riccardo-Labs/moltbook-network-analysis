# FEATURES.md — Feature Engineering Pipeline

Documentazione della feature matrix prodotta per la fase di analisi (clustering, anomaly detection).

## Dataset di riferimento

- **Sorgente**: `data/moltbook.db`, tabella `agent_features`
- **Subset analitico**: agenti nel grafo conversazionale (`in_degree IS NOT NULL`)
- **Dimensioni**: ~9.096 agenti, 19 feature ML

---

## Feature Matrix — 19 feature finali

### Attività

| Feature | Definizione | Trasformazione | Policy NaN |
|---|---|---|---|
| `n_posts` | Numero di post pubblicati | `log1p` | — (sempre definita) |
| `n_comments` | Numero di commenti scritti | `log1p` | — (sempre definita) |
| `n_comments_received` | Commenti ricevuti su propri commenti | `log1p` | — (sempre definita) |
| `active_days` | Numero di giorni distinti con almeno un'azione | nessuna | — (sempre definita) |

### Temporali

| Feature | Definizione | Trasformazione | Policy NaN |
|---|---|---|---|
| `burstiness_posts` | `(σ - μ) / (σ + μ)` sugli intervalli tra post; range [-1, 1] | nessuna (range già [-1,1]) | fillna(0) — NaN se n_posts < 3 o intervalli degeneri |
| `hour_entropy` | Entropia della distribuzione oraria di attività, normalizzata per `log2(24)`; range [0, 1] | nessuna (già bounded) | — (mai NaN se c'è attività) |

### Comportamentali

| Feature | Definizione | Trasformazione | Policy NaN |
|---|---|---|---|
| `reply_to_post_ratio` | `n_comments / (n_posts + n_comments)`; range [0, 1] | nessuna (già bounded) | fillna(0) — NaN se n_posts=0 e n_comments=0 |
| `self_reply_rate` | Frazione dei propri commenti che sono risposte a se stesso; range [0, 1] | nessuna (già bounded) | fillna(0) — NaN se nessun commento con parent_id |
| `mean_thread_depth` | Profondità media dei thread in cui l'agente ha commentato | nessuna | fillna(0) — NaN se depth NULL nel DB |

### Testuali

| Feature | Definizione | Trasformazione | Policy NaN |
|---|---|---|---|
| `mean_post_length` | Lunghezza media (caratteri) dei post | `log1p` | fillna(0) — NaN se n_posts=0 |
| `std_post_length` | Deviazione standard della lunghezza dei post | `log1p` | fillna(0) — NaN se n_posts=0 |
| `type_token_ratio` | Parole uniche / totale parole su post+commenti; range [0, 1] | nessuna (già bounded) | fillna(0) — NaN se nessun testo |

### Rete (NetworkX sul grafo diretto, senza self-loop)

| Feature | Definizione | Trasformazione | Policy NaN |
|---|---|---|---|
| `in_degree` | Numero di agenti diversi che hanno risposto all'agente | `log1p` | — (tutti gli agenti nel subset hanno in_degree valorizzato) |
| `out_degree` | Numero di agenti diversi a cui l'agente ha risposto | `log1p` | — |
| `pagerank` | PageRank sul grafo diretto | `log10` (epsilon=1e-6) | — |
| `betweenness` | Betweenness centrality normalizzata | `log10` (epsilon=1e-6) | — |
| `local_clustering` | Coefficiente di clustering locale; range [0, 1] | nessuna (già bounded) | — |
| `egonet_density` | Densità del sottografo ego (vicini diretti + nodo); range [0, 1] | nessuna (già bounded) | — |
| `reciprocity_local` | Frazione di archi uscenti reciprocati; range [0, 1] | nessuna (già bounded) | — |

---

## Feature escluse dalla ML matrix

| Feature | Motivo esclusione |
|---|---|
| `unique_targets` | Correlazione > 0.9999 con `out_degree` — ridondante |
| `egonet_size` | Correlazione > 0.9999 con `out_degree` — ridondante |
| `is_claimed` | 98.9% degli agenti è claimed → sbilanciamento estremo, non discriminante |
| `computed_at`, `feature_version` | Metadati operativi |
| `first_activity`, `last_activity` | Timestamp grezzi, non feature ML |

---

## Scelta di RobustScaler

`RobustScaler` scala ogni feature sottraendo la mediana e dividendo per l'IQR (Q75-Q25).
È la scelta corretta rispetto a `StandardScaler` perché:
1. Anche dopo `log1p`, alcune feature (es. `betweenness`, `pagerank`) hanno code pesanti con outlier estremi
2. Media e deviazione standard di queste distribuzioni sono fortemente influenzate dagli hub del grafo
3. Con RobustScaler la maggior parte degli agenti "normali" mantiene valori nell'ordine di grandezza [-1, 3], mentre gli outlier non distorcono la scala

La distribuzione post-scaling presenta valori massimi fino a ~13 per `betweenness` e `burstiness_posts`. Questi valori non sono outlier spuri ma riflettono la natura power-law della rete (pochi hub con centralità estrema) e la sparsità della misura di burstiness (calcolabile solo su agenti con ≥3 post, ~44% del subset). Nessun clipping è stato applicato per preservare il segnale strutturale di agenti con profili eccezionali, coerentemente con l'obiettivo di rilevare pattern di coordinamento.

---

## File prodotti

| File | Descrizione |
|---|---|
| `data/feature_matrix_graph_v1.parquet` | 9096 × 20 (agent_id + 19 feature), zero NaN, log1p applicato |
| `data/feature_matrix_scaled_v1.parquet` | Stesso shape, scalato con RobustScaler |
| `data/scaler_v1.joblib` | RobustScaler serializzato per uso in fase di clustering/inference |

---

## Pipeline di costruzione

```
DB (agent_features)
  → [04a] Verifica NaN (tutti strutturali → OK)
  → [04b] Filtro subset grafo + fillna(0) + log1p → feature_matrix_graph_v1.parquet
  → [04c] RobustScaler → feature_matrix_scaled_v1.parquet + scaler_v1.joblib
```
