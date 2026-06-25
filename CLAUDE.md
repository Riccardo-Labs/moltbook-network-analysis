# CLAUDE.md

Guida per Claude Code quando lavora su questo repository.

Questo file è il **punto di ingresso operativo**: contiene contesto, comandi, schema,
decisioni metodologiche, vincoli di scrittura e **puntatori** alle fonti autoritative.
**Non contiene numeri di analisi** (li tiene la SSoT, vedi sotto): qualunque metrica
va letta dal result file indicato, mai da qui.

**Progetto.** Tesi triennale (UniMI, rel. Prof. Matteo Zignani, consegna luglio 2026).
Crawling di Moltbook (social network di soli agenti AI) → ricostruzione del grafo
conversazionale → ricerca di firme strutturali compatibili con coordinamento.
**Stato:** analisi completata; fase attiva = revisione tesi e allineamento dei numeri
alla SSoT.

---

## 0 — Regola di precedenza (SSoT)

**In caso di conflitto su un dato, l'autorità è il result file; in caso di dubbio sul
result file, si rigenera il notebook.** L'ordine è:

1. `notebooks/NN_*.ipynb` (il calcolo) — autorità ultima
2. `docs/results_rq*.md` (output salvato del notebook) — autorità d'uso
3. `main.tex`, `FEATURES.md`, questo file — **derivati**, si allineano ai precedenti, mai viceversa

**CLAUDE.md e main.tex non devono mai reintrodurre un numero di analisi diverso da
quello del result file.** Se un numero qui sembrasse in conflitto con un result file,
vince il result file e questo file va corretto.

### Mappa SSoT — fonte autoritativa per tipo di informazione

| Informazione | Fonte autoritativa |
|---|---|
| Metriche RQ1 (struttura rete) | `docs/results_rq1.md` ← nb05 |
| Metriche RQ2 (clustering, sweep k, dimensioni cluster) | `docs/results_rq2.md` ← nb06 |
| Metriche RQ3 (OddBall, IsolationForest, Jaccard, NMI, lift) | `docs/results_rq3.md` ← nb07 |
| Layer interpretativi (assortatività, NMI, η², fingerprint, lift intra-cluster) | `docs/results_rq_interpretive.md` ← nb08 |
| Pipeline feature (definizioni, transform, NaN, scaling) | `FEATURES.md` |
| Conteggi dataset (agenti/post/commenti/archi) | query su `data/moltbook.db` (vedi `src/db.py`) |
| Contenuto, struttura e testo della tesi | `main.tex` |
| Bibliografia | `references.bib` |
| Schema DB, comandi, architettura, decisioni, vincoli di scrittura | **questo file** |
| Pianificazione storica / pre-registrazione soglie | `archive/thesis_plan_apr2026.md` (storico, NON operativo) |

> `thesis_index.md` è **obsoleto**: l'indice della tesi è `main.tex`.

---

## 1 — Vincoli di scrittura (validi per ogni testo prodotto)

- **Lingua:** italiano, registro accademico formale; termini tecnici in inglese
  (LLM, betweenness, burstiness, lift, IsolationForest, k-means, GCC, submolt).
- **Hedging epistemico (non negoziabile).** I risultati sono *firme strutturali*, non prove.
  - USA: «firma strutturale compatibile con coordinamento», «compatibile con l'ipotesi di coordinamento».
  - NON usare: «coordinamento dimostrato/provato», «evidenza di coordinamento» senza «compatibile con».
- **Isolamento di C0/C10:** descrivere come «frazione di archi intra-cluster centinaia di
  volte superiore all'attesa casuale (lift di densità)». **NON** scrivere «si parlano quasi
  esclusivamente tra loro»: il flusso grezzo maggiore di C0/C10 è diretto verso altri cluster
  (cfr. `figures/08_intercluster_flow.png`).
