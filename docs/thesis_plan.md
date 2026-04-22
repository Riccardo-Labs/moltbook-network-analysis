# Analisi strutturale di una rete sociale di agenti AI

## Il caso Moltbook

> **Documento guida operativo — Tesi Triennale**

| | |
|---|---|
| **Studente** | Riccardo — Informatica per la Comunicazione Digitale, Università degli Studi di Milano |
| **Supervisore** | Prof. Matteo Zignani |
| **Scadenza** | Luglio 2026 |
| **Versione documento** | v2.0 — Aprile 2026 (aggiornata allo stato reale del progetto) |
| **Scopo** | Documento guida operativo: fissa ciò che non cambia, lascia flessibile ciò che evolve con i risultati. |

---

## 1 — Titolo e framing

**Titolo di lavoro:** Pattern di coordinamento in un social network AI-native: analisi strutturale e multi-view di Moltbook.

**Perché questo oggetto è interessante.** Moltbook è un social network popolato esclusivamente da agenti AI, lanciato nel gennaio 2026 e acquisito da Meta nel marzo 2026. L'assenza di utenti umani elimina il problema classico della bot detection (distinguere bot da umani) e sposta il segnale discriminante dal livello semantico-lessicale — dove tutti producono testo generato da LLM — al livello strutturale del grafo conversazionale e dei ritmi temporali. Questa osservazione è il contributo originale difendibile in discussione.

---

## 2 — Research Questions

> **RQ principale (fissata)**
>
> In una rete sociale popolata esclusivamente da agenti AI, esistono gruppi di agenti che condividono pattern strutturali, temporali e comportamentali sufficientemente simili da suggerire coordinamento, e come si differenziano da agenti che operano indipendentemente?

### Sub-questions

| RQ | Domanda | Stato |
|---|---|---|
| **RQ1** | Qual è la struttura della rete conversazionale Moltbook e come si confronta con proprietà attese di social network umani? | Fissata |
| **RQ2** | Costruendo una similarity network multi-view sugli agenti, emergono cluster densi compatibili con ipotesi di coordinamento? | Fissata |
| **RQ3** | I cluster identificati sono stabili rispetto a metodi indipendenti (community detection vs anomaly detection)? | Fissata |
| **RQ4** | *(Esplorativa)* La proporzione di agenti unclaimed nei cluster sospetti si discosta dalla baseline dell'1.4%? | *Esplorativa* |

**Nota sul framing linguistico.** La formulazione «suggerire coordinamento» e «compatibili con ipotesi di coordinamento» è un hedging deliberato: non esiste ground truth verificabile, quindi non si afferma coordinamento, lo si identifica come firma strutturale.

---

## 3 — Criterio di successo e contributo originale

> **Criterio di successo minimo (fissato)**
>
> Almeno 3 cluster identificati da Louvain sulla similarity network trovano corrispondenza significativa in anomalie rilevate da OddBall/PyGOD sul grafo conversazionale. «Corrispondenza significativa» = overlap Jaccard ≥ 0.3 tra gli insiemi dei nodi dei cluster confrontati.

**Contributo originale dichiarato.** Le feature classiche di bot detection includono segnali lessicali-semantici (detector AI-vs-human, stilometria anti-LLM) che su Moltbook sono non informative: tutti gli agenti producono testo LLM-generated. La tesi identifica questa osservazione, ne deriva le conseguenze metodologiche, e costruisce una pipeline di rilevamento del coordinamento che opera esclusivamente sulle dimensioni strutturale, temporale e comportamentale. Il framework esistente (Pacheco & Nizzoli) viene adattato al contesto AI-native.

---

## 4 — Dataset e stato corrente

### Statistiche del dataset raccolto

| Metrica | Valore |
|---|---|
| Agenti totali | 27.107 |
| Post totali | 311.448 |
| Commenti totali | 794.814 |
| Archi conversazionali (reply edges) | 191.671 |
| Agenti claimed | 98,6% (~26.755) |
| Agenti unclaimed | 1,4% (~352) |
| Copertura temporale | 28 gennaio — 15 aprile 2026 |

### Subset analitico

Le analisi di rete (RQ1, RQ2, RQ3) sono condotte sul sottoinsieme di agenti effettivamente presenti nel grafo conversazionale: **9.096 agenti** (filtro: `in_degree ≥ 1` dopo rimozione dei self-loop). Gli ~18.000 agenti fuori dal grafo sono descritti separatamente come fenomeno marginale della piattaforma, non entrano nelle analisi ML.

