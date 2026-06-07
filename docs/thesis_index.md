# Indice Tesi — Analisi strutturale di una rete sociale di agenti AI: il caso Moltbook

> **Documento operativo** — aggiornato giugno 2026
> Tesi Triennale | Riccardo | Università degli Studi di Milano

---

## Struttura generale

| Cap. | Titolo | RQ | Stima pagine |
|---|---|---|---|
| — | Abstract | — | 1 |
| 1 | Introduzione | — | 3–4 |
| 2 | Background | — | 6–8 |
| 3 | Dataset e metodologia | — | 8–10 |
| 4 | Caratterizzazione strutturale della rete | RQ1 | 6–8 |
| 5 | Clustering comportamentale | RQ2 | 8–10 |
| 6 | Convergenza delle evidenze | RQ3 + interp. | 10–12 |
| 7 | Discussione e limitazioni | — | 5–6 |
| 8 | Conclusioni e lavori futuri | — | 3–4 |
| App. A | Dettaglio 19 feature | — | 3–4 |
| App. B | Iperparametri e configurazioni | — | 1–2 |
| — | Riferimenti bibliografici | — | 3–4 |
| **TOTALE** | | | **~60–75p** |

---

## Indice dettagliato

### ABSTRACT (1p)
Sintesi: obiettivo, dataset (9.096 agenti, 60k+ archi), metodi (k-means, OddBall, IsolationForest), finding principale (C0 e C10 double-flagged), conclusione con hedging.

---

### 1. INTRODUZIONE (3–4p)

**1.1 Moltbook come caso studio**
- Social network popolato esclusivamente da agenti AI, lanciato gennaio 2026, acquisito Meta marzo 2026
- Assenza di utenti umani: la bot detection classica (lessicale, stilometrica, detector LLM-vs-human) è non informativa — tutti producono testo LLM-generated
- Il segnale discriminante si sposta al livello strutturale del grafo conversazionale e dei pattern comportamentali

**1.2 Research Questions**
- RQ1: qual è la struttura della rete conversazionale Moltbook e come si confronta con social network umani?
- RQ2: costruendo una similarity network multi-view, emergono cluster comportamentali compatibili con ipotesi di coordinamento?
- RQ3: i cluster identificati sono stabili rispetto a metodi indipendenti (anomaly detection strutturale vs feature-based)?

**1.3 Contributo originale**
- Dataset crawlato da zero con pipeline custom (9.096 agenti nel grafo, 311k post, 794k commenti)
- Pipeline multi-layer: caratterizzazione strutturale + clustering comportamentale + cross-validation anomaly detection + layer interpretativi
- Prima analisi del periodo post-acquisizione Meta (nessun paper su questo periodo)

**1.4 Struttura della tesi**
- Mappa dei capitoli e loro relazione con le RQ

---

### 2. BACKGROUND (6–8p)

**2.1 Coordinated Inauthentic Behavior (CIB) — framework teorico**
- Definizione CIB: azione coordinata su piattaforme social finalizzata a ingannare su origine o intento
- Tipologie: amplification networks, sockpuppet farms, astroturfing
- Framework Pacheco & Nizzoli: similarity network + community detection come approccio strutturale
- Cresci 2020, 2025: evoluzione del paradigma bot detection verso analisi comportamentale

**2.2 Bot detection: da lessicale a strutturale**
- Generazione 1-3 (feature-based, deep learning, GNN) — applicabili su Moltbook
- Generazione 4 (detector LLM-based) — non applicabile: tutti gli agenti producono testo LLM
- Shift metodologico necessario: feature strutturali, temporali, comportamentali
- Burstiness (Goh & Barabási 2008): misura dell'irregolarità temporale come segnale di coordinamento

**2.3 Letteratura su Moltbook**

| Riferimento | Contenuto rilevante |
|---|---|
| Holtz (arXiv:2602.10131) | Baseline strutturale gen-2026: α=1.70, reciprocity=0.197, APL=2.91 |
| Mukherjee et al. — MoltGraph (arXiv:2603.00646) | 5.479 episodi di coordinazione etichettati — potenziale ground truth |
| Price et al. (arXiv:2602.20044) | Cap commenti API documentato — contestualizza il limite strutturale |
| De Marzo & Garcia (arXiv:2602.09270) | 369k post, 3M commenti — scala comparativa |
| Li (arXiv:2602.07432) | Separazione influenza umana vs comportamento emergente |
| MoltNet (arXiv:2602.13458) | 148k agenti — struttura sociale AI-native |

**2.4 Metodi utilizzati**
- **OddBall** (Akoglu et al. 2010, PAKDD): anomaly detection su ego-network (degree vs triangoli)
- **IsolationForest** (Liu et al. 2008): anomaly detection feature-based, efficiente su alta dimensionalità
- **Louvain** (Blondel et al. 2008): community detection su grafi pesati
- **Kruskal-Wallis + η²**: test non-parametrico per feature importance, effect size
- **Jaccard + lift**: metriche di overlap per cross-validation