- **Convergenza RQ3:** «due fonti (feature matrix; archi del grafo), tre letture
  (k-means genera l'ipotesi, IsolationForest la conferma sulla stessa fonte con logica diversa,
  il lift conversazionale è il segnale indipendente)». **NON** «metodi con dati sorgente
  completamente diversi» (k-means e IsolationForest condividono la feature matrix).
- **Power-law:** «coda compatibile con una power-law (α ≈ 2.15)», dichiarando che non è stata
  testata contro alternative (lognormale). NON «la distribuzione segue una legge di potenza».
- **Small-world σ:** riportare il valore, **non** interpretarne la magnitudine come tratto
  AI-native: σ è gonfiato dalla sparsità (confronto con grafo casuale a clustering ~nullo).
- **Claim di primato:** «prima caratterizzazione *esclusivamente strutturale* del coordinamento
  su Moltbook». Evitare «uno dei dataset più estesi» (de Marzo/MoltNet sono più grandi) e
  «prima caratterizzazione empirica».

---

## 2 — Eseguire il codice

```bash
source venv/Scripts/activate   # Windows (bash)
python src/crawler.py          # pipeline crawling (resumable: checkpoint queries)
python src/feature.py          # feature extraction SQL → agent_features
jupyter notebook               # analisi (notebooks/)
```

---

## 3 — Architettura

```
crawler.py (main pipeline)
├── config.py       ← parametri tunable (rate limit, paths, soglie)
├── db.py           ← TUTTE le operazioni SQLite (nessun raw SQL fuori da qui)
└── Moltbook API    ← pubblica, no auth
        ↓
data/moltbook.db    ← SQLite (dataset definitivo)

src/feature.py      ← feature SQL-based → agent_features
notebooks/          ← analisi ML e grafici
```

**Pipeline crawler (4 fasi):**
0. Fetch di tutti i submolt (community)
1. Paginazione integrale dei post per submolt
2. Commenti per post con ≥ `MIN_COMMENTS_FOR_CRAWL` (=3); ogni post 3 volte (sort = best/new/old)
3/4. Fetch profili agenti per tutti gli autori scoperti

**Archi del grafo:** da `comments.parent_id` — se A risponde al commento di B → arco A→B.

---

## 4 — Schema DB

5 tabelle in `schema.sql`:
- **agents** — nodi. `id` = UUID API; `name` = username univoco. Upsert su refetch.
- **posts** — flag `comments_fetched` (0/1) come checkpoint.
- **comments** — `parent_id` NULL = top-level, UUID = risposta (fonte degli archi).
- **submolts** — metadati community.
- **agent_features** — feature ML, popolata in due fasi.

> **GOTCHA CRITICA — `id` vs `name`.** `agents.id` (UUID) ≠ `agents.name` (username).
> Il **grafo** usa `name` come nodo. La **feature matrix** e `cluster_assignments_v1.parquet`
> usano `id` come `agent_id`. Per incrociare cluster ↔ nodi del grafo serve il join
> `SELECT id, name FROM agents`. Sbagliare questo join produce risultati silenziosamente errati.

---

## 5 — Pipeline feature (sintesi; dettaglio in `FEATURES.md`)

Struttura dei conteggi (orientamento, non valori di analisi):
**22 feature calcolate − 3 ridondanti/sbilanciate (`unique_targets`, `egonet_size`, `is_claimed`)
= 19 feature ML; − 4 di volume (`n_posts`, `n_comments`, `n_comments_received`, `active_days`)
= 15 feature usate nel clustering.**

- Grafo costruito **senza self-loop** (`AND c.author_name != p.author_name`): i self-loop
  causano `egonet_density > 1.0` su grafo diretto; la loro presenza è catturata da `self_reply_rate`.
- Trasformazioni e policy NaN: **vedi `FEATURES.md`** (fonte autoritativa).
- Pipeline matrice: `04a` (verifica NaN) → `04b` (filtro subset + fillna(0) + log) →
  `04c` (RobustScaler). Artefatti in §8.

