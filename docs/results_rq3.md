# Risultati RQ3 — Cross-validation (giu 2026)

## Metodi

| Metodo | Tipo | Input |
|---|---|---|
| OddBall | Strutturale (ego-network) | Grafo conversazionale |
| IsolationForest | Feature-based | Feature matrix 19 dim |

## Criterio di successo

Soglia: Jaccard ≥ 0.3 su ≥ 3 cluster

| Metodo | Cluster che passano | Criterio soddisfatto |
|---|---|---|
| OddBall | 0/5 | NO |
| IsolationForest | 0/5 | NO |

## Jaccard — OddBall

|              |   K=100 |   K=200 |   K=500 |   K=1000 |
|:-------------|--------:|--------:|--------:|---------:|
| C0 (n=213)   |  0.0097 |  0.0147 |  0.0157 |   0.0341 |
| C1 (n=372)   |  0.0043 |  0.007  |  0.0235 |   0.0269 |
| C2 (n=386)   |  0.0041 |  0.0174 |  0.0219 |   0.0343 |
| C3 (n=392)   |  0.0061 |  0.0137 |  0.0183 |   0.0349 |
| C4 (n=2346)  |  0      |  0.0004 |  0.0078 |   0.0176 |
| C5 (n=421)   |  0.0276 |  0.0333 |  0.0419 |   0.0557 |
| C6 (n=659)   |  0.0271 |  0.054  |  0.0781 |   0.0943 |
| C7 (n=175)   |  0      |  0      |  0      |   0.0034 |
| C8 (n=172)   |  0.0074 |  0.0109 |  0.0166 |   0.0174 |
| C9 (n=432)   |  0      |  0.0016 |  0.0032 |   0.0106 |
| C10 (n=253)  |  0.0086 |  0.0157 |  0.0176 |   0.0407 |
| C11 (n=725)  |  0.016  |  0.0198 |  0.0426 |   0.0563 |
| C12 (n=518)  |  0.0422 |  0.0685 |  0.1089 |   0.1162 |
| C13 (n=1499) |  0.0082 |  0.0186 |  0.0605 |   0.0917 |
| C14 (n=533)  |  0      |  0      |  0      |   0.0046 |

## Jaccard — IsolationForest

|              |   K=100 |   K=200 |   K=500 |   K=1000 |
|:-------------|--------:|--------:|--------:|---------:|
| C0 (n=213)   |  0.1593 |  0.1733 |  0.1864 |   0.1509 |
| C1 (n=372)   |  0.0021 |  0.0053 |  0.0081 |   0.0096 |
| C2 (n=386)   |  0.0083 |  0.0191 |  0.0485 |   0.0811 |
| C3 (n=392)   |  0.0123 |  0.0332 |  0.076  |   0.1391 |
| C4 (n=2346)  |  0      |  0      |  0      |   0      |
| C5 (n=421)   |  0      |  0.0032 |  0.0199 |   0.0503 |
| C6 (n=659)   |  0.0026 |  0.007  |  0.0185 |   0.0349 |
| C7 (n=175)   |  0.0073 |  0.0218 |  0.0305 |   0.0389 |
| C8 (n=172)   |  0.0112 |  0.0136 |  0.0182 |   0.0254 |
| C9 (n=432)   |  0      |  0      |  0.0032 |   0.0085 |
| C10 (n=253)  |  0.1171 |  0.1736 |  0.1915 |   0.1656 |
| C11 (n=725)  |  0      |  0.0022 |  0.0033 |   0.0076 |
| C12 (n=518)  |  0      |  0      |  0.0079 |   0.0195 |
| C13 (n=1499) |  0      |  0      |  0.0005 |   0.0012 |
| C14 (n=533)  |  0.0032 |  0.0223 |  0.0716 |   0.0865 |

## NMI (K=500)

| Metodo | NMI |
|---|---|
| OddBall | 0.0187 |
| IsolationForest | 0.0595 |

## Lift max vs random baseline