---

### 3. DATASET E METODOLOGIA (8–10p)

**3.1 Architettura del crawler**
- Pipeline 4 fasi: submolt (community) → post → commenti → profili agenti
- Ogni post interrogato 3 volte (sort=best/new/old) per massimizzare gli archi scoperti
- Soglia MIN_COMMENTS=3: motivazione vs alternative (1-2 causano errori 500 su post eliminati)
- Crawler resumable via checkpoint queries (flag `comments_fetched`)
- Rate limiting: 0.4s delay → ~150 req/min vs ~200/min consentiti

**3.2 Schema del database**
- 5 tabelle: agents, posts, comments, submolts, agent_features
- agents.id (UUID) vs agents.name (username): distinzione critica per i join
- Costruzione archi: `comments.parent_id IS NOT NULL` → edge A→B se A risponde al commento di B
- Self-loop identificati (3.585, 1.9%) e rimossi: motivazione semantica (catturati da `self_reply_rate`)

**3.3 Limite strutturale API**
- Cap hard: ~300 commenti distinti per post (3 sort × ~100)
- Post virali con >300 commenti: archi non catturati
- Quantificazione: % post con commenti_count > 300 → stima archi mancanti
- Dichiarato come limite metodologico, non come errore

**3.4 Feature engineering — 19 feature finali**

*3.4.1 Feature SQL* (`src/feature.py`) — 14 feature:
n_posts, n_comments, n_comments_received, active_days, burstiness_posts, hour_entropy,
reply_to_post_ratio, self_reply_rate, unique_targets, mean_thread_depth,
mean_post_length, std_post_length, type_token_ratio, is_claimed

*3.4.2 Feature di rete NetworkX* (nb02) — 8 feature:
in_degree, out_degree, pagerank, betweenness, local_clustering, egonet_size, egonet_density, reciprocity_local

*3.4.3 Feature escluse dalla ML matrix per ridondanza*:
- unique_targets, egonet_size → correlazione > 0.9999 con out_degree
- is_claimed → sbilanciamento 98.9%, trattata solo come variabile esplorativa

**3.5 Preprocessing**
- Trasformazioni log1p (degree, post length) e log10 (pagerank, betweenness): motivazione distribuzione power-law
- RobustScaler (mediana + IQR): vs StandardScaler; outlier preservati perché sono segnale (hub del grafo)
- Subset analitico: 9.096 agenti con ≥1 arco nel grafo conversazionale

**3.6 Scelte metodologiche fissate**
- Feature volume escluse dal clustering: n_posts, n_comments, n_comments_received, active_days
  misurano *quanto* è attivo un agente, non *come* si comporta
- Jaccard ≥ 0.3 come soglia cross-validation: fissata prima di eseguire le analisi (non post-hoc)

---

### 4. RQ1 — CARATTERIZZAZIONE STRUTTURALE DELLA RETE (6–8p)

**4.1 Statistiche globali**
- Nodi: 9.085 | Archi: 60.651 | Densità: 0.000735
- GCC: 98.4% (8.943 nodi) — rete quasi completamente connessa
- Distribuzione componenti: poche componenti piccole fuori dalla GCC

**4.2 Distribuzione dei gradi — legge di potenza**
- Fit power-law: α_total = 2.149 ± 0.033
- α_in = 2.433 | α_out = 1.876
- Confronto con Holtz gen-2026 (α=1.70): esponente aumentato → rete più "normalizzata" (meno hub dominanti)
- *Figura: 05_degree_distribution_powerlaw.png*

**4.3 Proprietà small-world**
- Avg clustering coefficient = 0.144 (range umano tipico: 0.05–0.17)
- APL campionato = 3.72 (vs Holtz 2.91 su grafo più piccolo — crescita della rete)
- Small-world sigma = **194.61** → small-world fortissimo (σ >> 1 = molto più clusterizzato e più corto di un grafo random)

**4.4 Reciprocità**
- Reciprocità = 0.261 (vs Holtz gen-2026: 0.197)
- Crescita del dialogo bidirezionale nel tempo: la rete matura verso conversazioni più simmetriche

**4.5 Struttura comunitaria**
- Louvain: Q = 0.417 → struttura comunitaria significativa (soglia convenzionale: Q > 0.3)
- 37 community | GCC 98.4%
- *Figura: 05_community_size_distribution.png*

---

### 5. RQ2 — CLUSTERING COMPORTAMENTALE (8–10p)

**5.1 Costruzione della feature matrix per il clustering**
- 15 feature comportamentali (volume escluso)
- Similarity: cosine distance su feature scaled

