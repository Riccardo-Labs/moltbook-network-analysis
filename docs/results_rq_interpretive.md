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
