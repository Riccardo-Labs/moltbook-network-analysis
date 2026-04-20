"""
feature.py — Calcolo delle feature per agente e inserimento in agent_features.

Calcola tutte le feature derivabili via SQL (attività, temporali, comportamentali, testuali).
Le feature di rete (NetworkX) vengono calcolate separatamente in un notebook.
"""

import math
from datetime import datetime
from collections import Counter
from db import get_connection


def compute_agent_features(agent_name: str):
    """
    Calcola tutte le feature SQL-based per un singolo agente
    e le inserisce/aggiorna in agent_features.

    Args:
        agent_name: il name dell'agente (usato come chiave in posts/comments)
    """
    with get_connection() as conn:

        # ── Dati base dall'agente ─────────────────────────────────────────
        agent = conn.execute(
            "SELECT id, is_claimed FROM agents WHERE name = ?",
            (agent_name,)
        ).fetchone()

        if not agent:
            print(f"[SKIP] Agente '{agent_name}' non trovato in agents")
            return

        agent_id = agent["id"]
        is_claimed = agent["is_claimed"] or 0

        # ── Feature di attività ───────────────────────────────────────────
        n_posts = conn.execute(
            "SELECT COUNT(*) as n FROM posts WHERE author_name = ?",
            (agent_name,)
        ).fetchone()["n"]

        n_comments = conn.execute(
            "SELECT COUNT(*) as n FROM comments WHERE author_name = ?",
            (agent_name,)
        ).fetchone()["n"]

        # Commenti ricevuti: commenti il cui parent è un commento di questo agente
        n_comments_received = conn.execute("""
            SELECT COUNT(*) as n
            FROM comments c
            JOIN comments parent ON c.parent_id = parent.id
            WHERE parent.author_name = ?
        """, (agent_name,)).fetchone()["n"]

        # ── Feature temporali ─────────────────────────────────────────────
        # Raccogliamo tutti i timestamp di attività (post + commenti)
        timestamps_raw = conn.execute("""
            SELECT created_at FROM posts WHERE author_name = ? AND created_at IS NOT NULL
            UNION ALL
            SELECT created_at FROM comments WHERE author_name = ? AND created_at IS NOT NULL
        """, (agent_name, agent_name)).fetchall()

        timestamps = sorted([row["created_at"] for row in timestamps_raw])

        if timestamps:
            first_activity = timestamps[0]
            last_activity = timestamps[-1]
            # Giorni attivi: numero di date distinte
            active_days = len(set(t[:10] for t in timestamps))  # prende solo YYYY-MM-DD
        else:
            first_activity = None
            last_activity = None
            active_days = 0

        # Burstiness dei post: B = (σ - μ) / (σ + μ) sugli intervalli tra post
        post_times = conn.execute("""
            SELECT created_at FROM posts
            WHERE author_name = ? AND created_at IS NOT NULL
            ORDER BY created_at
        """, (agent_name,)).fetchall()

        burstiness_posts = None
        if len(post_times) >= 3:
            from datetime import datetime as dt
            intervals = []
            for i in range(1, len(post_times)):
                try:
                    t1 = dt.fromisoformat(post_times[i-1]["created_at"].replace("Z", "+00:00"))
                    t2 = dt.fromisoformat(post_times[i]["created_at"].replace("Z", "+00:00"))
                    diff = (t2 - t1).total_seconds()
                    if diff >= 0:
                        intervals.append(diff)
                except (ValueError, TypeError):
                    continue

            if len(intervals) >= 2:
                mean_interval = sum(intervals) / len(intervals)
                std_interval = (sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5
                denom = std_interval + mean_interval
                burstiness_posts = (std_interval - mean_interval) / denom if denom > 0 else None

        # Hour entropy: entropia della distribuzione oraria di attività
        hour_entropy = None
        if timestamps:
            hours = []
            for t in timestamps:
                try:
                    h = int(t[11:13])  # estrae HH da ISO 8601
                    hours.append(h)
                except (ValueError, IndexError):
                    continue

            if hours:
                counts = Counter(hours)
                total = sum(counts.values())
                probs = [c / total for c in counts.values()]
                entropy = -sum(p * math.log2(p) for p in probs if p > 0)
                # Normalizza per log2(24) così il range è [0, 1]
                hour_entropy = entropy / math.log2(24)

        # ── Feature comportamentali ───────────────────────────────────────
        # Reply-to-post ratio
        reply_to_post_ratio = n_comments / n_posts if n_posts > 0 else None

        # Self-reply rate: quanti dei propri commenti sono risposte a se stesso
        self_replies = conn.execute("""
            SELECT COUNT(*) as n
            FROM comments c
            JOIN comments parent ON c.parent_id = parent.id
            WHERE c.author_name = ? AND parent.author_name = ?
        """, (agent_name, agent_name)).fetchone()["n"]

        comments_with_parent = conn.execute("""
            SELECT COUNT(*) as n FROM comments
            WHERE author_name = ? AND parent_id IS NOT NULL
        """, (agent_name,)).fetchone()["n"]

        self_reply_rate = self_replies / comments_with_parent if comments_with_parent > 0 else None

        # Unique targets: a quanti agenti diversi ha risposto
        unique_targets = conn.execute("""
            SELECT COUNT(DISTINCT parent.author_name) as n
            FROM comments c
            JOIN comments parent ON c.parent_id = parent.id
            WHERE c.author_name = ? AND parent.author_name != ?
        """, (agent_name, agent_name)).fetchone()["n"]

        # Mean thread depth
        depth_row = conn.execute("""
            SELECT AVG(depth) as mean_depth FROM comments
            WHERE author_name = ? AND depth IS NOT NULL
        """, (agent_name,)).fetchone()

        mean_thread_depth = depth_row["mean_depth"]

        # ── Feature testuali leggere ──────────────────────────────────────
        # Lunghezza dei post
        post_lengths = conn.execute("""
            SELECT LENGTH(content) as len FROM posts
            WHERE author_name = ? AND content IS NOT NULL
        """, (agent_name,)).fetchall()

        if post_lengths:
            lengths = [row["len"] for row in post_lengths]
            mean_post_length = sum(lengths) / len(lengths)
            if len(lengths) >= 2:
                std_post_length = (sum((x - mean_post_length) ** 2 for x in lengths) / len(lengths)) ** 0.5
            else:
                std_post_length = 0.0
        else:
            mean_post_length = None
            std_post_length = None

        # Type-token ratio: vocabolario unico / totale parole (su post + commenti)
        texts = conn.execute("""
            SELECT content FROM posts WHERE author_name = ? AND content IS NOT NULL
            UNION ALL
            SELECT content FROM comments WHERE author_name = ? AND content IS NOT NULL
        """, (agent_name, agent_name)).fetchall()

        type_token_ratio = None
        if texts:
            all_words = []
            for row in texts:
                all_words.extend(row["content"].lower().split())
            if all_words:
                type_token_ratio = len(set(all_words)) / len(all_words)

        # ── INSERT in agent_features ──────────────────────────────────────
        conn.execute("""
            INSERT OR REPLACE INTO agent_features (
                agent_id, computed_at, feature_version,
                n_posts, n_comments, n_comments_received,
                first_activity, last_activity, active_days,
                burstiness_posts, hour_entropy,
                reply_to_post_ratio, self_reply_rate, unique_targets, mean_thread_depth,
                mean_post_length, std_post_length, type_token_ratio,
                is_claimed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id, datetime.now().isoformat(), "1.0",
            n_posts, n_comments, n_comments_received,
            first_activity, last_activity, active_days,
            burstiness_posts, hour_entropy,
            reply_to_post_ratio, self_reply_rate, unique_targets, mean_thread_depth,
            mean_post_length, std_post_length, type_token_ratio,
            is_claimed,
        ))

    print(f"[OK] {agent_name}: {n_posts} post, {n_comments} commenti, {unique_targets} target unici")


# ── Main: processa tutti gli agenti ──────────────────────────────────────────

if __name__ == "__main__":
    with get_connection() as conn:
        agents = conn.execute("SELECT name FROM agents").fetchall()

    total = len(agents)
    print(f"Calcolo feature per {total} agenti...\n")

    for i, row in enumerate(agents, 1):
        compute_agent_features(row["name"])
        if i % 500 == 0:
            print(f"  → {i}/{total} completati")

    print(f"\nDone. {total} agenti processati.")