---

## 6 — Decisioni metodologiche fissate

Non rimettere in discussione senza motivo tecnico nuovo. (Razionali qualitativi;
per i numeri esatti → result file indicati.)

- `is_claimed` è variabile **esplorativa**, mai target di classificazione (classe maggioritaria estrema).
- **Self-loop rimossi** dal grafo strutturale; catturati da `self_reply_rate`.
- **Subset analitico** = agenti nel grafo conversazionale (un agente fuori dal grafo non può
  essere coordinato). *NB: il conteggio nodi differisce tra subset feature e grafo RQ1 — vedi §10.*
- `MIN_COMMENTS_FOR_CRAWL = 3` (abbassato da 5 su indicazione relatore; soglia 1–2 scartata
  per errori HTTP 500 su post vuoti/eliminati).
- **RobustScaler senza clipping** — gli outlier sono segnale (hub del grafo), non rumore.
- `unique_targets`, `egonet_size` esclusi per ridondanza (corr. > 0.9999 con `out_degree`).
- **Feature di volume escluse dal clustering**: misurano *quanto*, non *come* (diagnosi del
  fallimento v2; cfr. `results_rq2.md`).
- **k-means** scelto dopo il fallimento di mutual k-NN; **IsolationForest** scelto su LOF per
  scalabilità in alta dimensionalità.
- SQLite sufficiente; nessuna migrazione a PostgreSQL.
- **Jaccard ≥ 0.3** come soglia di overlap RQ3, **fissata prima delle analisi**. Risultato:
  non soddisfatta (0/15); difesa via lift (metrica corretta con cluster di dimensioni variabili).
  *Terminologia: usare «soglia fissata a priori», NON «pre-registrata», salvo registrazione formale.*

---

## 7 — Stato notebook

| Notebook | Contenuto | Stato |
|---|---|---|
| `01_graph_analysis.ipynb` | esplorativo iniziale | **output obsoleti — NON rieseguire** |
| `02_popolazione_table_agent_feature.ipynb` | feature rete NetworkX → agent_features | COMPLETATO |
| `03_sanity_check_agent_features.ipynb` | data-quality sanity check | COMPLETATO |
| `04a_nan_investigation.ipynb` | verifica NaN strutturali | COMPLETATO |
| `04b_feature_matrix.ipynb` | costruzione feature matrix | COMPLETATO |
| `04c_scaling.ipynb` | RobustScaler | COMPLETATO |
| `05_structural_characterization.ipynb` | RQ1 | COMPLETATO → `docs/results_rq1.md` |
| `06_similarity_network.ipynb` | RQ2 (clustering) | COMPLETATO → `docs/results_rq2.md` |
| `07_cross_validation.ipynb` | RQ3 (OddBall + IsolationForest + Jaccard) | COMPLETATO → `docs/results_rq3.md` |
| `08_interpretive_analysis.ipynb` | nb08 (assortatività, NMI, η², fingerprint) | COMPLETATO → `docs/results_rq_interpretive.md` |
| `src/testQuery.ipynb` | esplorazione SQL ad-hoc | utility |

---

## 8 — Artefatti prodotti

| File | Contenuto |
|---|---|
| `data/feature_matrix_graph_v1.parquet` | (`agent_id` + 19 feature), zero NaN, post log-transform |
| `data/feature_matrix_scaled_v1.parquet` | stesso shape, scalato RobustScaler |
| `data/scaler_v1.joblib` | RobustScaler serializzato |
| `data/cluster_assignments_v1.parquet` | (`agent_id` UUID, `cluster_id`), k=15 |
| `data/similarity_network_v1.pkl` | union k-NN graph (cosine) |
| `docs/results_rq1.md` … `results_rq_interpretive.md` | result file (SSoT, vedi §0) |
| `figures/*.png` | figure per la tesi (mappa Cap → figura in §9) |

---

