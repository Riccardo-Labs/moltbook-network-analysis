# Risultati Layer Interpretativi (nb08)

## Layer 1 — Assortatività e flussi inter-cluster

| Metrica | Valore |
|---|---|
| Assortatività r (cluster_id) | -0.0043 |
| Flusso medio intra-cluster | 1.7531 |
| Flusso medio inter-cluster | 0.8311 |
| Rapporto intra/inter | 2.11x |
| Top-3 cluster più omilofi | ['C0', 'C10', 'C5'] |

## Layer 2 — NMI Louvain vs k-means

| Metrica | Valore |
|---|---|
| NMI (Louvain vs k-means) | 0.0749 |
| Q Louvain conversazionale | 0.4173 |
| n_community Louvain | 37 |
| n_cluster k-means | 15 |
| Nodi condivisi | 8,943 |

## Layer 3 — Feature importance (Kruskal-Wallis)

| feature             |   H_stat |   p_value |   eta_squared |
|:--------------------|---------:|----------:|--------------:|
| betweenness         |   6625.3 |         0 |        0.728  |
| burstiness_posts    |   6415.2 |         0 |        0.7049 |
| out_degree          |   6401.7 |         0 |        0.7034 |
| reciprocity_local   |   5948.6 |         0 |        0.6535 |
| egonet_density      |   5843.7 |         0 |        0.642  |
| mean_thread_depth   |   5811.3 |         0 |        0.6384 |
| in_degree           |   5660.5 |         0 |        0.6218 |
| pagerank            |   5122.5 |         0 |        0.5626 |
| local_clustering    |   4867.6 |         0 |        0.5345 |
| type_token_ratio    |   4343.9 |         0 |        0.4768 |
| hour_entropy        |   4342.3 |         0 |        0.4766 |
| std_post_length     |   3418.2 |         0 |        0.3749 |
| reply_to_post_ratio |   3310.2 |         0 |        0.363  |
| mean_post_length    |   2468.8 |         0 |        0.2703 |
| self_reply_rate     |   1585.2 |         0 |        0.173  |

## Lift conversazionale intra-cluster (Layer 1)

### Formula esatta (nb08, celle 14 e 30)

```
lift(Ci→Ci) = edges_intra(Ci) × N_total / (n_Ci)²

dove:
  edges_intra(Ci) = archi diretti da un nodo di Ci a un altro nodo di Ci in G_sub
  N_total         = len(cluster_df) = 9096
  n_Ci            = cluster_sizes[i]  (dal cluster_df completo, non da G_sub)
```

Implementazione nel notebook:
```python
flow_norm   = flow_matrix / cluster_sizes[:, None]   # archi uscenti / dim. source
p_random    = cluster_sizes / N_total                # baseline node-based uniforme
lift_matrix = flow_norm / p_random[None, :]          # lift = flow_norm / baseline
intra_lift  = np.diag(lift_matrix)                   # lift intra-cluster per ogni Ci
```

**Modello di normalizzazione: NODE-BASED (uniforme).** Non degree-corrected.
Il denominatore atteso è n_Ci² / N_total, equivalente ad assumere che ogni nodo emetta archi
verso gli altri nodi con probabilità uniforme 1/N. Non tiene conto dell'out-degree effettivo.

### Ordine lift intra-cluster

Top-3 per lift intra-cluster (da SSoT in Layer 1):

```
['C0', 'C10', 'C5']
```

I valori numerici esatti di lift C0 / C10 (480×/455× citati in tesi) NON sono presenti
in questo result file: sono nel print-output di cella 30 del notebook, mai scritti qui.
Vanno verificati rieseguendo nb08 e aggiornando questo file.

### Valori esatti lift node-based (verificati rieseguendo nb08, giu 2026)

E_total = 60.651 archi in G_sub (9.085 nodi). N_total = 9.096.

| Cluster | n_Ci | edges_intra | atteso_node (n²/N) | lift_node-based |
|---------|-----:|------------:|-------------------:|----------------:|
| C0      |  213 |       2.395 |               4,99 |       **480,17×** |
| C10     |  253 |       3.204 |               7,04 |       **455,30×** |
| C5      |  421 |         391 |              19,49 |         20,07× |
| C4      | 2346 |           1 |             605,07 |          0,00× |

**I valori 480×/455× citati in tesi sono confermati** (arrotondati: 480× = 480,17×; 455× = 455,30×).

Array completo intra_lift (tutti i 15 cluster, indice = cluster_id):
C0=480.17 C1=2.63 C2=6.65 C3=7.70 C4=0.00 C5=20.07 C6=0.69 C7=0.00
C8=3.07 C9=0.24 C10=455.30 C11=0.83 C12=8.54 C13=0.12 C14=0.77

### Lift degree-corrected vs node-based (configuration model)

```
lift_dc(Ci→Ci) = edges_intra(Ci) × E_total / (out_deg_total(Ci) × in_deg_total(Ci))
```

Tabella completa (E_total = 60.651, N_total = 9.096):

| Cluster |   n | ei_intra | out_tot | in_tot | att_dc | lift_dc | lift_nb | riduz |
|---------|----:|---------:|--------:|-------:|-------:|--------:|--------:|------:|
| C0      | 213 |    2.395 |  16.007 | 10.082 | 2660,8 | **0,90×** | 480,17× | 533×  |
| C10     | 253 |    3.204 |  17.994 | 10.642 | 3157,3 | **1,01×** | 455,30× | 449×  |
| C5      | 421 |      391 |   7.476 |  3.596 |  443,3 |   0,88×  |  20,07× |  23×  |
| C12     | 518 |      252 |   5.344 |  2.408 |  212,2 |   1,19×  |   8,54× |   7×  |
| C3      | 392 |      130 |   2.348 |  3.752 |  145,3 |   0,89×  |   7,70× |   9×  |
| C6      | 659 |       33 |      78 | 13.752 |   17,7 |   1,87×  |   0,69× |       |