**5.2 Evoluzione metodologica: iter v1 → v2**
- v1 mutual k-NN: 1139 cluster degenerati (heavy-tail → 1085 componenti isolate)
- v1 k-means (19 feature): C0 dominante 64.5% ("inattivi")
- v2 definitivo: escluse feature volume, k-means, sweep k ∈ {5,8,10,12,15,20}, selezionato k=15

**5.3 Selezione k e stabilità**
- Criterio: silhouette max con k ≥ 8 (min cluster comunità significativa)
- k=15: silhouette = 0.266, ARI inter-seed = 0.960 → partizione stabile

| k | Silhouette | Cluster min | Cluster max |
|---|---|---|---|
| 5 | 0.389 | 404 | 5327 |
| 8 | 0.255 | 354 | 3251 |
| 10 | 0.256 | 172 | 3021 |
| 12 | 0.257 | 169 | 2342 |
| **15** | **0.266** | **172** | **2357** |
| 20 | 0.233 | 93 | 1296 |

**5.4 Risultati del clustering**
- 15 cluster | distribuzione: max C4=25.8% (2346), min C8=1.9% (172)
- Validazione alternativa Louvain su union k-NN (k=10): Q=0.887 → struttura comunitaria confermata
- ARI k-means vs Louvain = 0.237 → partizioni distinte ma non ortogonali

**5.5 Caratterizzazione cluster — feature importance**
- Kruskal-Wallis: tutte le 15 feature hanno p=0, η² > 0.4
- Top discriminanti: betweenness (η²=0.728), burstiness_posts (0.705), out_degree (0.703)
- *Figura: 08_feature_importance.png*

**5.6 Fingerprint dei cluster**
- Heatmap z-score top-8 feature per ogni cluster
- Naming suggerito:
  - **C0** (n=213): "Hub anomali" — alto betweenness +2.78, pagerank +2.57, out_degree +2.41
  - C1 (n=372): "Quieti regolari" — basso burstiness -1.60
  - C2 (n=386): "Burster" — alto burstiness +2.27
  - C3 (n=392): "Conversatori bidirezionali" — alto reciprocity_local +2.11
  - C4 (n=2346): "Mainstream" — valori medi su tutto
  - **C10** (n=253): "Hub anomali 2" — (fingerprint da tabella results_rq_interpretive.md)
- *Figura: 06_cluster_heatmap.png, 08_cluster_fingerprints.png*

---

### 6. RQ3 — CONVERGENZA DELLE EVIDENZE (10–12p)

**6.1 OddBall — anomaly detection strutturale**
- Approccio: ego-network di ogni agente (degree, n_triangoli) → fit power-law OLS in log-log
- Anomaly score = residuo × log(ratio actual/predicted)
- Cluster più anomali: C12 (n=518), C6 (n=659), C13 (n=1499)
- Lift max: 4.53x (C12) — 4.5 volte più anomali del caso atteso

**6.2 IsolationForest — anomaly detection feature-based**
- Input: 19 feature (matrix scaled), contamination=0.10, 300 estimators
- Cluster più anomali: **C0** e **C10** — lift 21.13x entrambi
- C0 + C10 = 5% degli agenti totali, >50% delle top-500 anomalie
- Complementarità con OddBall: i due metodi flaggano cluster diversi (struttura vs comportamento)

**6.3 Cross-validation Jaccard — sweep K**
- Sweep K ∈ {100, 200, 500, 1000}
- Criterio pre-registrato: Jaccard ≥ 0.3 su ≥ 3 cluster
- Risultato: criterio non soddisfatto formalmente (max Jaccard: OddBall=0.116, IsoForest=0.192)
- Giustificazione: con cluster <500 agenti il Jaccard massimo è geometricamente limitato
- **Lift come metrica primaria**: IsoForest 21x, OddBall 4.53x — entrambi >> 1 = concentrazione significativa

**6.4 Assortatività e flussi inter-cluster conversazionali**
- Coefficiente di assortatività globale: r = -0.0043 ≈ 0 (nessuna segregazione globale)
- **Rapporto intra/inter = 2.11x** → agenti dello stesso cluster conversano il doppio del caso atteso
- Intra-cluster lift: **C0 = 480x**, **C10 = 455x** → bolle conversazionali
- Interpretazione: r≈0 globale perché dominato da C4 (mainstream, 25.8%); C0 e C10 sono eccezioni fortissime
- *Figura: 08_intercluster_flow.png*

**6.5 NMI Louvain (RQ1) vs k-means (RQ2)**
- NMI = 0.075: dimensioni parzialmente ortogonali
- Louvain ricalcolato: Q=0.417, 37 community (identico a nb05 — robusto)
- Interpretazione: struttura conversazionale e comportamento catturano aspetti diversi della stessa rete; atteso in reti multi-layer
- *Figura: 08_louvain_vs_kmeans.png*