### Stato di avanzamento (aprile 2026)

| Componente | Stato |
|---|---|
| Raccolta dati via crawler personalizzato (`crawler.py`, ~4 giorni) | Completato |
| Database SQLite con schema `agents`/`posts`/`comments` + indici | Completato |
| Estrattore feature per singolo agente (`feature.py`) esteso a 27k agenti | Completato |
| Feature di rete (NetworkX) calcolate sul grafo post rimozione self-loop | Completato |
| Sanity check feature + identificazione ridondanze + fix bug | Completato |
| Investigazione NaN per feature (verdetti documentati) | Completato |
| Feature matrix: filtraggio, imputazione, log-transform, scaling (RobustScaler) | Completato |
| Documentazione metodologica (`FEATURES.md`) | Completato |
| **Caratterizzazione strutturale (RQ1) — Fase A** | **Da avviare** |
| Similarity network + community detection (RQ2) — Fase B | *Pianificato* |
| Validazione cross-metodo (RQ3) — Fase C | *Pianificato* |
| Analisi esplorativa claimed/unclaimed (RQ4) — Fase D | *Pianificato* |

**Artefatti attualmente prodotti:** `feature_matrix_graph_v1.parquet` (9.096 × 20, raw con log-transform applicato), `feature_matrix_scaled_v1.parquet` (scalato con RobustScaler), `scaler_v1.joblib`. Il dettaglio tecnico delle 19 feature finali è in [`FEATURES.md`](./FEATURES.md).

---

## 5 — Vincoli e scelte metodologiche fissate

Le seguenti decisioni sono prese e non vengono rimesse in discussione salvo obiezione esplicita del supervisore. Sono le fondamenta metodologiche difendibili in sede di discussione.

### Vincolo API: cap di 300 commenti distinti per post

Gli endpoint pubblici restituiscono al massimo ~300 commenti per post (3 opzioni di sort × 100 commenti). Per post virali con migliaia di commenti, una frazione degli archi conversazionali non è catturata. Da documentare nel Capitolo 3 come limite metodologico dichiarato; da quantificare (percentuale di post > 300 commenti) come osservazione empirica.

### Claimed/unclaimed come variabile esplorativa, non target

Con 98,6% di classe maggioritaria e ambiguità semantica della label «unclaimed», il flag non è un target di classificazione affidabile. Decisione fissata: trattato come variabile correlazionale in RQ4, osservata a valle dei cluster identificati da RQ2. Nessun classificatore supervisionato claimed-vs-unclaimed.

### Subset analitico = 9.096 agenti nel grafo

Un agente non presente nel grafo conversazionale non può essere «coordinato» per definizione: esclusione semanticamente giustificata, non è filtraggio arbitrario.

### Self-loop rimossi dal grafo strutturale

I self-reply esistono (6,6% degli agenti attivi) ma sono catturati dalla feature dedicata `self_reply_rate`. Rimuoverli dal grafo rende PageRank e degree fedeli al loro significato semantico («popolarità ricevuta da altri»).

### RobustScaler, non StandardScaler

Le distribuzioni power-law degli hub rendono media e deviazione standard inaffidabili. Mediana e IQR sono robuste e preservano il segnale degli agenti estremi senza distorcere la scala della maggioranza. I valori estremi post-scaling (fino a ~13 in betweenness) non sono clippati: sono segnale, non rumore.

### Metrica di overlap per RQ3

Jaccard index tra cluster. Soglia minima accettabile: ≥ 0.3 per almeno 3 coppie di cluster. NMI tra le due partizioni come metrica secondaria. Fissata **ora**, prima di eseguire le analisi — non post-hoc.

---

## 6 — Indice della tesi (scaletta)

Struttura a 8 capitoli. Titoli fissati; contenuto dettagliato evolve con i risultati.

| Cap. | Titolo | Collegamento RQ |
|---|---|---|
| 1 | Introduzione | — |
| 2 | Background: bot detection, coordinated inauthentic behavior, social network AI-native | — |
| 3 | Dataset e metodologia | — |
| 4 | Caratterizzazione strutturale della rete Moltbook | RQ1 |
| 5 | Similarity network e identificazione di cluster | RQ2 |
| 6 | Validazione cross-metodo e analisi esplorativa | RQ3 + RQ4 |
| 7 | Discussione e limitazioni | — |
| 8 | Conclusioni e lavori futuri | — |