| Metodo | Lift max | Cluster | K | Formula |
|---|---|---|---|---|
| OddBall | 4.53× | C12 | top-100 | Jaccard-based (vedi tabella per-cluster) |
| IsolationForest | 21.13× | C0 | top-100 | Jaccard-based (vedi tabella per-cluster) |

Baseline primaria = top-100. Valori a K diversi: vedi tabelle per-cluster sottostanti.

## Lift IsolationForest per-cluster (Jaccard-based)

N = 9096 (feature matrix). Top-K = primi K agenti per score decrescente (score = −iso.score_samples(X)).
Ordinato per lift@100 decrescente.

| Cluster | n | inter@100 | lift@100 | inter@200 | lift@200 | inter@500 | lift@500 |
|---------|--:|----------:|---------:|----------:|---------:|----------:|---------:|
| C0  | 213  | 43 | 21.13 | 61 | 15.11 | 112 | 11.16 |
| C10 | 253  | 37 | 14.74 | 67 | 13.97 | 121 | 10.18 |
| C8  | 172  |  3 |  1.60 |  5 |  1.32 |  12 |  1.28 |
| C3  | 392  |  6 |  1.39 | 19 |  2.25 |  63 |  3.07 |
| C7  | 175  |  2 |  1.04 |  8 |  2.10 |  20 |  2.11 |
| C2  | 386  |  4 |  0.94 | 11 |  1.30 |  41 |  1.98 |
| C14 | 533  |  2 |  0.34 | 16 |  1.37 |  69 |  2.45 |
| C6  | 659  |  2 |  0.27 |  6 |  0.41 |  21 |  0.57 |
| C1  | 372  |  1 |  0.24 |  3 |  0.37 |   7 |  0.34 |
| C4  | 2346 |  0 |  0.00 |  0 |  0.00 |   0 |  0.00 |
| C5  | 421  |  0 |  0.00 |  2 |  0.21 |  18 |  0.77 |
| C9  | 432  |  0 |  0.00 |  0 |  0.00 |   3 |  0.12 |
| C11 | 725  |  0 |  0.00 |  2 |  0.13 |   4 |  0.10 |
| C12 | 518  |  0 |  0.00 |  0 |  0.00 |   8 |  0.28 |
| C13 | 1499 |  0 |  0.00 |  0 |  0.00 |   1 |  0.01 |

**Finding:** le top-100 anomalie IsolationForest contengono 43 (C0) + 37 (C10) = **80 agenti su 100 (80%)**,
pur essendo C0∪C10 il 5.1% del totale (466/9096 agenti).
E_random[Jaccard] per C0@K=100 = 0.00754; osservato = 0.1593 → lift 21.13×.
E_random[Jaccard] per C10@K=100 = 0.00794; osservato = 0.1171 → lift 14.74×.

## Lift OddBall per-cluster (Jaccard-based)

N = 9096 (stesso universo: feature matrix, agenti fuori dal grafo hanno score OddBall = 0).
Top-K = primi K agenti per score OddBall decrescente (residuo log-log fit power-law ego-network).
Ordinato per lift@100 decrescente.

| Cluster | n | inter@100 | lift@100 | inter@200 | lift@200 | inter@500 | lift@500 |
|---------|--:|----------:|---------:|----------:|---------:|----------:|---------:|
| C12 | 518  | 25 | 4.53 | 46 | 4.25 | 100 | 3.78 |
| C5  | 421  | 14 | 3.08 | 20 | 2.20 |  37 | 1.63 |
| C6  | 659  | 20 | 2.81 | 44 | 3.15 |  84 | 2.42 |
| C11 | 725  | 13 | 1.64 | 18 | 1.13 |  50 | 1.27 |
| C0  | 213  |  3 | 1.29 |  6 | 1.28 |  11 | 0.94 |
| C10 | 253  |  3 | 1.08 |  7 | 1.26 |  13 | 0.94 |
| C8  | 172  |  2 | 1.06 |  4 | 1.06 |  11 | 1.16 |
| C13 | 1499 | 13 | 0.79 | 31 | 0.94 | 114 | 1.41 |
| C3  | 392  |  3 | 0.69 |  8 | 0.93 |  16 | 0.74 |
| C1  | 372  |  2 | 0.49 |  4 | 0.48 |  20 | 0.98 |
| C2  | 386  |  2 | 0.47 | 10 | 1.18 |  19 | 0.89 |
| C4  | 2346 |  0 | 0.00 |  1 | 0.02 |  22 | 0.16 |
| C7  | 175  |  0 | 0.00 |  0 | 0.00 |   0 | 0.00 |
| C9  | 432  |  0 | 0.00 |  1 | 0.10 |   3 | 0.12 |
| C14 | 533  |  0 | 0.00 |  0 | 0.00 |   0 | 0.00 |