## 9 — Mappa tesi → fonti (per il lavoro di scrittura)

Contenuto e testo della tesi: **`main.tex`** (autoritativo). Per i numeri di ogni capitolo:

| Capitolo `main.tex` | RQ | Result file | Figure principali |
|---|---|---|---|
| Cap. 3 — Dataset e metodologia | — | query DB + `FEATURES.md` | `feature_matrix_heatmap`, `preprocessing_*` |
| Cap. 4 — Caratterizzazione strutturale | RQ1 | `results_rq1.md` | `05_degree_distribution_powerlaw`, `05_component_size_distribution`, `05_community_size_distribution`, `smallworld_visualization` |
| Cap. 5 — Clustering comportamentale | RQ2 | `results_rq2.md` + `results_rq_interpretive.md` (fingerprint, η²) | `06_kmeans_sweep`, `06_cluster_heatmap`, `06_cluster_pca`, `06_cluster_size_distribution`, `08_feature_importance`, `08_cluster_fingerprints` |
| Cap. 6 — Convergenza delle evidenze | RQ3 | `results_rq3.md` + `results_rq_interpretive.md` | `07_oddball_scatter`, `07_score_distribution_per_cluster`, `08_intercluster_flow`, `08_louvain_vs_kmeans` |
| Cap. 7–8 — Discussione e conclusioni | — | sintesi dai precedenti | — |

---

## 10 — Known issues / da risolvere prima della consegna

Problemi aperti. **Da risolvere alla fonte (notebook/result file) prima di propagarli a `main.tex`.**

1. **Lift IsolationForest per-cluster + top-K.** `results_rq3.md` riporta solo il lift max
   (21.13×, = C0). Mancano il valore di **C10** e il **top-K** usato. La tesi dice top-500/C10 17.80×,
   le slide top-100/C10 14.74×. **21.13× a top-500 è impossibile** (tetto teorico 18.17× per 213 nodi).
   → Rigenerare nb07, emettere lift per-cluster + K, scrivere in `results_rq3.md`.
2. **Lift intra-cluster C0/C10 (480×/455×).** Numeri di punta della tesi **non presenti** in
   `results_rq_interpretive.md` (che dà solo ratio 2.11×). → Rigenerare nb08, emettere il lift
   intra-cluster per cluster, scrivere nel result file.
3. **Gap nodi 9.096 vs 9.085.** 9.096 = subset feature matrix; 9.085 = nodi grafo RQ1. Ipotesi:
   11 agenti con soli self-loop escono dopo la rimozione. → Verificare in nb02/04b/05 e documentare.
4. **Epsilon log10.** `FEATURES.md` dice 1e-6; tesi (Appendice) dice 1e-8. → Leggere il valore reale
   in nb04b e uniformare ovunque.
5. **`claimed %` = 98.6%** (= 26.738/27.107). Correggere il «98.9%» in `FEATURES.md`. Documentare i
   due denominatori: unclaimed 1.4% sul totale (27k), 1.11% sul subset grafo (`results_rq3.md`).
6. **RQ4 (unclaimed per cluster).** Computata (`results_rq3.md`) ma **esclusa dalla tesi**.
   → Marcare nel result file «computata, non inclusa nella tesi».
7. **Silhouette / scelta k.** Il massimo globale è a **k=5 (0.389)**; k=15 è il massimo solo sotto
   il vincolo k≥8. → Dichiararlo esplicitamente nella tesi (Cap. 5), non presentarlo come massimo assoluto.
8. **Fingerprint cluster.** Verificati C0/C2/C3/C4/C5/C6/C8/C11/C12/C13/C14 contro
   `results_rq_interpretive.md`. Da ricontrollare C7 (`local_clustering` non nel top-5 del result file).
9. **Citazione Pacheco.** Usare `\citet{pacheco2021}` (Pacheco et al. 2021). «Pacheco & Nizzoli»
   è errato (due paper distinti) — residua in materiali storici/slide.