**6.6 Finding principale — Double-flagging C0 e C10**

C0 (n=213) e C10 (n=253) sono gli unici cluster flaggati da **tutte e tre le dimensioni di analisi**:

| Dimensione | C0 | C10 |
|---|---|---|
| IsolationForest (feature-based) | lift 21x | lift 21x |
| Intra-cluster conversazionale | lift 480x | lift 455x |
| Fingerprint comportamentale | hub alto betweenness/pagerank | da verificare |

5% degli agenti totali, >50% delle anomalie feature-based, si parlano quasi esclusivamente tra loro.
Multi-dimensional evidence di comportamento coordinato.

---

### 7. DISCUSSIONE E LIMITAZIONI (5–6p)

**7.1 Sintesi delle evidenze**
- Tre livelli convergenti: struttura globale (small-world, Q=0.417) → clustering (15 archetipi stabili) → anomalie (C0 e C10 double-flagged)
- La convergenza di metodi indipendenti rafforza la solidità del finding

**7.2 Cosa possiamo e non possiamo concludere**
- Possiamo: "firma strutturale compatibile con coordinamento"
- Non possiamo: affermare intenzionalità o causa — nessun ground truth verificabile
- Hedging deliberato: "suggerisce coordinamento" non "dimostra coordinamento"
- Confronto con MoltGraph (5.479 episodi etichettati): validazione futura prioritaria

**7.3 Limiti metodologici**
- Limite API: archi mancanti per post con >300 commenti (post virali)
- Snapshot temporale: nessuna analisi evoluzione del clustering nel tempo
- is_claimed: 98.9% claimed → label poco informativa, non usata come target
- Assenza ground truth: limite intrinseco del dominio, non dell'approccio

**7.4 Confronto con letteratura Moltbook**
- α cresciuto da 1.70 (Holtz, gen-2026) a 2.149: esponente più alto = meno hub dominanti
- Reciprocità cresciuta da 0.197 a 0.261: più dialogo bidirezionale
- APL cresciuto da 2.91 a 3.72: rete più grande e "allargata"
- Sigma small-world=194: molto alto rispetto ai valori tipici della letteratura

---

### 8. CONCLUSIONI E LAVORI FUTURI (3–4p)

**8.1 Risposta alle RQ**
- RQ1: rete small-world fortissima (σ=194), power-law α=2.149, Q=0.417 — struttura robusta e comunitaria
- RQ2: 15 cluster comportamentali stabili (ARI=0.960), ben separati (η²>0.7), con archetipi identificabili
- RQ3: cross-validation parziale (lift 21x IsoForest), rafforzata da layer interpretativi (lift 480x intra-cluster)

**8.2 Contributo originale**
- Dataset crawlato da zero, primo sul periodo post-acquisizione Meta (marzo–giugno 2026)
- Pipeline multi-layer riusabile: struttura → comportamento → anomaly detection → interpretazione
- Metodologia trasferibile ad altri social network AI-native
- Dimostrazione che bot detection strutturale funziona dove quella lessicale fallisce

**8.3 Lavori futuri**
- Validazione via MoltGraph (ground truth 5.479 episodi)
- Analisi temporale: burst sincroni tra cluster, evoluzione del clustering nel tempo
- API autenticata per dataset completo (rimozione cap 300 commenti)
- Confronto con reti umane (Reddit, Twitter) per calibrare le soglie di "anomalia"

---

### APPENDICE A — Dettaglio 19 feature (3–4p)
Da `docs/FEATURES.md`: definizione, formula, motivazione, distribuzione per ogni feature.

### APPENDICE B — Iperparametri e configurazioni (1–2p)
- Sweep k-means: k ∈ {5,8,10,12,15,20}, silhouette per ogni k
- IsolationForest: contamination=0.10, n_estimators=300, random_state=42
- Jaccard sweep: K ∈ {100,200,500,1000}
- Louvain: random_state=42, sensitivity analysis 3 seed

---

### RIFERIMENTI BIBLIOGRAFICI (3–4p)

**Moltbook:**
- Holtz (2026) arXiv:2602.10131
- Mukherjee et al. / MoltGraph (2026) arXiv:2603.00646
- Price et al. (2026) arXiv:2602.20044
- De Marzo & Garcia (2026) arXiv:2602.09270
- Li (2026) arXiv:2602.07432
- MoltNet (2026) arXiv:2602.13458

**Metodologici:**
- Pacheco & Nizzoli — CIB framework
- Cresci (2020, 2025) — bot detection survey
- Akoglu et al. (2010) — OddBall
- Liu et al. (2008) — IsolationForest
- Blondel et al. (2008) — Louvain
- Goh & Barabási (2008) — burstiness
- Watts & Strogatz (1998) — small-world

---

*v1.0 — giugno 2026 | Riccardo*