**Nota:** C12 è il cluster con lift OddBall più alto (4.53× a top-100); C0 e C10 hanno lift OddBall
moderato (1.29× e 1.08×), confermando che la loro anomalia è più visibile nello spazio feature
(IsolationForest) che nella topologia locale (OddBall).

## NOTE — Definizioni e metadati

**Formula lift (Jaccard-based, uguale per entrambi i metodi):**
```
lift(Cj, K) = Jaccard(Cj, topK) / E_random[Jaccard(Cj, topK)]
E_random[Jaccard] = (n_c/N · K) / (n_c + K − n_c/N · K)
```
dove `n_c = |Cj|`, `K` = dimensione insieme anomalie, `N` = universo.

**Insieme anomalie:**
- IsolationForest: top-K agenti per score = −iso.score_samples(X), decrescente.
  300 estimators, contamination=0.10, random_state=42.
- OddBall: top-K agenti per score OddBall decrescente (residuo log-log ego-network).

**N usato nel Jaccard:**
- IsolationForest: N = 9096 (righe feature matrix scalata).
- OddBall: N = 9096 (stesso indice — oddball_scores è un array di lunghezza 9096,
  con score = 0 per agenti non presenti nel grafo conversazionale).
  Il grafo conversazionale ha ~9085 nodi; i ~11 agenti nel subset fuori dal grafo
  ricevono score OddBall = 0 e non compaiono mai nel top-K a K piccolo. Questo è atteso
  e non costituisce una contraddizione: entrambi i metodi condividono lo stesso universo.

**Baseline primaria = top-100.** I valori a K=200 e K=500 sono riportati per completezza.

**Finding di concentrazione (IsolationForest, top-100):**
Le top-100 anomalie contengono 43 agenti di C0 + 37 agenti di C10 = 80 su 100 (80%),
pur essendo C0∪C10 il 5.1% della popolazione (466/9096).

## RQ4 — Unclaimed per cluster

**Nota: RQ4 computata ma NON inclusa nella tesi (sezione eliminata).**

Baseline unclaimed: 1.11%

|   cluster_id |   n_agenti |   n_unclaimed |   pct_unclaimed |   lift_vs_baseline |
|-------------:|-----------:|--------------:|----------------:|-------------------:|
|            7 |        175 |            25 |           14.29 |              12.87 |
|            4 |       2346 |            62 |            2.64 |               2.38 |
|            9 |        432 |             8 |            1.85 |               1.67 |
|           11 |        725 |             4 |            0.55 |               0.5  |
|            0 |        213 |             1 |            0.47 |               0.42 |
|            3 |        392 |             1 |            0.26 |               0.23 |
|            2 |        386 |             0 |            0    |               0    |
|            6 |        659 |             0 |            0    |               0    |
|            5 |        421 |             0 |            0    |               0    |
|            1 |        372 |             0 |            0    |               0    |
|            8 |        172 |             0 |            0    |               0    |
|           10 |        253 |             0 |            0    |               0    |
|           12 |        518 |             0 |            0    |               0    |
|           13 |       1499 |             0 |            0    |               0    |
|           14 |        533 |             0 |            0    |               0    |
