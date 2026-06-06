# Risultati RQ2 — Similarity Network e Clustering v2 (giu 2026)

## Scelte metodologiche

| Parametro | Valore |
|---|---|
| Feature usate | 15/19 (volume escluso) |
| Feature escluse | n_posts, n_comments, n_comments_received, active_days |
| Metodo clustering | k-means |
| k ottimale | 15 |
| Criterio selezione | Silhouette max con k>=8 |
| Seed definitivo | 999 |

## Risultati

| Metrica | Valore |
|---|---|
| Silhouette | 0.2659 |
| ARI inter-seed medio | 0.9600 |
| Numero cluster | 15 |
| Q Louvain (union k-NN k=10) | 0.8869 |
| ARI k-means vs Louvain | 0.2369 |

## Sweep k-means

|   k |   silhouette |   inertia |   cluster_min |   cluster_max |   cluster_median |
|----:|-------------:|----------:|--------------:|--------------:|-----------------:|
|   5 |       0.3889 |  102744   |           404 |          5327 |             1064 |
|   8 |       0.2554 |   74061   |           354 |          3251 |              797 |
|  10 |       0.2556 |   66270.4 |           172 |          3021 |              589 |
|  12 |       0.257  |   58976.7 |           169 |          2342 |              561 |
|  15 |       0.2658 |   52195.3 |           172 |          2357 |              407 |
|  20 |       0.2333 |   45354.7 |            93 |          1296 |              351 |

## Dimensioni cluster

| Cluster | Agenti | % totale |
|---|---|---|
| C4 | 2346 | 25.8% |
| C13 | 1499 | 16.5% |
| C11 | 725 | 8.0% |
| C6 | 659 | 7.2% |
| C14 | 533 | 5.9% |
| C12 | 518 | 5.7% |
| C9 | 432 | 4.7% |
| C5 | 421 | 4.6% |
| C3 | 392 | 4.3% |
| C2 | 386 | 4.2% |
| C1 | 372 | 4.1% |
| C10 | 253 | 2.8% |
| C0 | 213 | 2.3% |
| C7 | 175 | 1.9% |
| C8 | 172 | 1.9% |