**Rischio noto:** il Capitolo 3 tende a diventare troppo denso (dataset, costruzione grafo, feature engineering, policy NaN, scaling, similarity network, tecniche di validazione). Mitigazione: spostare il dettaglio delle singole feature in Appendice A e mantenere nel capitolo solo le scelte metodologiche motivate.

---

## 7 — Piano operativo (aprile–luglio 2026)

| Periodo | Attività prioritaria |
|---|---|
| **Fine aprile 2026** | Fase A — Caratterizzazione strutturale (RQ1). Distribuzioni degree con fit power-law, statistiche globali, componenti connesse, Louvain sul grafo conversazionale. Deliverable: notebook 05 + bozza Capitolo 4 (5-8 pagine). |
| **Maggio 2026** | Fase B — Similarity network + community detection (RQ2). Sweep di configurazioni k-NN e threshold cosine, scelta motivata, Louvain con sensitivity analysis. Caratterizzazione dei cluster candidati. Deliverable: notebook 06 + bozza Capitolo 5. |
| **Inizio giugno 2026** | Fase C — Validazione cross-metodo (RQ3). OddBall implementato custom, PyGOD (DOMINANT) come secondo confronto. Calcolo Jaccard tra cluster e anomalie. Fase D — Analisi esplorativa claimed/unclaimed (RQ4). Deliverable: notebook 07 + bozza Capitolo 6. |
| **Fine giugno 2026** | Scrittura Capitoli 1, 2, 7, 8. Revisione capitoli precedenti. Sistemazione Appendici. |
| **Luglio 2026** | Revisione finale con supervisore, impaginazione, consegna. |

### Frequenza di sincronizzazione con il supervisore

Un meeting ogni 3-4 settimane, preparato: un risultato chiave, una decisione da validare, un blocco corrente. Durata target 20-30 minuti.

---

## 8 — Punti aperti da discutere con il supervisore

Decisioni che non vengono prese in autonomia ma richiedono validazione esplicita.

- **Baseline umana per RQ1.** Quale dataset di confronto per il Capitolo 4? Opzioni: SNAP Twitter, Reddit pubblico, o solo le metriche aggregate da Holtz (arXiv:2602.10131) come baseline Moltbook.
- **Uso di MoltGraph come ground truth parziale (RQ3).** Il dataset Mukherjee et al. (arXiv:2603.00646) contiene 5.479 episodi di coordinazione etichettati. Decisione da prendere dopo aver prodotto i cluster in autonomia: valutare se confrontare. In caso positivo, rinforza significativamente il contributo.
- **Confronto con Reddit (dal progetto di gruppo).** Conferma se rientra nello scope della tesi. Richiesto: mail diretta al supervisore per risposta binaria.

---

## 9 — Letteratura chiave

### Paper Moltbook (verificati)

| Riferimento | Rilevanza |
|---|---|
| Holtz (arXiv:2602.10131) | Baseline strutturale primi giorni Moltbook: α=1.70, reciprocity 0.197, path length 2.91 |
| Mukherjee et al. (arXiv:2603.00646) — MoltGraph | Dataset temporale con ground truth coordinazione (5.479 episodi) |
| Price et al. (arXiv:2602.20044) | Cap commenti documentato — contestualizza il vincolo API |
| De Marzo & Garcia (arXiv:2602.09270) | 369k post, 3M commenti — scala maggiore |
| Li (arXiv:2602.07432) | Separazione influence umana vs comportamento emergente |
| MoltNet (arXiv:2602.13458) | 148k agenti — struttura sociale AI-native |

### Riferimenti metodologici

| Metodo | Riferimento principale |
|---|---|
| Similarity network + CIB framework | Pacheco & Nizzoli |
| Bot detection paradigm shift | Cresci 2020, 2025 |
| OddBall — egonet anomaly | Akoglu et al. 2010, PAKDD |
| PyGOD / BOND benchmark | Liu et al. 2022, NeurIPS D&B |
| Burstiness | Goh & Barabási 2008, EPL 81:48002 |
| Community detection | Blondel et al. 2008 (Louvain) |

---

## Note sul documento

Questo documento è pensato come **documento vivo**. Gli elementi fissati (§2 RQ, §3 criterio di successo, §5 scelte metodologiche) non si modificano salvo obiezione del supervisore. Lo stato di avanzamento (§4), il piano operativo (§7) e i punti aperti (§8) si aggiornano ogni ~2 settimane.

---

*v2.0 — Aprile 2026 | Riccardo — Università degli Studi di Milano | Supervisore: Prof. Matteo Zignani*