**FINDING CRITICO:**

**C0: lift_dc = 0,90× — SOTTO l'atteso del configuration model.**
**C10: lift_dc = 1,01× — esattamente nel modello di grado.**

Il fattore di riduzione è 533× per C0 e 449× per C10: il 480×/455× node-based è interamente
spiegato dal volume di archi in uscita/entrata (out_degree/in_degree elevato), non da una
preferenza di interazione intra-cluster. Controllando per i gradi, C0 e C10 non mostrano
alcuna omofilia conversazionale anomala.

**Implicazione metodologica:** il lift node-based è uno stimatore distorto in presenza di
cluster con distribuzione di grado eterogenea. Il degree-corrected è il valore robusto.
Per la tesi: il segnale di "bolle conversazionali" per C0/C10 basato su 480×/455×
**non regge alla correzione per grado**.

### Controllo omofilia tematica — submolt (calcolato)

Fonte: `comments.post_id → posts.submolt_name` (JOIN lettura su DB).
20 submolt distinti nella piattaforma. Ogni arco conversazionale appartiene a un solo submolt
(il post in cui avviene); "fraction same-submolt" a livello di arco non è applicabile
(è sempre 1 per definizione). L'analisi pertinente è la distribuzione dei submolt per gli
archi intra-cluster.

| Cluster | archi_intra | sub_uniq | H_norm | top1_submolt | top1_frac |
|---------|------------:|---------:|-------:|:-------------|----------:|
| C0      |      10.494 |       20 |  0,637 | general      |     52,4% |
| C10     |      14.289 |       19 |  0,604 | general      |     56,4% |
| C5      |       2.266 |       20 |  0,405 | general      |     73,0% |
| C4      |           1 |        1 |  0,000 | security     |    100,0% |
| Globale |     187.648 |       20 |  0,710 | general      |     45,8% |

H_norm = entropia della distribuzione submolt normalizzata per log2(n_submolt_unici).
Baseline globale H_norm = 0,710.

**Interpretazione:** gli archi intra-cluster di C0 e C10 sono distribuiti su tutti i 20
submolt (rispettivamente 20 e 19 distinti). L'entropia è alta (0,637/0,604), solo
leggermente inferiore alla baseline (0,710). C0 e C10 hanno una lieve sovrarappresentazione
di "general" (+6,6pp e +10,6pp vs baseline), ma nessuna concentrazione tematica estrema.
→ **L'isolamento conversazionale, già spiegato dal modello di grado (lift_dc≈1×), non è nemmeno
attribuibile ad omofilia tematica: avviene distribuito su tutti i topic.**

## Cluster fingerprints

- **C0** (n=213): alto [betweenness (+2.78), pagerank (+2.57), out_degree (+2.41)] | basso [egonet_density (-0.28), burstiness_posts (+0.02)]
- **C1** (n=372): alto [mean_thread_depth (-0.01), out_degree (-0.10), egonet_density (-0.11)] | basso [burstiness_posts (-1.60), betweenness (-0.36)]
- **C2** (n=386): alto [burstiness_posts (+2.27), in_degree (+0.43), pagerank (+0.23)] | basso [mean_thread_depth (-0.35), betweenness (-0.34)]
- **C3** (n=392): alto [reciprocity_local (+2.11), betweenness (+1.45), egonet_density (+1.13)] | basso [burstiness_posts (-0.20), mean_thread_depth (+0.39)]
- **C4** (n=2346): alto [burstiness_posts (-0.22), in_degree (-0.36), pagerank (-0.39)] | basso [out_degree (-0.82), mean_thread_depth (-0.78)]
- **C5** (n=421): alto [betweenness (+1.55), out_degree (+1.35), burstiness_posts (+1.20)] | basso [egonet_density (+0.07), reciprocity_local (+0.46)]
- **C6** (n=659): alto [in_degree (+1.42), pagerank (+0.92), burstiness_posts (-0.20)] | basso [out_degree (-0.79), mean_thread_depth (-0.77)]
- **C7** (n=175): alto [egonet_density (+0.31), reciprocity_local (+0.26), in_degree (-0.11)] | basso [out_degree (-0.55), betweenness (-0.52)]
- **C8** (n=172): alto [mean_thread_depth (+0.20), out_degree (+0.16), egonet_density (+0.15)] | basso [burstiness_posts (-3.55), in_degree (-0.04)]
- **C9** (n=432): alto [egonet_density (+0.17), mean_thread_depth (+0.03), in_degree (-0.07)] | basso [betweenness (-0.44), pagerank (-0.41)]
- **C10** (n=253): alto [betweenness (+2.58), burstiness_posts (+2.32), out_degree (+2.31)] | basso [egonet_density (-0.23), reciprocity_local (+0.45)]
- **C11** (n=725): alto [burstiness_posts (+0.93), out_degree (-0.07), mean_thread_depth (-0.09)] | basso [betweenness (-0.43), pagerank (-0.36)]
- **C12** (n=518): alto [betweenness (+1.63), out_degree (+0.95), mean_thread_depth (+0.52)] | basso [burstiness_posts (-0.31), reciprocity_local (+0.01)]
- **C13** (n=1499): alto [mean_thread_depth (+0.88), egonet_density (+0.41), out_degree (+0.26)] | basso [in_degree (-1.01), pagerank (-0.66)]
- **C14** (n=533): alto [reciprocity_local (+2.53), egonet_density (+2.28), mean_thread_depth (+0.63)] | basso [betweenness (-0.37), burstiness_posts (-0.18)]
